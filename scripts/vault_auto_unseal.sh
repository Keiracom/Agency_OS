#!/usr/bin/env bash
# vault_auto_unseal.sh — auto-unseal the persistent Vault on boot (P10 / bd lmce).
#
# The persistent Vault (container keiracom-vault, file storage) survives reboot
# but comes up SEALED — which would leave cold-spawned agents unable to resolve
# creds, failing P11 loop-recovery. This unseals it from the threshold keys in
# the 0600 init file so a reboot is non-fatal.
#
# Phase-1 auto-unseal: keys live in a root/owner-only file on the host. Security
# tradeoff (keys at rest) is accepted for single-node Phase-1 and documented in
# docs/runbooks/vault_persistence.md; prod path is cloud-KMS auto-unseal.
#
# Wire via keiracom-vault-unseal.service (runs on boot, after the container).
# Idempotent: no-op when already unsealed.
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
INIT_FILE="${VAULT_INIT_FILE:-/home/elliotbot/.config/agency-os/vault-init.json}"
PYTHON="${PYTHON:-/home/elliotbot/clawd/venv/bin/python3}"

if [[ ! -r "${INIT_FILE}" ]]; then
    echo "vault_auto_unseal: init file ${INIT_FILE} not readable" >&2
    exit 2
fi

# Wait for Vault to answer seal-status (container may still be starting).
for _ in $(seq 1 30); do
    if curl -fsS "${VAULT_ADDR}/v1/sys/seal-status" >/dev/null 2>&1; then break; fi
    sleep 2
done

VAULT_ADDR="${VAULT_ADDR}" INIT_FILE="${INIT_FILE}" "${PYTHON}" - <<'PY'
import json, os, sys, urllib.request

addr = os.environ["VAULT_ADDR"]
init = json.load(open(os.environ["INIT_FILE"]))


def _get(path):
    with urllib.request.urlopen(f"{addr}{path}", timeout=10) as r:
        return json.loads(r.read())


if not _get("/v1/sys/seal-status").get("sealed"):
    print("vault_auto_unseal: already unsealed")
    sys.exit(0)

for key in init["unseal_keys_b64"][: init.get("unseal_threshold", 3)]:
    req = urllib.request.Request(
        f"{addr}/v1/sys/unseal",
        data=json.dumps({"key": key}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)

sealed = _get("/v1/sys/seal-status").get("sealed")
print(f"vault_auto_unseal: sealed={sealed}")
sys.exit(1 if sealed else 0)
PY
