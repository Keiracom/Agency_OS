#!/usr/bin/env bash
# session_resumption_watchdog.sh — Drevon PR-C periodic stuck-session reaper.
#
# Sweeps sessions where ended_at IS NULL AND started_at < NOW() - INTERVAL
# stuck_minutes and marks them status='stuck' so the resolver will not pick
# them up. Best-effort; never blocks Claude Code execution.
#
# Wire-up: invoke from cron, systemd timer, or a long-running agent loop. Not
# wired into .claude/settings.json by default — operator chooses cadence.
#
# Env overrides (optional):
#     SESSION_STUCK_MINUTES   — staleness threshold (default 60)
#     SESSION_WATCHDOG_SCOPE  — single callsign to scope; unset = all

set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
stuck_minutes="${SESSION_STUCK_MINUTES:-60}"
scope="${SESSION_WATCHDOG_SCOPE:-}"

cd "$repo_root" && python3 - "$stuck_minutes" "$scope" <<'PY'
import sys

stuck_minutes = int(sys.argv[1])
scope = sys.argv[2] or None

try:
    from src.session_resumption.watchdog import clear_stuck_sessions
except Exception as exc:
    sys.stderr.write(f"[watchdog] import failed (non-fatal): {exc}\n")
    sys.exit(0)

cleared = clear_stuck_sessions(callsign=scope, stuck_minutes=stuck_minutes)
print(f"[watchdog] cleared={cleared} scope={scope or '<all>'} stuck_minutes={stuck_minutes}")
PY
