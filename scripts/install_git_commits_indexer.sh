#!/usr/bin/env bash
# install_git_commits_indexer.sh — KEI-85 phase C install entry-point.
#
# KEI-108 CI-gate requirement: per-unit install wrapper anchors the literal
# `git-commits-indexer.service` for the grep gate.
#
# Usage:
#   scripts/install_git_commits_indexer.sh

set -euo pipefail

UNIT="git-commits-indexer"
exec /home/elliotbot/clawd/Agency_OS/scripts/orchestrator/install_indexer.sh "${UNIT}"

# Anchored unit: git-commits-indexer.service
