#!/usr/bin/env bash
# install_keiracom_go_sidecar.sh — Install Wave 1 go_sidecar systemd unit.
# References: infra/keiracom_system/go_sidecar/keiracom-go-sidecar.service.
#
# Thin wrapper around the nested installer; the unit's ExecStartPre auto-runs
# scripts/build.sh if the binary is missing. Idempotent — re-running while the
# unit is active just re-installs the file + restarts.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_NAME="keiracom-go-sidecar.service"
NESTED_INSTALL="${REPO_DIR}/infra/keiracom_system/go_sidecar/scripts/install-systemd.sh"
UNIT_SOURCE="${REPO_DIR}/infra/keiracom_system/go_sidecar/${UNIT_NAME}"

if [[ ! -f "${UNIT_SOURCE}" ]]; then
    echo "missing source unit: ${UNIT_SOURCE}" >&2
    exit 2
fi
if [[ ! -f "${NESTED_INSTALL}" ]]; then
    echo "missing nested installer: ${NESTED_INSTALL}" >&2
    exit 2
fi

bash "${NESTED_INSTALL}" "$@"
echo "${UNIT_NAME} installed via ${NESTED_INSTALL}"
