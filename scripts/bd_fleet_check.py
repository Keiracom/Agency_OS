#!/usr/bin/env python3
"""bd fleet-check — capture last 10 lines of each agent tmux pane and post an
R11-compliant bullet report (KEI-94 + KEI-97).

Bypasses the Supabase task-state abstraction by reading tmux directly. Caught
the 2026-05-16 incident where tasks showed 'active' while the underlying tmux
sessions had been dead for an hour.

Routing
-------
- #ceo (default): outcome-first bullet summary only — `**Fleet Check**` header,
  `- aiden: alive` bullets. NO code fences, NO pane content (R11 ban-list).
  Goes through scripts/slack_relay.py so it traverses the central enforcer
  chain (R11 / callsign tag / concur-gate / escalation scan).
- #execution: full detail with code-fenced pane tails. Same relay path.
- --no-post: same full detail printed to stdout for local debug.

Usage
-----
    bd fleet-check                      # post bullet summary to #ceo
    bd fleet-check --channel execution  # post detailed report to #execution
    bd fleet-check --no-post            # print detailed report to stdout

Exit codes
----------
    0 success (posted or dry-run completed)
    1 relay subprocess failed
    2 verify gate (--verify) found an R11 violation

Acceptance (Dave KEI-94 addendum 2026-05-17): Dave types 'check' in #ceo →
Elliot runs `bd fleet-check` → bullet report lands in #ceo within 60s.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Canonical tmux session names per infra/systemd/agents/*.service. Must stay
# aligned with scripts/agent_keepalive.sh callers.
FLEET = [
    ("elliot", "elliottbot"),
    ("aiden", "aiden"),
    ("max", "maxbot"),
    ("atlas", "atlas"),
    ("orion", "orion"),
    ("scout", "scout"),
]

CHANNELS = {
    "ceo": "C0B2PM3TV0B",
    "execution": "C0B3QB0K1GQ",
}

CAPTURE_LINES = 10
TMUX_TIMEOUT_SEC = 5

# KEI-97 zombie detection — any callsign whose last_heartbeat is older than
# HEARTBEAT_STALE_SEC has missed ≥3 of the 30s pings. Treat as dead even if
# tmux capture-pane returns a "live" buffer (zombie session).
HEARTBEAT_STALE_SEC = 90
_LIVENESS_SQL = """
SELECT callsign,
       EXTRACT(EPOCH FROM (NOW() - last_heartbeat))::int AS age_sec
  FROM public.fleet_agents
"""

REPO_ROOT = Path(__file__).resolve().parent.parent
SLACK_RELAY = REPO_ROOT / "scripts" / "slack_relay.py"


def capture_pane(session: str) -> tuple[str, str]:
    """Return (status, last_n_lines). status is ALIVE | DEAD | ERROR."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", f"{session}:0.0", "-p"],
            capture_output=True,
            text=True,
            timeout=TMUX_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ("ERROR", "tmux capture timeout")
    except FileNotFoundError:
        return ("ERROR", "tmux not installed")

    if result.returncode != 0:
        stderr = (result.stderr or "").strip().lower()
        if "no server" in stderr or "can't find session" in stderr or "session not found" in stderr:
            return ("DEAD", stderr or "session absent")
        return ("ERROR", stderr or f"rc={result.returncode}")

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    tail = "\n".join(lines[-CAPTURE_LINES:]) if lines else "(empty pane)"
    return ("ALIVE", tail)


def _resolve_dsn() -> str | None:
    """psycopg-compatible DSN from env, stripping asyncpg prefix."""
    import os

    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def query_db_liveness() -> dict[str, int]:
    """KEI-97 — return {callsign: age_seconds_since_last_heartbeat} from fleet_agents.

    Fail-open: returns {} on missing DSN, missing psycopg, missing table, or any
    DB error. The tmux-based status remains the primary signal; DB liveness only
    *downgrades* ALIVE→DEAD when a heartbeat is stale.
    """
    dsn = _resolve_dsn()
    if not dsn:
        return {}
    try:
        import psycopg

        with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(_LIVENESS_SQL)
            return {row[0]: int(row[1]) for row in cur.fetchall()}
    except Exception:  # noqa: BLE001 — fail-open per dispatch
        return {}


