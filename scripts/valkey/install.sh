#!/usr/bin/env bash
# Install Valkey on the Vultr Sydney host per Linear KEI-75 / bd KEI-101.
# Idempotent. Localhost bind, RDB persistence, 2GB cgroup cap, no AUTH.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DROPIN_SRC="$REPO_ROOT/infra/valkey/memory-cap.conf"
DROPIN_DIR="/etc/systemd/system/valkey-server.service.d"
DROPIN_DST="$DROPIN_DIR/memory-cap.conf"
CONF="/etc/valkey/valkey.conf"

if ! command -v valkey-server >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y valkey-server valkey-tools
fi

if ! sudo grep -qE '^save 3600 1 300 100 60 10000' "$CONF"; then
  sudo sed -i 's|^# save 3600 1 300 100 60 10000|save 3600 1 300 100 60 10000|' "$CONF"
fi

sudo install -d -m 0755 "$DROPIN_DIR"
sudo install -m 0644 "$DROPIN_SRC" "$DROPIN_DST"
sudo systemctl daemon-reload
sudo systemctl restart valkey-server
sudo systemctl enable valkey-server >/dev/null

python3 "$REPO_ROOT/scripts/valkey/init_streams.py"

echo "--- post-install state ---"
systemctl is-enabled valkey-server
systemctl show valkey-server -p MemoryMax,MemoryHigh
valkey-cli ping
python3 "$REPO_ROOT/scripts/valkey/smoke_pubsub.py"
