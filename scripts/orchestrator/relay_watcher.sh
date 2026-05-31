#!/bin/bash
# Relay Watcher — bridges Telegram inbox to Claude's tmux pane
# Per-callsign isolation (LAW XVII): each callsign has its own relay dir + tmux target
# Usage: relay_watcher.sh [callsign]  (default: elliot)

CALLSIGN="${1:-elliot}"
RELAY_DIR="/tmp/telegram-relay-${CALLSIGN}"
INBOX="${RELAY_DIR}/inbox"
PROCESSED="${RELAY_DIR}/processed"
STATE_FILE="${RELAY_DIR}/last_chat_id"

# KEI-99 / Linear KEI-83 — Priority list per callsign. Tried in order; first
# session that `tmux has-session` answers gets the message. If Dave manually
# starts a session with a non-default name (e.g. `elliot` instead of
# `elliottbot`), delivery still works.
case "$CALLSIGN" in
    elliot)  TMUX_CANDIDATES=("elliottbot:0.0" "elliot:0.0" "elliot-agent:0.0") ;;
    aiden)   TMUX_CANDIDATES=("aiden:0.0" "aidenbot:0.0" "aiden-agent:0.0") ;;
    scout)   TMUX_CANDIDATES=("scout:0.0" "scoutbot:0.0" "scout-agent:0.0") ;;
    max)     TMUX_CANDIDATES=("maxbot:0.0" "max:0.0" "max-agent:0.0") ;;
    *)       TMUX_CANDIDATES=("${CALLSIGN}bot:0.0" "${CALLSIGN}:0.0" "${CALLSIGN}-agent:0.0") ;;
esac

# KEI-99 final fallback: probe live tmux sessions for any whose name contains
# the callsign (case-insensitive). Catches non-default session names Dave or
# install scripts may create (e.g. `scout-clawd`, `scout_main`, capitalised
# `Scout`). Dynamic candidates are appended AFTER the hardcoded primaries so
# the curated names still win when available.
discover_callsign_sessions() {
    local -a live=()
    local sess lowered cs_lower="${CALLSIGN,,}"
    mapfile -t live < <(tmux list-sessions -F '#{session_name}' 2>/dev/null || true)
    for sess in "${live[@]}"; do
        lowered="${sess,,}"
        if [[ "$lowered" == *"$cs_lower"* ]]; then
            local candidate="${sess}:0.0"
            local already=0
            for existing in "${TMUX_CANDIDATES[@]}"; do
                if [[ "$existing" == "$candidate" ]]; then
                    already=1
                    break
                fi
            done
            if [[ $already -eq 0 ]]; then
                TMUX_CANDIDATES+=("$candidate")
            fi
        fi
    done
    return 0
}
discover_callsign_sessions

TMUX_TARGET="${TMUX_CANDIDATES[0]}"

# Resolve a live tmux target. Sets TMUX_TARGET on success; returns 1 if all
# candidates miss. Logs a promotion when we settle on a non-primary name.
resolve_tmux_target() {
    local candidate session previous="$TMUX_TARGET"
    for candidate in "${TMUX_CANDIDATES[@]}"; do
        session="${candidate%%:*}"
        if tmux has-session -t "$session" 2>/dev/null; then
            if [[ "$candidate" != "$previous" ]]; then
                echo "[relay-watcher-${CALLSIGN}] PROMOTED session: $previous → $candidate"
            fi
            TMUX_TARGET="$candidate"
            return 0
        fi
    done
    return 1
}

# Alert on delivery failure. Elliot is the only callsign with #ceo access
# (per acceptance criteria); every other callsign falls back to #execution
# where peers can pick up the alert. Failures here are swallowed so the
# watcher never crashes on a notification path.
alert_delivery_failure() {
    local tg_bin alert_channel msg
    tg_bin="$(command -v tg 2>/dev/null)"
    [[ -x "$tg_bin" ]] || return 0
    if [ "$CALLSIGN" = "elliot" ]; then
        alert_channel="ceo"
    else
        alert_channel="execution"
    fi
    msg="[SYSTEM] [${CALLSIGN^^}] relay delivery failed — no live tmux session under known names: ${TMUX_CANDIDATES[*]}. Manual intervention required."
    CALLSIGN="$CALLSIGN" "$tg_bin" -c "$alert_channel" "$msg" >/dev/null 2>&1 || true
}

