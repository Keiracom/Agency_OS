# Layer 11 — Cost optimization (caching + token budgets + routing)

**Owner:** Atlas + Orion (joint — Orion on cache strategy + LiteLLM routing)
**Status:** PARTIAL — metering pipeline shipped (PR #1137); cache framework canonical registered (`ceo:cache_framework_canonical`); Valkey running per Cat 4; per-tier multipliers PROPOSAL pending pressure-test
**Directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500

## Notes — canonical evidence pasted per audit-dispatch checklist

`ceo:cache_framework_canonical` (queried 2026-05-25, verbatim):
```json
{
  "directive": "KEI-SYSTEM-DEEP-DIVE",
  "connects_to": ["cost.cache_discipline","cost.token_budget","cost.semantic_cache_valkey",
                  "temp.inline.cache_check","deepdive.layer11_cost_optimization"],
  "ratified_ts": "2026-05-25T~1779746500",
  "layer_1_anthropic_prompt_cache": {"content":"structurally stable per-domain content","multiplier":"0.10x input cost"},
  "layer_2_uncached": {"content":"per-call dynamic content","multiplier":"1.0x"},
  "valkey_semantic_cache": "layered on top for repetitive query hits",
  "history_beyond_active_window": "stored in Hindsight for queryable recall, NOT held in active context",
  "per_tier_multipliers_proposal": {"sandbox":"0.5x","solo":"1.0x","pro":"1.5x","team":"2.0x","enterprise":"custom"},
  "tier_multipliers_status": "PROPOSAL — pressure-test in Phase 2"
}
```

Inventory Cat 4 verbatim:
- `cost.metering_pipeline` (RATIFIED-CEO, PR #1137) — "V1 captures token-counts only; cost $AUD translation deferred to P3"
- `cost.cache_discipline` (RATIFIED-CEO placement; LOOSE implementation) — "SHIFTING to Temporal interception layer per ratify 2026-05-25"
- `cost.semantic_cache_valkey` (RATIFIED-DM) — "Valkey running today" per Viktor verbatim
- `cost.token_budget` (LOOSE) — "per-call cap + tier-scaled pool + dispatcher-enforced + model-cost-calibrated"
- `cost.dashboard` (LOOSE) — admin-dashboard panel per-tenant + per-callsign + per-agent-role
- `cost.metering.production_wiring` (LOOSE, P1 Orion follow-up) — psycopg adapter + Prefect daily rollup
- `cost.metering.log_shipper_config` (LOOSE, P2 Orion follow-up) — Vector or Filebeat
- `cost.metering.provider_billing_api` (DEFERRED P3) — per-model-per-tenant $AUD translation

## §1 Designed

The framework is multi-layer:

**Cache tiers (the cost-reduction substrate):**
1. **Anthropic prompt cache** — 0.10× input cost; targets structurally stable content (per-domain knowledge, tool definitions, system prompts).
2. **Uncached** — 1.0× baseline; per-call dynamic content.
3. **Valkey semantic cache** — vector-similarity hits on repetitive queries. Layered on top of (1)/(2) — short-circuits the LLM call entirely when a similar prior query is in cache.
4. **Hindsight beyond active window** — NOT a per-request cache; an observability + recall store for context beyond what fits in the active window. Stops being "cache" and starts being "memory" at this point.

**Token budget (the cost-cap substrate):**
- Per-call cap (hard ceiling on a single LLM request)
- Tier-scaled pool (per-tenant aggregate budget per day/month — `cost.token_budget` Viktor 4-component proposal)
- Dispatcher-enforced (the cap is checked by the dispatcher BEFORE the workflow starts, not after the LLM call completes)
- Model-cost-calibrated (a Sonnet call counts more against the cap than a Haiku call, weighted by per-model $AUD)

**Routing (the cost-control substrate):**
- LiteLLM governance router (`gov.litellm_router` RATIFIED-CEO running) routes per BYOK key + per tier + per model preference
- Internal fleet uses hardcoded Gemini 2.5 Flash per `reference_model_routing.md` (cost-optimal for internal governance)

**Metering (the cost-visibility substrate):**
- Per-call token attribution (PR #1137, this session — already shipped)
- Per-tenant per-day per-model rollup table (`keiracom_tenant_metering` from PR #1137 migration)
- Dashboard column "token-counts only V1; $AUD when P3 ships" per `cost.metering_pipeline` reframe

## §2 Built

| Component | Status | Evidence |
|---|---|---|
| Cache framework canonical | REGISTERED | `ceo:cache_framework_canonical` (2026-05-25) |
| Cache placement decision | RATIFIED-CEO | `cost.cache_discipline` row 79 — placement at Temporal interception layer |
| Cache implementation | LOOSE | Not yet built. Needs `temp.middleware` deploy (Layer 5 HARD GAP). |
| Anthropic prompt cache | NOT WIRED | No Keiracom-side wiring; needs per-domain stable-content templates |
| Valkey semantic cache | RUNNING | "Valkey running today" per Cat 4. Not yet wired into Temporal dispatch (which doesn't exist) |
| Token budget (per-call cap) | NOT BUILT | LOOSE — needs `temp.inline.token_gate` (Layer 5 HARD GAP) |
| Token budget (tier-scaled pool) | NOT BUILT | LOOSE — needs dispatcher tracking per-tenant pool |
| LiteLLM router | RUNNING | T0.2 audit — pre-this-session |
| Metering pipeline (V1: token-counts) | MERGED | PR #1137 (my work) — `src/keiracom_system/metering/` |
| Metering production wiring | LOOSE (P1) | psycopg adapter + Prefect daily rollup — follow-up I named in PR #1137 |
| Metering log shipper | LOOSE (P2) | Vector/Filebeat → metering service stdin |
| Provider billing API ($AUD translation) | DEFERRED (P3) | post-first-paying-customer per PR #1128 §5 |
| Cost dashboard | LOOSE | Admin panel per-tenant/callsign/agent-role |
| Cost attribution wrappers | LOOSE | `cost.attribution_wrappers` Cat 4 row 77 — wrappers around 6 MAL primitives |
| Governance cost attribution | LOOSE | `cost.governance_attribution` — PR-review + canonical-key query + audit-dispatch cost attribution |

## §3 Measured

What IS measured per PR #1137 metering pipeline + this session's il34 spike:

| Metric | Value | Source |
|---|---|---|
| LLM tokens per Hindsight `retain` call | ~2,377 tokens per fixture (n=100 corpus) | il34 spike `/tmp/c7_bench.json` |
| LLM tokens total at n=100 fixture ingest | 237,737 tokens (~$0.71 OpenAI gpt-4o-mini at quoted rates) | il34 spike |
| LLM tokens total at n=1000 fixture ingest | 1,663,309 tokens (~$4.99) | il34 spike |
| Hindsight extraction expansion at n=100 | 100 fixtures → 107 memory units (1.07× expansion) | il34 spike |
| Hindsight CONSOLIDATION at n=1000 | 1000 fixtures → 719 memory units (0.72× — de-duplication kicks in at scale) | il34 spike |
| Metering DB schema | `keiracom_tenant_metering(tenant_id, date_utc, model, request_count, input_tokens_sum, output_tokens_sum)` | PR #1137 migration |
| Cost columns deferred to P3 | TRUE — no `cost_aud_sum` column V1 | PR #1137 migration verbatim |

What is NOT measured:
- Anthropic prompt cache hit rate (no Keiracom-side wiring)
- Valkey semantic cache hit rate (not wired into a chokepoint to track)
- Per-tier actual vs proposed multiplier (no production traffic)
- LiteLLM routing latency overhead (not benchmarked)
- Tool-call overhead vs LLM tokens (not separately attributed per Layer 8 §4)
- $AUD spend per tenant per day (deferred to P3 provider-billing-API)

## §4 Token budget / cost behaviour

THIS layer's entire mandate is token budget + cost behaviour. Per-substrate:

**Anthropic prompt cache** — 0.10× INPUT cost on cache hits. Output cost unchanged. Cache breakpoints + 5-min TTL per Anthropic spec. For Keiracom, this means:
- Stable system prompts → cache breakpoint (cache hit on every subsequent call within 5 min)
- MCP tools/list catalog → cache breakpoint
- Tenant-specific context (BYOK, preferences) → cache breakpoint OR NOT depending on size threshold

**Valkey semantic cache** — full call avoidance. Cache hit = 0 LLM cost + ~1ms Valkey lookup. Cache miss = baseline cost + ~1ms Valkey write.

**Hindsight recall (beyond active window)** — recall is itself an LLM-mediated step in Hindsight (the reflect/recall calls hit the embedding model + sometimes the synthesis LLM). NOT zero cost. Per il34 spike, embedding via TEI sidecar is free (local BGE-small). Recall synthesis is ~hundreds of tokens depending on top-k.

**Token budget enforcement** — runs at `temp.inline.token_gate` (Layer 5). Without Temporal: no enforcement today. With Temporal: per-call cap + per-tenant pool checked at workflow start.

**Routing decisions:**
- Customer-facing calls → customer's BYOK key (zero Keiracom cost; customer pays provider)
- Internal governance calls → Keiracom-funded Gemini 2.5 Flash (low rate; per `reference_model_routing.md`)
- Internal sub-tasks → may route to Haiku or local model depending on tier/model-cost-calibration (LOOSE)

## §5 Cache strategy applicable

THIS layer IS the cache strategy. Spec'd above in §1 + §4. Implementation pieces:

- **Prompt cache wiring** — Keiracom-side template scaffold for per-domain stable content. NOT BUILT.
- **Valkey wiring** — Valkey running but not yet wired into a dispatch chokepoint. Awaits Temporal deploy (Layer 5).
- **Hindsight wiring** — TEI sidecar (PR #1133) + Hindsight wrappers (Atlas PR #1134) shipped. Recall already routed through them in dev.
- **Cache invalidation policy** — PER-SUBSTRATE:
  - Prompt cache: time-based (5-min Anthropic-side)
  - Valkey: TTL per cache key (1min for live-data queries, 24hr for definitions)
  - Hindsight: no invalidation — append-only memory; relevance scoring at recall time

**Cache discipline enforcement** — `cost.cache_discipline` was "triple-option A discipline-doc + B runtime-warn + C PR-linter" but SHIFTED to Temporal interception layer per 2026-05-25 ratify (Cat 4 row 79). Means: gates A/B/C are SUPERSEDED by mechanical enforcement at `temp.inline.cache_check` (Layer 5). Without Temporal: no enforcement today.

## §6 LOOSE items / open questions

1. **Per-tier multipliers PROPOSAL pressure-test** — Sandbox 0.5× / Solo 1.0× / Pro 1.5× / Team 2.0× — no production data to validate. Phase 2 work per `ceo:cache_framework_canonical.tier_multipliers_status`.
2. **Token budget Viktor 4-component proposal** — `cost.token_budget` LOOSE. Sub-deliberation per directive; not yet ratified.
3. **Provider-billing-API integration (P3)** — DEFERRED post-first-paying-customer. Until then, dashboard shows token-counts only, no $AUD.
4. **Cost attribution wrappers (`cost.attribution_wrappers`)** — wrappers around the 6 MAL primitives to attribute per-primitive cost. LOOSE; pending build.
5. **Governance cost attribution (`cost.governance_attribution`)** — attribute PR review / canonical-key query / audit-dispatch cost to governance budget. LOOSE.
6. **Cost dashboard scope** — admin only? customer-visible breakdown by callsign + agent-role? Cat 19 customer-product surface needs deliberator concur on scope.
7. **Aiden §3.C nits**:
   - `cost.tier_router_attribution` — how tier-router decides Solo/Pro/Scale topology routing (cost differs per topology)
   - `cost.cache_post_ephemeral_validity` — semantic cache validity in ephemeral-agent world (each spawn loses local cache locality; Valkey shared survives across spawns but prompt cache resets)
8. **Metering production wiring** — psycopg adapter + Prefect daily rollup deployment. LOOSE; I named as P1 follow-up in PR #1137.
9. **Log shipper config** — Vector or Filebeat tailing Hindsight container logs → metering service stdin. LOOSE; P2 follow-up I named.

## §7 Per-tier behaviour variation

Per-tier multipliers PROPOSAL pressure-test (per `ceo:cache_framework_canonical`):

| Tier | Multiplier | Practical meaning |
|---|---|---|
| Sandbox | 0.5× | Aggressive caching; force Anthropic prompt cache hits where possible; deny calls that miss cache budget. Free-tier protection. |
| Solo | 1.0× | Baseline. Cache opportunistically; allow uncached calls within per-call cap. |
| Pro | 1.5× | Looser per-call cap (multi-thread chats allowed → more parallel cache pressure). Higher Valkey TTL acceptable (Pro customers tolerate slightly stale data for $$ savings). |
| Team | 2.0× | Per-user accounting → cache key includes user_id to avoid cross-user cache poisoning. Higher per-call cap. |
| Enterprise | Custom | Per-tenant cache configuration (some Enterprise customers will WANT cache-busting for regulatory determinism — provable freshness). Per-tenant Valkey instance for Topology A. |

The multipliers are PROPOSAL — pressure-test means: run a per-tier sample at first-paying-customer scale, observe actual cache hit rates + costs, calibrate up/down.

The model-cost-calibration question (per `cost.token_budget`): a Sonnet call is ~3× more expensive than Haiku per token. Tier-scaled pool means a Sandbox user gets fewer Sonnet calls than a Solo user gets, weighted by $AUD-per-call. Token-budget enforcement needs the per-model multiplier baked in.

## §8 Per-agent-type variation

| Agent type | Cache profile | Cost-control specific |
|---|---|---|
| Chat agent (Keira, Tier 1) | Heavy Anthropic prompt cache (chat history is structurally stable per turn); Valkey for repetitive customer queries ("what's my balance" type) | Customer's BYOK key; per-tenant pool applies |
| Deliberators (Tier 2) | Light prompt cache (each deliberator's prompt is structurally stable but per-PR content varies); minimal Valkey hits | Internal Gemini routing → low absolute cost; per-callsign attribution for governance budget |
| Worker agents (Tier 3) | Tool-result cache via Valkey (HubSpot company lookup is cacheable for N seconds); minimal prompt cache | Customer's BYOK key; per-tenant pool; per-worker-type cost attribution wrapper |

Ephemeral-agent caveat (Layer 8 §5 + Aiden §3.C nit `cost.cache_post_ephemeral_validity`):
- Each agent spawn = new Anthropic prompt cache miss on first call (5-min TTL doesn't survive spawn cycles)
- Valkey is shared so hits survive across spawns
- Net: prompt cache effectiveness DROPS in ephemeral world; Valkey effectiveness UNCHANGED
- Compensation: pre-warm Anthropic prompt cache from a "cache-warmer" workflow on tenant signup OR per-tier health check (LOOSE — name as follow-up)

## Cross-cutting concerns

- **Multi-tenancy enforcement** — Valkey cache keys MUST namespace by tenant_id (cross-tenant cache poisoning = data leakage). LiteLLM virtual key per tenant = per-tenant rate limiting. Metering rolls up per tenant.
- **Security (BYOK + secret mgmt)** — Vault Transit (PR #1146) for BYOK envelope; LiteLLM looks up per-tenant key at call time. Cache layer NEVER stores decrypted keys. Go Sidecar (Layer 8) blocks key leakage into LLM context.
- **CI/CD + rollback** — cache TTL / multiplier config should be GitOps-managed; rollback = re-apply prior config. No runtime mutation.
- **Backup-DR (V1.x)** — Valkey cache is regenerable (no backup needed). Metering data IS critical (needs Postgres backup per `infra.backup_dr`). Hindsight memory is the long-term store; backup via per-tenant export (`Agency_OS-il34` V1.x).
- **Customer file system** — file uploads NOT cached at this layer (binary data, no semantic cache value). Object Storage handles its own caching.
- **Reasoning trace + audit trail** — every cache hit / miss / token spend → audit event for Layer 12 observability. Required for compliance attestation (Enterprise tier).
- **Compliance gates** — regulated customers may demand provable cache-free path (every query = fresh LLM call). Enterprise tier per-tenant cache config supports this.

## Sources

- `ceo:cache_framework_canonical` (queried 2026-05-25)
- `ceo:keiracom_architecture_v2_locked` Cat 4 + Cat 11
- `ceo:keiracom_build_priority` Phase E e2 (rate limit + token spend hard-stop)
- Inventory Cat 4 (10 rows) + Cat 11 (2 rows) + Cat 20 line 525
- PR #1137 — metering pipeline (Orion, this session window)
- PR #1128 — BYOK LLM routing spike (Orion)
- PR #1133 — TEI sidecar (Orion)
- PR #1146 — Vault decryptor (Orion, this session)
- `reference_model_routing.md` — internal Gemini routing memo
- il34 spike report at `/home/elliotbot/clawd/keiracom_system/dev/hindsight/spike/SPIKE_REPORT.md` (empirical per-corpus cost measurements)
