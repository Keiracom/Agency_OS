#!/usr/bin/env bash
# install_a6_observation_alert.sh — Install Phase A6 observation-alert
# systemd user units (Agency_OS-vjcq).
#
# References:
#   infra/systemd/a6-observation-alert.service
#   infra/systemd/a6-observation-alert.timer
#
# Wires the 6-hour observation-alert cadence onto the host. The .service runs
# `scripts/a6_observation_check.sh --alert` (oneshot), which publishes a
# Viktor-voice envelope to NATS `keiracom.elliot.inbox` on FAIL_CLOSED state.
# The .timer fires every 6h (OnUnitActiveSec=6h, OnBootSec=10min).
#
# Anchored units (KEI-108 grep gate):
#   a6-observation-alert.service
#   a6-observation-alert.timer
#
# Prerequisites:
#   1. nats CLI on PATH (alert publish path).
#   2. /home/elliotbot/.config/agency-os/.env present (loaded by .service).
#   3. scripts/a6_observation_check.sh executable in this worktree.
#
# Idempotent: copies units fresh, reloads daemon, enables + starts the timer.

set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_SRC="${REPO_DIR}/infra/systemd/a6-observation-alert.service"
TIMER_SRC="${REPO_DIR}/infra/systemd/a6-observation-alert.timer"
SCRIPT_SRC="${REPO_DIR}/scripts/a6_observation_check.sh"

if [[ ! -f "${SERVICE_SRC}" ]]; then
    echo "missing source unit: ${SERVICE_SRC}" >&2
    exit 2
fi
if [[ ! -f "${TIMER_SRC}" ]]; then
    echo "missing source unit: ${TIMER_SRC}" >&2
    exit 2
fi
if [[ ! -x "${SCRIPT_SRC}" ]]; then
    echo "missing or non-executable: ${SCRIPT_SRC}" >&2
    echo "  fix: chmod +x ${SCRIPT_SRC}" >&2
    exit 2
fi

mkdir -p "${UNITS_DIR}"
cp "${SERVICE_SRC}" "${UNITS_DIR}/a6-observation-alert.service"
cp "${TIMER_SRC}"   "${UNITS_DIR}/a6-observation-alert.timer"

systemctl --user daemon-reload
systemctl --user enable --now a6-observation-alert.timer

if ! systemctl --user is-active --quiet a6-observation-alert.timer; then
    echo "a6-observation-alert.timer failed to activate" >&2
    systemctl --user status a6-observation-alert.timer >&2 || true
    exit 1
fi

echo "a6-observation-alert.timer installed and active"
systemctl --user list-timers a6-observation-alert.timer --no-pager || true
