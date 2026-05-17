#!/usr/bin/env bash
# install_dispatcher.sh — Install dispatcher.service user unit (KEI-179).
# References: dispatcher.service
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="${REPO_DIR}/infra/systemd/agents"
LOG_DIR="${HOME}/clawd/logs"

mkdir -p "${UNITS_DIR}" "${LOG_DIR}"

cp "${AGENTS_DIR}/dispatcher.service" "${UNITS_DIR}/"

systemctl --user daemon-reload
systemctl --user enable --now dispatcher.service

systemctl --user is-active dispatcher.service
echo "dispatcher.service installed and started"
