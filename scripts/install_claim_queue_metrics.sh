#!/usr/bin/env bash
# install_claim_queue_metrics.sh — KEI-136 systemd-user installer.
#
# Installs:
#   ~/.config/systemd/user/claim_queue_metrics.service
#   ~/.config/systemd/user/claim_queue_metrics.timer
#
# Then daemon-reloads, enables, and starts the timer.
#
# Prerequisites (one-time operator setup):
#   1. Create the BS heartbeat — see docs/runbooks/claim_queue_observability.md
#   2. Append CLAIM_QUEUE_HEARTBEAT_URL=https://uptime.betterstack.com/api/v1/heartbeat/...
#      to ~/.config/agency-os/.env
#
# Without CLAIM_QUEUE_HEARTBEAT_URL the exporter exits clean (no fail-loud);
# safe to install before BS setup is complete.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"

mkdir -p "${SYSTEMD_DST}"
cp -v "${SYSTEMD_SRC}/claim_queue_metrics.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/claim_queue_metrics.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now claim_queue_metrics.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status claim_queue_metrics.timer"
echo "  systemctl --user list-timers --all | grep claim_queue"
echo "  journalctl --user -u claim_queue_metrics.service -n 50 --no-pager"
