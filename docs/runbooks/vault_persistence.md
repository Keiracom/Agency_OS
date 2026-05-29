# Runbook — Persistent Vault + unseal (P10 / Agency_OS-lmce)

The cutover-grade credential store. Replaces the in-memory dev Vault (which lost
all secrets on restart → cold agents couldn't auth → P11 loop couldn't recover).

## What it is

- **Container:** `keiracom-vault` — `hashicorp/vault:1.18`, `server` (file storage, NOT `-dev`).
- **Storage:** `file` backend at `/vault/file`, host bind-mount `/home/elliotbot/clawd/vault/data` → persists across container restart AND host reboot.
- **Config:** `infra/vault/vault.hcl` (copied to `/home/elliotbot/clawd/vault/config/vault.hcl`).
- **Address:** `http://127.0.0.1:8200` (loopback only). KV v2 mount at `secret/`.
- **Secrets:** 37 fleet secrets at `secret/keiracom/<service>/<key>` (field `value`). Manifest = `src/keiracom_system/vault/kv_resolver.py` `SECRET_MANIFEST`.

## Unseal — the one manual-ish step

A file-storage Vault comes up **sealed** on every start (incl. reboot). Init
keys + root token live in **`/home/elliotbot/.config/agency-os/vault-init.json`
(mode 0600)** — `unseal_keys_b64` (5 keys, threshold 3) + `root_token`.

### Auto-unseal (Phase-1)

`keiracom-vault-unseal.service` runs `scripts/vault_auto_unseal.sh` on boot
(after `docker.service`), which reads the threshold keys from the 0600 file and
unseals — so a reboot is non-fatal and cold agents recover without a human.

Install:
```bash
install -m0644 infra/systemd/agents/keiracom-vault-unseal.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now keiracom-vault-unseal.service
```

**Security tradeoff (accepted, Phase-1 single-node):** unseal keys at rest in a
0600 file. Prod path = cloud-KMS / Transit auto-unseal (no keys on disk) — filed
as a post-Phase-1 follow-up. Do NOT commit `vault-init.json` to git (it is under
`~/.config`, outside the repo).

### Manual unseal (fallback)

If the auto-unseal service is unavailable:
```bash
python3 - <<'PY'
import json, urllib.request
init = json.load(open("/home/elliotbot/.config/agency-os/vault-init.json"))
for k in init["unseal_keys_b64"][:3]:
    urllib.request.urlopen(urllib.request.Request(
        "http://127.0.0.1:8200/v1/sys/unseal",
        data=json.dumps({"key": k}).encode(), method="POST",
        headers={"Content-Type": "application/json"}))
print("unsealed")
PY
```

## Verify

```bash
curl -s http://127.0.0.1:8200/v1/sys/seal-status   # initialized=true, sealed=false
ROOT=$(python3 -c "import json;print(json.load(open('/home/elliotbot/.config/agency-os/vault-init.json'))['root_token'])")
env -i VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN="$ROOT" \
  /home/elliotbot/clawd/venv/bin/python3 scripts/cold_auth_proof.py   # expect 18/18 PASS
```

## Re-provision (if secrets rotate / vault rebuilt)

```bash
set -a; source ~/.config/agency-os/.env; set +a
VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN="$ROOT" \
  python3 scripts/provision_vault_secrets.py
```

## Rollback

The in-memory dev Vault (`keiracom-dev-vault`) is **stopped, not removed**, for
rollback:
```bash
docker stop keiracom-vault
docker start keiracom-dev-vault     # dev token: keiracom-dev-root (in-memory; re-provision needed)
```
Rollback loses persistence — only for emergency. Forward fix is preferred.

## Known gaps

- **PREFECT_API_KEY + RAILWAY_TOKEN** are absent from `.env` (not provisioned) —
  likely needed for Phase-1; source from the Prefect/Railway dashboards and run
  the provisioner. **STRIPE_SECRET_KEY** is not Phase-1.
- Durable auto-unseal without keys-at-rest (cloud KMS) is a post-Phase-1 item.
