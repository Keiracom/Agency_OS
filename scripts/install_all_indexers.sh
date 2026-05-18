#!/usr/bin/env bash
# install_all_indexers.sh — install all 5 Weaviate auto-indexers in one shot.
#
# Dispatcher KEI: Elliot 2026-05-18 directive — install the indexer fleet
# on the Vultr Sydney host. Wraps the per-unit installers (each of which
# wraps scripts/orchestrator/install_indexer.sh) so an operator with SSH
# to the host can deploy the whole stack with one command.
#
# Idempotent — re-running on already-installed units just reloads.
#
# Usage:
#   ssh vultr-sydney
#   cd /home/elliotbot/clawd/Agency_OS && git pull
#   bash scripts/install_all_indexers.sh
#
# Post-install verify (one-liner):
#   for u in ceo-memory elliot-memories git-commits linear-state tool-call-log; do
#       systemctl --user is-active "${u}-indexer.service" || echo "FAIL: ${u}"
#   done

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${HOME}/clawd/logs"
mkdir -p "${LOG_DIR}"

INDEXERS=(
    ceo-memory
    elliot-memories
    git-commits
    linear-state
    tool-call-log
)

echo "install_all_indexers: installing ${#INDEXERS[@]} units"

failed=()
for name in "${INDEXERS[@]}"; do
    script="${REPO_DIR}/scripts/install_${name//-/_}_indexer.sh"
    if [[ ! -x "${script}" ]]; then
        echo "install_all_indexers: SKIP ${name} — missing ${script}" >&2
        failed+=("${name} (missing installer)")
        continue
    fi
    echo "----- ${name} -----"
    if ! bash "${script}"; then
        echo "install_all_indexers: FAIL ${name}" >&2
        failed+=("${name}")
    fi
done

echo "----- verify -----"
for name in "${INDEXERS[@]}"; do
    unit="${name}-indexer.service"
    if systemctl --user is-active "${unit}" >/dev/null 2>&1; then
        echo "  ${unit}: active"
    else
        echo "  ${unit}: NOT ACTIVE" >&2
        failed+=("${name} (not active post-install)")
    fi
done

if ((${#failed[@]} > 0)); then
    echo "install_all_indexers: ${#failed[@]} failure(s):" >&2
    printf '  - %s\n' "${failed[@]}" >&2
    exit 1
fi

echo "install_all_indexers: all ${#INDEXERS[@]} indexers installed + active"

# Anchored units (KEI-108 grep targets — DO NOT remove):
# - ceo-memory-indexer.service
# - elliot-memories-indexer.service
# - git-commits-indexer.service
# - linear-state-indexer.service
# - tool-call-log-indexer.service
