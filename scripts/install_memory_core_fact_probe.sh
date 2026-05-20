#!/usr/bin/env bash
# install_memory_core_fact_probe.sh — Agency_OS-zbvs installer.
#
# Installs memory-core-fact-probe.service + .timer (6h cadence) — the
# standing check that Cognee's recall of core system facts still matches
# ARCHITECTURE.md ground truth (the content-drift check the plumbing
# probes cannot do).
#
# KEI-108 CI-gate compliance: anchors the literal unit name
# `memory-core-fact-probe.service` for the grep gate.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_SRC="${REPO_ROOT}/infra/systemd"
SYSTEMD_DST="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/clawd/logs"

mkdir -p "${SYSTEMD_DST}" "${LOG_DIR}"
cp -v "${SYSTEMD_SRC}/memory-core-fact-probe.service" "${SYSTEMD_DST}/"
cp -v "${SYSTEMD_SRC}/memory-core-fact-probe.timer"   "${SYSTEMD_DST}/"

systemctl --user daemon-reload
systemctl --user enable --now memory-core-fact-probe.timer

echo
echo "Installed. Verify:"
echo "  systemctl --user status memory-core-fact-probe.timer"
echo "  systemctl --user list-timers --all | grep memory-core-fact"
echo "  tail -n 50 ~/clawd/logs/memory-core-fact-probe.log"
