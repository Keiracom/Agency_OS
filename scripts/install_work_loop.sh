#!/usr/bin/env bash
# install_work_loop.sh — Install the work-loop systemd units (Agency_OS-nkc0).
# References: keiracom-work-loop-bridge.service + keiracom-work-loop-consumer.service
#
# ⚠ GATED — DO NOT RUN until the Phase-1 cutover go-live (Dave's budget-gate
# decision). `enable --now` STARTS the self-driving loop (live auto-spawns +
# LLM spend). The script EXISTS to satisfy the deployment contract (KEI-108:
# every shipped unit is referenced by an installer) and to give the operator a
# one-command install at go-live — its existence is not its execution.
#
# Prereqs at go-live: dispatcher running (:4001), Valkey up (:6379), and the
# Vault bootstrap (VAULT_ADDR + VAULT_TOKEN) present in the dispatcher .env so
# scrubbed-tmux agents resolve their creds (P10 / Agency_OS-8dvl).
set -euo pipefail

UNITS_DIR="${HOME}/.config/systemd/user"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_DIR="${REPO_DIR}/systemd"

mkdir -p "${UNITS_DIR}"

cp "${SYSTEMD_DIR}/keiracom-work-loop-bridge.service" "${UNITS_DIR}/"
cp "${SYSTEMD_DIR}/keiracom-work-loop-consumer.service" "${UNITS_DIR}/"

systemctl --user daemon-reload

# Bridge first (the producer: Postgres task_event → Valkey), then the consumer
# (Valkey → tier-gated /dispatcher/spawn). Both Restart=always (P11 / c2xk).
systemctl --user enable --now keiracom-work-loop-bridge.service
systemctl --user enable --now keiracom-work-loop-consumer.service

echo "work-loop bridge + consumer installed and started"
