#!/usr/bin/env bash
# vault_envwrap_live.sh
#
# LIVE proof for the vault-envwrap launcher (vault_secrets Phase 2): a process
# launched through the launcher resolves its secrets FROM VAULT — proven by
# running with NO .env (env -i, only VAULT_ADDR/VAULT_TOKEN) so the only possible
# source is Vault. Bound as proof_gate_contract.cmd (contract.cmd=bash → a pytest
# run_cmd fails Check A).
#
# Required run_output substrings (Check B):
#   VAULT_RESOLVE_NO_ENV_OK        (--verify resolves >0 secrets with no .env)
#   WRAPPED_CMD_SAW_VAULT_SECRET=true  (exec'd cmd inherits a Vault-resolved secret)
#   VAULT_ENVWRAP_PROOF_OK
#
# Exit 0 on a verified Vault-sourced launch; 2 on assertion failure; 3 env error.
#
# ref: NOVA vault-envwrap launcher (#1448 design) built->proven.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LAUNCHER="$REPO_ROOT/scripts/vault_envwrap.py"

if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi
if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
    echo "ERROR: VAULT_ADDR/VAULT_TOKEN not set" >&2
    exit 3
fi

# 1. --verify with NO .env inheritance: the only secret source is Vault.
VOUT="$(env -i VAULT_ADDR="$VAULT_ADDR" VAULT_TOKEN="$VAULT_TOKEN" PATH="$PATH" \
    python3 "$LAUNCHER" --verify 2>&1)"
echo "$VOUT"
if echo "$VOUT" | grep -Eq "VERIFY OK — [1-9][0-9]* secrets resolved from Vault"; then
    echo "VAULT_RESOLVE_NO_ENV_OK"
else
    echo "MISSING: VAULT_RESOLVE_NO_ENV_OK" >&2
    exit 2
fi

# 2. exec mode with NO .env: the wrapped command must inherit a Vault-resolved secret.
WOUT="$(env -i VAULT_ADDR="$VAULT_ADDR" VAULT_TOKEN="$VAULT_TOKEN" PATH="$PATH" \
    python3 "$LAUNCHER" -- bash -c 'echo SAW=${ANTHROPIC_API_KEY:+true}' 2>&1)"
echo "$WOUT"
if echo "$WOUT" | grep -Fq "SAW=true"; then
    echo "WRAPPED_CMD_SAW_VAULT_SECRET=true"
else
    echo "MISSING: WRAPPED_CMD_SAW_VAULT_SECRET=true" >&2
    exit 2
fi

echo "VAULT_ENVWRAP_PROOF_OK"
exit 0
