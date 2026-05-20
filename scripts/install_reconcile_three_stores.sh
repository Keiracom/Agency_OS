#!/usr/bin/env bash
# install_reconcile_three_stores.sh — Agency_OS-lc7b systemd-user installer (KEI-230).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_DST}"
cp -v "${SYSTEMD_SRC}/reconcile_three_stores.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/reconcile_three_stores.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now reconcile_three_stores.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status reconcile_three_stores.timer"
echo "  systemctl --user list-timers --all | grep reconcile_three_stores"
echo "  journalctl --user -u reconcile_three_stores.service -n 50 --no-pager"
