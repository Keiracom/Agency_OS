#!/usr/bin/env bash
# Build the Go sidecar binary in-place. Called by the systemd ExecStartPre
# guard when the binary is missing or stale. Idempotent.
#
# Anchor: keiracom-go-sidecar.service (Wave 1 dispatch Agency_OS-2c7m).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${ROOT}/bin"
GO_BIN="${GO_BIN:-/usr/lib/go-1.22/bin/go}"

if [[ ! -x "${GO_BIN}" ]]; then
  # Fall back to PATH if the pinned version isn't installed.
  GO_BIN="$(command -v go)"
fi
if [[ -z "${GO_BIN}" || ! -x "${GO_BIN}" ]]; then
  echo "build.sh: no go binary found (tried /usr/lib/go-1.22/bin/go and PATH)" >&2
  exit 1
fi

mkdir -p "${BIN_DIR}"
cd "${ROOT}"
CGO_ENABLED=0 "${GO_BIN}" build -trimpath -ldflags='-s -w' -o "${BIN_DIR}/sidecar" ./cmd/sidecar
echo "build.sh: wrote ${BIN_DIR}/sidecar"
