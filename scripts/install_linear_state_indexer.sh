#!/usr/bin/env bash
# install_linear_state_indexer.sh — KEI-85 phase B install entry-point.
#
# KEI-108 CI-gate requirement: per-unit named install script anchors the
# literal unit name `linear-state-indexer.service` for the grep gate.
#
# Usage:
#   scripts/install_linear_state_indexer.sh

set -euo pipefail

UNIT="linear-state-indexer"
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# Anchored unit: linear-state-indexer.service
