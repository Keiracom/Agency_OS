# Hindsight Spike — Item (iii): Multi-Tenancy under Solo/Pro/Scale

**Phase 2.1 Hindsight verification spike** (Aiden gate A).
Authored 2026-05-24 by Atlas.
Empirical research against `vectorize-io/hindsight@main` (commit-of-record at the time of writing: see `## Evidence trail` at the end of this doc).

---

## Bottom line (one-paragraph executive)

**Hindsight has NATIVE multi-tenancy primitives** that the ratified MAL V1 architecture did not account for. `TenantExtension` + `SupabaseTenantExtension` deliver PostgreSQL schema-per-tenant isolation inside a single Hindsight instance — exactly the "schema-per-tenant + 20-30 tripwire" tenancy line in `ceo:memory_abstraction_layer_v1` eleven_agreed_positions. The ratified substantive_lock item "deployed one instance per tenant VPC" is therefore a viable deployment topology but **not the only one** and **not required** by Hindsight's design. Recommendation: revise the substantive_lock to describe tenancy as a deployment-topology choice keyed off the tier model (Solo/Pro on shared-instance + schema-per-tenant; Scale + regulated verticals on per-tenant VPC). The six MAL primitives (Ingest/Recall/Synthesize/Supersede/Trace/Delete) and the TenantExtension contract abstract topology away from agent code — V1 ships with both topologies addressable from day one.

---

## Notes — canonical key values (per audit-dispatch checklist `_orchestrator.md`)

`ceo:memory_abstraction_layer_v1` queried 2026-05-24 ahead of authoring (updated 2026-05-24T15:12Z). Relevant subset pasted verbatim so reviewers can cross-check the finding against the SSOT.

> **substantive_lock** (item 2 of 4):
> > "Hindsight self-hosted as engine (Vectorize.io open-source MIT, **deployed one instance per tenant VPC**)"
>
> **eleven_agreed_positions** (tenancy line):
> > "Tenancy: **schema-per-tenant** + 20-30 tripwire + migration runner pre-launch"
>
> **eleven_agreed_positions** (BYOK / collective-scope line):
> > "Collective scope: tenant-bounded only, never cross-tenant inference (BYOK sovereignty)"
>
> **eleven_agreed_positions** (MCP swap line):
> > "MCP swappability: agents call memory MCP tools, never SQL/Cypher; swap backend = rewrite DAL"
>
> **aiden_six_phase_2_build_gates** (gate A — this spike):
> > "A: Hindsight spike completes favourable with verbatim findings to #ceo BEFORE Phase 2 build starts"

The substantive_lock and the eleven_agreed_positions are **in tension**: a literal reading of "one instance per tenant VPC" rules out the schema-per-tenant pattern (which lives inside a shared instance). This spike resolves the tension empirically.

---

## Empirical findings

### Finding 1 — Hindsight ships a `TenantExtension` interface for multi-tenancy

**Source:** `hindsight-docs/docs/developer/extensions.md` (Extensions docs in the official repo).

> "**TenantExtension** — Handles multi-tenancy and API key authentication. Validates incoming requests and **determines which PostgreSQL schema to use for database operations, enabling tenant isolation at the database level**."

The contract has two built-in implementations:

| Extension | Mechanism | Use-case |
| --- | --- | --- |
| `ApiKeyTenantExtension` | Validates a single API key; uses `public` schema for all authenticated requests | Single-tenant production deployments (Solo tier) |
| `SupabaseTenantExtension` | Validates Supabase JWTs (local JWKS verification, no network call per request); **each authenticated user gets their own PostgreSQL schema** (`{prefix}_{user_id}`) | Out-of-the-box multi-tenant (Pro tier) |

> "For other multi-tenant setups with separate schemas per tenant (e.g., custom JWT-based auth), implement a custom `TenantExtension`."

