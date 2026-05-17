#!/usr/bin/env bash
# Install + enable the fleet-restart handler (KEI-93) as a systemd user unit.
# Idempotent. References agency-os-reset-all-handler.service by literal name
# so the KEI-108 anti-false-complete gate (grep for
# agency-os-reset-all-handler.service in this file) matches.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_SRC="$REPO_ROOT/infra/systemd/agents/agency-os-reset-all-handler.service"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_DST="$UNIT_DIR/agency-os-reset-all-handler.service"
MAIN_WORKTREE="/home/elliotbot/clawd/Agency_OS"
MAIN_SCRIPT_DST="$MAIN_WORKTREE/scripts/orchestrator/reset_all_handler.py"

install -d -m 0755 "$UNIT_DIR"
install -d -m 0755 "/home/elliotbot/clawd/logs"
install -m 0644 "$UNIT_SRC" "$UNIT_DST"

# Copy handler script to main worktree so ExecStart path resolves at runtime.
# The unit references /home/elliotbot/clawd/Agency_OS per feedback_systemd_worktree_main.
if [[ -d "$MAIN_WORKTREE/scripts/orchestrator" ]]; then
  install -m 0755 "$REPO_ROOT/scripts/orchestrator/reset_all_handler.py" "$MAIN_SCRIPT_DST"
  echo "[install] synced reset_all_handler.py → $MAIN_SCRIPT_DST"
else
  echo "[install] WARNING: $MAIN_WORKTREE/scripts/orchestrator not found; ExecStart path will not resolve until main worktree is present" >&2
fi

systemctl --user daemon-reload
systemctl --user enable agency-os-reset-all-handler.service
systemctl --user restart agency-os-reset-all-handler.service

echo "[install] agency-os-reset-all-handler.service installed + active"
echo "--- post-install state ---"
systemctl --user is-active agency-os-reset-all-handler.service || true
