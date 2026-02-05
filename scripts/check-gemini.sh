#!/bin/bash
# Quick check of recent Gemini messages in shared context
# Usage: ./check-gemini.sh [count]

COUNT=${1:-5}
CONTEXT_FILE="/home/elliotbot/clawd/data/boardroom_chat.jsonl"

echo "=== Last $COUNT Gemini messages ==="
grep '"agent": "gemini"' "$CONTEXT_FILE" | tail -n "$COUNT" | while read line; do
    ts=$(echo "$line" | jq -r '.ts // empty')
    text=$(echo "$line" | jq -r '.text // empty' | head -c 200)
    echo "[$ts]"
    echo "  $text"
    echo ""
done
