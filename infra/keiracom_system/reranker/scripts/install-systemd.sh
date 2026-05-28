#!/usr/bin/env bash
# Install + enable the user-scope systemd unit for the reranker sidecar.
#
# Wave 2 dispatch Agency_OS-0thg. Idempotent. Mirrors the Wave 1 Go sidecar
# install pattern at infra/keiracom_system/go_sidecar/scripts/install-systemd.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT="keiracom-reranker-sidecar.service"
USER_UNIT_DIR="${HOME}/.config/systemd/user"

mkdir -p "${USER_UNIT_DIR}"
install -m 0644 "${ROOT}/${UNIT}" "${USER_UNIT_DIR}/${UNIT}"

systemctl --user daemon-reload
systemctl --user enable "${UNIT}"
systemctl --user restart "${UNIT}"

echo "install-systemd.sh: enabled + restarted ${UNIT}"
echo "Logs: tail -f /home/elliotbot/clawd/logs/keiracom-reranker-sidecar.log"
echo "Health: curl -fsS http://127.0.0.1:8091/health"
echo "Smoke:  bash ${ROOT}/scripts/install_reranker_sidecar.sh"