mkdir -p "$INBOX" "$PROCESSED"

# ── jne8 pattern: wait-for-prompt + literal send + commit-verify ─────────────
# Mirrors inbox_watcher.sh. Reference: Agency_OS-jne8 + watchdog resume fix
# (2026-05-31). Root cause: bare send-keys+sleep+C-m does not always commit —
# Enter races claude's render / permission prompts. Fix: send text with -l
# (literal, no tmux key-name interpretation), then retry C-m until the probe
# string (first 40 chars) is GONE from the bottom of the pane (= submitted).

wait_for_prompt_local() {
    local attempts="${1:-30}"
    for _ in $(seq 1 "$attempts"); do
        tmux capture-pane -t "$TMUX_TARGET" -p 2>/dev/null | tail -5 | grep -q '❯' && return 0
        sleep 2
    done
    return 1
}

inject_and_verify() {
    local content="$1"
    local probe attempt
    tmux send-keys -t "$TMUX_TARGET" -l "$content" 2>/dev/null || return 1
    sleep 0.4
    probe="$(printf '%s' "$content" | head -c 40)"
    for attempt in 1 2 3; do
        tmux send-keys -t "$TMUX_TARGET" C-m 2>/dev/null
        sleep 2
        if ! tmux capture-pane -t "$TMUX_TARGET" -p 2>/dev/null | tail -3 | grep -qF "$probe"; then
            [ "$attempt" -gt 1 ] && echo "[relay-watcher-${CALLSIGN}] committed on C-m retry #$attempt"
            return 0
        fi
        echo "[relay-watcher-${CALLSIGN}] C-m attempt $attempt did not commit; retrying"
    done
    return 1
}
# ─────────────────────────────────────────────────────────────────────────────

echo "[relay-watcher-${CALLSIGN}] Started. Watching $INBOX → tmux candidates: ${TMUX_CANDIDATES[*]}"

