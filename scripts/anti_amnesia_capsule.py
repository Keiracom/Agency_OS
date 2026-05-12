#!/usr/bin/env python3
"""anti_amnesia_capsule.py — pre-compact session snapshot + post-resume reader.

Extends PR #751 (PreCompact alert + HEARTBEAT.md) per Stream 4 Item #3
dispatch (2026-05-12): serialise the top-20 most critical *active* facts from
THIS session to a per-callsign capsule file before context compresses, so the
post-compaction agent can recover working state without re-deriving from
durable stores.

Modes:
    write (default)  PreCompact hook target. Composes capsule + writes to
                     ~/.claude/capsules/<callsign>_capsule.md. Best-effort.
    --read           SessionStart hook target. Cats the capsule to stdout so
                     the resuming session sees it in its initial context.

Sources (ranked, deduplicated to top-20 lines, ~1500 char cap):
    1. HEARTBEAT.md (agent-maintained continuation anchor) — highest priority
    2. Drevon-port turn_logs for this callsign's active session (last N tools)
    3. Git: current branch + porcelain dirty marker + recent commits
    4. Recent agent_memories rows for this callsign (last 3)
    5. Last outbound TG messages from /tmp/telegram-relay-<callsign>/outbox/

Best-effort: any source failure logs+swallows. Capsule write never blocks
compaction; capsule read never blocks startup. Stale capsule on a fresh
non-compaction restart is harmless — it just gives the new session a view
of the previous session's tail.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("anti_amnesia_capsule")

CAPSULE_DIR = Path.home() / ".claude" / "capsules"
MAX_CAPSULE_CHARS = 1500
MAX_LINES = 20


def resolve_callsign() -> str:
    env_val = os.environ.get("CALLSIGN", "").strip()
    if env_val:
        return env_val.lower()
    for candidate in (Path.cwd() / "IDENTITY.md", Path.cwd().parent / "IDENTITY.md"):
        if candidate.exists():
            match = re.search(
                r"^\s*\*\*?CALLSIGN:?\*\*?\s*([A-Za-z]\w*)",
                candidate.read_text(),
                re.IGNORECASE | re.MULTILINE,
            )
            if match:
                return match.group(1).lower()
    return "unknown"


def _run(args: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("subprocess %s failed: %s", args[:2], exc)
        return ""


def collect_heartbeat() -> list[str]:
    hb = Path.cwd() / "HEARTBEAT.md"
    if not hb.exists():
        return []
    try:
        text = hb.read_text()
    except OSError:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    return [f"HB: {ln}" for ln in lines[:8]]


def collect_git() -> list[str]:
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "?"
    porcelain = _run(["git", "status", "--porcelain"])
    dirty = " [DIRTY]" if porcelain else ""
    log_out = _run(["git", "log", "--oneline", "-5"])
    lines = [f"BRANCH: {branch}{dirty}"]
    lines.extend(f"COMMIT: {ln}" for ln in log_out.splitlines() if ln.strip())
    return lines


def collect_recent_memories(callsign: str) -> list[str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return []
    import json as _json
    import urllib.error
    import urllib.parse
    import urllib.request

    try:
        params = urllib.parse.urlencode(
            {
                "callsign": f"eq.{callsign}",
                "state": "eq.confirmed",
                "order": "created_at.desc",
                "limit": "3",
                "select": "source_type,content,created_at",
            }
        )
        req = urllib.request.Request(
            f"{url}/rest/v1/agent_memories?{params}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            rows = _json.loads(r.read())
        return [f"MEM[{r['source_type']}]: {r['content'][:120]}" for r in rows]
    except (urllib.error.URLError, _json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
        logger.warning("agent_memories query failed: %s", exc)
        return []


def collect_recent_outbox(callsign: str) -> list[str]:
    outbox = Path(f"/tmp/telegram-relay-{callsign}/outbox")
    if not outbox.is_dir():
        return []
    try:
        files = sorted(outbox.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
        out = []
        for f in files:
            try:
                preview = f.read_text(errors="replace")[:120].replace("\n", " ")
                out.append(f"TG-OUT: {preview}")
            except OSError:
                continue
        return out
    except OSError:
        return []


def compose_capsule(callsign: str) -> str:
    sections: list[tuple[str, list[str]]] = [
        ("HEARTBEAT", collect_heartbeat()),
        ("GIT", collect_git()),
        ("MEMORIES", collect_recent_memories(callsign)),
        ("RECENT TG", collect_recent_outbox(callsign)),
    ]
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    header = f"# Anti-Amnesia Capsule — {callsign}\n_Snapshot: {timestamp}_\n"
    body_lines: list[str] = []
    for title, items in sections:
        if not items:
            continue
        body_lines.append(f"\n## {title}")
        body_lines.extend(items)
    capsule = header + "\n".join(body_lines)
    if len(capsule) > MAX_CAPSULE_CHARS:
        capsule = capsule[: MAX_CAPSULE_CHARS - 20].rstrip() + "\n…[truncated]"
    return capsule


def capsule_path(callsign: str) -> Path:
    return CAPSULE_DIR / f"{callsign}_capsule.md"


def write_capsule(callsign: str) -> int:
    try:
        CAPSULE_DIR.mkdir(parents=True, exist_ok=True)
        path = capsule_path(callsign)
        path.write_text(compose_capsule(callsign))
        print(f"[capsule] wrote {path} ({path.stat().st_size}B)", file=sys.stderr)
        return 0
    except OSError as exc:
        logger.warning("capsule write failed: %s", exc)
        return 0  # never block compaction


def read_capsule(callsign: str) -> int:
    path = capsule_path(callsign)
    if not path.exists():
        return 0
    try:
        sys.stdout.write("\n=== ANTI-AMNESIA CAPSULE ===\n")
        sys.stdout.write(path.read_text())
        sys.stdout.write("\n=== END CAPSULE ===\n")
        return 0
    except OSError as exc:
        logger.warning("capsule read failed: %s", exc)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", action="store_true", help="Read capsule (SessionStart mode)")
    args = parser.parse_args()
    callsign = resolve_callsign()
    if args.read:
        return read_capsule(callsign)
    return write_capsule(callsign)


if __name__ == "__main__":
    sys.exit(main())
