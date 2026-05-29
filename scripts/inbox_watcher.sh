#!/bin/bash
# inbox_watcher.sh <callsign> — per-callsign inbox -> tmux pane dispatch injector.
#
# Canonical, VERSIONED source for every *-inbox-watcher.service. One parameterised
# script replaces the 7 byte-identical-modulo-callsign host copies. Install via
# scripts/install_inbox_watchers.sh (copies to a stable host path + points the
# units at it — must NOT run from a git worktree, which drifts branches).
#
# Reliability fixes (Agency_OS-jne8 + swi6):
#   jne8 — the bare `send-keys ... ; sleep ; C-m` did not always COMMIT (the Enter
#          races claude's permission prompts / render). Now: after C-m, capture the
#          input region and RETRY C-m up to MAX_COMMIT_RETRIES if the text is still
#          sitting unsubmitted (an extra Enter on an already-empty prompt is a no-op).
#   swi6 — the file was moved to processed/ UNCONDITIONALLY, so a non-committed
#          dispatch was silently lost. Now: committed -> processed/, NOT committed
#          -> failed/ (never silently dropped), and EVERY file is logged (heartbeat)
#          so a stalled agent is detectable instead of invisible.
set -uo pipefail

CALLSIGN="${1:?usage: inbox_watcher.sh <callsign>}"
RELAY="/tmp/telegram-relay-${CALLSIGN}"
INBOX="$RELAY/inbox"
PROCESSED="$RELAY/processed"
FAILED="$RELAY/failed"
TMUX_TARGET="${CALLSIGN}:0.0"
LOG="/home/elliotbot/clawd/logs/inbox_watcher_${CALLSIGN}.log"
REPO="/home/elliotbot/clawd/Agency_OS"
MAX_COMMIT_RETRIES=3
PROMPT_WAIT_S=30

mkdir -p "$INBOX" "$PROCESSED" "$FAILED" "$(dirname "$LOG")"

log() { echo "$(date -u +%FT%TZ) [$CALLSIGN] $*" | tee -a "$LOG"; }

hmac_ok() {  # $1=filepath -> 0 ok / 1 reject. No secret set = accept (dev/clone).
    [ -z "${INBOX_HMAC_SECRET:-}" ] && return 0
    python3 -c "
import sys; sys.path.insert(0, '$REPO')
from src.security.inbox_hmac import verify
ok, reason = verify('$1')
sys.exit(0 if ok else 1)
" 2>/dev/null
}

extract_content() {  # $1=filepath -> dispatch text on stdout
    python3 -c "
import json
try:
    d = json.load(open('$1'))
    kind = d.get('type') or d.get('kind') or ''
    text = d.get('brief') or d.get('summary') or d.get('text') or json.dumps(d)
    print(f'[DISPATCH FROM {d.get(\"from\",\"unknown\")}] {text}' if kind in ('task_dispatch','status','scrutiny_and_step0') else text)
except Exception:
    print(open('$1').read())
" 2>/dev/null
}

# Inject content into the pane and VERIFY it committed. 0 = committed, 1 = not.
inject_and_verify() {
    local content="$1" probe attempt
    # Wait (bounded) for claude's prompt so we don't type into a mid-render pane.
    for _ in $(seq 1 "$PROMPT_WAIT_S"); do
        tmux capture-pane -t "$TMUX_TARGET" -p 2>/dev/null | tail -5 | grep -q '❯' && break
        sleep 1
    done
    tmux send-keys -t "$TMUX_TARGET" -l "$content" 2>/dev/null || return 1
    sleep 0.4
    # First ~40 chars as a commit probe: before Enter it sits on the input line;
    # after Enter the input line clears (the message renders above). If it's still
    # on the bottom lines after C-m+settle, the Enter didn't take — retry (jne8).
    probe="$(printf '%s' "$content" | head -c 40)"
    for attempt in $(seq 1 "$MAX_COMMIT_RETRIES"); do
        tmux send-keys -t "$TMUX_TARGET" C-m 2>/dev/null
        sleep 2
        if ! tmux capture-pane -t "$TMUX_TARGET" -p 2>/dev/null | tail -3 | grep -qF "$probe"; then
            [ "$attempt" -gt 1 ] && log "committed on C-m retry #$attempt"
            return 0
        fi
        log "C-m attempt $attempt did not commit; retrying"
    done
    return 1
}

log "watcher started (target=$TMUX_TARGET, inbox=$INBOX)"
inotifywait -m -e create -e moved_to "$INBOX" --format '%f' 2>/dev/null | while read -r FILE; do
    FILEPATH="$INBOX/$FILE"
    [ -f "$FILEPATH" ] || continue
    log "received: $FILE"

    if ! hmac_ok "$FILEPATH"; then
        log "HMAC REJECT -> failed/: $FILE"
        mv "$FILEPATH" "$FAILED/REJECTED_$FILE" 2>/dev/null
        continue
    fi

    CONTENT="$(extract_content "$FILEPATH")"
    if [ -z "$CONTENT" ]; then
        log "EMPTY content -> failed/: $FILE"
        mv "$FILEPATH" "$FAILED/EMPTY_$FILE" 2>/dev/null
        continue
    fi

    if inject_and_verify "$CONTENT"; then
        log "injected+committed -> processed/: $FILE"
        mv "$FILEPATH" "$PROCESSED/" 2>/dev/null
    else
        log "INJECTION FAILED after $MAX_COMMIT_RETRIES retries -> failed/ (NOT dropped): $FILE"
        mv "$FILEPATH" "$FAILED/" 2>/dev/null
    fi
done
