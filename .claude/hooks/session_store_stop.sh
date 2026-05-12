#!/usr/bin/env bash
# Drevon PR-A + PR-C clean-close — Stop hook closes the open session row with
# status='closed_clean' so PR-C resolver can pick the UUID back up via
# `claude --resume <uuid>` on the next launch. status='closed' is now reserved
# for caller-initiated graceful closes that should NOT resume (none today).
# Watchdog continues to mark unresponsive rows status='stuck'.
# Best-effort recording — always exits 0.

set -u

LOG_DIR="${SESSION_STORE_LOG_DIR:-/tmp/agency-os-session-store}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

callsign="${CALLSIGN:-}"
if [[ -z "$callsign" && -r ./IDENTITY.md ]]; then
    callsign="$(grep -m1 -oE '\*\*CALLSIGN:\*\* [A-Za-z]+' ./IDENTITY.md 2>/dev/null \
        | sed 's/^.*\*\* //' | tr '[:upper:]' '[:lower:]')"
fi
callsign="${callsign:-unknown}"

SESSION_STATE_FILE="/tmp/.session_${callsign}"
TURN_STATE_FILE="/tmp/.turn_${callsign}"

# Local audit line
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\t%s\t session_end\n' "$ts" "$callsign" \
    >>"$LOG_DIR/stop.log" 2>/dev/null || true

# Background write
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
(
    PYTHONPATH="$REPO_ROOT" CALLSIGN="$callsign" \
        /home/elliotbot/clawd/venv/bin/python3 -c "
import os, sys
sys.path.insert(0, os.environ.get('PYTHONPATH', '.'))
try:
    from src.session_store.recorder import record_session_end, record_turn_complete
except Exception as e:
    sys.stderr.write(f'session_store import failed: {e}\n')
    sys.exit(0)

callsign = os.environ.get('CALLSIGN', 'unknown')
session_state = f'/tmp/.session_{callsign}'
turn_state = f'/tmp/.turn_{callsign}'

# Close open turn (if any)
if os.path.exists(turn_state):
    try:
        from uuid import UUID
        tid = open(turn_state).read().strip()
        if tid:
            record_turn_complete(turn_id=UUID(tid), status='completed')
        os.remove(turn_state)
    except Exception as e:
        sys.stderr.write(f'turn close failed: {e}\n')

# Close session
if os.path.exists(session_state):
    try:
        from uuid import UUID
        sid = open(session_state).read().strip().split(':')[0]
        if sid:
            record_session_end(session_id=UUID(sid), status='closed_clean')
        os.remove(session_state)
    except Exception as e:
        sys.stderr.write(f'session close failed: {e}\n')
" 2>>"$LOG_DIR/recorder.err" &
    disown 2>/dev/null || true
)

exit 0
