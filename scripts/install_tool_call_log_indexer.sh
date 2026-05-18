#!/usr/bin/env bash
# install_tool_call_log_indexer.sh — KEI-54B install entry-point.
#
# KEI-108 CI-gate requirement: per-unit install wrapper anchors the literal
# `tool-call-log-indexer.service` for the grep gate. The .service unit has
# shipped without a matching install script — this PR closes that gap so
# the KEI-108 grep over `scripts/install*` finds the unit name.
#
# Usage:
#   scripts/install_tool_call_log_indexer.sh

set -euo pipefail

UNIT="tool-call-log-indexer"
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# Anchored unit: tool-call-log-indexer.service
