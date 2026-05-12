#!/usr/bin/env bash
# Drevon PR-A follow-up — UserPromptSubmit hook that records messages rows
# into the 5-table session store. Closes the silent data-loss in
# src/skill_gen/extractor._fetch_user_messages (audit Surprise #1, 2026-05-12):
# skill_gen queries public.messages for role=user but no production hook ever
# wrote there → every compression returned [] silently.
#
# Bash plumbing only — the actual recording logic lives in
# src/session_store/userpromptsubmit_handler.py (tested module). Mirrors the
# session_store_posttooluse.sh shape: read stdin, resolve callsign, background
# subprocess, never block the agent. Adds a per-callsign monotone
# message_index counter at /tmp/.msgidx_<callsign>.
#
# stdin format (Claude Code UserPromptSubmit):
#   { "prompt": "<user text>", "session_id": "...", ... }
#
# Best-effort recording — always exits 0.

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

# Skip if skill-gen subprocess (env-marker recursion guard from PR #728)
if [[ -n "${CLAUDE_CODE_SKILL_GEN:-}" ]]; then
    exit 0
fi

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
prompt_bytes=0
if command -v jq >/dev/null 2>&1 && [[ -n "$PAYLOAD" ]]; then
    prompt_bytes="$(printf '%s' "$PAYLOAD" | jq -r '.prompt // "" | length' 2>/dev/null || echo 0)"
fi
printf '%s\t%s\t%s\n' "$ts" "$callsign" "$prompt_bytes" \
    >>"$LOG_DIR/userpromptsubmit.log" 2>/dev/null || true

# Background subprocess — never blocks
(
    PYTHONPATH="$REPO_ROOT" CALLSIGN="$callsign" \
        /home/elliotbot/clawd/venv/bin/python3 -c "
import os, sys
sys.path.insert(0, os.environ.get('PYTHONPATH', '.'))
try:
    from src.session_store.userpromptsubmit_handler import handle_user_prompt_submit
except ImportError as e:
    sys.stderr.write(f'handler import failed: {e}\n')
    sys.exit(0)
handle_user_prompt_submit(
    callsign=os.environ.get('CALLSIGN', 'unknown'),
    payload_text=sys.stdin.read(),
    working_directory=os.getcwd(),
)
" <<< "$PAYLOAD" 2>>"$LOG_DIR/recorder.err" &
    disown 2>/dev/null || true
)

exit 0
