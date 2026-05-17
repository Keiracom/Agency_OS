#!/usr/bin/env bash
# install_elliot_memories_indexer.sh — KEI-109 install entry-point.
#
# KEI-108 CI-gate requirement: per-unit named install script anchors the
# literal unit name `elliot-memories-indexer.service` for the grep gate.
#
# Usage:
#   scripts/install_elliot_memories_indexer.sh

set -euo pipefail

UNIT="elliot-memories-indexer"
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# Anchored unit: elliot-memories-indexer.service