# H10 — also watch -e moved_to so we don't drop dispatches the Write tool
# delivers via atomic rename (which fires moved_to, not create).
inotifywait -m -q -e create -e moved_to "$INBOX" --format '%f' 2>/dev/null | while read fname; do
    # Only process JSON metadata files
    [[ "$fname" != *.json ]] && continue

    fpath="$INBOX/$fname"
    [ ! -f "$fpath" ] && continue

    # Small delay to let file finish writing
    sleep 0.2

    # KEI-99: Resolve a live tmux session BEFORE attempting delivery. If no
    # candidate is live, alert #ceo and quarantine the message (move to
    # processed so we don't busy-loop on the same file).
    if ! resolve_tmux_target; then
        echo "[relay-watcher-${CALLSIGN}] DELIVERY FAILED — no live tmux session in: ${TMUX_CANDIDATES[*]}"
        alert_delivery_failure
        mv "$fpath" "$PROCESSED/" 2>/dev/null
        continue
    fi

    # Parse the message
    msg_type=$(python3 -c "import json; print(json.load(open('$fpath')).get('type',''))" 2>/dev/null)
    chat_id=$(python3 -c "import json; print(json.load(open('$fpath')).get('chat_id',''))" 2>/dev/null)

    # Save last chat_id for tg reply script
    [ -n "$chat_id" ] && echo "$chat_id" > "$STATE_FILE"

    if [ "$msg_type" = "text" ]; then
        text=$(python3 -c "
import json, sys
d = json.load(open('$fpath'))
# Escape special characters for tmux
t = d.get('text', '')
# Replace newlines with spaces for single-line tmux input
t = t.replace('\n', ' ')
print(t)
" 2>/dev/null)

        if [ -n "$text" ]; then
            sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender','unknown'))" 2>/dev/null)
            # Skip idle echo messages from PEER BOTS ONLY to prevent feedback loops.
            # Never filter messages from dave, max, or unknown senders.
            if echo "$sender" | grep -qiP '^(elliotbot|aidenbot|atlasbot|orionbot|scoutbot)$'; then
                stripped=$(echo "$text" | sed 's/\[[^]]*\]//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -s ' ')
                if [ ${#stripped} -le 40 ] && { [ -z "$stripped" ] || echo "$stripped" | grep -qiP '\b(hold|wait|stand|ack|noted|session\.wrap|concur)\b'; }; then
                    echo "[relay-watcher-${CALLSIGN}] SKIPPED idle echo from ${sender}: ${text:0:60}"
                    mv "$fpath" "$PROCESSED/" 2>/dev/null
                    continue
                fi
            fi
            echo "[relay-watcher-${CALLSIGN}] Text from Telegram: ${text:0:80}..."
            wait_for_prompt_local 60
            inject_and_verify "[TG-${sender^^}] $text" || echo "[relay-watcher-${CALLSIGN}] WARNING: text inject did not commit"
        fi

    elif [ "$msg_type" = "photo" ]; then
        photo_path=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_path',''))" 2>/dev/null)
        caption=$(python3 -c "import json; print(json.load(open('$fpath')).get('caption',''))" 2>/dev/null)
        sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender','unknown'))" 2>/dev/null)

        echo "[relay-watcher-${CALLSIGN}] Photo from Telegram: $photo_path"
        wait_for_prompt_local 60
        inject_and_verify "[TG-${sender^^}] Dave sent a screenshot: $photo_path ${caption:+— $caption}" || echo "[relay-watcher-${CALLSIGN}] WARNING: photo inject did not commit"

    elif [ "$msg_type" = "document" ]; then
        file_path=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_path',''))" 2>/dev/null)
        file_name=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_name',''))" 2>/dev/null)
        sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender','unknown'))" 2>/dev/null)

        echo "[relay-watcher-${CALLSIGN}] Document from Telegram: $file_name"
        wait_for_prompt_local 60
        inject_and_verify "[TG-${sender^^}] Dave sent a file: $file_path ($file_name)" || echo "[relay-watcher-${CALLSIGN}] WARNING: document inject did not commit"

    elif [ "$msg_type" = "task_dispatch" ]; then
        text=$(python3 -c "
import json
d = json.load(open('$fpath'))
sender = d.get('from', 'unknown')
brief = d.get('brief', 'no brief').replace('\n', ' ')
task_ref = d.get('task_ref', '')
suffix = f' (ref: {task_ref})' if task_ref else ''
print(f'[DISPATCH FROM {sender.upper()}] {brief}{suffix}')
" 2>/dev/null)
        if [ -n "$text" ]; then
            echo "[relay-watcher-${CALLSIGN}] Dispatch: ${text:0:80}..."
            wait_for_prompt_local 60
            inject_and_verify "$text" || echo "[relay-watcher-${CALLSIGN}] WARNING: dispatch inject did not commit"
        fi

    else
        # Fallback: format any unknown message type for injection
        text=$(python3 -c "
import json
d = json.load(open('$fpath'))
t = d.get('text', d.get('brief', json.dumps(d, default=str)))
t = t.replace('\n', ' ')[:500]
print(t)
" 2>/dev/null)
        sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender', json.load(open('$fpath')).get('from','unknown')))" 2>/dev/null)
        if [ -n "$text" ]; then
            echo "[relay-watcher-${CALLSIGN}] Unknown type '${msg_type}' from ${sender}: ${text:0:80}..."
            wait_for_prompt_local 60
            inject_and_verify "[TG-${sender^^}] $text" || echo "[relay-watcher-${CALLSIGN}] WARNING: fallback inject did not commit"
        fi
    fi

    # Move to processed (don't delete — audit trail)
    mv "$fpath" "$PROCESSED/" 2>/dev/null

    # Also move associated media files
    base="${fname%.json}"
    for ext in jpg png pdf doc docx txt; do
        [ -f "$INBOX/${base}.${ext}" ] && mv "$INBOX/${base}.${ext}" "$PROCESSED/" 2>/dev/null
    done
done
