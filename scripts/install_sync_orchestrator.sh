#!/usr/bin/env bash
# install_sync_orchestrator.sh — KEI-229 systemd-user installer.
#
# Installs the sync-orchestrator.service unit + daemon-reloads + enables.
# Source: infra/systemd/sync-orchestrator.service (matches the repo-wide
# infra/systemd location used by completion-sync-worker.service and peers).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/infra/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_DST}"
cp -v "${SYSTEMD_SRC}/sync-orchestrator.service" "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now sync-orchestrator.service

echo
echo "Installed. Verify:"
echo "  systemctl --user status sync-orchestrator.service"
echo "  journalctl --user -u sync-orchestrator.service -n 50 --no-pager"
echo "  tail -n 20 ~/clawd/logs/sync-orchestrator.log"
