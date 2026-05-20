#!/usr/bin/env bash
# install_governance_freshness_probe.sh — KEI Agency_OS-cd36 installer.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/infra/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/clawd/logs"

mkdir -p "${SYSTEMD_DST}" "${LOG_DIR}"
cp -v "${SYSTEMD_SRC}/governance-freshness-probe.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/governance-freshness-probe.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now governance-freshness-probe.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status governance-freshness-probe.timer"
echo "  systemctl --user list-timers --all | grep governance-freshness"
echo "  journalctl --user -u governance-freshness-probe.service -n 50 --no-pager"
echo "  tail -n 50 ~/clawd/logs/governance-freshness-probe.log"
