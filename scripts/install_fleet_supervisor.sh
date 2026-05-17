#!/usr/bin/env bash
# install_fleet_supervisor.sh — Install fleet-supervisor systemd units (KEI-174).
# References: fleet-supervisor.service and fleet-supervisor.timer
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="${REPO_DIR}/infra/systemd/agents"

mkdir -p "${UNITS_DIR}"

cp "${AGENTS_DIR}/fleet-supervisor.service" "${UNITS_DIR}/"
cp "${AGENTS_DIR}/fleet-supervisor.timer" "${UNITS_DIR}/"

systemctl --user daemon-reload
systemctl --user enable --now fleet-supervisor.timer

echo "fleet-supervisor.timer installed and started"
