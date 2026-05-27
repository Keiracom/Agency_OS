#!/usr/bin/env bash
# install_agency_cost_rollup.sh — Install Cutover Blocker 1 daily cost rollup.
# References: agency-cost-rollup.service and agency-cost-rollup.timer
# bd: Agency_OS-j12p (Cutover Readiness Gate COST-TELEMETRY criterion)
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${REPO_DIR}/systemd"

mkdir -p "${UNITS_DIR}"

cp "${SYSTEMD_DIR}/agency-cost-rollup.service" "${UNITS_DIR}/"
cp "${SYSTEMD_DIR}/agency-cost-rollup.timer" "${UNITS_DIR}/"

systemctl --user daemon-reload
systemctl --user enable --now agency-cost-rollup.timer

echo "agency-cost-rollup.timer installed and started (next fire: 23:55 AEST / 13:55 UTC)"
systemctl --user list-timers agency-cost-rollup.timer --no-pager
