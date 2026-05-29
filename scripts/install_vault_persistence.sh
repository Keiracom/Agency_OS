#!/usr/bin/env bash
# install_vault_persistence.sh — stand up the persistent Keiracom Vault + boot
# auto-unseal (P10 / Agency_OS-lmce). Replaces the in-memory dev Vault.
#
# Idempotent. See docs/runbooks/vault_persistence.md for unseal/rollback.
#
# Installs:
#   - keiracom-vault container (hashicorp/vault:1.18, file storage, persistent
#     host volume) on 127.0.0.1:8200
#   - keiracom-vault-unseal.service (boot auto-unseal from the 0600 init keys)
#
# First run requires a manual init+unseal+KV-enable (the init keys must be saved
# to /home/elliotbot/.config/agency-os/vault-init.json 0600) — see the runbook.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT_HOME="${HOME}/clawd/vault"
UNITS_DIR="${HOME}/.config/systemd/user"
LOG_DIR="${HOME}/clawd/logs"
AGENCY_CFG_DIR="${HOME}/.config/agency-os"  # stable home for the boot unseal script + init keys

mkdir -p "${VAULT_HOME}/config" "${VAULT_HOME}/data" "${UNITS_DIR}" "${LOG_DIR}" "${AGENCY_CFG_DIR}"
# Only meaningful on true first install (empty dir owned by us). On re-run the dir is
# owned by the container's vault uid and this chmod is both unnecessary and not-permitted
# — so it must be non-fatal under `set -e`.
chmod 777 "${VAULT_HOME}/data" 2>/dev/null || true
# First install only: once the container is running it takes ownership of the
# bind-mounted config dir, so re-installing the hcl would fail (not-permitted) and is
# unnecessary (the running vault is already using it). Skip if present.
if [[ ! -f "${VAULT_HOME}/config/vault.hcl" ]]; then
    install -m 0644 "${REPO_DIR}/infra/vault/vault.hcl" "${VAULT_HOME}/config/vault.hcl"
fi

# Copy the unseal script to a stable, worktree-independent path (the unit's ExecStart
# targets this, NOT the repo path — see keiracom-vault-unseal.service for why).
install -m 0755 "${REPO_DIR}/scripts/vault_auto_unseal.sh" \
    "${AGENCY_CFG_DIR}/vault_auto_unseal.sh"

if ! sg docker -c "docker ps -a --format '{{.Names}}'" | grep -qx keiracom-vault; then
    echo "starting keiracom-vault (file storage)..."
    sg docker -c "docker run -d --name keiracom-vault --cap-add IPC_LOCK \
        -p 127.0.0.1:8200:8200 \
        -v ${VAULT_HOME}/config:/vault/config \
        -v ${VAULT_HOME}/data:/vault/file \
        -e VAULT_ADDR=http://127.0.0.1:8200 \
        --restart unless-stopped hashicorp/vault:1.18 server"
else
    echo "keiracom-vault already exists — leaving as-is"
fi

# Boot auto-unseal unit (KEI-108 anchor: keiracom-vault-unseal.service).
install -m 0644 "${REPO_DIR}/infra/systemd/agents/keiracom-vault-unseal.service" \
    "${UNITS_DIR}/keiracom-vault-unseal.service"
systemctl --user daemon-reload
systemctl --user enable --now keiracom-vault-unseal.service || true

echo "install_vault_persistence: done."
echo "  If first install: init+unseal+enable KV per docs/runbooks/vault_persistence.md,"
echo "  then: VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=<root> python3 scripts/provision_vault_secrets.py"