**This is not aspirational.** `SupabaseTenantExtension` is a working built-in; the extension contract is publicly documented and the source is in the repo (`hindsight-api-slim/hindsight_api/extensions/builtin/supabase_tenant.py`).

### Finding 2 — Schema migrations are tenant-aware out of the box

**Source:** `hindsight-docs/docs/developer/configuration.md`.

> `hindsight-admin run-db-migration --schema tenant_acme` — "Migrate the base schema plus all discovered tenant schemas"

The admin CLI knows how to discover and migrate per-tenant schemas. Operationally this is what "schema-per-tenant + migration runner pre-launch" needs.

### Finding 3 — Memory banks are intra-tenant context separation, NOT the tenant boundary

**Source:** `hindsight-docs/docs/developer/api/memory-banks.mdx`.

> "Memory banks are isolated containers that store all memory-related data for a specific context or use case. … Banks are completely isolated from each other — memories stored in one bank are not visible to another."

Banks isolate **contexts within a tenant** (e.g. one bank per agent, per project, per use-case). They are not the tenant boundary — TenantExtension is. Inside a tenant's schema, the agent may use one or many banks.

Implication for the tier model: a Solo customer with one agent likely has one bank in one schema; a Pro customer with multiple agents and projects may have many banks in one schema; a Scale customer with strict regulatory needs gets their own instance + schema + banks.

### Finding 4 — API service is stateless and horizontally scalable

**Source:** `hindsight-docs/docs/developer/services.md`.

> "The API service is **stateless** and can be **horizontally scaled** behind a load balancer. All state is stored in PostgreSQL."

A single Hindsight cluster (1+ API replicas + 1+ workers + 1 Postgres) can serve many tenants concurrently. There is no architectural requirement for one instance per tenant — that's a deployment choice, not a design limit.

### Finding 5 — Tenant identity is observable in logs

**Source:** `hindsight-docs/docs/developer/configuration.md`.

> `HINDSIGHT_API_LOG_JSON_FIELDS` — "Available: `severity`, `message`, `timestamp`, `logger`, **`tenant`**, `exception`."

The `tenant` field is a first-class log dimension. Operationally this means observability + per-tenant metering + billing-per-tenant are addressable today via log aggregation; no custom instrumentation needed at the engine layer.

---

## Verify or refute "one Hindsight instance per tenant VPC"

The ratified substantive_lock makes a deployment claim ("deployed one instance per tenant VPC"). Empirically this is **one valid topology of three**, not the only one:

| Topology | Description | Cost-per-tenant | Isolation strength | Best fit |
| --- | --- | --- | --- | --- |
| **A — Per-tenant instance** | Full Hindsight stack per tenant VPC | Linear in N | Strongest (physical infra boundary) | Scale tier + regulated verticals (HIPAA, legal privilege) |
| **B — Shared instance + schema-per-tenant** | One Hindsight cluster; TenantExtension routes each tenant to their own Postgres schema | Sub-linear (shared compute, shared embedding model cache) | Strong (logical DB boundary; cross-tenant queries impossible) | Solo + Pro tiers |
| **C — Hybrid** | Topology B for Solo/Pro; Topology A for Scale + regulated | Mixed | Tier-dependent | V1.0 default |

**Recommendation:** **Topology C (Hybrid)**, codified by tier:

| Tier | Topology | Tenant boundary | Migration burden |
| --- | --- | --- | --- |
| Solo | B (shared) | One schema per customer in shared Postgres | 1× schema migration on launch |
| Pro | B (shared) | One schema per customer in shared Postgres | Same migration path as Solo |
| Scale | A (per-tenant VPC) | Whole Hindsight stack per customer | Per-instance migration runner |

