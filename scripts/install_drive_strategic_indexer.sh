#!/usr/bin/env bash
# install_drive_strategic_indexer.sh — KEI Agency_OS-3nwh installer.
#
# Installs drive-strategic-indexer.service + .timer (15min cadence) into
# the user-systemd config dir. Replaces the KEI-208 thin wrapper that
# called install_indexer.sh — generic installer didn't handle timers.
#
# KEI-108 CI-gate compliance: anchors the literal unit name
# `drive-strategic-indexer.service` for the grep gate.
#
# Prerequisite: /home/elliotbot/google-service-account.json (Drive auth,
# same keyfile write_manual_mirror.py uses). Operator must provision.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/infra/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/clawd/logs"
SERVICE_ACCOUNT="/home/elliotbot/google-service-account.json"

if [[ ! -f "${SERVICE_ACCOUNT}" ]]; then
    echo "install_drive_strategic_indexer: missing ${SERVICE_ACCOUNT}" >&2
    echo "  KEI-208/3nwh indexer requires the same service-account JSON used by" >&2
    echo "  write_manual_mirror.py. Operator must provision before install." >&2
    exit 2
fi

mkdir -p "${SYSTEMD_DST}" "${LOG_DIR}"
cp -v "${SYSTEMD_SRC}/drive-strategic-indexer.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/drive-strategic-indexer.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now drive-strategic-indexer.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status drive-strategic-indexer.timer"
echo "  systemctl --user list-timers --all | grep drive-strategic"
echo "  journalctl --user -u drive-strategic-indexer.service -n 50 --no-pager"
echo "  tail -n 50 ~/clawd/logs/drive-strategic-indexer.log"

# Anchored unit: drive-strategic-indexer.service
