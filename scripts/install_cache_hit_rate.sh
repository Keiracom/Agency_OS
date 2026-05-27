#!/usr/bin/env bash
# install_cache_hit_rate.sh — Install Cutover Blocker 9 cache hit-rate observability.
# References: cache_hit_rate_ingest.{service,timer} + cache_hit_rate_alert.{service,timer}
# bd: Agency_OS-if0r (Cutover Readiness Gate COST-TELEMETRY criterion)
#
# Mirrors scripts/install_agency_cost_rollup.sh shape per KEI-108 wiring discipline.
# Installs both unit+timer pairs (ingest fires at 13:50 UTC, alert at 13:53 UTC,
# sandwiched before the 23:55 AEST / 13:55 UTC CEO rollup window).
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${REPO_DIR}/systemd"

mkdir -p "${UNITS_DIR}"

cp "${SYSTEMD_DIR}/cache_hit_rate_ingest.service" "${UNITS_DIR}/"
cp "${SYSTEMD_DIR}/cache_hit_rate_ingest.timer" "${UNITS_DIR}/"
cp "${SYSTEMD_DIR}/cache_hit_rate_alert.service" "${UNITS_DIR}/"
cp "${SYSTEMD_DIR}/cache_hit_rate_alert.timer" "${UNITS_DIR}/"

systemctl --user daemon-reload
systemctl --user enable --now cache_hit_rate_ingest.timer
systemctl --user enable --now cache_hit_rate_alert.timer

echo "cache_hit_rate_ingest.timer installed and started (next fire: 13:50 UTC / 23:50 AEST)"
echo "cache_hit_rate_alert.timer installed and started (next fire: 13:53 UTC / 23:53 AEST)"
systemctl --user list-timers cache_hit_rate_ingest.timer cache_hit_rate_alert.timer --no-pager
