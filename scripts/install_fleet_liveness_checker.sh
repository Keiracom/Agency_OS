#!/usr/bin/env bash
# install_fleet_liveness_checker.sh — Install fleet liveness checker (Head of Ops directive 2026-06-02).
# Anchored units (KEI-108 grep gate):
#   fleet-liveness-checker.service
#   fleet-liveness-checker.timer
#
# Run once on the host after the PR lands on main and `git pull` has synced
# scripts/orchestrator/fleet_liveness_checker.py into ~/clawd/Agency_OS/.
# The systemd unit's ExecStart resolves to the main worktree via %h macro.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="${HOME}/.config/systemd/user"

mkdir -p "$UNIT_DIR"
cp "$REPO_ROOT/systemd/fleet-liveness-checker.service" "$UNIT_DIR/"
cp "$REPO_ROOT/systemd/fleet-liveness-checker.timer" "$UNIT_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now fleet-liveness-checker.timer

echo "fleet-liveness-checker.timer installed and started"