Topology C **does not require revising the MAL V1 primitives** (Ingest/Recall/Synthesize/Supersede/Trace/Delete) — they all sit above the TenantExtension boundary. The MCP-swappability gate (eleven_agreed_positions item 9) is preserved because agents call the MCP tools, not SQL. The "schema-per-tenant + 20-30 tripwire" line in eleven_agreed_positions describes the Topology B / Solo+Pro case; the substantive_lock line describes the Topology A / Scale case. The two are reconciled by reading them as tier-conditioned, not contradictory.

The "20-30 tripwire" referenced in eleven_agreed_positions presumably triggers a Solo/Pro → Scale upgrade conversation when shared-instance schema count gets unwieldy (operational ceiling, not a hard product gate). That tripwire is honoured under Topology C — it just means "promote this tenant from shared instance to dedicated when their footprint warrants it".

---

## Gaps — what must be built ABOVE Hindsight for the tier model

Hindsight's primitives are sound; the **control plane** above them must be built. Items, sequenced:

### G1 — Tenant provisioning service

When a new customer signs up:

1. Allocate a `tenant_id` (currently the `prefix_user_id` shape in SupabaseTenantExtension).
2. Mint a tenant API credential (Supabase JWT or custom JWT depending on `TenantExtension` chosen).
3. Run `hindsight-admin run-db-migration --schema <tenant_id>` to create the per-tenant schema.
4. Seed the first memory bank.
5. Emit a `tenant.provisioned` event to the billing system.

**Status:** No built-in service in Hindsight; this is V1.0 product code. ~200 LoC + tests.

### G2 — Tenant deprovisioning / GDPR delete

Per BYOK sovereignty: when a customer churns or files a deletion request, drop the schema + revoke API credentials. Idempotent. Must emit a `tenant.deprovisioned` event to billing.

**Status:** Drop-schema is a Postgres one-liner; the orchestration around it (credential revocation + event emission + audit trail per the Trace primitive) is V1.0 product code.

### G3 — Tier-router

When a Solo or Pro tenant crosses the "20-30 tripwire" or upgrades to Scale, migrate them from the shared instance (Topology B) to a dedicated instance (Topology A). Uses the same `migration_runner` from the five_converged_decisions_locked (multi-tenant + rollback-per-tenant) — this is **the same code path** as a normal product schema migration, just with a target-instance switch.

**Status:** P0 critical-path per the locked decision; this spike confirms the migration_runner shape is right.

### G4 — Per-tenant metering

Hindsight emits `tenant` in JSON logs (Finding 5). Aggregation → per-tenant token counts, Ingest/Recall counts, storage bytes → billing. Likely a small Vector / Promtail pipeline + a Postgres rollup table.

**Status:** V1.0 product code; no Hindsight changes needed.

### G5 — Tier-aware MCP server

The MCP server exposes the same six primitives regardless of tier. The tier-router (G3) makes the topology choice transparent to agents.

**Status:** Honours the MCP swappability gate (eleven_agreed_positions item 9). The MCP server reads the tenant's `topology` flag at session start and routes to the right Hindsight cluster URL.

### G6 — Cross-tenant aggregate metrics

Operational dashboards need cluster-wide views (e.g. "how many tenants on shared-instance hit the tripwire this week"). Reads from the per-tenant metering rollup (G4), never from Hindsight Postgres directly — the BYOK-sovereign collective-scope line (eleven_agreed_positions item 5) forbids cross-tenant DB queries.

**Status:** V1.0 product code.

---

## Implications for the MAL V1 ratification

The ratified substantive_lock has **one item** that should be revised in light of this spike:

| Current substantive_lock item 2 | Recommended revision |
| --- | --- |
| "Hindsight self-hosted as engine (Vectorize.io open-source MIT, deployed one instance per tenant VPC)" | "Hindsight self-hosted as engine (Vectorize.io open-source MIT, deployment topology is tier-keyed: Solo/Pro on shared-instance + schema-per-tenant via TenantExtension; Scale + regulated verticals on per-tenant VPC. Same MAL primitives across topologies via MCP swappability gate.)" |

