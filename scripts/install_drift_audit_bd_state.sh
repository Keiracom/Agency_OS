#!/usr/bin/env bash
# install_drift_audit_bd_state.sh — Agency_OS-z27a systemd-user installer.
#
# Installs:
#   ~/.config/systemd/user/drift_audit_bd_state.service
#   ~/.config/systemd/user/drift_audit_bd_state.timer
#
# Then daemon-reloads, enables, and starts the timer.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_DST}"
cp -v "${SYSTEMD_SRC}/drift_audit_bd_state.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/drift_audit_bd_state.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now drift_audit_bd_state.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status drift_audit_bd_state.timer"
echo "  systemctl --user list-timers --all | grep drift_audit"
echo "  journalctl --user -u drift_audit_bd_state.service -n 50 --no-pager"
