#!/usr/bin/env bash
# install_external_knowledge_ingester.sh — KEI-232 systemd-user installer.
#
# Installs:
#   ~/.config/systemd/user/external-knowledge-ingester.service
#   ~/.config/systemd/user/external-knowledge-ingester.timer
# Then daemon-reloads, enables, and starts the timer (weekly Sun 03:00 Sydney).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/infra/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/clawd/logs"

mkdir -p "${SYSTEMD_DST}" "${LOG_DIR}"
cp -v "${SYSTEMD_SRC}/external-knowledge-ingester.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/external-knowledge-ingester.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now external-knowledge-ingester.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status external-knowledge-ingester.timer"
echo "  systemctl --user list-timers --all | grep external-knowledge-ingester"
echo "  journalctl --user -u external-knowledge-ingester.service -n 50 --no-pager"
echo "  tail -n 50 ~/clawd/logs/external-knowledge-ingester.log"