Aiden's gate A is satisfied empirically (the engine supports the tenancy model the eleven_agreed_positions already specified). No new gates blocked by this finding.

**No primitive changes.** Ingest/Recall/Synthesize/Supersede/Trace/Delete are unchanged. The TenantExtension boundary sits below all six.

**No protocol changes.** MCP tool surface is unchanged. The tier-router (G5 above) makes topology transparent.

**No deferred items resurfaced.** Trace-in-V1, fastembed default, schema-per-tenant, migration runner P0, whiteboard-flush-through-Ingest — all of these survive Topology C unchanged.

---

## Open questions (out of scope for this spike — surfaced for downstream)

1. **Solo/Pro/Scale tier definition.** The dispatch references Solo/Pro/Scale as a tier model, but no `ceo:tier_model_v1` (or similar) key exists. This spike used the dispatch's tier framing; locking the tier definition (pricing breakpoints, included features, the "20-30 tripwire" actual numeric threshold) is a separate product-side artefact. Surfaced for Dave / Elliot prioritisation.
2. **Regulated-vertical default.** Topology A (per-tenant VPC) is the conservative default for HIPAA / legal privilege. Is the tier router automatic on regulated-vertical onboarding, or a manual operator decision per tenant?
3. **20-30 tripwire numeric.** Eleven_agreed_positions says "20-30 tripwire" — schemas per shared instance before promoting. Empirically what's the operational sweet spot (Postgres connection pool sizing, migration time, monitoring overhead)? Belongs in Phase 3 load-testing.
4. **SupabaseTenantExtension vs custom.** Keiracom already runs Supabase. Using `SupabaseTenantExtension` directly (rather than implementing a custom TenantExtension) is the path of least resistance, but couples the auth boundary to Supabase. Acceptable for Solo/Pro; revisit at Scale.

---

## Evidence trail

All findings sourced from the public `vectorize-io/hindsight` repository, `main` branch as of 2026-05-24. Repo metadata at fetch time: Python, 14.4k stars, MIT license, last commit < 24h before fetch (active).

| File | Finding | Quote anchor |
| --- | --- | --- |
| `README.md` | Hindsight is the agent-memory engine | "Hindsight is focused on making agents that learn" |
| `hindsight-docs/docs/developer/extensions.md` | TenantExtension + SupabaseTenantExtension (Finding 1) | "TenantExtension — Handles multi-tenancy and API key authentication" |
| `hindsight-docs/docs/developer/configuration.md` | Tenant-aware migrations (Finding 2); `tenant` log field (Finding 5) | "run-db-migration --schema tenant_acme"; "Available: severity, message, timestamp, logger, tenant, exception" |
| `hindsight-docs/docs/developer/api/memory-banks.mdx` | Banks are intra-tenant, not the tenant boundary (Finding 3) | "Memory banks are isolated containers… banks are completely isolated from each other" |
| `hindsight-docs/docs/developer/services.md` | API stateless + horizontally scalable (Finding 4) | "The API service is stateless and can be horizontally scaled behind a load balancer" |
| `hindsight-api-slim/hindsight_api/extensions/builtin/supabase_tenant.py` | Production implementation of schema-per-tenant | (source linked from extensions.md) |

---

## Spike status

- Item (iii) — multi-tenancy under Solo/Pro/Scale: **FAVOURABLE with one recommended revision to substantive_lock item 2**.
- Aiden gate A item (iii): **CLEARED** pending Aiden + Max concur on this finding.
- Phase 2 build is unblocked on this dimension once items (i), (ii), (iv), (v), (vi) of the spike clear.

If the recommended revision is adopted, the substantive_lock + eleven_agreed_positions become self-consistent (Topology B is exactly what "schema-per-tenant" already specified; Topology A remains for Scale + regulated). If the revision is rejected, the spike still clears favourable — the per-tenant-VPC topology is supported by Hindsight, just sub-optimally cost-structured for Solo/Pro.
