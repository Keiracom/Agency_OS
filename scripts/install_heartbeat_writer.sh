#!/usr/bin/env bash
# install_heartbeat_writer.sh — KEI-105 install entry-point.
#
# KEI-108 CI gate: this file anchors heartbeat-writer@.service for the grep gate.
#
# Usage:
#   scripts/install_heartbeat_writer.sh <callsign>     # install for one callsign
#   scripts/install_heartbeat_writer.sh --all          # install for all known callsigns

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATE_SVC="$REPO_ROOT/infra/systemd/agents/heartbeat-writer@.service"
TEMPLATE_TMR="$REPO_ROOT/infra/systemd/agents/heartbeat-writer@.timer"
UNIT_DIR="$HOME/.config/systemd/user"

ALL_CALLSIGNS=("orion" "atlas" "scout" "aiden" "max" "elliot")

# ── arg parse ────────────────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <callsign> | --all" >&2
    exit 1
fi

if [[ "$1" == "--all" ]]; then
    TARGETS=("${ALL_CALLSIGNS[@]}")
else
    TARGETS=("$1")
fi

# ── preflight ────────────────────────────────────────────────────────────────
for src in "$TEMPLATE_SVC" "$TEMPLATE_TMR"; do
    if [[ ! -f "$src" ]]; then
        echo "install_heartbeat_writer: missing source: $src" >&2
        exit 2
    fi
done

install -d -m 0755 "$UNIT_DIR"
install -d -m 0755 "/home/elliotbot/clawd/logs"

# Install template units (idempotent — same file each run)
install -m 0644 "$TEMPLATE_SVC" "$UNIT_DIR/heartbeat-writer@.service"
install -m 0644 "$TEMPLATE_TMR" "$UNIT_DIR/heartbeat-writer@.timer"

systemctl --user daemon-reload

# ── enable + start per callsign ──────────────────────────────────────────────
for cs in "${TARGETS[@]}"; do
    systemctl --user enable "heartbeat-writer@${cs}.timer" >/dev/null
    systemctl --user restart "heartbeat-writer@${cs}.timer"
    echo "[install] heartbeat-writer@${cs}.timer installed + active"
done

echo "--- post-install timer state ---"
for cs in "${TARGETS[@]}"; do
    systemctl --user is-active "heartbeat-writer@${cs}.timer" || true
done

# Anchored unit: heartbeat-writer@.service
