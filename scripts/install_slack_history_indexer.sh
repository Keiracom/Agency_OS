#!/usr/bin/env bash
# install_slack_history_indexer.sh — KEI-201 Phase 2 systemd-user installer.
#
# Installs:
#   ~/.config/systemd/user/slack_history_indexer.service
#   ~/.config/systemd/user/slack_history_indexer.timer
#
# Then daemon-reloads, enables, and starts the timer.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_DST}"
cp -v "${SYSTEMD_SRC}/slack_history_indexer.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/slack_history_indexer.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now slack_history_indexer.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status slack_history_indexer.timer"
echo "  systemctl --user list-timers --all | grep slack_history"
echo "  journalctl --user -u slack_history_indexer.service -n 50 --no-pager"
