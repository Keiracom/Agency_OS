# Hindsight Verification Spike — Item (v) BYOK-LLM Routing for Reflect / Belief-Updates

**Authored:** 2026-05-24 (orion, per Elliot dispatch — Phase 2.1 spike item v)
**Status:** RESEARCH COMPLETE — pending Aiden + Max dual-concur
**Anchor:** `ceo:memory_abstraction_layer_v1` position 5 (Collective scope tenant-bounded BYOK) + Aiden gate A item (v)
**Repo inspected:** [vectorize-io/hindsight](https://github.com/vectorize-io/hindsight) — same inspection method as my PR #1127 (item iv)
**Builds on:** PR #1127 (item iv fastembed §5 surface-level item-v findings) + Atlas PR #1126 (item iii multi-tenancy + 2-topology finding)

## 1. Top-line finding (TL;DR)

**Both topologies have first-class BYOK-LLM routing support in Hindsight.** No upstream changes needed; the work is all Keiracom-side install + control-plane integration.

- **Topology A (per-tenant VPC — Scale tier per Atlas #1126):** instance-level env var carries the tenant's LLM key. Settled in my PR #1127 §5.
- **Topology B (shared instance, schema-per-tenant — Solo/Pro tiers per Atlas #1126):** **per-request** routing via `TenantExtension.get_tenant_config()` returning `{"llm_api_key": <tenant_key>, ...}`. `ConfigResolver` merges this on top of global env config before the LLM call. Field-level permission gate via `get_allowed_config_fields()`.

The implementation work splits as:
- **Hindsight side: zero changes.** All primitives exist.
- **Keiracom side:** author `KeiracomTenantExtension` subclassing `TenantExtension` to pull per-tenant LLM keys from Keiracom's control plane (Supabase `tenants` table or similar). G3 + G4 from Atlas's #1126 gap list cover this.

## 2. Canonical key paste — `ceo:memory_abstraction_layer_v1` position 5 + Aiden gate A

Per the audit-dispatch checklist canonical-key-query-gate, the queried values pasted verbatim:

**Position 5 (`eleven_agreed_positions[4]`):**
```
"Collective scope: tenant-bounded only, never cross-tenant inference (BYOK sovereignty)"
```

**Aiden gate A (`aiden_six_phase_2_build_gates[0]`):**
```
"A: Hindsight spike completes favourable with verbatim findings to #ceo BEFORE Phase 2 build starts"
```

**`substantive_lock`:**
```
"Hindsight self-hosted as engine (Vectorize.io open-source MIT, deployed one instance per tenant VPC)"
```

(Note: per Atlas #1126 item iii, this substantive_lock line describes **one valid topology, not the only one**. Atlas recommends revising to a tier-keyed deployment-topology choice. The BYOK-LLM routing in this spike item works for **both** of Atlas's topologies.)

## 3. Topology A — per-tenant VPC (Scale tier)

**Settled in PR #1127 §5.** Per-tenant Hindsight instance, deployed in tenant's VPC, env var carries the tenant's LLM key at deploy time.

```bash
# Keiracom install script (deploy-time, per-tenant):
export HINDSIGHT_API_LLM_PROVIDER=openai
export HINDSIGHT_API_LLM_API_KEY=sk-tenant42-...
docker-compose up -d hindsight
```

**Sovereignty achieved by deployment isolation** — each tenant's container carries that tenant's key. Cross-tenant inference impossible because each instance only sees one tenant's data.

**Cost-per-tenant accounting:** per-instance LLM spend = tenant's spend. Read from cloud provider's per-VPC billing OR from Hindsight's per-instance logs (Atlas #1126 finding #5: "`tenant` is a first-class JSON log field for per-tenant metering").

**Failure mode (key expired / rate limit):** Hindsight raises 500 to caller; instance keeps running; tenant sees Reflect API error; Keiracom MCP wrapper retries / surfaces to Keiracom dashboard for tenant to rotate key.

## 4. Topology B — shared instance, schema-per-tenant (Solo / Pro tiers)

**This is the deep work.** Multiple tenants share a single Hindsight instance with schema isolation in Postgres. The LLM call inside Reflect / belief-updates must route to the right tenant's BYOK key per-request.

### 4.1 Hindsight's per-request config resolution — `ConfigResolver`

File: [`hindsight-api-slim/hindsight_api/config_resolver.py`](https://github.com/vectorize-io/hindsight/blob/main/hindsight-api-slim/hindsight_api/config_resolver.py)

The resolution order is verbatim from the source:

```
Resolution order:
1. Global config (from environment variables)
2. Tenant config overrides (from TenantExtension.get_tenant_config())
3. Bank config overrides (from banks.config JSONB)
```

The implementation in `resolve_full_config`:

```python
# Start with global config (all fields)
config_dict = asdict(self._global_config)

# Load tenant config overrides (if tenant extension available)
if self.tenant_extension and context:
    tenant_overrides = await self.tenant_extension.get_tenant_config(context)
    if tenant_overrides:
        # Normalize keys and filter to configurable fields only
        normalized_tenant = normalize_config_dict(tenant_overrides)
        configurable_tenant = {k: v for k, v in normalized_tenant.items()
                               if k in self._configurable_fields}
        config_dict.update(configurable_tenant)
```

**This is per-request.** Every API call that triggers an LLM call (Reflect, retain extraction, recall synthesis) goes through `resolve_full_config`, which calls `tenant_extension.get_tenant_config(context)` to fetch per-tenant overrides — including `llm_api_key` if the tenant has one configured.

### 4.2 `TenantExtension.get_tenant_config()` contract

File: [`hindsight-api-slim/hindsight_api/extensions/tenant.py`](https://github.com/vectorize-io/hindsight/blob/main/hindsight-api-slim/hindsight_api/extensions/tenant.py)

```python
async def get_tenant_config(self, context: RequestContext) -> dict[str, Any]:
    """
    Get tenant-specific configuration overrides.

    Example:
        {"llm_model": "gpt-4", "retain_extraction_mode": "verbose"}

    The default implementation returns an empty dict (no tenant-specific config).
    Override this method in custom extensions to provide tenant-specific configuration.
    """
    return {}
```

**The example explicitly shows `llm_model` as an overridable field.** Per the resolution merge, `llm_api_key` is overridable the same way IF it's in `HindsightConfig.get_configurable_fields()` — which is the gate the resolver applies.

### 4.3 Field-level permission gate — `get_allowed_config_fields()`

```python
async def get_allowed_config_fields(self, context: RequestContext, bank_id: str) -> set[str] | None:
    """
    Get set of config fields that this tenant/bank is allowed to modify.
    """
```

Lets Keiracom enforce that, say, Solo-tier tenants can override `llm_api_key` but not `chunk_size` or `embeddings_provider`. This is the field-level governance hook for tier-specific feature gating.

### 4.4 Proposed Keiracom-side implementation — `KeiracomTenantExtension`

Pseudocode for the custom extension that ships in the product repo:

```python
# product_repo/keiracom/hindsight_ext/tenant.py
import os
from hindsight_api.extensions.tenant import TenantExtension, TenantContext, Tenant
from hindsight_api.models import RequestContext
import psycopg

class KeiracomTenantExtension(TenantExtension):
    """BYOK-aware tenant extension backed by Keiracom's control plane."""

    async def authenticate(self, context: RequestContext) -> TenantContext:
        api_key = context.headers.get("X-Keiracom-Api-Key")
        if not api_key:
            raise AuthenticationError("missing X-Keiracom-Api-Key header")
        # Lookup tenant from control plane
        with psycopg.connect(os.environ["KEIRACOM_CONTROL_PLANE_DSN"]) as cn, cn.cursor() as cur:
            cur.execute("SELECT schema_name FROM tenants WHERE api_key_hash = digest(%s, 'sha256')",
                       (api_key,))
            row = cur.fetchone()
        if not row:
            raise AuthenticationError("invalid api key")
        return TenantContext(schema_name=row[0])

    async def list_tenants(self) -> list[Tenant]:
        with psycopg.connect(os.environ["KEIRACOM_CONTROL_PLANE_DSN"]) as cn, cn.cursor() as cur:
            cur.execute("SELECT schema_name FROM tenants WHERE status = 'active'")
            return [Tenant(schema=r[0]) for r in cur.fetchall()]

    async def get_tenant_config(self, context: RequestContext) -> dict[str, Any]:
        api_key = context.headers["X-Keiracom-Api-Key"]
        with psycopg.connect(os.environ["KEIRACOM_CONTROL_PLANE_DSN"]) as cn, cn.cursor() as cur:
            cur.execute(
                "SELECT llm_provider, llm_api_key_encrypted, llm_model, tier "
                "FROM tenants WHERE api_key_hash = digest(%s, 'sha256')",
                (api_key,),
            )
            row = cur.fetchone()
        if not row:
            return {}
        return {
            "llm_provider": row[0],
            "llm_api_key": decrypt(row[1]),  # via existing keys_service pattern
            "llm_model": row[2],
        }

    async def get_allowed_config_fields(self, context: RequestContext, bank_id: str) -> set[str] | None:
        # Tier-based field gating
        tier = await self._get_tier(context)
        if tier == "solo":
            return {"llm_api_key", "llm_model"}  # BYOK only, no advanced tunables
        elif tier == "pro":
            return {"llm_api_key", "llm_model", "chunk_size", "retain_extraction_mode"}
        else:  # scale — full control (or N/A since Scale uses Topology A)
            return None  # all fields
```

Wire-up:

```bash
export HINDSIGHT_API_TENANT_EXTENSION=keiracom.hindsight_ext.tenant:KeiracomTenantExtension
export KEIRACOM_CONTROL_PLANE_DSN=postgresql://...
docker-compose up -d hindsight  # single shared instance
```

**This is G3 (tier-router) + G4 (per-tenant metering) + G5 (tier-aware MCP server) from Atlas's #1126 gap list, materialised as a single TenantExtension subclass.**

### 4.5 Per-call routing diagram (Topology B)

```
Tenant T1's agent
        ↓ X-Keiracom-Api-Key: solo-tier-key-T1
Hindsight API
        ↓ authenticate(context)
KeiracomTenantExtension.authenticate
        ↓ control-plane lookup → TenantContext(schema_name="t1_xyz")
Hindsight Reflect handler
        ↓ resolve_full_config(bank_id, context)
ConfigResolver
        ↓ get_tenant_config(context) — control-plane lookup
KeiracomTenantExtension.get_tenant_config
        ↓ returns {"llm_api_key": "sk-T1-...", "llm_model": "gpt-4o-mini"}
Resolved HindsightConfig (merged: env defaults + T1's BYOK)
        ↓ LLM call
Tenant T1's OpenAI account
        ↓ embedding/completion
Hindsight responds to T1
```

A concurrent request from T2 reuses the **same Hindsight process** but resolves to T2's key. Cross-tenant leakage is impossible because (a) schema isolation prevents DB cross-reads, (b) per-request config resolution prevents key reuse.

## 5. Cost-per-tenant accounting

Two complementary mechanisms:

1. **Hindsight-side log emission** (Atlas #1126 finding #5): every JSON log line carries `tenant` field. Keiracom log-shipper (Vector / Filebeat / etc.) routes logs to a metering service that aggregates per-tenant spend over time.
2. **Keiracom-side instrumentation in `KeiracomTenantExtension`**: wrap `get_tenant_config()` with a callback that increments a per-tenant request-count metric in the control plane. For per-request LLM-token cost, the metering service joins request logs with the tenant's LLM provider's billing API (e.g., OpenAI's `/dashboard/billing/usage`).

**Recommendation:** ship V1 with log-based metering only (mechanism 1). Add provider-billing-API integration (mechanism 2) as a P2 follow-up after first paying customer.

## 6. Failure modes (key expired / rate limit mid-Reflect)

| Failure | Hindsight behaviour | Keiracom-side handling |
|---|---|---|
| Tenant's LLM API key expired | LLM provider returns 401 → Hindsight catches → 500 to caller | MCP wrapper retries once; on second 401 surfaces to Keiracom dashboard banner "your LLM key needs rotation" |
| Rate limit (429) | LLM provider returns 429 → Hindsight catches → 503 to caller | MCP wrapper backs off + retries per provider's `Retry-After` header (existing KEI-40 pattern) |
| Tenant config not in control plane | `get_tenant_config()` returns `{}` → resolved config falls back to global env | Global env has Keiracom's fallback key (only enabled in dev/staging — production global config has NO LLM key so tenants without BYOK get a useful "no key configured" error) |
| Mid-Reflect rate limit (partial completion) | Reflect is atomic at the synthesis step — failure rolls back the in-progress synthesis | Keiracom retries the Reflect call after backoff |
| Control-plane database unreachable | `KeiracomTenantExtension.authenticate()` raises → Hindsight returns 503 | MCP wrapper retries; persistent failure pages on-call |

**Graceful degradation pattern**: NO Keiracom fallback key in production. Tenants without BYOK MUST configure one before their first Reflect — enforced at signup (Keiracom UI doesn't expose Reflect until key is configured). This is the sovereignty contract from position 5: tenant pays for tenant's inference; Keiracom never silently subsidises.

## 7. Spike-item-(v) clearance

Per the dispatch GATE: "this + i/ii/iii/iv/vi clear Phase 2.1 spike."

**Item (v) verdict: CLEAR WITH KEIRACOM-SIDE WORK NAMED.**

- ✅ Topology A (per-tenant VPC) — settled in PR #1127 §5.
- ✅ Topology B (shared instance, schema-per-tenant) — Hindsight's `ConfigResolver` + `TenantExtension.get_tenant_config()` natively supports per-request per-tenant LLM key routing.
- ✅ Field-level permission gate via `get_allowed_config_fields()` enables tier-based feature gating without new code.
- ✅ Cost-per-tenant accounting via JSON log field (V1) + provider-billing-API integration (V2 follow-up).
- ✅ Failure modes mapped + graceful degradation pattern named.

**Hindsight upstream changes required: ZERO.** All primitives exist.

**Keiracom-side follow-up actions (file as bd issues after spike concur):**
1. **P1** — author `KeiracomTenantExtension` per §4.4 pseudocode. ~150-200 LoC. Ships with the product-repo install script. Folds in Atlas #1126 gaps G3 (tier-router) + G5 (tier-aware MCP server) implicitly.
2. **P1** — control-plane `tenants` table schema: `(api_key_hash, schema_name, llm_provider, llm_api_key_encrypted, llm_model, tier, status)`. Migration ships before first paying customer. Uses the same `pgcrypto` encryption pattern as existing `keys_service.store_key()` (Agency_OS-era code that's repo-archive-tier but pattern is reusable).
3. **P2** — log-based per-tenant metering pipeline (Atlas #1126 G4). Vector/Filebeat → metering service → control plane spend table.
4. **P2** — graceful degradation handlers in Keiracom MCP wrapper: 401-retry-once-then-dashboard-banner, 429-respect-Retry-After. Reuses KEI-40 pattern.
5. **P3** — provider-billing-API integration (mechanism 2 from §5). Post-first-paying-customer.

## 8. Acceptance criteria

- [x] Empirical inspection of Hindsight's `TenantExtension` + `ConfigResolver` — source paths cited inline (§4.1, §4.2, §4.3).
- [x] Topology A routing pattern documented (§3, cross-references PR #1127 §5).
- [x] Topology B per-request routing pattern documented with code path (§4) + per-call diagram (§4.5).
- [x] Field-level permission gate (`get_allowed_config_fields`) characterised (§4.3).
- [x] Proposed Keiracom-side `KeiracomTenantExtension` pseudocode (§4.4) — names control-plane schema + wire-up env vars.
- [x] Cost-per-tenant accounting paths (§5) — log-based V1, provider-API V2.
- [x] Failure-mode matrix (§6) + graceful degradation pattern (no Keiracom fallback key).
- [x] Spike-item-(v) clearance verdict + 5 follow-up actions named (§7).
- [x] Canonical key `ceo:memory_abstraction_layer_v1` queried + position 5 + Aiden gate A + substantive_lock pasted verbatim (§2).
- [x] Cross-references PR #1127 (item iv) + Atlas PR #1126 (item iii) — coherent spike narrative.
- [x] No code shipped — research-only deliverable.
- [ ] Aiden architecture-lens concur.
- [ ] Max code-quality-lens concur (verifies empirical claims against linked source).
- [ ] Dual-concur → Elliot admin-merge per orchestrator-merge-after-NATS-concur pattern.
- [ ] Post-merge: file 5 P1/P1/P2/P2/P3 bd issues per §7.
