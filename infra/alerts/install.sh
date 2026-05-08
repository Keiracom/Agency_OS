#!/usr/bin/env bash
# install.sh — copy Agency OS alert systemd units to ~/.config/systemd/user/.
#
# Idempotent. Does NOT enable/start timers — that is left as a manual ops
# step so the operator chooses when alerts go live:
#
#   systemctl --user daemon-reload
#   systemctl --user enable --now \
#       agency-os-alert-pipeline-failure.timer \
#       agency-os-alert-daily-digest.timer \
#       agency-os-alert-budget-threshold.timer \
#       agency-os-alert-lead-quality.timer
#
# To uninstall: systemctl --user disable --now <each timer>; rm the files;
# systemctl --user daemon-reload.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$DEST_DIR"

for unit in "$SRC_DIR"/agency-os-alert-*.service "$SRC_DIR"/agency-os-alert-*.timer; do
    install -m 0644 "$unit" "$DEST_DIR/"
    echo "installed: $(basename "$unit")"
done

echo
echo "8 unit files copied to $DEST_DIR"
echo "Next: systemctl --user daemon-reload && systemctl --user enable --now <timers>"
