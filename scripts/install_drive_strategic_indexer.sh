#!/usr/bin/env bash
# install_drive_strategic_indexer.sh — KEI-208 install entry-point.
#
# KEI-108 CI-gate requirement: per-unit install wrapper anchors the literal
# `drive-strategic-indexer.service` for the grep gate.
#
# What this does:
#   1. Verifies /home/elliotbot/google-service-account.json exists
#      (Drive auth — same keyfile write_manual_mirror.py uses)
#   2. Copies the systemd user unit + enables + starts
#   3. Tails the log to confirm first poll cycle started
#
# Re-runnable — daemon-reload + enable --now is idempotent.
#
# Usage:
#   scripts/install_drive_strategic_indexer.sh
#
# Anchored unit: drive-strategic-indexer.service

set -euo pipefail

UNIT="drive-strategic-indexer"
SERVICE_ACCOUNT="/home/elliotbot/google-service-account.json"

if [[ ! -f "${SERVICE_ACCOUNT}" ]]; then
    echo "install_drive_strategic_indexer: missing ${SERVICE_ACCOUNT}" >&2
    echo "  KEI-208 indexer requires the same service-account JSON used by" >&2
    echo "  write_manual_mirror.py. Operator must provision before install." >&2
    exit 2
fi

# Use the existing generic indexer installer.
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# Anchored unit: drive-strategic-indexer.service
