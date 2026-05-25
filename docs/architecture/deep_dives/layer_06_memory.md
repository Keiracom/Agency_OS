# Layer 6 — Memory (joint: Atlas impl + Aiden architecture)

**Owner:** Atlas (impl ground-truth) + Aiden (architecture). Directive: KEI-SYSTEM-DEEP-DIVE 2026-05-25.

## Notes — canonical key evidence (per audit-dispatch checklist)

`ceo:keiracom_architecture_v2_locked.v2_locks_not_for_redeliberation` locks the engine + topology:
- `mem.engine_hindsight` — Hindsight (Vectorize.io MIT) as the engine
- `mem.topology_tier_keyed` — Solo/Pro shared-instance + schema-per-tenant (B); Enterprise per-tenant VPC (A)
- `mem.primitives_six` — Ingest / Recall / Synthesize / Supersede / Trace / Delete
- `mem.tempr_cara` — TEMPR + Opinion/Reflect pathway (CARA citation pending Viktor reconciliation)
- `mem.cognee_retired` — Cognee removed (PR #1143)
- `mem.llamaindex_pinned` — LlamaIndex pinned; retires via Hindsight cutover step 5-B
- `mem.weaviate_coldstart` — Weaviate kept as auxiliary (live state IS the cold-start target per A3 Elliot operational call)

## §1 Designed

Memory Abstraction Layer V1 (MAL V1) ratified 2026-05-24 (`ceo:memory_abstraction_layer_v1`). Six primitives over Hindsight engine. Four MAL node types map onto Hindsight primitives per PR #1129:
- Decision → World (direct)
- Artifact → Experience (direct)
- TaskContext → Observation (direct, via background consolidation)
- AntiPattern → Opinion (wrapper-required; entity_label + supersession edge)

Tier-keyed deployment topology per PR #1126: Solo/Pro use shared Hindsight instance + schema-per-tenant via `SupabaseTenantExtension`; Enterprise uses per-tenant VPC.

## §2 Built

- **Engine deployed:** fleet Hindsight container running on port 8889 via PR #1145 (Phase A1). Health check passing; volume-persistent.
- **Wrappers shipped:** 4 wrappers + Trace composition in PR #1134 (`src/keiracom_system/memory/wrappers/`).
- **MCP server:** PR #1136 exposes all 6 primitives via tier-gated tools. Gate E (dual-backend parity) proven.
- **Control-plane tenants table:** PR #1131. Fleet tenant_id `00000000-0000-0000-0000-000000000001` provisioned.
- **TenantExtension:** Orion PR #1132 with `get_bank_id` hotfix PR #1135.
- **Indexer dual-write mirror:** PR #1147 (in flight). Default OFF; per-service opt-in via `INDEXER_HINDSIGHT_MIRROR=on`.
- **Snapshot archive:** Orion 2026-05-25, 2.1GB chmod 444 at `/home/elliotbot/clawd/backups/memory_pre_hindsight_migration_20260525/` (NOT `/backups/...` as inventory said — path corrected in PR #1147 commit chain).

**Not yet built:** Weaviate retirement (waiting on indexer reader-cutover via LlamaIndex retirement step 5-B); per-tenant export endpoint (Orion KEI Agency_OS-il34); fastembed native upstream (Orion PR #1127 Path 1 deferred — Path 3 TEI sidecar is V1).

## §3 Measured

- **Pre-build-commit smoke (PR #1130):** 20-item pilot ingested at 7.6s/item via gpt-4o-mini. Recall latency ~0.5s/query (4 queries in 1.9s aggregate). Consolidation: 49 ops → 31 new + 13 updated observations in 158s.
- **Fleet Phase A1 smoke (PR #1145):** 4 wrappers wired against deployed instance; 4/4 writes OK + 15 read-back rows.
- **Production data:** **no customer data exists**; all measurements are fleet-internal smoke runs. The fitness rubric methodology gap (G3 from PR #1130) requires LLM-judge + ground-truth sets before the first-customer-checkpoint hard gate per `phase_2_1_spike_verdict.two_checkpoint_structure`.

## §4 Token budget / cost behaviour at this layer

Hindsight `retain()` calls fire an LLM extraction per memory (gpt-4o-mini in fleet V1 — see Layer 11 for tier-keyed swap). Cost-per-retain observed in PR #1130 smoke: ~1K–3K input tokens per item; output ~200 tokens. Recall calls are local (BGE-small-en-v1.5 embedding + Postgres pgvector); no LLM cost per recall. Reflect calls invoke the LLM agentic loop (up to 10 iterations per Hindsight reflect.mdx) — most expensive per-call surface.

Per-tenant attribution: Layer 11 metering pipeline (PR #1137) captures token counts from Hindsight's OTel spans. PR #1139 Item 1 wires per-MAL-primitive attribution on top.

## §5 Cache strategy applicable

- **Layer 1 (Anthropic prompt cache, 0.10x):** N/A at the engine layer — Hindsight uses OpenAI per fleet config, not Anthropic. Layer 1 cache only applies if customer BYOK key is Anthropic AND Hindsight is configured to use it (Pro+ tier feature).
- **Layer 2 (uncached, 1.0x):** baseline for retain extraction.
- **Valkey semantic cache:** YES — recall queries with similar embedding signatures should short-circuit before hitting Hindsight. Hit rate at Pro+ tier where repeated decision-lookup patterns emerge. Implementation: PR #1139 Item 3 cache discipline.
- **Hindsight beyond active window:** the engine IS the beyond-active-window store. Observations + raw facts preserved indefinitely (no TTL); supersession-via-AntiPattern is the only retraction path.

## §6 LOOSE items / open questions

- **L1:** CARA citation in substantive_lock — Viktor reconciliation pending (bd Agency_OS-wlfd). Treat as "Opinion/Reflect pathway" verbatim per PR #1129 finding.
- **L2:** Per-tenant export endpoint (Agency_OS-il34) — Hindsight upstream lacks bulk per-tenant export; my PR #1130 G4 confirmed. Build-vs-fork-Hindsight choice belongs in Orion's KEI.
- **L3:** TEI sidecar swap to native fastembed (Orion PR #1127 Path 1) — deferred; Path 3 TEI works for V1 but adds latency hop.
- **L4:** Weaviate cold-start operationally not yet executed — `mem.weaviate_coldstart` row notes live state IS the target; cold-start ops skipped per Elliot operational call (b).
- **L5:** Reconciliation script (PR #1147 NIT-2) — Phase A3 ops step 2.5; backfills divergence between Weaviate + Hindsight during dual-write window.

## §7 Per-tier behaviour variation

| Tier | Topology | Memory deployment | Cache framework multiplier proposal |
| --- | --- | --- | --- |
| Sandbox | B (shared) | Shared Hindsight + per-tenant schema | 0.5x (trial-grade; recall cache evicts faster) |
| Solo | B (shared) | Same as Sandbox; quota-bounded | 1.0x (baseline; Valkey cache warm for active tenant) |
| Pro | B (shared) | Same; larger schema footprint | 1.5x (dedicated semantic-cache namespace) |
| Team | B (shared) | Same; multi-user → larger working set | 2.0x (warmer Valkey + larger Hindsight quota) |
| Enterprise | A (per-VPC) | Dedicated Hindsight instance + Postgres + TEI sidecar in tenant VPC | custom (full stack isolation) |

20–30 tenants per shared Hindsight per `eleven_agreed_positions` #6 tenancy tripwire; promote to Enterprise (Topology A) above that or on regulated-vertical signup.

## §8 Per-agent-type variation

Memory access shape varies by agent role:

| Agent | Memory primitive mix | Bank routing |
| --- | --- | --- |
| Chat agent | Recall (heavy), Ingest (medium), Reflect (medium) | Per-tenant primary bank |
| Worker | Ingest (heavy on task-context), Recall (medium for prior decisions) | Same per-tenant bank, scoped via TenantExtension |
| Deliberator | Recall (very heavy — canonical-key lookups), Trace (medium — audit composition) | Per-tenant bank + audit-log bank |
| Audit (regulated verticals) | Trace (heavy), Recall (heavy) | Per-tenant bank with `audit_purpose=hipaa\|legal_privilege\|accounting` tagging per PR #1134 trace_composition |

Multi-tenancy enforcement is mechanical at the TenantExtension boundary (Layer 7 API gate); the memory layer itself trusts the bank_id it receives. Cross-tenant inference is forbidden per `eleven_agreed_positions` #5 (BYOK sovereignty).
