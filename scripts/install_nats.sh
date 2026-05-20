#!/usr/bin/env bash
# install_nats.sh — KEI-205 install entry-point.
#
# KEI-108 CI-gate requirement: per-unit install wrapper anchors the literal
# `nats-server.service` for the grep gate.
#
# What this does:
#   1. Downloads NATS server binary (idempotent — skips if already installed)
#   2. Installs the systemd user unit nats-server.service
#   3. Creates the JetStream store dir + log dir
#   4. Enables + starts the service
#   5. Verifies the service is active
#
# Stream creation is in scripts/nats_create_streams.sh — run that AFTER
# this so JetStream is up first.
#
# Usage:
#   bash scripts/install_nats.sh
#
# Post-install:
#   bash scripts/nats_create_streams.sh
#
# Anchored unit: nats-server.service

set -euo pipefail

NATS_VERSION="${NATS_VERSION:-2.10.20}"
NATS_BIN="/usr/local/bin/nats-server"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SRC="${REPO_DIR}/infra/systemd/agents/nats-server.service"
UNIT_DST="${HOME}/.config/systemd/user/nats-server.service"
CONF_SRC="${REPO_DIR}/infra/nats/nats-server.conf"
JETSTREAM_DIR="${HOME}/clawd/nats-jetstream"
LOG_DIR="${HOME}/clawd/logs"

# ----- 1. Download NATS binary if missing -----
if [[ ! -x "${NATS_BIN}" ]]; then
    echo "install_nats: NATS binary missing — downloading v${NATS_VERSION}"
    arch="$(uname -m)"
    case "${arch}" in
        x86_64)  nats_arch="amd64" ;;
        aarch64) nats_arch="arm64" ;;
        *) echo "install_nats: unsupported arch ${arch}" >&2; exit 2 ;;
    esac
    tarball="nats-server-v${NATS_VERSION}-linux-${nats_arch}.tar.gz"
    url="https://github.com/nats-io/nats-server/releases/download/v${NATS_VERSION}/${tarball}"
    tmp="$(mktemp -d)"
    trap 'rm -rf "${tmp}"' EXIT
    echo "install_nats: fetching ${url}"
    curl -sSL "${url}" -o "${tmp}/${tarball}"
    tar -xzf "${tmp}/${tarball}" -C "${tmp}"
    sudo install -m 0755 "${tmp}/nats-server-v${NATS_VERSION}-linux-${nats_arch}/nats-server" "${NATS_BIN}"
    echo "install_nats: installed $("${NATS_BIN}" --version)"
else
    echo "install_nats: NATS binary present ($("${NATS_BIN}" --version))"
fi

# ----- 2. Verify conf exists -----
if [[ ! -f "${CONF_SRC}" ]]; then
    echo "install_nats: missing config ${CONF_SRC}" >&2
    exit 2
fi

# ----- 3. Create runtime dirs -----
mkdir -p "${JETSTREAM_DIR}" "${LOG_DIR}" "$(dirname "${UNIT_DST}")"

# ----- 4. Install systemd unit -----
install -m 0644 "${UNIT_SRC}" "${UNIT_DST}"
systemctl --user daemon-reload
systemctl --user enable --now nats-server.service

# ----- 5. Verify active -----
systemctl --user is-active nats-server.service
echo "install_nats: nats-server.service installed + enabled + started"
systemctl --user --no-pager status nats-server.service | head -10

# ----- 6. Smoke health endpoint -----
sleep 1
if curl -sf http://127.0.0.1:8222/healthz >/dev/null 2>&1; then
    echo "install_nats: /healthz returned 200"
else
    echo "install_nats: WARNING /healthz did not respond (NATS may still be booting)" >&2
fi

echo
echo "Next step: bash scripts/nats_create_streams.sh"
