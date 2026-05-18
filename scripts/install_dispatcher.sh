#!/usr/bin/env bash
# install_dispatcher.sh — Install Keiracom Dispatcher systemd user unit (KEI-213).
# References: infra/systemd/agents/dispatcher.service.
#
# Wires the merged Dispatcher components (auth_minter + interceptor_proxy +
# spend_tracker + watchdog + reaper) under one user-mode systemd service.
#
# Prerequisites:
#   1. /home/elliotbot/clawd/Agency_OS worktree on origin/main with KEI-209,
#      KEI-210, KEI-211, KEI-212 merged.
#   2. /home/elliotbot/.config/agency-os/.env populated with JWT_SECRET,
#      SUPABASE_DB_DSN, NATS_URL, and DISPATCHER_PORT (default 4001).
#   3. nats-server.service installed + active (Requires= dependency).
#   4. /home/elliotbot/clawd/Agency_OS/.venv has uvicorn + fastapi installed.
#
# Idempotent: copies the unit fresh, reloads daemon, enables + starts. Safe to
# run as part of KEI-214 identity-confirmation restart sequence (Step 3).
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE="${REPO_DIR}/infra/systemd/agents/dispatcher.service"

if [[ ! -f "${UNIT_SOURCE}" ]]; then
    echo "missing source unit: ${UNIT_SOURCE}" >&2
    exit 2
fi

mkdir -p "${UNITS_DIR}"
cp "${UNIT_SOURCE}" "${UNITS_DIR}/dispatcher.service"

systemctl --user daemon-reload
systemctl --user enable --now dispatcher.service

echo "dispatcher.service installed and started"
