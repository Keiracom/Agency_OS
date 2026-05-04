#!/usr/bin/env bash
# inbox_check_hook.sh — PreToolUse hook that checks TG inbox for new messages.
# Prints message content to stdout so Claude picks it up between tool calls.
# Replaces relay_watcher prompt-polling as primary delivery path.
#
# Callsign detection: reads IDENTITY.md from repo root (same as context_compiler).
# Falls back to "elliot" if IDENTITY.md missing.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Detect callsign from IDENTITY.md
CALLSIGN="elliot"
if [ -f "$REPO_ROOT/IDENTITY.md" ]; then
    cs=$(grep 'CALLSIGN:' "$REPO_ROOT/IDENTITY.md" 2>/dev/null | head -1 | sed 's/.*CALLSIGN:\*\*//' | sed 's/\*\*//g' | tr -d '[:space:]')
    [ -n "$cs" ] && CALLSIGN="$cs"
fi

INBOX="/tmp/telegram-relay-${CALLSIGN}/inbox"
PROCESSED="/tmp/telegram-relay-${CALLSIGN}/processed"

# Quick exit if no inbox or no messages (most common path — keep fast)
[ -d "$INBOX" ] || exit 0
shopt -s nullglob
files=("$INBOX"/*.json)
[ ${#files[@]} -eq 0 ] && exit 0

mkdir -p "$PROCESSED"

for fpath in "${files[@]}"; do
    # Parse with python for reliable JSON handling
    msg=$(python3 -c "
import json, sys
try:
    m = json.load(open('$fpath'))
    t = m.get('type', 'unknown')
    sender = m.get('sender', 'unknown').upper()
    if t == 'text':
        print(f'[TG-{sender}] {m.get(\"text\", \"\")}')
    elif t == 'photo':
        cap = m.get('caption', '')
        fp = m.get('file_path', '')
        print(f'[TG-{sender}] [PHOTO: {fp}] {cap}')
    else:
        print(f'[TG-{sender}] [{t.upper()}] {m.get(\"text\", m.get(\"caption\", \"\"))}')
except Exception as e:
    print(f'[TG-ERROR] Failed to parse {sys.argv[0]}: {e}', file=sys.stderr)
" 2>/dev/null)

    if [ -n "$msg" ]; then
        echo "$msg"
    fi

    mv "$fpath" "$PROCESSED/" 2>/dev/null || true
done
