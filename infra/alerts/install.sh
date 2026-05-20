#!/usr/bin/env bash
# install.sh — copy Agency OS alert + monitor systemd units to
# ~/.config/systemd/user/, then enable+start the always-on monitor timers.
#
# Idempotent.
#
# Units copied: every file in this directory matching
# agency-os-*.service / agency-os-*.timer (the 4 alert pairs +
# 5 monitor pairs).
#
# Units AUTO-ENABLED (gap-hunt 2026-05-20 — Elliot directive):
#   agency-os-alert-vendor-budget.timer        (vendor cost drift)
#   agency-os-artifact-freshness-monitor.timer (stale governance docs)
#   agency-os-hook-failure-monitor.timer       (git hook breakage)
#   agency-os-service-health-monitor.timer     (systemd failed-unit)
#   agency-os-skill-pr-staleness-monitor.timer (skill PR drift)
# These are always-on operator-facing watchdogs — no business logic decision
# attached, so we enable them at install instead of leaving as a manual step
# that nobody runs.
#
# Units NOT auto-enabled (operator chooses when alerts go live):
#   agency-os-alert-pipeline-failure.timer
#   agency-os-alert-daily-digest.timer
#   agency-os-alert-budget-threshold.timer
#   agency-os-alert-lead-quality.timer
# Enable these manually when ready:
#   systemctl --user enable --now <timer>
#
# To uninstall: systemctl --user disable --now <each timer>; rm the files;
# systemctl --user daemon-reload.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

mkdir -p "$DEST_DIR"

copied=0
for unit in "$SRC_DIR"/agency-os-*.service "$SRC_DIR"/agency-os-*.timer; do
    install -m 0644 "$unit" "$DEST_DIR/"
    echo "installed: $(basename "$unit")"
    copied=$((copied + 1))
done

echo
echo "$copied unit files copied to $DEST_DIR"

# Auto-enable monitor timers. Idempotent — systemctl enable --now is a no-op
# if the timer is already enabled+active.
AUTO_ENABLE_TIMERS=(
    "agency-os-alert-vendor-budget.timer"
    "agency-os-artifact-freshness-monitor.timer"
    "agency-os-hook-failure-monitor.timer"
    "agency-os-service-health-monitor.timer"
    "agency-os-skill-pr-staleness-monitor.timer"
)

if command -v systemctl >/dev/null 2>&1; then
    echo
    echo "Reloading systemd user units..."
    systemctl --user daemon-reload

    echo "Enabling monitor timers..."
    for timer in "${AUTO_ENABLE_TIMERS[@]}"; do
        if systemctl --user enable --now "$timer" 2>&1; then
            echo "  enabled: $timer"
        else
            echo "  WARN: failed to enable $timer (continuing)" >&2
        fi
    done

    echo
    echo "Monitor timers active. To check status:"
    echo "  systemctl --user list-timers 'agency-os-*'"
else
    echo
    echo "WARN: systemctl not on PATH; skipped daemon-reload + timer enable." >&2
    echo "Run manually: systemctl --user daemon-reload && systemctl --user enable --now <timer>" >&2
fi
