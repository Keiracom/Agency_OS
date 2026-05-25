#!/usr/bin/env bash
# install_systemd_unit.sh — install user-systemd unit for keiracom-fleet-hindsight.
#
# Mirrors the cognee.service pattern on Vultr fleet host. Host-side install
# script; the unit file lives at ~/.config/systemd/user/ (NOT in repo, since
# systemd unit content references host-absolute paths).
#
# Run once on the fleet host:
#   bash keiracom_system/fleet/hindsight/install_systemd_unit.sh
#   systemctl --user daemon-reload
#   systemctl --user enable --now keiracom-fleet-hindsight.service
#
# Idempotent: re-runs overwrite the unit file safely.
set -euo pipefail

UNIT_PATH="${HOME}/.config/systemd/user/keiracom-fleet-hindsight.service"
COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$(dirname "$UNIT_PATH")"

cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Keiracom System — Fleet Hindsight memory engine (Phase A1)
Documentation=https://github.com/Keiracom/Agency_OS/blob/main/keiracom_system/fleet/hindsight/README.md
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${COMPOSE_DIR}
ExecStartPre=/usr/bin/sg docker -c "docker compose pull"
ExecStart=/usr/bin/sg docker -c "docker compose up -d --remove-orphans"
ExecStop=/usr/bin/sg docker -c "docker compose down"
TimeoutStartSec=300

[Install]
WantedBy=default.target
UNIT

echo "Wrote ${UNIT_PATH}"
echo "Run: systemctl --user daemon-reload && systemctl --user enable --now keiracom-fleet-hindsight.service"
