#!/usr/bin/env bash
# install_keiracom_reranker_sidecar.sh — Install Wave 2 reranker sidecar.
# References: infra/keiracom_system/reranker/keiracom-reranker-sidecar.service.
#
# Wraps docker-compose bring-up (TEI + BAAI/bge-reranker-base on :8090) under
# a user-scope systemd unit. Idempotent: re-running while healthy is a no-op.
#
# Sequence:
#   1. Bring up the docker-compose stack via the nested installer (handles
#      pull, health poll, /info lineage check, /rerank smoke).
#   2. Install keiracom-reranker-sidecar.service into ~/.config/systemd/user.
#   3. systemctl --user daemon-reload + enable --now.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_NAME="keiracom-reranker-sidecar.service"
UNIT_SOURCE="${REPO_DIR}/infra/keiracom_system/reranker/${UNIT_NAME}"
UNITS_DIR="${HOME}/.config/systemd/user"
NESTED_INSTALL="${REPO_DIR}/infra/keiracom_system/reranker/scripts/install_reranker_sidecar.sh"

if [[ ! -f "${UNIT_SOURCE}" ]]; then
    echo "missing source unit: ${UNIT_SOURCE}" >&2
    exit 2
fi
if [[ ! -x "${NESTED_INSTALL}" && ! -f "${NESTED_INSTALL}" ]]; then
    echo "missing nested installer: ${NESTED_INSTALL}" >&2
    exit 2
fi

echo "==> docker-compose bring-up via ${NESTED_INSTALL}"
bash "${NESTED_INSTALL}" "$@"

echo "==> installing ${UNIT_NAME} to ${UNITS_DIR}"
mkdir -p "${UNITS_DIR}"
cp "${UNIT_SOURCE}" "${UNITS_DIR}/${UNIT_NAME}"

systemctl --user daemon-reload
systemctl --user enable --now "${UNIT_NAME}"

echo "${UNIT_NAME} installed and started"
