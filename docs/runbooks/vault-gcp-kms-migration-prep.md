# Vault Transit — GCP KMS Auto-Unseal Migration Prep

**Status:** RESEARCH + PREP. **No provisioning. No code changes. No live-Vault touches.**
**Owner:** Aiden (review/governance) + engineer-tier TBD (execution) + Elliot (policy).
**Anchor:** `infra.secrets_management` (Cat 16, V1-launch HARD GATE — Phase 2 sub-deliberation item (a): "Vault unseal posture — Cloud-KMS auto-unseal vs shamir-shares-on-disk vs manual").
**Beads:** Agency_OS-djeb (pre-launch hardening), Agency_OS-hpst (queue).
**Cross-cite — KV backend:** Agency_OS-2mbs (KV v2 backend setup, referenced in dispatch).
**Cross-cite — Transit phase work:** Vault Transit Phase A1 (referenced in dispatch; no script artefact in current repo HEAD — see §0 honest-state probe).
**Dispatched:** elliot 2026-05-26.
**LAW XIV mandate:** verbatim Vault config, verbatim CLI commands, raw cost arithmetic.
**LAW II — currency:** all financial outputs $AUD at 1 USD = 1.55 AUD.

---

## §0 — Honest-state probe (repo + GCP)

Before writing the rest of this runbook, surfacing what is and isn't true at probe time so engineer-tier doesn't act on stale assumptions:

| Claim | State at probe (2026-05-26) | Note |
|---|---|---|
| `scripts/install_prod_vault.sh` exists | ❌ NOT in repo | Dispatch cross-cite references it; `find` across all worktrees returned 0 hits. Treat as historical artefact or pending PR. Engineer-tier verifies before depending. |
| `src/keiracom_system/vault/vault_decryptor.py` | ✅ exists | Only Vault-related code in current `origin/main`. Tests at `tests/keiracom_system/vault/test_vault_decryptor.py`. |
| Live production Vault running | UNKNOWN from repo | Repo has the client-side decryptor but no installer / config / systemd unit. Engineer-tier confirms via the actual host (Vultr per `infra.secrets_management` row). |
| GCP service account `elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com` | Referenced but not probed | `gcloud` CLI not present in scout's worktree; probe at engineer-tier execution time. |
| Existing GCP project + key rings | UNKNOWN | None visible to scout. Engineer-tier confirms via `gcloud kms keyrings list`. |
| Vault Transit Phase A1 PR | Referenced in dispatch but no PR number cited | Engineer-tier cross-checks `gh pr list --search vault` before depending. |

**Read-out:** this runbook is **migration-prep**, not a step-by-step playbook ready to run against a live cluster. Engineer-tier must verify the §0 unknowns before lifting any HOLD on the actual migration execution.

---

## §1 — GCP service account requirements (roles + key ring + crypto key permissions)

### 1.1 Minimum IAM permissions (the underlying ACL)

