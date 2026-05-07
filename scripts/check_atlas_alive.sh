#!/usr/bin/env bash
# LAW XVIII preflight — verify ATLAS clone is alive before dispatch.
# Exit 0 alive, 1 dead. Used by scripts/dispatch_to_atlas.sh.

set -u

ATLAS_INBOX="/tmp/telegram-relay-atlas/inbox"
ATLAS_TMUX_SESSION="atlas"
ATLAS_WATCHER_SERVICE="atlas-inbox-watcher"

fail() {
    echo "DEAD: $1" >&2
    exit 1
}

# Check 1 — tmux session exists
if ! tmux has-session -t "$ATLAS_TMUX_SESSION" 2>/dev/null; then
    fail "tmux session '$ATLAS_TMUX_SESSION' not found"
fi

# Check 2 — inbox dir present and writable
if [ ! -d "$ATLAS_INBOX" ]; then
    fail "inbox dir $ATLAS_INBOX missing"
fi
if [ ! -w "$ATLAS_INBOX" ]; then
    fail "inbox dir $ATLAS_INBOX not writable"
fi

# Check 3 — watcher service active (try user scope first, then system)
if systemctl --user is-active --quiet "$ATLAS_WATCHER_SERVICE" 2>/dev/null; then
    :
elif systemctl is-active --quiet "$ATLAS_WATCHER_SERVICE" 2>/dev/null; then
    :
else
    fail "service '$ATLAS_WATCHER_SERVICE' not active (checked --user and system)"
fi

echo "ALIVE"
exit 0
