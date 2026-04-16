#!/bin/bash
# Relay Watcher — bridges Telegram inbox to Claude's tmux pane
# Per-callsign isolation (LAW XVII): each callsign has its own relay dir + tmux target
# Usage: relay_watcher.sh [callsign]  (default: elliot)

CALLSIGN="${1:-elliot}"
RELAY_DIR="/tmp/telegram-relay-${CALLSIGN}"
INBOX="${RELAY_DIR}/inbox"
PROCESSED="${RELAY_DIR}/processed"
STATE_FILE="${RELAY_DIR}/last_chat_id"

# Map callsign to tmux session name
if [ "$CALLSIGN" = "elliot" ]; then
    TMUX_TARGET="elliottbot:0.0"
elif [ "$CALLSIGN" = "aiden" ]; then
    TMUX_TARGET="aiden:0.0"
else
    TMUX_TARGET="${CALLSIGN}bot:0.0"
fi

mkdir -p "$INBOX" "$PROCESSED"

echo "[relay-watcher-${CALLSIGN}] Started. Watching $INBOX → tmux $TMUX_TARGET"

inotifywait -m -q -e create "$INBOX" --format '%f' 2>/dev/null | while read fname; do
    # Only process JSON metadata files
    [[ "$fname" != *.json ]] && continue

    fpath="$INBOX/$fname"
    [ ! -f "$fpath" ] && continue

    # Small delay to let file finish writing
    sleep 0.2

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
            echo "[relay-watcher-${CALLSIGN}] Text from Telegram: ${text:0:80}..."
            sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender','unknown'))" 2>/dev/null)
            # Inject into Claude's tmux pane — prefix with [TG-SENDER] so Claude knows the source
            tmux send-keys -t "$TMUX_TARGET" "[TG-${sender^^}] $text" Enter
        fi

    elif [ "$msg_type" = "photo" ]; then
        photo_path=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_path',''))" 2>/dev/null)
        caption=$(python3 -c "import json; print(json.load(open('$fpath')).get('caption',''))" 2>/dev/null)
        sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender','unknown'))" 2>/dev/null)

        echo "[relay-watcher-${CALLSIGN}] Photo from Telegram: $photo_path"
        tmux send-keys -t "$TMUX_TARGET" "[TG-${sender^^}] Dave sent a screenshot: $photo_path ${caption:+— $caption}" Enter

    elif [ "$msg_type" = "document" ]; then
        file_path=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_path',''))" 2>/dev/null)
        file_name=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_name',''))" 2>/dev/null)
        sender=$(python3 -c "import json; print(json.load(open('$fpath')).get('sender','unknown'))" 2>/dev/null)

        echo "[relay-watcher-${CALLSIGN}] Document from Telegram: $file_name"
        tmux send-keys -t "$TMUX_TARGET" "[TG-${sender^^}] Dave sent a file: $file_path ($file_name)" Enter
    fi

    # Move to processed (don't delete — audit trail)
    mv "$fpath" "$PROCESSED/" 2>/dev/null

    # Also move associated media files
    base="${fname%.json}"
    for ext in jpg png pdf doc docx txt; do
        [ -f "$INBOX/${base}.${ext}" ] && mv "$INBOX/${base}.${ext}" "$PROCESSED/" 2>/dev/null
    done
done
