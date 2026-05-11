#!/usr/bin/env bash
# Drevon PR-A — PostToolUse hook that records turn_logs + turn_files rows
# into the 5-table session store. NOT yet wired in .claude/settings.json
# (follow-up). Standalone-callable for manual testing.
#
# Per Elliot dispatch 2026-05-11: Python ORM + Claude Code hooks for write
# paths. Auto-creates a session row on first invocation if /tmp/.session_<callsign>
# state file is missing. Stop hook closes the session.
#
# stdin format (Claude Code PostToolUse):
#   { "tool_name": "Edit", "tool_input": {...}, "tool_response": {...}, ... }
#
# Best-effort recording — exits 0 on all failures. Never blocks the agent.

set -u

LOG_DIR="${SESSION_STORE_LOG_DIR:-/tmp/agency-os-session-store}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

PAYLOAD="$(cat || true)"

callsign="${CALLSIGN:-}"
if [[ -z "$callsign" && -r ./IDENTITY.md ]]; then
    callsign="$(grep -m1 -oE '\*\*CALLSIGN:\*\* [A-Za-z]+' ./IDENTITY.md 2>/dev/null \
        | sed 's/^.*\*\* //' | tr '[:upper:]' '[:lower:]')"
fi
callsign="${callsign:-unknown}"

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SESSION_STATE_FILE="/tmp/.session_${callsign}"

# Local audit line first (cheap, always works)
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
tool_name="unknown"
if command -v jq >/dev/null 2>&1 && [[ -n "$PAYLOAD" ]]; then
    tool_name="$(printf '%s' "$PAYLOAD" | jq -r '.tool_name // "unknown"' 2>/dev/null || echo unknown)"
fi
printf '%s\t%s\t%s\n' "$ts" "$callsign" "$tool_name" \
    >>"$LOG_DIR/posttooluse.log" 2>/dev/null || true

# Background recorder write (fire and forget, never blocks).
(
    PYTHONPATH="$REPO_ROOT" CALLSIGN="$callsign" \
        /home/elliotbot/clawd/venv/bin/python3 -c "
import json, os, sys, hashlib
sys.path.insert(0, os.environ.get('PYTHONPATH', '.'))
try:
    from src.session_store.recorder import record_session_start, record_tool_call, record_turn_start
except Exception as e:
    sys.stderr.write(f'session_store import failed: {e}\n')
    sys.exit(0)

callsign = os.environ.get('CALLSIGN', 'unknown')
state_file = f'/tmp/.session_{callsign}'

# Resolve or create session
sid = None
if os.path.exists(state_file):
    try:
        sid = open(state_file).read().strip().split(':')[0] or None
    except Exception:
        sid = None
if not sid:
    new_sid = record_session_start(callsign=callsign, working_directory=os.getcwd())
    if new_sid is not None:
        sid = str(new_sid)
        open(state_file, 'w').write(f'{sid}:0:0')  # session_id:turn_index:tool_index
if not sid:
    sys.exit(0)

# Resolve or create turn (single turn per session for V1 — turn boundaries
# in Claude Code aren't directly observable from hooks alone; Stop hook
# will close it).
parts = open(state_file).read().strip().split(':') if os.path.exists(state_file) else [sid, '0', '0']
turn_index = int(parts[1]) if len(parts) > 1 else 0
tool_index = int(parts[2]) if len(parts) > 2 else 0
turn_id = None
turn_state_file = f'/tmp/.turn_{callsign}'
if os.path.exists(turn_state_file):
    try:
        turn_id = open(turn_state_file).read().strip() or None
    except Exception:
        turn_id = None
if not turn_id:
    from uuid import UUID
    new_tid = record_turn_start(session_id=UUID(sid), turn_index=turn_index)
    if new_tid is not None:
        turn_id = str(new_tid)
        open(turn_state_file, 'w').write(turn_id)
if not turn_id:
    sys.exit(0)

# Parse payload + record tool call
payload_text = sys.stdin.read().strip() if not sys.stdin.isatty() else ''
try:
    payload = json.loads(payload_text) if payload_text else {}
except json.JSONDecodeError:
    payload = {}

tool_name = payload.get('tool_name') or 'unknown'
tool_input = payload.get('tool_input') or {}

# Build files list from tool_input where it makes sense
files = []
file_path = tool_input.get('file_path') or tool_input.get('notebook_path')
if file_path and tool_name in ('Write', 'Edit', 'NotebookEdit', 'Read'):
    op = 'write' if tool_name == 'Write' else ('edit' if tool_name in ('Edit', 'NotebookEdit') else 'read')
    files.append({'file_path': file_path, 'operation': op})

from uuid import UUID
record_tool_call(
    turn_id=UUID(turn_id),
    tool_name=tool_name,
    tool_args=tool_input,
    exit_status='success',
    files=files or None,
)

# Increment counters
new_tool_index = tool_index + 1
open(state_file, 'w').write(f'{sid}:{turn_index}:{new_tool_index}')
" <<< "$PAYLOAD" 2>>"$LOG_DIR/recorder.err" &
    disown 2>/dev/null || true
)

exit 0
