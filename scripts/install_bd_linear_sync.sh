#!/usr/bin/env bash
# install_bd_linear_sync.sh — Agency_OS-iosu systemd-user installer.
#
# Installs:
#   ~/.config/systemd/user/bd_linear_sync.service
#   ~/.config/systemd/user/bd_linear_sync.timer
#
# Then daemon-reloads, enables, and starts the timer.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_DST}"
cp -v "${SYSTEMD_SRC}/bd_linear_sync.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/bd_linear_sync.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now bd_linear_sync.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status bd_linear_sync.timer"
echo "  systemctl --user list-timers --all | grep bd_linear_sync"
echo "  journalctl --user -u bd_linear_sync.service -n 50 --no-pager"
echo "  tail -n 20 ~/clawd/logs/bd-linear-sync.log"
