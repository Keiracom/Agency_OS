# Layer 9 — State / Persistence (Postgres + Valkey + Supabase)

**Owner:** Atlas. Directive: KEI-SYSTEM-DEEP-DIVE 2026-05-25.

## Notes — canonical key evidence (per audit-dispatch checklist)

- `ceo:keiracom_architecture_v2_locked.v2_locks_not_for_redeliberation` locks `mem.topology_tier_keyed` (Postgres schema-per-tenant for Solo/Pro; per-VPC Postgres for Enterprise).
- Cat 4 `cost.semantic_cache_valkey` RATIFIED-DM — Valkey is the semantic-cache substrate (NOT standard KV).
- `tenant.single_supabase` (Cat 9 inventory) — one Supabase + one dashboard; fleet is tenant_id=1; customers are tenant_id=2+.
- Aiden Cat 17 architecture-fit verdict: "Primary architectural bottleneck — Postgres connection pool: Supabase Pro = 200 conns/instance; all-Pro cohort saturates at ~12.5 tenants/instance".

## §1 Designed

Three state stores serve V1 with distinct roles:

- **Supabase (managed Postgres):** control-plane data + customer-business data. Single project `jatzvazlbusedwsnqxzr` for fleet + customer. `public.keiracom_tenants` (PR #1131) is the canonical tenants table; per-tenant schemas (`keiracom_<uuid>`) hold per-customer data.
- **Hindsight embedded Postgres:** memory engine's own storage (Layer 6). Separate from Supabase. Per-tenant schema-per-tenant within shared instance (Solo/Pro); per-VPC for Enterprise.
- **Valkey:** semantic cache + ephemeral whiteboard. Per `eleven_agreed_positions` #8 "whiteboard flush through Ingest at every task boundary" — Valkey is the transient before-Ingest state; persistent state always lands in Hindsight via the wrappers.

## §2 Built

- **Supabase:** project active; `public.keiracom_tenants` migration applied PR A1 (commit before #1145). Fleet tenant row populated.
- **Hindsight embedded Postgres:** persists in named docker volume `keiracom_fleet_hindsight_pg_data` (PR #1145). Survives compose down/up + daemon restart.
- **Valkey:** running on fleet host (`cost.semantic_cache_valkey` row says "Valkey running today"). 15-min RDB snapshots (per Cat 16 `infra.backup_dr` row).
- **Indexer dual-write mirror:** PR #1147 — opt-in mirror to Hindsight; Weaviate stays as reader-of-record until step 5-B retires LlamaIndex.

**Not yet built:** PgBouncer transaction-mode pooling (Aiden Cat 17 sub-item — needs `prepare_threshold=None` per `reference_psycopg_supabase_pgbouncer`); per-tier connection pool sizing via `get_pool_size_hint(tenant_id)` on TenantExtension (Aiden Cat 17 sub-item; ~30–50 LoC additive per my spot-check); Vault envelope encryption for `llm_api_key_encrypted` column (LOOSE-BLOCKER per Cat 16 `infra.secrets_management`).

## §3 Measured

- **Supabase connection pool baseline:** 200 conns/instance (Supabase Pro). Per-tenant load (Aiden Cat 17): Solo 10, Pro 16, Team 28. All-Pro cohort saturates at ~12.5 tenants/instance.
- **Valkey snapshot cadence:** 15 minutes (per inventory). Snapshot size — **NOT MEASURED IN PRODUCTION**; pre-revenue.
- **Hindsight embedded PG (PR #1130 smoke):** running RSS ~1.4 GB at idle; embedded PG starts in <30s grace period.
- **No customer data exists.** All counts are fleet-internal.

## §4 Token budget / cost behaviour at this layer

Layer 9 does not consume LLM tokens directly. Cost shape is INFRASTRUCTURE not token:
- Supabase Pro = $39 AUD/mo per environment + PITR overhead (per Cat 16 `infra.backup_dr` sub-item)
- Valkey self-hosted: zero marginal cost (runs on fleet Vultr host alongside everything else)
- Hindsight embedded PG: zero marginal cost (in-container)
- Per-tenant Enterprise (Topology A) per-VPC Postgres adds ~$50–100 AUD/mo per tenant (Aiden Cat 17 cost floor)

Cost-attribution at this layer flows to Layer 11 via the metering pipeline tagging each tenant's connection-pool consumption + query latency.

## §5 Cache strategy applicable

- **Layer 1 (Anthropic prompt cache, 0.10x):** N/A — Layer 9 is storage, not LLM-call surface.
- **Layer 2 (uncached, 1.0x):** baseline — every query to Supabase / Valkey / Hindsight PG is direct.
- **Valkey semantic cache:** **Valkey IS the cache substrate at this layer** (per `cost.semantic_cache_valkey`). Semantic cache stores recent query→result pairs keyed by embedding similarity. Hit rate is the lever this layer optimises.
- **Hindsight beyond active window:** Hindsight observations themselves ARE the long-term recall store. Layer 9 stores the schema/edges that index them.

Cache eviction policy per tier per `ceo:cache_framework_canonical.tier_multipliers_status` — proposal pending Phase 2 pressure-test.

## §6 LOOSE items / open questions

- **L1:** PgBouncer transaction-mode pooling — not yet wired. Without it, Solo/Pro cohort saturates Supabase at ~12 tenants. Critical for going past ~10 active tenants.
- **L2:** Per-tier connection pool sizing in TenantExtension (Aiden Cat 17 sub-item) — needs to be additive method on Orion PR #1132's TenantExtension.
- **L3:** Vault envelope encryption for `llm_api_key_encrypted` — column ready (PR #1131); encryption layer is Vault-blocked per Cat 16 `infra.secrets_management` LOOSE-BLOCKER + atlas spot-check + Composio sub-question (`Agency_OS-aynv` POC required).
- **L4:** Valkey HA / replication — single-node V1; SPOF if Vultr host fails. Same DR class as Postgres backup procedure.
- **L5:** Pro-weighted tripwire variant (Aiden Cat 17 sub-item c) — trip at 12 Pro tenants OR 20 Solo tenants whichever first, instead of fixed 20–30.

## §7 Per-tier behaviour variation

| Tier | Postgres topology | Valkey footprint | Cache multiplier proposal |
| --- | --- | --- | --- |
| Sandbox | Schema in shared Supabase (Topology B) | Shared Valkey namespace; small TTL | 0.5x |
| Solo | Schema in shared Supabase | Per-tenant Valkey namespace; baseline TTL | 1.0x |
| Pro | Schema in shared Supabase (counts toward 12-tenant tripwire heavier than Solo) | Larger per-tenant Valkey namespace; longer TTL | 1.5x |
| Team | Schema in shared Supabase + multi-user pool | Multi-user shared Valkey pool with per-user prefix | 2.0x |
| Enterprise | Per-VPC dedicated Postgres + Valkey | Dedicated Valkey instance | custom |

The 12-tenant Postgres tripwire is per-instance — not a global limit. Promotion path: spin up additional Supabase project when one approaches saturation.

## §8 Per-agent-type variation

Layer 9 access is uniform across agent types — they all hit Postgres/Valkey via the TenantExtension boundary. Variation is in PRIMITIVE mix:

| Agent | Read pattern | Write pattern |
| --- | --- | --- |
| Chat | Heavy Valkey reads (cache) + light Postgres writes (session state) | Burst-y writes on user input |
| Worker | Heavy Postgres reads (bd, KEIs, code) + medium Valkey reads | Batch writes via PRs + bd updates |
| Deliberator | Heavy Postgres reads (canonical keys via Supabase MCP); light writes | Low write volume; canonical_key paste = write |
| Audit | Heavy reads across ALL stores (Supabase audit logs + Hindsight audit-tagged memories) | Append-only writes to audit log |

Cross-cutting concerns at this layer:
- **Multi-tenancy enforcement:** mechanical at TenantExtension boundary — connection-pool routing per tenant_id; queries scoped to tenant's schema. NEVER UI-layer.
- **Security (BYOK):** `llm_api_key_encrypted` column ready; envelope encryption blocked on Vault.
- **CI/CD + rollback:** Supabase PITR (Pro tier, 7-day window) is the rollback substrate. Pulumi IaC (per Cat 16 `infra.iac`) plans tenant-provisioning automation.
- **Backup-DR:** Cat 16 `infra.backup_dr` — Supabase PITR + Hindsight per-tenant export endpoint (Agency_OS-il34) + Valkey RDB 15-min snapshots. Live recovery drill REQUIRED before V1 launch per GOV-12.
- **Customer file system:** Vultr Object Storage + Postgres hierarchy table per Cat 19 `ux.files.storage`. Layer 9 owns the metadata; binary content lives in Object Storage.
