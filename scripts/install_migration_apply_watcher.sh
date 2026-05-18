#!/usr/bin/env bash
# install_migration_apply_watcher.sh — KEI-188 install entry-point.
#
# Installs BOTH the service (oneshot scanner) AND the timer (10-min cadence).
# KEI-108 CI-gate requirement: per-unit named install script anchors the
# literal `migration-apply-watcher.service` + `migration-apply-watcher.timer`
# strings for the grep gate.
#
# Usage:
#   scripts/install_migration_apply_watcher.sh

set -euo pipefail

SRC_DIR="/home/elliotbot/clawd/Agency_OS/infra/systemd/agents"
DST_DIR="/home/elliotbot/.config/systemd/user"

install -D -m 0644 "${SRC_DIR}/migration-apply-watcher.service" "${DST_DIR}/migration-apply-watcher.service"
install -D -m 0644 "${SRC_DIR}/migration-apply-watcher.timer"   "${DST_DIR}/migration-apply-watcher.timer"

systemctl --user daemon-reload
systemctl --user enable --now migration-apply-watcher.timer

echo "install_migration_apply_watcher: migration-apply-watcher.service + .timer installed + enabled"
systemctl --user --no-pager status migration-apply-watcher.timer | head -10

# Anchored units: migration-apply-watcher.service migration-apply-watcher.timer