def reconcile_liveness(
    label: str, tmux_status: str, age_map: dict[str, int]
) -> tuple[str, str | None]:
    """Combine tmux status with DB heartbeat age.

    Returns (final_status, reason). final_status is ALIVE/DEAD/ERROR; reason is
    a short suffix appended to the bullet when the DB downgrades the verdict.
    """
    age = age_map.get(label)
    if age is None:
        # No DB row → DB liveness unavailable for this callsign. Don't downgrade.
        return tmux_status, None
    if age > HEARTBEAT_STALE_SEC:
        return "DEAD", f"no heartbeat for {age}s (stale > {HEARTBEAT_STALE_SEC}s)"
    return tmux_status, None


def collect_statuses() -> list[tuple[str, str, str, str]]:
    """Return [(label, session, status, tail), ...] for the full fleet.

    KEI-97 — DB heartbeat age can override a tmux ALIVE verdict if the agent
    process has stopped pinging fleet_agents for ≥HEARTBEAT_STALE_SEC seconds.
    """
    age_map = query_db_liveness()
    out = []
    for label, session in FLEET:
        status, tail = capture_pane(session)
        final_status, reason = reconcile_liveness(label, status, age_map)
        if reason and final_status != status:
            tail = reason
        out.append((label, session, final_status, tail))
    return out


def render_ceo(rows: list[tuple[str, str, str, str]]) -> str:
    """R11-compliant bullet summary for #ceo.

    - Leading `**Fleet Check**` bold header (R11_HEADER_RE).
    - Bullet list `- <label>: <status>` only.
    - NO code fences, NO pane content, NO PR/path/SHA/env tokens.
    """
    lines = ["**Fleet Check**", ""]
    for label, _session, status, tail in rows:
        bullet = f"- {label}: {status.lower()}"
        if status != "ALIVE":
            detail = tail.split("\n", 1)[0][:60]
            bullet += f" — {detail}"
        lines.append(bullet)
    return "\n".join(lines)


def render_full(rows: list[tuple[str, str, str, str]]) -> str:
    """Detailed report with code-fenced pane tails. Safe for #execution and
    --no-post (R11 only fires on #ceo channel)."""
    lines = ["**Fleet Check (detailed)**", ""]
    for label, session, status, tail in rows:
        if status == "ALIVE":
            lines.append(f"- {label} (tmux={session}): {status.lower()} — last {CAPTURE_LINES}:")
            lines.append(f"```\n{tail}\n```")
        else:
            lines.append(f"- {label} (tmux={session}): {status.lower()} — {tail}")
    return "\n".join(lines)


def post_via_relay(channel_id: str, text: str) -> bool:
    """Hand off to scripts/slack_relay.py so the central enforcer chain
    (R11, callsign tag, concur-gate, escalation scan) processes the body.

    Returns True on relay exit 0, False otherwise.
    """
    if not SLACK_RELAY.exists():
        print(f"[fleet-check] relay missing: {SLACK_RELAY}", file=sys.stderr)
        return False
    try:
        result = subprocess.run(
            ["python3", str(SLACK_RELAY), "-c", channel_id, text],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("[fleet-check] relay timeout", file=sys.stderr)
        return False
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        print(f"[fleet-check] relay rc={result.returncode}: {err}", file=sys.stderr)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="bd fleet-check (KEI-94 + KEI-97)")
    parser.add_argument(
        "--no-post",
        action="store_true",
        help="print detailed report to stdout only (no relay call)",
    )
    parser.add_argument(
        "--channel",
        default="ceo",
        choices=sorted(CHANNELS.keys()),
        help="target channel — ceo (bullet summary, default) or execution (detailed)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="run R11 enforcer check on the would-be ceo body and exit",
    )
    args = parser.parse_args(argv)

    started = time.monotonic()
    rows = collect_statuses()
    elapsed = time.monotonic() - started
    status_map = {label: status for label, _s, status, _t in rows}

    ceo_body = render_ceo(rows)
    full_body = render_full(rows)

    if args.verify:
        from src.bot_common.enforcer_deterministic import check_r11

        verdict = check_r11(ceo_body, channel=CHANNELS["ceo"])
        if verdict is None:
            print(f"[fleet-check] R11 verify PASS — body OK for #ceo (captured {elapsed:.1f}s)")
            return 0
        print(f"[fleet-check] R11 verify FAIL: {verdict}", file=sys.stderr)
        return 2

    if args.no_post:
        print(full_body)
        print(f"\n(captured in {elapsed:.1f}s; statuses={status_map})", file=sys.stderr)
        return 0

    body = ceo_body if args.channel == "ceo" else full_body
    channel_id = CHANNELS[args.channel]
    ok = post_via_relay(channel_id, body)
    total = time.monotonic() - started
    print(
        f"[fleet-check] elapsed={total:.1f}s posted={ok} channel=#{args.channel}",
        file=sys.stderr,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