Per [Vault GCP KMS seal docs](https://developer.hashicorp.com/vault/docs/configuration/seal/gcpckms), the service account must hold these three permissions on the specific crypto key resource:

```
cloudkms.cryptoKeyVersions.useToEncrypt
cloudkms.cryptoKeyVersions.useToDecrypt
cloudkms.cryptoKeys.get
```

These are the *granular* permissions — the same set that any predefined role bundles up.

### 1.2 Predefined role recommendation

Vault docs name a predefined role for cleaner granting:

> **`roles/cloudkms.cryptoKeyEncrypterDecrypter`** — covers `useToEncrypt` + `useToDecrypt`.

The third permission (`cloudkms.cryptoKeys.get`) is required for Vault to read crypto-key metadata at startup. `cryptoKeyEncrypterDecrypter` does **not** include `cryptoKeys.get`. **Two paths:**

- **Path A (least-privilege, recommended):** grant `cryptoKeyEncrypterDecrypter` + a custom role / additional binding that gives `cloudkms.cryptoKeys.get`.
- **Path B (slightly broader):** grant `roles/cloudkms.viewer` on the key ring (includes `get`) in addition to `cryptoKeyEncrypterDecrypter`. Adds list/view ability on sibling keys — acceptable if the key ring has only the Vault-unseal key.

Engineer-tier picks A or B; both are defensible. **Recommend A** for V1 — least surprise + least audit-log noise.

### 1.3 Scope of the IAM grant — resource-level, NOT project-wide

```
gcloud kms keys add-iam-policy-binding \
  vault-unseal-key \
  --location=australia-southeast1 \
  --keyring=keiracom-vault-unseal \
  --member=serviceAccount:<vault-unseal-sa-email> \
  --role=roles/cloudkms.cryptoKeyEncrypterDecrypter
```

Note `add-iam-policy-binding` is invoked on the **specific crypto key** (`vault-unseal-key`), NOT on the project. Granting at project level inflates blast radius — if the SA is compromised, attacker has KMS encrypt/decrypt on every key in the project, not just the unseal key.

### 1.4 Key ring + crypto key creation prerequisites

- **Key ring location:** must match Vault server region. Recommend **`australia-southeast1`** (Sydney) to match `vercel.json` `"regions": ["syd1"]` + LAW II Australia-first.
- **Key purpose:** `ENCRYPT_DECRYPT` (symmetric).
- **Protection level:** `SOFTWARE` for V1 ($0.06 USD/mo). `HSM` is $1.00 USD/mo and adds FIPS 140-2 Level 3 — overkill pre-revenue.
- **Rotation period:** Vault docs recommend **automatic rotation enabled** (90-day default). KMS handles key version transitions transparently; Vault re-wraps the barrier key on next unseal cycle.

### 1.5 Service account creation commands (engineer-tier reference, not for execution from this doc)

```
# 1. Create the dedicated service account (NOT the elliotbot SA — see §6)
gcloud iam service-accounts create vault-unseal \
  --display-name="Vault auto-unseal (KMS encrypt/decrypt only)" \
  --description="Least-priv SA for Vault seal=gcpckms; only the seal key" \
  --project=<gcp-project-id>

# 2. Create the key ring
gcloud kms keyrings create keiracom-vault-unseal \
  --location=australia-southeast1 \
  --project=<gcp-project-id>

# 3. Create the crypto key
gcloud kms keys create vault-unseal-key \
  --keyring=keiracom-vault-unseal \
  --location=australia-southeast1 \
  --purpose=encryption \
  --rotation-period=90d \
  --next-rotation-time=2026-08-26T00:00:00Z \
  --project=<gcp-project-id>

# 4. Bind least-priv role on the SPECIFIC key (NOT project-wide)
gcloud kms keys add-iam-policy-binding vault-unseal-key \
  --keyring=keiracom-vault-unseal \
  --location=australia-southeast1 \
  --member=serviceAccount:vault-unseal@<gcp-project-id>.iam.gserviceaccount.com \
  --role=roles/cloudkms.cryptoKeyEncrypterDecrypter \
  --project=<gcp-project-id>

# 5. Also bind the `get` permission via viewer role on the key ring
#    (or build a custom role with just cryptoKeys.get — engineer-tier choice)
gcloud kms keyrings add-iam-policy-binding keiracom-vault-unseal \
  --location=australia-southeast1 \
  --member=serviceAccount:vault-unseal@<gcp-project-id>.iam.gserviceaccount.com \
  --role=roles/cloudkms.viewer \
  --project=<gcp-project-id>

# 6. Generate a JSON credentials file for the Vault host
gcloud iam service-accounts keys create /tmp/vault-unseal-creds.json \
  --iam-account=vault-unseal@<gcp-project-id>.iam.gserviceaccount.com
```

After step 6: move the JSON file to the Vault host at a path Vault can read (recommend `/etc/vault.d/gcp-unseal-creds.json`, mode `0400`, owner `vault:vault`).

---

## §2 — Vault config block — the `seal "gcpckms"` stanza

### 2.1 Verbatim stanza syntax (per official Vault docs)

```hcl
seal "gcpckms" {
  credentials = "/etc/vault.d/gcp-unseal-creds.json"
  project     = "<gcp-project-id>"
  region      = "australia-southeast1"
  key_ring    = "keiracom-vault-unseal"
  crypto_key  = "vault-unseal-key"
}
```

### 2.2 Parameter table (verbatim from Vault docs)

| Parameter | Type | Required | Purpose |
|---|---|---|---|
| `credentials` | string | required | Path to JSON credentials file on the Vault host disk. |
| `project` | string | required | GCP project ID where the key ring lives. |
| `region` | string | required | GCP region / location for the key ring. |
| `key_ring` | string | required | GCP KMS key ring name. |
| `crypto_key` | string | required | GCP KMS crypto key (within the key ring) used for sealing. |
| `disabled` | string | `""` | Set to `true` only when migrating FROM auto-unseal back to Shamir — irrelevant for Shamir→KMS direction. |

### 2.3 Authentication modes (three supported)

Per Vault docs, Vault picks credentials in this order:

1. **JSON file path** via the `credentials =` parameter — recommended for V1 (explicit + auditable + bind-mountable).
2. **Environment variables** — `GOOGLE_CREDENTIALS` or `GOOGLE_APPLICATION_CREDENTIALS`, plus `GOOGLE_PROJECT` and `GOOGLE_REGION`.
3. **Application Default Credentials** — picked up automatically if Vault runs on a GCE instance with a service account attached.

**Recommendation for V1:** explicit JSON file path (option 1). Vultr-hosted Vault (per `infra.secrets_management` row) means Application Default Credentials don't apply — we're not on GCE.

### 2.4 Stanza placement in `vault.hcl` (critical)

The `seal` stanza is **top-level**, not nested under `listener` or `storage`. Common mistake — drop it at the same depth as `storage "raft"` or `listener "tcp"`. Example minimum config:

```hcl
ui            = true
disable_mlock = true
cluster_addr  = "https://vault-1.keiracom.internal:8201"
api_addr      = "https://vault.keiracom.app:8200"

storage "raft" {
  path    = "/opt/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_cert_file = "/etc/vault.d/tls.crt"
  tls_key_file  = "/etc/vault.d/tls.key"
}

seal "gcpckms" {
  credentials = "/etc/vault.d/gcp-unseal-creds.json"
  project     = "<gcp-project-id>"
  region      = "australia-southeast1"
  key_ring    = "keiracom-vault-unseal"
  crypto_key  = "vault-unseal-key"
}
```

(The storage + listener stanzas above are illustrative; engineer-tier confirms against actual production config when it surfaces.)

---

## §3 — Migration procedure (Shamir → GCP KMS) — sequenced runbook

### 3.1 Pre-flight (BEFORE touching anything)

```bash
# 1. Confirm Vault current state
vault status
#   - Expect: Sealed=false, Storage Type=raft (or whatever), Seal Type=shamir, Initialized=true

# 2. Confirm shamir key threshold + share count
vault operator key-status
#   - Read out: M-of-N key shares (typical: 3 of 5)

# 3. CRITICAL: snapshot existing Vault data — DO NOT SKIP
#    Per HashiCorp docs verbatim: "You should make sure to create a backup before
#    you start the seal migration process, in case something goes wrong."
vault operator raft snapshot save /tmp/vault-pre-migration-$(date -u +%Y%m%dT%H%M%SZ).snap
#   - Verify: ls -la the snapshot, sha256sum it, copy to off-host storage

# 4. Confirm GCP KMS prerequisites exist (per §1.5 creation steps already complete)
gcloud kms keys describe vault-unseal-key \
  --keyring=keiracom-vault-unseal \
  --location=australia-southeast1

# 5. Confirm Vault host can authenticate to GCP KMS
sudo -u vault GOOGLE_APPLICATION_CREDENTIALS=/etc/vault.d/gcp-unseal-creds.json \
  gcloud auth application-default print-access-token
#   - Should print a token string; failure = SA binding wrong → STOP

# 6. Note the M shamir keys + the M-of-N threshold — required for the unseal -migrate step
#    These are held by the keyholders per the M-of-N policy; gather quorum before continuing
```

### 3.2 Execution (the actual cutover — irreversible to Shamir without restore)

Per Vault [seal-concept docs](https://developer.hashicorp.com/vault/docs/concepts/seal) §Seal Migration:

```bash
# Step 1 — Take server cluster offline
sudo systemctl stop vault
#   - Single-node V1 = simple. HA cluster = quiesce nodes one at a time.

# Step 2 — Update the seal configuration
#   Edit /etc/vault.d/vault.hcl — ADD the seal "gcpckms" block (per §2.4).
#   IMPORTANT: do NOT remove any existing seal stanza if you have one
#              (Shamir is "no stanza" — there's nothing to remove).
sudo nano /etc/vault.d/vault.hcl
sudo vault operator validate -config=/etc/vault.d/vault.hcl
#   - Confirms HCL parses + seal stanza is recognised

# Step 3 — Bring Vault back up
sudo systemctl start vault
vault status
#   - Expect: Sealed=true, Seal Type=gcpckms, Initialized=true, Migration in progress

# Step 4 — Multi-node only: leave remaining nodes offline during migration
#   (Single-node Vultr V1 skips this step.)

# Step 5 — Run the unseal process WITH the -migrate flag
#   For each of M shamir keys (one per keyholder), run:
vault operator unseal -migrate
#   - Vault prompts: "Unseal Key (will be hidden):"
#   - Each keyholder enters their key share
#   - After M-of-N met: Vault completes migration
#   - VERBATIM from docs: "Once you enter the required threshold of unseal keys,
#     Vault migrates the unseal keys to recovery keys."

# Step 6 — Multi-node only: bring remaining nodes back online; they auto-unseal via KMS

# Step 7 — Verify
vault status
#   - Expect: Sealed=false, Seal Type=gcpckms, Initialized=true, Migration complete
vault operator key-status
#   - Confirms recovery keys (formerly shamir unseal keys) intact
```

### 3.3 Post-cutover verification

```bash
# 1. Restart Vault to confirm auto-unseal actually works
sudo systemctl restart vault
sleep 5
vault status
#   - Expect: Sealed=false within ~5s of restart (auto-unsealed via KMS)
#   - If Sealed=true after 30s → KMS unseal FAILED → roll forward to §4 failure modes

# 2. Confirm GCP KMS shows the encrypt+decrypt audit-log entries
gcloud logging read 'resource.type="cloudkms_cryptokey" AND \
  resource.labels.crypto_key_id="vault-unseal-key" AND \
  protoPayload.methodName=~"Decrypt"' \
  --limit=10 --format=json

# 3. Confirm the new RECOVERY keys (formerly shamir unseal keys) work
#    by generating a new root token via recovery keys:
vault operator generate-root -init
# Each recovery keyholder provides their share via:
vault operator generate-root <one-time-password>
#    Discard the generated root token after verify (or keep for next admin op).

# 4. Snapshot post-migration state
vault operator raft snapshot save /tmp/vault-post-migration-$(date -u +%Y%m%dT%H%M%SZ).snap

# 5. Document the migration in #ceo via NATS / Slack relay
```

### 3.4 Rollback path — there isn't a clean one

Per the HashiCorp seal-concept doc: **"No explicit rollback procedure is documented"** for Shamir→KMS migration. The auto-unseal→Shamir reverse migration IS documented (using `disabled = "true"` on the old auto-seal stanza) — but for Shamir→KMS specifically, the rollback is:

1. **Best path: restore from pre-migration snapshot.** Stop Vault, replace `/opt/vault/data` with the pre-migration snapshot contents, remove the `seal "gcpckms"` stanza from vault.hcl, restart. Vault is back at Shamir state.
2. **No-snapshot path:** if the snapshot was lost (don't!), the only path is auto-unseal→Shamir reverse migration — but this requires the auto-unseal to be WORKING. If KMS access is what broke, this path is unavailable. **Total break.**

**Implication for the runbook:** §3.1 step 3 (snapshot before migration) is **not optional**. It is the only rollback path.

---

## §4 — Failure modes during migration

Five concrete failure modes — what each looks like + recovery shape.

### 4.1 SA permissions wrong (most common)

**Symptom:** Vault start logs show:
```
[ERROR] core: failed to setup seal: error="failed to encrypt with GCP CKMS: rpc error: code = PermissionDenied"
```
**Recovery:** check the IAM policy binding on the crypto key (§1.3 verbatim command). Re-bind if missing. Restart Vault.

### 4.2 Wrong key_ring or crypto_key name

**Symptom:**
```
[ERROR] core: failed to setup seal: error="failed to retrieve key: rpc error: code = NotFound"
```
**Recovery:** `gcloud kms keys list --keyring=<name> --location=<location>` to confirm name. Fix `vault.hcl`. Restart.

### 4.3 Wrong region

**Symptom:** same NotFound as 4.2 but with subtle dns/region-not-found wrapper. Distinguishing test:
```bash
gcloud kms keyrings describe keiracom-vault-unseal --location=australia-southeast1
# vs
gcloud kms keyrings describe keiracom-vault-unseal --location=global
```
Only one of these returns the resource; that's the right region.

### 4.4 Shamir keyholder quorum not gathered

**Symptom:** `vault operator unseal -migrate` blocks indefinitely waiting for more keys. Vault stays Sealed=true.
**Recovery:** gather the remaining keyholders. If keyholders unavailable: there is NO recovery (Vault's encryption-at-rest is mathematically dependent on the M-of-N threshold). Restore from the pre-migration snapshot.

### 4.5 GCP KMS network unreachable at unseal time

**Symptom:** Vault hangs at startup, log shows:
```
[WARN] core: seal could not unseal: error="failed to decrypt with GCP CKMS: context deadline exceeded"
```
**Recovery:** confirm Vault host has egress to `cloudkms.googleapis.com:443`. Vultr firewall + DNS check. **Once KMS is reachable, Vault auto-recovers** (no manual intervention).

### 4.6 KMS key version deleted (catastrophic)

**Symptom:** Vault won't unseal; KMS API returns `KEY_VERSION_DESTROYED`.
**Recovery:** **none.** Without the key version that wrapped Vault's barrier key, the encrypted barrier key is unrecoverable. **This is why GCP KMS key deletion is a 30-day soft-delete by default — the engineer-tier MUST NOT short-circuit that with `gcloud kms keys versions destroy --immediate`.**

**Prevention:** add a constraint to the GCP project preventing immediate-destroy of crypto key versions. Documented as engineer-tier item 7 below.

---

## §5 — Cost estimate (AUD per month)

### 5.1 GCP KMS pricing facts (verbatim, 2026)

Per [GCP Cloud KMS pricing](https://cloud.google.com/kms/pricing):

| Item | USD price | AUD (×1.55) |
|---|---:|---:|
| Key ring | FREE | FREE |
| Active key version (SOFTWARE protection, symmetric) | $0.06/month | **$0.093/month** |
| Active key version (HSM protection) | $1.00/month | $1.55/month |
| Active key version (EXTERNAL) | $3.00/month | $4.65/month |
| Cryptographic operations | $0.03 per 10,000 ops | **$0.0465 per 10,000 ops** |
| Key rotation | FREE | FREE |
| Free tier | 10,000 ops/month — Autokey-only | not applicable to our setup |

### 5.2 Vault auto-unseal usage pattern — the load-bearing insight

**Vault uses the KMS unseal key for ONE thing:** wrapping the Vault barrier key. Operations:

- 1 KMS decrypt op per Vault startup (typical production: 0-5/day; restart-light)
- 1 KMS encrypt op when the barrier key is rotated (Vault default: never automatic; only via `vault operator rekey`)
- **0 KMS ops during steady-state Vault running** (barrier key stays in memory)

**The number of secrets stored in Vault does NOT drive KMS cost.** A 1-secret Vault and a 10,000-secret Vault use the same single barrier key, wrapped by the same single KMS key. This is the key insight engineer-tier should internalise.

### 5.3 Cost projection table

| Stage | Vault clusters | Secrets | Ops/month estimate | Active key versions | Monthly cost (AUD) |
|---|---:|---:|---:|---:|---:|
| V1 (now) | 1 | ~10 | ~30 unseal cycles | 1 | **~$0.09 AUD** |
| V1.x | 1 | ~100 | ~30 unseal cycles | 1 | **~$0.09 AUD** |
| Multi-tenant single-Vault | 1 | ~1000 | ~50 unseal cycles | 1 | **~$0.09 AUD** |
| Multi-tenant per-tenant-Vault (if topology shifts at 20-30 tenant tripwire) | N | ~1000 | ~50N unseal cycles | N | **~$0.09 × N AUD** |

**Arithmetic for the per-tenant scenario (N = 100 tenants):**
- 100 active key versions × $0.06 USD = $6.00 USD/month = **$9.30 AUD/month**
- 100 × 50 unseal cycles = 5,000 ops/month → $0.03 × (5000 / 10000) = $0.015 USD = **$0.023 AUD/month**
- **Total at N=100: ~$9.32 AUD/month**

**Read-out:** KMS cost is bounded by **cluster count**, not secret count. V1 cost is **negligible** ($0.09 AUD/month) and the pricing model rewards the single-Vault-multi-tenant topology over per-tenant-Vault for KMS spend alone. Other factors (security blast radius, HA tripwire per `infra.secrets_management` Phase 2 sub-deliberation item c — "Vault HA tripwire at 20-30 tenants") may still drive per-tenant topology later.

### 5.4 Hidden costs to flag

- **GCP egress** from the Vault host to `cloudkms.googleapis.com` — counts against Vultr's egress bandwidth. Per-unseal payload is small (<1KB); 50 ops/month × 1KB = 50KB/month. **Negligible.**
- **GCP logging** — KMS audit logs (recommended for security review) cost ~$0.50 USD/GB ingested. Auto-unseal generates ~1KB/op. 50 ops × 12 months × 1KB = 600KB/yr. **<$0.001 AUD/yr.** Negligible.
- **Key rotation** — free per GCP pricing. Recommended quarterly (90-day rotation period).
- **Recovery key custody** — not a GCP cost; engineering / policy cost. M-of-N recovery key shares need secure custody (offline storage, multi-keyholder).

---

## §6 — Service account reuse vs fresh KMS-scoped account

### 6.1 The existing account

`elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com` is the Elliot orchestrator's general-purpose Google account. From the env-var probe in §0, it touches:
- Google Drive (Manual doc, ceo briefing, intelligence feed)
- Gmail (OAuth client)
- Google API key

The account is multi-purpose, shared across many fleet workflows.

### 6.2 The least-privilege recommendation — DO NOT REUSE

**Recommend a fresh dedicated SA** for Vault auto-unseal. Reasons in order of weight:

1. **Blast radius.** If `elliottbot` SA credentials leak (Drive scope is broad, more attack surface), an attacker would also get KMS decrypt on the Vault unseal key. **One compromised credential = Vault sealed-state broken.**
2. **Audit clarity.** Separate SA = separate `protoPayload.authenticationInfo.principalEmail` in GCP audit logs. Easier to detect "this KMS unseal happened — was it Vault, or was someone else?"
3. **IAM clarity.** GCP-canonical pattern is one role per SA. `elliottbot` already holds multiple roles; adding KMS roles entangles the IAM graph further.
4. **Rotation.** Vault unseal SA can be rotated independently of Drive workflows. With `elliottbot`, a rotation affects everything at once → coordination headache.
5. **Naming/intent.** `vault-unseal@...iam.gserviceaccount.com` is self-documenting; future engineers can identify purpose at a glance.

### 6.3 Recommended SA shape

```
Name:         vault-unseal
Email:        vault-unseal@<gcp-project-id>.iam.gserviceaccount.com
Display:      Vault auto-unseal (KMS encrypt/decrypt only)
Description:  Least-priv SA for Vault seal=gcpckms; only the unseal key
Role:         roles/cloudkms.cryptoKeyEncrypterDecrypter  ON  vault-unseal-key
              + roles/cloudkms.viewer ON keiracom-vault-unseal key-ring (or custom role w/ only cloudkms.cryptoKeys.get)
Keys:         exactly one JSON key, mounted at /etc/vault.d/gcp-unseal-creds.json on the Vault host
```

### 6.4 Cost of the new SA

Zero. GCP service accounts are free; only the resources they consume cost money. KMS pricing already covered in §5.

### 6.5 If engineer-tier disagrees and wants reuse

The dispatch asked the question, so honest answer to "can it be reused?" — **yes technically, no architecturally.** Reuse path:

```
gcloud kms keys add-iam-policy-binding vault-unseal-key \
  --keyring=keiracom-vault-unseal \
  --location=australia-southeast1 \
  --member=serviceAccount:elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com \
  --role=roles/cloudkms.cryptoKeyEncrypterDecrypter
```

This works. It just adds Vault-unseal-key access to a credential that already opens Drive + Gmail + Google APIs. **Recommend NOT taking this path.** Surface to Aiden + Elliot if engineer-tier wants to debate.

---

## §7 — Engineer-tier handoff scope (what's left after this prep doc)

This runbook is **prep**, not execution. The remaining engineer-tier items:

1. **Confirm §0 honest-state probe unknowns** — does `install_prod_vault.sh` exist somewhere not visible to scout? Is there a live Vault instance? What's the actual Vault version? ~30 min.
2. **Dave decision** — proceed with the migration? (Out of scope for engineer-tier; orchestrator gate.)
3. **Commercial cost approval** — even though §5 says ~$0.09 AUD/month, formal approval per `infra.secrets_management` HARD GATE governance. ~10 min (post #ceo, get verbatim sign-off).
4. **Provision GCP KMS key ring + key + SA** per §1.5 commands. ~15 min.
5. **Capture pre-migration Vault snapshot** per §3.1 step 3. ~5 min.
6. **Execute migration** per §3.2 sequenced steps. ~30 min including keyholder coordination.
7. **Post-cutover verification** per §3.3. ~15 min.
8. **Lock down KMS key deletion** — add an organization policy or GCP constraint preventing immediate-destroy of the unseal key version (per §4.6 prevention). ~15 min.
9. **Document the actual production state** — replace this prep doc's `<gcp-project-id>` placeholders with the real id (or move to a separate operate runbook). ~10 min.
10. **Drill quarterly** — restart Vault from a cold state, verify auto-unseal works. Mirrors KEI-126 Postgres restore drill cadence. Ongoing.

**Total engineer-tier time estimate:** ~2-3 hours for the full migration including verification, plus quarterly ongoing drill burden.

---

## §8 — Risks + open questions for deliberation

1. **`install_prod_vault.sh` missing from repo.** Cross-citation in dispatch but no artefact at probe time (§0). Either it lives outside the repo (host-only), was retired, or is in a worktree scout can't see. Aiden/Elliot resolve before engineer-tier executes.
2. **No documented Shamir→KMS rollback path** (§3.4). The only rollback is restore-from-snapshot. **Snapshot in §3.1 step 3 is the safety net — do not skip.**
3. **Single-region KMS** — `australia-southeast1` matches LAW II + `vercel.json`. GCP KMS has multi-region rings for HA but cost slightly more. V1 ships single-region; V1.x re-evaluate if multi-region Vault HA lands.
4. **SA credentials file on disk.** §2.3 recommends explicit JSON file. The JSON file IS sensitive — if leaked, attacker has KMS encrypt/decrypt on the unseal key. Mitigations: `chmod 0400`, `owner vault:vault`, mounted from a tmpfs at boot, deleted after Vault loads it (Vault keeps the SA credential in-memory after start).
5. **Recovery keys still need M-of-N custody.** Shamir keys become recovery keys post-migration. The custody policy doesn't change — still need M-of-N keyholders with secure storage. This is operational, not technical.
6. **Auto-unseal does NOT remove the need for keyholder ceremonies.** Recovery keys are still required for `vault operator generate-root`, `vault operator rekey`, and `vault operator seal-rewrap` ops. Engineer-tier item: document the (now smaller) keyholder protocol for these admin events.
7. **GCP KMS audit-log retention.** Default is 400 days for admin-activity logs, 30 days for data-access logs. Vault auto-unseal generates data-access events. For HIPAA/legal/accounting compliance (per `mem.wrap.trace` downstream), 30 days may be insufficient. Engineer-tier item: configure GCP log sink to long-term storage if compliance verticals require it.
8. **Multi-cluster sealing.** If Vault moves to HA cluster (per `infra.secrets_management` HA tripwire), all cluster nodes share the same KMS unseal key — no per-node SA needed. Verify before HA rollout.

---

## §9 — Sources (verbatim probe trail)

- `find /home/elliotbot/clawd -iname "*vault*"` — confirmed `install_prod_vault.sh` absent; only `vault_decryptor.py` + tests present at probe time
- `git ls-tree -r origin/main` filtered on vault/kms/seal terms — same result
- https://developer.hashicorp.com/vault/docs/configuration/seal/gcpckms — verbatim `seal "gcpckms"` stanza, parameter table, IAM permissions list (`cloudkms.cryptoKeyVersions.useToEncrypt`, `useToDecrypt`, `cloudkms.cryptoKeys.get`)
- https://developer.hashicorp.com/vault/tutorials/auto-unseal/autounseal-gcp-kms — initial-setup quotes (recovery-keys-replace-unseal-keys at init time)
- https://developer.hashicorp.com/vault/docs/concepts/seal — Shamir→KMS migration verbatim steps (`-migrate` flag, "unseal keys to recovery keys", "make sure to create a backup")
- https://cloud.google.com/kms/pricing — verbatim pricing ($0.06 USD/key/month, $0.03 USD per 10K ops, free key rings, free rotations, Autokey-only free tier)
- `infra.secrets_management` row of `ceo:keiracom_architecture_v2_locked` inventory (HARD GATE V1-launch; Phase 2 sub-deliberation item (a) explicitly names "Cloud-KMS auto-unseal vs shamir-shares-on-disk vs manual" as the choice this prep enables)
- Existing GCP context surfaced via env vars (Drive, Gmail, generic API key — all under the `elliottbot` SA per dispatch's named account)
- `gcloud` CLI not present in scout's worktree — engineer-tier verifies all `gcloud kms` commands above on the host that actually has gcloud + GCP access
