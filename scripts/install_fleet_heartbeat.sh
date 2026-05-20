#!/bin/bash
# install_fleet_heartbeat.sh — KEI-97 install per-callsign heartbeat timer.
# Usage:  install_fleet_heartbeat.sh <callsign> [<callsign> ...]
#         install_fleet_heartbeat.sh --all     # install for the canonical fleet

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"
mkdir -p "$UNIT_DIR"

cp "$REPO_ROOT/infra/systemd/agents/fleet-heartbeat@.service" "$UNIT_DIR/"
cp "$REPO_ROOT/infra/systemd/agents/fleet-heartbeat@.timer"   "$UNIT_DIR/"

systemctl --user daemon-reload

FLEET=(elliot aiden max atlas orion scout)
if [[ "${1:-}" == "--all" ]]; then
    callsigns=("${FLEET[@]}")
else
    callsigns=("$@")
fi

if [[ ${#callsigns[@]} -eq 0 ]]; then
    echo "usage: install_fleet_heartbeat.sh <callsign> [<callsign> ...] | --all" >&2
    exit 1
fi

for cs in "${callsigns[@]}"; do
    systemctl --user enable --now "fleet-heartbeat@${cs}.timer"
    echo "installed fleet-heartbeat@${cs}.timer"
done
