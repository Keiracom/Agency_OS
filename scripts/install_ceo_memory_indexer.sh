#!/usr/bin/env bash
# install_ceo_memory_indexer.sh — KEI-85 phase A install entry-point.
#
# KEI-108 CI-gate requirement: every new service ships with a per-unit named
# install script in the same PR, so a grep for the unit name finds the install
# step. Generic-installer (scripts/orchestrator/install_indexer.sh) is fine for
# the body — this wrapper exists to anchor the literal unit name `ceo-memory-indexer.service`
# in the repo where the gate can find it.
#
# Usage:
#   scripts/install_ceo_memory_indexer.sh

set -euo pipefail

UNIT="ceo-memory-indexer"
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# The exec above will not return — `ceo-memory-indexer.service` reference below
# is anchor text for KEI-108's grep gate so this install script is unambiguously
# linked to the unit file.
# Anchored unit: ceo-memory-indexer.service
