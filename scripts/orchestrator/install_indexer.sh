#!/usr/bin/env bash
# install_indexer.sh — install a multi-source indexer unit into user systemd.
#
# KEI-85 + KEI-108 enforcement: every new indexer service ships with its
# install step in the same PR so the CI gate doesn't fail on "unit added
# but not installable from this checkout."
#
# Usage:
#   scripts/orchestrator/install_indexer.sh ceo-memory-indexer
#   scripts/orchestrator/install_indexer.sh linear-state-indexer
#   etc.
#
# Idempotent — re-running on an already-installed unit just reloads.

set -euo pipefail

UNIT="${1:?usage: install_indexer.sh <unit-name-without-.service>}"
SRC="/home/elliotbot/clawd/Agency_OS/infra/systemd/agents/${UNIT}.service"
DST="/home/elliotbot/.config/systemd/user/${UNIT}.service"

if [[ ! -f "${SRC}" ]]; then
    echo "install_indexer: missing unit source: ${SRC}" >&2
    exit 2
fi

install -D -m 0644 "${SRC}" "${DST}"
systemctl --user daemon-reload
systemctl --user enable --now "${UNIT}.service"

echo "install_indexer: ${UNIT}.service installed + enabled + started"
systemctl --user --no-pager status "${UNIT}.service" | head -10
