#!/usr/bin/env bash
# install_silent_failure_probe.sh — Agency_OS-52wu liveness probe install.
#
# Installs silent-failure-probe.service + .timer to ~/.config/systemd/user/
# and enables the timer.
#
# Idempotent.
#
# Usage:
#   scripts/install_silent_failure_probe.sh

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../infra/alerts" && pwd)"
DST_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$DST_DIR"

install -m 0644 "${SRC_DIR}/silent-failure-probe.service" "${DST_DIR}/silent-failure-probe.service"
install -m 0644 "${SRC_DIR}/silent-failure-probe.timer"   "${DST_DIR}/silent-failure-probe.timer"

echo "installed: silent-failure-probe.service"
echo "installed: silent-failure-probe.timer"

systemctl --user daemon-reload
systemctl --user enable --now silent-failure-probe.timer

echo ""
echo "silent-failure-probe.service + .timer installed and enabled."
systemctl --user --no-pager status silent-failure-probe.timer | head -10

# Anchored units: silent-failure-probe.service silent-failure-probe.timer
