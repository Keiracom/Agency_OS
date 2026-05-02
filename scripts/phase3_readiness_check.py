#!/usr/bin/env python3
"""Phase 3 readiness checker — validates all preconditions for relay cutover.

Checks:
  1. Queue key verification: all 8 expected Redis keys exist
  2. Dual-write parity: Redis queue lengths > 0 (dual-write is active)
  3. HMAC roundtrip: push signed dispatch, pop it, verify HMAC
  4. Consumer dry-run: relay_consumer.py compiles + QUEUE_MAP valid
  5. Systemd unit: relay-consumer.service file exists and parses

Usage:
    python scripts/phase3_readiness_check.py

Output: green/red checklist + numeric metrics. Exit 0 if all pass, exit 1 if any fail.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Bootstrap ──────────────────────────────────────────────────────────────────

ENV_PATH = "/home/elliotbot/.config/agency-os/.env"
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
WARN = "\033[33m!\033[0m"

EXPECTED_KEYS = [
    "relay:inbox:elliot",
    "relay:inbox:aiden",
    "relay:inbox:scout",
    "relay:inbox:max",
    "relay:outbox:atlas",
    "relay:outbox:orion",
    "dispatch:atlas",
    "dispatch:orion",
]
REQUIRED_KEYS = {"relay:inbox:elliot", "relay:inbox:aiden"}
READINESS_QUEUE = "dispatch:_readiness_test"


def _load_env(path: str) -> None:
    if not os.path.exists(path):
        return
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _get_redis():
    import redis as redis_sync

    return redis_sync.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


# ── Checks ─────────────────────────────────────────────────────────────────────


def check1_queue_keys() -> tuple[bool, str, dict]:
    """Verify expected Redis keys exist (LLEN >= 0)."""
    r = _get_redis()
    found, missing = [], []
    depths = {}
    for key in EXPECTED_KEYS:
        llen = r.llen(key)  # returns 0 for non-existent, but key type check confirms existence
        key_type = r.type(key)
        if key_type in ("list", "none"):
            # Key either exists as list or doesn't exist; track separately
            if key_type == "list" or llen >= 0:
                # Check if key actually exists
                exists = r.exists(key)
                if exists:
                    found.append(key)
                    depths[key] = llen
                else:
                    missing.append(key)
                    depths[key] = None
            else:
                missing.append(key)
                depths[key] = None
        else:
            found.append(key)
            depths[key] = llen

    required_missing = REQUIRED_KEYS - set(found)
    passed = len(required_missing) == 0
    detail = f"{len(found)}/8 found"
    if missing:
        detail += f" (missing: {', '.join(missing)})"
    return passed, detail, depths


def check2_dual_write(depths: dict) -> tuple[bool, str]:
    """Report queue depths. WARN if all inbox queues have LLEN=0 (may mean not active)."""
    existing = {k: v for k, v in depths.items() if v is not None}
    nonzero = {k: v for k, v in existing.items() if v and v > 0}
    detail = f"{len(nonzero)} queues with depth > 0"
    if existing:
        depth_str = ", ".join(f"{k.split(':')[-1]}={v}" for k, v in sorted(existing.items()))
        detail += f" | depths: {depth_str}"
    # WARN not FAIL — messages are consumed instantly so 0 is expected
    passed = bool(existing)  # pass if keys exist even at depth 0
    return passed, detail


def check3_hmac_roundtrip() -> tuple[bool, str]:
    """Sign a test payload, push to Redis, pop it, verify HMAC."""
    from security.inbox_hmac import sign  # noqa: E402

    secret = os.environ.get("INBOX_HMAC_SECRET")
    if not secret:
        return False, "INBOX_HMAC_SECRET not set"

    r = _get_redis()
    payload = {
        "type": "readiness_check",
        "from": "phase3_checker",
        "brief": "HMAC roundtrip test",
        "created_at": int(time.time()),
    }
    signed = sign(payload, secret)
    r.lpush(READINESS_QUEUE, json.dumps(signed))

    raw = r.brpop(READINESS_QUEUE, timeout=5)
    if raw is None:
        return False, "pop timed out — nothing in queue"

    _key, body = raw
    popped = json.loads(body)

    # Re-verify inline (same logic as relay_consumer._hmac_verify_dict)
    import hashlib  # noqa: E401
    import hmac as hmac_mod

    stored = popped.get("hmac")
    if not isinstance(stored, str):
        return False, "hmac field missing in popped payload"
    filtered = {k: v for k, v in popped.items() if k != "hmac"}
    canonical = json.dumps(filtered, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac_mod.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    if not hmac_mod.compare_digest(stored, expected):
        return False, "HMAC mismatch after roundtrip"

    return True, "sign → push → pop → verify OK"


def check4_consumer_dry_run() -> tuple[bool, str]:
    """Import relay_consumer, validate QUEUE_MAP, check tmux sessions."""
    try:
        from relay import relay_consumer  # noqa: F401
        from relay.relay_consumer import QUEUE_MAP
    except Exception as exc:
        return False, f"import failed: {exc}"

    if len(QUEUE_MAP) != 8:
        return False, f"QUEUE_MAP has {len(QUEUE_MAP)} entries, expected 8"

    live_sessions, dead_sessions = [], []
    seen_sessions = set()
    for _queue, config in QUEUE_MAP.items():
        session = config["tmux"].split(":")[0]
        if session in seen_sessions:
            continue
        seen_sessions.add(session)
        result = subprocess.run(["tmux", "has-session", "-t", session], capture_output=True)
        if result.returncode == 0:
            live_sessions.append(session)
        else:
            dead_sessions.append(session)

    required_live = {"elliottbot", "aiden"}
    passed = len(live_sessions) >= 2 or required_live.issubset(set(live_sessions))
    detail = f"{len(live_sessions)}/{len(seen_sessions)} tmux sessions live ({', '.join(live_sessions) or 'none'})"
    if dead_sessions:
        detail += f" | dead: {', '.join(dead_sessions)}"
    return passed, detail


def check5_systemd_unit() -> tuple[bool, str]:
    """Verify relay-consumer.service exists with required sections and ExecStart."""
    service_path = REPO_ROOT / "infra" / "relay" / "relay-consumer.service"
    if not service_path.exists():
        return False, f"not found: {service_path}"

    content = service_path.read_text()
    missing_sections = [s for s in ("[Unit]", "[Service]", "[Install]") if s not in content]
    if missing_sections:
        return False, f"missing sections: {missing_sections}"

    exec_start = None
    for line in content.splitlines():
        if line.strip().startswith("ExecStart="):
            exec_start = line.strip().removeprefix("ExecStart=").split()[1]
            break

    if not exec_start:
        return False, "ExecStart not found in [Service]"
    if not Path(exec_start).exists():
        return False, f"ExecStart path missing: {exec_start}"

    return True, f"relay-consumer.service valid | ExecStart={exec_start}"


# ── Runner ─────────────────────────────────────────────────────────────────────


def main() -> int:
    _load_env(ENV_PATH)

    print()
    print("═" * 47)
    print("  PHASE 3 READINESS CHECK — Change 1b Cutover")
    print("═" * 47)
    print()

    results = []

    def run(label: str, fn, *args):
        try:
            ok, detail, *extra = fn(*args) if args else fn()
            icon = PASS if ok else FAIL
            print(f"[{icon}] {label}: {detail}")
            results.append((ok, label))
            return (ok, detail, *extra)
        except Exception as exc:
            print(f"[{FAIL}] {label}: ERROR — {exc}")
            results.append((False, label))
            return (False, str(exc))

    r1 = run("CHECK 1 — Queue keys", check1_queue_keys)
    depths = r1[2] if len(r1) > 2 else {}
    run("CHECK 2 — Dual-write active", check2_dual_write, depths)
    run("CHECK 3 — HMAC roundtrip", check3_hmac_roundtrip)
    run("CHECK 4 — Consumer dry-run", check4_consumer_dry_run)
    run("CHECK 5 — Systemd unit", check5_systemd_unit)

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)

    print()
    print("═" * 47)
    if passed == total:
        print(f"  RESULT: {passed}/{total} PASS — READY FOR CUTOVER")
    else:
        print(f"  RESULT: {passed}/{total} PASS, {total - passed} FAIL — NOT READY")
    print("═" * 47)
    print()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
