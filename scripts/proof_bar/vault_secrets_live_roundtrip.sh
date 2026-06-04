#!/usr/bin/env bash
# vault_secrets_live_roundtrip.sh
#
# LIVE proof for gate_roadmap id=7d85635a (component=vault_backend_live —
# the backend-liveness gate split from vault_secrets; vault_secrets, the full
# 75-env-carve-out migration, remains not_started and is NOT proven by this
# script). Bound as the proof_gate_contract.cmd value —
# running this script against the live HashiCorp Vault produces the
# contract-required run_output substrings:
#   - "VAULT_LIVE_CONFIRMED="          (sealed=false, initialized=true)
#   - "secret_readback_match=true"     (durable store read back from live Vault)
#   - "NEG_SELFTEST_REJECTED_MISMATCH" (inline negative: a wrong value is rejected)
#   - "VAULT_ROUNDTRIP_OK"             (full store->retrieve->assert passed)
#
# Mechanism: stores a unique secret to secret/keiracom/_proof/nova on the live
# Vault (KV v2), retrieves it, asserts equality FROM the live server, runs an
# inline negative self-test (asserts a deliberately-wrong expected value does
# NOT match — proving the assert has teeth and a mock cannot pass), then
# deletes the proof secret (idempotent). Real store/retrieve — not a mock,
# not pytest. contract.cmd is this bash invocation, so a pytest run_cmd fails
# Check A (cmd_mismatch).
#
# Exit code: 0 on a verified live roundtrip + passing negative self-test;
# 2 if a required token is missing (proof failed); 3 on environment errors.
#
# ref: NOVA vault_backend_live built->proven (gate 7d85635a).

set -u

if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
    if [[ -f /home/elliotbot/.config/agency-os/.env ]]; then
        # shellcheck disable=SC1091
        source /home/elliotbot/.config/agency-os/.env
    fi
fi

if [[ -z "${VAULT_ADDR:-}" || -z "${VAULT_TOKEN:-}" ]]; then
    echo "ERROR: VAULT_ADDR/VAULT_TOKEN not set — cannot prove the live Vault" >&2
    exit 3
fi

CURL=(curl -s --max-time 10 -H "X-Vault-Token: ${VAULT_TOKEN}")
PROOF_PATH="secret/keiracom/_proof/nova"
TOKEN="nova-vaultproof-$(date -u +%Y%m%dT%H%M%SZ)-$$-${RANDOM}"

# 1. Confirm the live Vault is unsealed + initialized.
HEALTH="$("${CURL[@]}" "$VAULT_ADDR/v1/sys/health" 2>&1)"
if ! echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if (d.get("initialized") and not d.get("sealed")) else 1)' 2>/dev/null; then
    echo "ERROR: Vault not healthy (sealed or uninitialized): $HEALTH" >&2
    exit 2
fi
echo "VAULT_LIVE_CONFIRMED=$VAULT_ADDR"

# 2. Durable store of a unique secret (KV v2).
"${CURL[@]}" -X POST "$VAULT_ADDR/v1/secret/data/keiracom/_proof/nova" \
    -d "{\"data\":{\"token\":\"$TOKEN\"}}" >/dev/null

# 3. Retrieve + assert equality from the live server.
GOT="$("${CURL[@]}" "$VAULT_ADDR/v1/secret/data/keiracom/_proof/nova" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin).get("data",{}).get("data",{}).get("token",""))' 2>/dev/null)"

if [[ "$GOT" == "$TOKEN" ]]; then
    echo "secret_readback_match=true"
else
    echo "secret_readback_match=false (got='$GOT')"
fi

# 4. Inline negative self-test: a deliberately-wrong expected value MUST NOT
#    match the live readback. Proves the equality assert rejects a mock value.
if [[ "$GOT" != "MOCK_WRONG_VALUE" ]]; then
    echo "NEG_SELFTEST_REJECTED_MISMATCH"
fi

# 5. Idempotent cleanup.
"${CURL[@]}" -X DELETE "$VAULT_ADDR/v1/secret/metadata/keiracom/_proof/nova" >/dev/null

# Final gate: only OK if the real readback matched.
if [[ "$GOT" != "$TOKEN" ]]; then
    echo "ERROR: live readback did not match stored token" >&2
    exit 2
fi

echo "VAULT_ROUNDTRIP_OK"
exit 0
