#!/usr/bin/env bash
# install_systemd_health_monitor.sh — KEI-141 install entry-point.
#
# KEI-108 CI gate: this file anchors systemd-health-monitor.service for the grep gate.
#
# Installs the systemd-health-monitor.service (oneshot) and its 30s timer.
# Does NOT install or modify any other unit files (unit-file changes are
# Atlas's lane — file as KEI-141-followup).
#
# Usage:
#   scripts/install_systemd_health_monitor.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
LOG_DIR="/home/elliotbot/clawd/logs"

SVC_SRC="$REPO_ROOT/infra/systemd/agents/systemd-health-monitor.service"
TMR_SRC="$REPO_ROOT/infra/systemd/agents/systemd-health-monitor.timer"

# ── preflight ────────────────────────────────────────────────────────────────
for src in "$SVC_SRC" "$TMR_SRC"; do
    if [[ ! -f "$src" ]]; then
        echo "install_systemd_health_monitor: missing source: $src" >&2
        exit 2
    fi
done

install -d -m 0755 "$UNIT_DIR"
install -d -m 0755 "$LOG_DIR"

# ── copy unit files ──────────────────────────────────────────────────────────
install -m 0644 "$SVC_SRC" "$UNIT_DIR/systemd-health-monitor.service"
install -m 0644 "$TMR_SRC" "$UNIT_DIR/systemd-health-monitor.timer"

systemctl --user daemon-reload

# ── enable + start timer (timer drives the oneshot service) ─────────────────
systemctl --user enable systemd-health-monitor.timer
systemctl --user restart systemd-health-monitor.timer

echo "[install] systemd-health-monitor.timer installed + active"
echo "--- post-install timer state ---"
systemctl --user is-active systemd-health-monitor.timer || true

# Anchored unit: systemd-health-monitor.service
