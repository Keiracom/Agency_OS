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

mkdir -p "${VAULT_HOME}/config" "${VAULT_HOME}/data" "${UNITS_DIR}" "${LOG_DIR}"
chmod 777 "${VAULT_HOME}/data"
install -m 0644 "${REPO_DIR}/infra/vault/vault.hcl" "${VAULT_HOME}/config/vault.hcl"

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
