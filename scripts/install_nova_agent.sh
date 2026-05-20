#!/usr/bin/env bash
# install_nova_agent.sh — Install Nova engineer-clone systemd unit (KEI-185).
# References: nova-agent.service (mirrors atlas-agent / orion-agent install pattern).
#
# Prerequisites (must be in place before this script can usefully run):
#   1. /home/elliotbot/clawd/Agency_OS-nova worktree exists (git worktree add).
#   2. /home/elliotbot/.config/agency-os/.env populated with CALLSIGN=nova
#      vars + the same secrets the other agents use.
#   3. KEI-184 (SessionManager, Orion PR #1004) merged — otherwise spawn_nova
#      --force exits 2 with a clear missing-dep message.
#   4. KEI-183 (supervisor v2, Elliot PR #990) merged + FLEET_SUPERVISOR_V2_ENABLED=1
#      set in the supervisor env — until then v1 still drives + Nova is in v1's
#      AGENTS list as a no-claim placeholder.
#
# Idempotent: re-running copies the unit fresh + reloads daemon + enables if not
# already enabled. Safe to run as part of any agent-bootstrap pipeline.
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE="${REPO_DIR}/infra/systemd/agents/nova-agent.service"

if [[ ! -f "${UNIT_SOURCE}" ]]; then
    echo "missing source unit: ${UNIT_SOURCE}" >&2
    exit 2
fi

mkdir -p "${UNITS_DIR}"
cp "${UNIT_SOURCE}" "${UNITS_DIR}/nova-agent.service"

systemctl --user daemon-reload
systemctl --user enable --now nova-agent.service

echo "nova-agent.service installed and started"
