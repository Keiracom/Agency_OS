#!/usr/bin/env bash
# install_drive_strategic_indexer.sh — KEI-208 installer for the Drive → Weaviate indexer.
#
# KEI-108 CI-gate requirement: every new service ships with a per-unit named
# install script in the same PR, so a grep for the unit name finds the install
# step.  The literal unit names below are the anchors the gate scans for.
#
# Installs both the oneshot service AND the 6h timer:
#   drive-strategic-indexer.service
#   drive-strategic-indexer.timer
#
# Usage:
#   scripts/install_drive_strategic_indexer.sh           # install + enable + start timer
#   scripts/install_drive_strategic_indexer.sh --dry-run # print plan, no systemctl calls

set -euo pipefail

REPO_ROOT="/home/elliotbot/clawd/Agency_OS"
SRC_DIR="${REPO_ROOT}/infra/systemd/agents"
DST_DIR="/home/elliotbot/.config/systemd/user"
SERVICE_UNIT="drive-strategic-indexer.service"
TIMER_UNIT="drive-strategic-indexer.timer"
DRY_RUN=0

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=1
done

echo "install_drive_strategic_indexer: plan"
echo "  service : ${SRC_DIR}/${SERVICE_UNIT} -> ${DST_DIR}/${SERVICE_UNIT}"
echo "  timer   : ${SRC_DIR}/${TIMER_UNIT} -> ${DST_DIR}/${TIMER_UNIT}"

if [[ $DRY_RUN -eq 1 ]]; then
  echo "  [dry-run] no systemctl calls"
  echo "install_drive_strategic_indexer: dry-run OK"
  exit 0
fi

install -D -m 0644 "${SRC_DIR}/${SERVICE_UNIT}" "${DST_DIR}/${SERVICE_UNIT}"
install -D -m 0644 "${SRC_DIR}/${TIMER_UNIT}" "${DST_DIR}/${TIMER_UNIT}"

systemctl --user daemon-reload
systemctl --user enable --now "${TIMER_UNIT}"

echo "install_drive_strategic_indexer: ${TIMER_UNIT} installed + enabled + started"
systemctl --user --no-pager status "${TIMER_UNIT}" | head -10

# Anchor text for KEI-108 gate:
# drive-strategic-indexer.service
# drive-strategic-indexer.timer
