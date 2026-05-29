#!/usr/bin/env bash
# install_inbox_watchers.sh — deploy the canonical inbox_watcher.sh for every
# callsign (Agency_OS-jne8 + swi6). Copies the VERSIONED script to a stable host
# path (NOT a git worktree — worktrees drift branches and would break delivery on
# checkout), rewrites each *-inbox-watcher.service to call it, reloads + restarts.
#
# Idempotent. Backs up any pre-existing unit before rewriting. Run after the
# inbox_watcher.sh PR merges (or locally to deploy the fix).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_SCRIPT="/home/elliotbot/clawd/scripts/inbox_watcher.sh"
UNITS_DIR="${HOME}/.config/systemd/user"
CALLSIGNS=(atlas orion aiden max nova scout elliot)

install -m 0755 "${REPO_DIR}/scripts/inbox_watcher.sh" "$HOST_SCRIPT"
echo "installed canonical script -> $HOST_SCRIPT"

mkdir -p "$UNITS_DIR"
for cs in "${CALLSIGNS[@]}"; do
    unit="${UNITS_DIR}/${cs}-inbox-watcher.service"
    [ -f "$unit" ] && cp -a "$unit" "${unit}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
    cat > "$unit" <<UNIT
[Unit]
Description=${cs^^} Inbox Watcher (inbox dispatch -> tmux pane injection, jne8+swi6)
After=network.target

[Service]
Type=simple
ExecStart=${HOST_SCRIPT} ${cs}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT
    echo "wrote unit: ${cs}-inbox-watcher.service -> ExecStart=${HOST_SCRIPT} ${cs}"
done

systemctl --user daemon-reload
for cs in "${CALLSIGNS[@]}"; do
    systemctl --user enable --now "${cs}-inbox-watcher.service" >/dev/null 2>&1 || true
    systemctl --user restart "${cs}-inbox-watcher.service"
    echo "${cs}-inbox-watcher: $(systemctl --user is-active "${cs}-inbox-watcher.service")"
done
echo "done — all callsign inbox watchers on the reliable injector"
