#!/usr/bin/env bash
# install_heartbeat_monitor.sh — KEI-91 Gate 4 install entry-point.
#
# Installs BOTH the service (oneshot scanner) AND the timer (5-min cadence).
# KEI-108 CI-gate requirement: per-unit named install script anchors the
# literal `heartbeat-monitor.service` + `heartbeat-monitor.timer` strings
# for the grep gate.
#
# Usage:
#   scripts/install_heartbeat_monitor.sh

set -euo pipefail

SRC_DIR="/home/elliotbot/clawd/Agency_OS/infra/systemd/agents"
DST_DIR="/home/elliotbot/.config/systemd/user"

install -D -m 0644 "${SRC_DIR}/heartbeat-monitor.service" "${DST_DIR}/heartbeat-monitor.service"
install -D -m 0644 "${SRC_DIR}/heartbeat-monitor.timer"   "${DST_DIR}/heartbeat-monitor.timer"

systemctl --user daemon-reload
systemctl --user enable --now heartbeat-monitor.timer

echo "install_heartbeat_monitor: heartbeat-monitor.service + .timer installed + enabled"
systemctl --user --no-pager status heartbeat-monitor.timer | head -10

# Anchored units: heartbeat-monitor.service heartbeat-monitor.timer
