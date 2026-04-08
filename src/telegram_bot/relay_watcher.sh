#!/bin/bash
# Relay Watcher — bridges Telegram inbox to Claude's tmux pane
# Watches /tmp/telegram-relay/inbox/ for new messages
# Uses tmux send-keys to inject them into the Claude session
# This wakes Claude up as if Dave typed the message

INBOX="/tmp/telegram-relay/inbox"
TMUX_TARGET="elliottbot:0.0"
PROCESSED="/tmp/telegram-relay/processed"

mkdir -p "$INBOX" "$PROCESSED"

echo "[relay-watcher] Started. Watching $INBOX → tmux $TMUX_TARGET"

inotifywait -m -q -e create "$INBOX" --format '%f' 2>/dev/null | while read fname; do
    # Only process JSON metadata files
    [[ "$fname" != *.json ]] && continue

    fpath="$INBOX/$fname"
    [ ! -f "$fpath" ] && continue

    # Small delay to let file finish writing
    sleep 0.2

    # Parse the message
    msg_type=$(python3 -c "import json; print(json.load(open('$fpath')).get('type',''))" 2>/dev/null)

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
            echo "[relay-watcher] Text from Telegram: ${text:0:80}..."
            # Inject into Claude's tmux pane — prefix with [TG] so Claude knows the source
            tmux send-keys -t "$TMUX_TARGET" "[TG] $text" Enter
        fi

    elif [ "$msg_type" = "photo" ]; then
        photo_path=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_path',''))" 2>/dev/null)
        caption=$(python3 -c "import json; print(json.load(open('$fpath')).get('caption',''))" 2>/dev/null)

        echo "[relay-watcher] Photo from Telegram: $photo_path"
        tmux send-keys -t "$TMUX_TARGET" "[TG] Dave sent a screenshot: $photo_path ${caption:+— $caption}" Enter

    elif [ "$msg_type" = "document" ]; then
        file_path=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_path',''))" 2>/dev/null)
        file_name=$(python3 -c "import json; print(json.load(open('$fpath')).get('file_name',''))" 2>/dev/null)

        echo "[relay-watcher] Document from Telegram: $file_name"
        tmux send-keys -t "$TMUX_TARGET" "[TG] Dave sent a file: $file_path ($file_name)" Enter
    fi

    # Move to processed (don't delete — audit trail)
    mv "$fpath" "$PROCESSED/" 2>/dev/null

    # Also move associated media files
    base="${fname%.json}"
    for ext in jpg png pdf doc docx txt; do
        [ -f "$INBOX/${base}.${ext}" ] && mv "$INBOX/${base}.${ext}" "$PROCESSED/" 2>/dev/null
    done
done
