# Phase A7 — Cache architecture + cost infrastructure (design)

**Owner:** Orion (design lead) + Atlas (review)
**Phase:** A7 per `ceo:dave_migration_sequence.phase_a_extended.a7`
**Status:** DESIGN DRAFT — awaiting Atlas review concur + Max code-quality lens
**Date:** 2026-05-26

## Notes — canonical evidence pasted per audit-dispatch checklist

`ceo:cache_framework_canonical` (queried 2026-05-26, verbatim):
```json
{
  "directive": "KEI-SYSTEM-DEEP-DIVE",
  "connects_to": ["cost.cache_discipline","cost.token_budget","cost.semantic_cache_valkey",
                  "temp.inline.cache_check","deepdive.layer11_cost_optimization"],
  "layer_1_anthropic_prompt_cache": {"content":"structurally stable per-domain content","multiplier":"0.10x input cost"},
  "layer_2_uncached": {"content":"per-call dynamic content","multiplier":"1.0x"},
  "valkey_semantic_cache": "layered on top for repetitive query hits",
  "history_beyond_active_window": "stored in Hindsight for queryable recall, NOT held in active context",
  "per_tier_multipliers_proposal": {"sandbox":"0.5x","solo":"1.0x","pro":"1.5x","team":"2.0x","enterprise":"custom"},
  "tier_multipliers_status": "PROPOSAL — pressure-test in Phase 2"
}
```

Inventory Cat 4 verbatim (already-RATIFIED + LOOSE rows):
- `cost.cache_discipline` (RATIFIED-CEO placement; LOOSE implementation) — "SHIFTING to Temporal interception layer per ratify 2026-05-25"
- `cost.semantic_cache_valkey` (RATIFIED-DM) — "Valkey running today"
- `cost.token_budget` (LOOSE) — "per-call cap + tier-scaled pool + dispatcher-enforced + model-cost-calibrated" (Viktor 4-component)
- `cost.metering_pipeline` (RATIFIED-CEO, PR #1137) — token-counts only V1

Inventory Cat 5 verbatim (Temporal gates):
- `temp.inline.cache_check` — Cache discipline checks INLINE
- `temp.inline.token_gate` — Token spend gates INLINE
- `temp.middleware` — single chokepoint

`ceo:dave_decisions_2026_05_26.decision_5_temporal_ephemeral_instance` — A6 substrate live (vc2-2c-4gb Sydney, 45.76.114.137).

Layer 11 deep-dive (my PR #1150 `docs/architecture/deep_dives/layer_11_cost_optimization.md`) names: zero embedding/vector field in Hindsight 0.6.2 API; metering pipeline ships counts-only V1; per-corpus empirical token-cost data from il34 spike.

## §1 Scope + non-goals

### In scope (A7 build)

1. **Anthropic prompt-cache breakpoints in LiteLLM router** — instrument the existing LiteLLM router to apply `cache_control: {"type": "ephemeral"}` on structurally-stable prefix content (system prompts + tool definitions + per-domain knowledge).
2. **Layer 1 / Layer 2 module constants** — freeze the framework as importable Python constants (`CACHE_LAYER_1_MULTIPLIER = 0.10` etc.) so consumers reference one source-of-truth.
3. **Valkey semantic cache deployed + measured** — Valkey is RUNNING per Cat 4; needs (a) embedding-similarity threshold tuning, (b) cache-key canonicalisation, (c) instrumentation for hit/miss attribution.
4. **LiteLLM virtual key for Dave's tenant** — single virtual key with rate limit + budget pool; per-tenant flow lands at V1 customer onboarding (out of scope here).
5. **Token-budget enforcement via Temporal `temp.inline.token_gate`** — POLICY DATA only (the gate itself is implemented when LLM-call workflow #2 lands); A7 ships the per-tier cap + pool config that workflow #2 will enforce against.
6. **48h cache-hit-rate baseline** — instrument + observe; honest report on hit-rate behaviour pre-paying-customer.

### Out of scope (separately dispatched)

- LLM-call workflow #2 itself (where token_gate + cache_check + content_check + tier_gate WIRE INTO Temporal; A7 provides the policy data, workflow #2 enforces)
- Per-tenant virtual-key fanout (V1 customer onboarding, Phase C5/B5)
- Provider-billing-API integration for $AUD translation (P3 follow-up per PR #1128 §5; `cost.metering.provider_billing_api` DEFERRED)
- Cost dashboard UX (Cat 19 ux.surface — separate front-end work)
- Cache invalidation on Composio webhook (Layer 8 LOOSE; A7 names the integration point but doesn't ship it)
- Hindsight "beyond active window" recall — already exists via Atlas wrappers (PR #1134); A7 documents the boundary, not the build

## §2 Cache tier architecture

Three substrates, layered:

```
┌─────────────────────────────────────────────────────────────────┐
│ CHAT / WORKER / DELIBERATOR call enters Temporal workflow       │
│                          │                                      │
│                          ▼                                      │
│   ┌──────────────────────────────────────────────────┐          │
│   │ Gate 4 tier_gate (CHECK)                         │          │
│   │ Gate 6 content_check (CHECK)                     │          │
│   │ Gate 3 cache_check (DISPATCH ↓)                  │          │
│   └──────────────────────────────────────────────────┘          │
│                          │                                      │
│            ┌─────────────┼──────────────┐                       │
│            ▼             ▼              ▼                       │
│      [Valkey query]  [Hindsight query] [no-cache continue]      │
│            │             │              │                       │
│      HIT? ─┴── HIT? ─────┴──────────────┘                       │
│        │      │          │                                      │
│  return cached │ return Hindsight result                        │
│              MISS                                               │
│                ▼                                                │
│   ┌──────────────────────────────────────────────────┐          │
│   │ Gate 2 token_gate (CHECK — Phase 2 amendment 3)  │          │
│   └──────────────────────────────────────────────────┘          │
│                          │                                      │
│                          ▼                                      │
│   ┌──────────────────────────────────────────────────┐          │
│   │ LiteLLM router → LLM provider                    │          │
│   │  with cache_control breakpoints on stable prefix │          │
│   │  → Anthropic prompt cache (0.10× input)          │          │
│   └──────────────────────────────────────────────────┘          │
│                          │                                      │
│                          ▼                                      │
│   ┌──────────────────────────────────────────────────┐          │
│   │ Populate Valkey on response (TTL per tool type)  │          │
│   │ Gate 1 listener + Gate 5 audit INLINE post-call  │          │
│   │ Async Gate 7 post_validation                     │          │
│   └──────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Substrate roles

| Substrate | Role | Where it lives | Hit cost | Miss cost |
|---|---|---|---|---|
| **Anthropic prompt cache (Layer 1)** | Cache the stable prefix of LLM prompts (system + tools + per-domain context) at the provider | Anthropic-side; configured via `cache_control` breakpoint in the prompt | 0.10× input tokens; 5-min TTL per breakpoint | Standard input cost; populates cache for next call |
| **Valkey semantic cache** | Short-circuit the whole LLM call when the query is semantically similar to a recent cached query | Valkey on fleet host (RUNNING per Cat 4) | ~1ms Valkey lookup + 0 LLM tokens | ~1ms Valkey miss + standard LLM call + ~2ms Valkey write |
| **Hindsight beyond active window** | Recall stored prior knowledge to assemble in-context (NOT a perf cache — observability + memory) | Hindsight engine (PR #1133 + Atlas PR #1134 wrappers) | Embedding query (~100ms TEI + recall query) | Same — Hindsight is always-on, not a cache miss/hit semantic |

### Cache invalidation policy

- **Anthropic prompt cache** — time-based 5-min TTL per cache breakpoint. Caller does nothing; Anthropic clears on TTL. No invalidation API.
- **Valkey** — per-tool-type TTL config:
  - Read-mostly tools (HubSpot company lookup, Slack channel list): TTL = 60s
  - Definition fetches (tools/list catalog, mental-model lookups): TTL = 24h
  - Mutation tools (HubSpot company create, Slack message send): TTL = 0 (no cache; mutations always hit LLM with no Valkey check)
- **Hindsight** — append-only memory; relevance scoring at recall time. No invalidation.

### Cache-hit short-circuit (per Phase 2 amendment 3 / `Agency_OS-ucf8`)

The current contract V1 sequence fires `token_gate` BEFORE `cache_check`, which wastes token-gate work on cache-hit calls. The architecture ABOVE incorporates the proposed re-ordering:

```
tier_gate → content_check → cache_check
                              ├─ HIT: emit cache-hit-pass event + return cached response (skip token_gate + LLM)
                              └─ MISS: continue → token_gate → LLM → post-call gates
```

This is amendment #3 already filed as `Agency_OS-ucf8` for Phase 2 contract V2 ratification. Surfaced here because the cache architecture's correctness depends on this re-ordering — A7 should not build under V1 sequence then re-shuffle; contract V2 lift is the gate for A7 build dispatch.

## §3 Anthropic prompt-cache breakpoints

### LiteLLM instrumentation

LiteLLM (the existing `gov.litellm_router` RATIFIED-CEO running surface) sits between Keiracom code and the LLM provider. We instrument it to inject `cache_control` markers on the right content blocks.

**Where to instrument:**

LiteLLM supports per-call `cache_control` via the Anthropic provider passthrough. The router can be configured at deployment (via `litellm_config.yaml`) to apply cache_control breakpoints on:

1. **System prompt** — stable per-agent-type per-tenant; breakpoint at end of system block
2. **Tools/list catalog** — stable per-tier; breakpoint at end of tools block
3. **Per-domain context** — agent-type-specific (e.g., chat agent has different stable context than worker agents)

Per-call cache_control is set via the `cache_control` field on each content block (Anthropic API spec). LiteLLM's Anthropic provider passes this through transparently.

**Default breakpoint policy (V1 — refine in Phase 2 with measured hit rates):**

| Content block | Cache? | Max age |
|---|---|---|
| System prompt | YES | 5min (Anthropic default) |
| Tools/list | YES | 5min |
| Per-domain knowledge | YES (if >1024 tokens) | 5min |
| User input | NO | — |
| Tool result | NO | — |

**Edge case — short-prefix non-cacheable:** Anthropic requires ≥1024 tokens between breakpoint markers. Per-tier system prompts may not meet the threshold for Sandbox tier (smaller prompts) — those tiers get no Layer 1 benefit. Documented; Phase 2 may pad prompts or skip cache_control for under-threshold tiers.

### Layer 1 / Layer 2 module constants

Freeze the framework as importable Python constants so consumers have one source-of-truth:

```python
# src/keiracom_system/cache/constants.py
"""Cache framework canonical constants per ceo:cache_framework_canonical."""

# Multiplier on standard input cost when prompt cache HITS
CACHE_LAYER_1_MULTIPLIER = 0.10

# Multiplier when no cache (baseline)
CACHE_LAYER_2_MULTIPLIER = 1.0

# Per-tier multipliers PROPOSAL (per ceo:cache_framework_canonical)
# Status: PROPOSAL — pressure-test in Phase 2 with real traffic
TIER_MULTIPLIERS_PROPOSAL: dict[str, float | str] = {
    "sandbox": 0.5,
    "solo": 1.0,
    "pro": 1.5,
    "team": 2.0,
    "enterprise": "custom",
}

# Per-tool-type Valkey TTL (seconds). Conservative defaults; refine post-baseline.
VALKEY_TTL_READ_MOSTLY = 60
VALKEY_TTL_DEFINITION_FETCH = 24 * 3600
VALKEY_TTL_MUTATION = 0  # No cache on mutations
```

## §4 Valkey semantic cache

### Design

Valkey-side schema:
- **Cache key** = canonical hash of `(tenant_id, tool_name, normalised_args_json, query_intent_embedding_bucket)`
- **Cache value** = JSON `{response, cached_at, ttl_seconds, hit_count}`
- **Embedding bucket** = quantised 384-dim BGE embedding (TEI sidecar PR #1133); reduces to a bucket index so semantically-similar queries hit the same cache key

### Key canonicalisation

The canonicalisation function MUST be deterministic across spawns (so ephemeral agent #2 hits the cache that ephemeral agent #1 populated). Pseudocode:

```python
def canonical_cache_key(
    *, tenant_id: str, tool_name: str, args: dict, query_text: str | None = None
) -> str:
    args_normalised = json.dumps(args, sort_keys=True, separators=(",", ":"))
    args_hash = hashlib.sha256(args_normalised.encode()).hexdigest()[:16]
    if query_text:
        # Semantic component for natural-language tool queries
        embedding = tei_client.embed([query_text])[0]
        bucket = _quantise_to_bucket(embedding, num_buckets=4096)
        return f"v1:{tenant_id}:{tool_name}:{args_hash}:b{bucket}"
    return f"v1:{tenant_id}:{tool_name}:{args_hash}"
```

`_quantise_to_bucket` is the similarity threshold — too coarse and unrelated queries collide; too fine and semantically-similar queries miss each other. V1 PROPOSAL: 4096 buckets (12 bits) from a learned hash projection. Phase 2 tune from measured collision rate.

### Cross-tenant isolation

Cache key MUST start with `v1:{tenant_id}:` — namespace prefix. Cross-tenant cache hits are a data leakage class (a query against tenant A's HubSpot must NEVER return tenant B's HubSpot data, even if the natural-language query is identical). Valkey-side key inspection on read; no shared namespace.

### Instrumentation for measurement (A7 §6 baseline)

Every cache lookup emits a metric:
```
keiracom.cache.valkey.lookup{tenant_id, tool_name, outcome=hit|miss}
```

Stream to Better Stack (already in fleet env vars per Layer 10 deep-dive). The 48h baseline (§6 below) queries these metrics to compute hit rate.

## §5 LiteLLM virtual key for Dave's tenant

Dave is the V1 dogfooding moment per `ceo:dave_migration_sequence.rationale`. A7 ships a single LiteLLM virtual key for Dave's tenant. Per-customer flow lands at V1 customer onboarding (Phase C5).

### Config shape

```yaml
# litellm_config.yaml (excerpt)
virtual_keys:
  - key_alias: "dave-v1-dogfooding"
    tenant_id: "dave-internal"
    models:
      - anthropic/claude-3-5-sonnet
      - anthropic/claude-3-5-haiku
      - openai/gpt-4o-mini
    rate_limit_rpm: 60
    rate_limit_tpm: 200000
    budget:
      daily_usd: 50
      monthly_usd: 1000
    cache_control_enabled: true
    metadata:
      tier: "team"   # Dave's effective tier for capacity allocation
```

Per `gov.litellm_router` config — Dave operates at Team-tier-equivalent for capacity allocation purposes per his migration scope.

## §6 Token-budget enforcement (policy data hook)

Per A7 dispatch item 5: A7 provides the POLICY DATA that the `temp.inline.token_gate` (LLM-call workflow #2) enforces against. A7 does NOT itself wire the gate (that's workflow #2 scope).

### Policy data shape

```python
# src/keiracom_system/cache/token_budget_policy.py
@dataclass
class TenantBudgetPolicy:
    tenant_id: str
    tier: str  # sandbox | solo | pro | team | enterprise
    per_call_cap_tokens: int           # hard ceiling on single LLM call
    daily_pool_tokens: int             # tenant aggregate per UTC day
    monthly_pool_tokens: int           # tenant aggregate per UTC month
    model_cost_calibration: dict[str, float]  # weight per model (Sonnet 3.0×, Haiku 1.0× etc.)
```

### Default policies per tier (V1 PROPOSAL — pressure-test)

| Tier | per_call_cap | daily_pool | monthly_pool |
|---|---|---|---|
| Sandbox | 10K | 50K (warn at 25K) per amendment 2 | 500K |
| Solo | 50K | 1M | 30M |
| Pro | 100K | 5M | 150M |
| Team | 200K | 20M | 600M |
| Enterprise | custom | custom | custom |

Model-cost-calibration weight (default V1):
- Claude Sonnet 3.5: 3.0× (most expensive)
- Claude Haiku 3.5: 1.0× (baseline)
- GPT-4o: 2.5×
- GPT-4o-mini: 0.8×
- Gemini 2.5 Flash: 0.5× (internal-only per `reference_model_routing`)

`token_gate` in workflow #2 reads this policy data via `from_env`-style factory and applies the cap + pool check before the LLM call.

### Storage

`keiracom_tenant_budgets` Postgres table (sibling to `keiracom_tenant_metering` from PR #1137):

```sql
CREATE TABLE keiracom_tenant_budgets (
  tenant_id            UUID PRIMARY KEY REFERENCES keiracom_tenants(tenant_id) ON DELETE CASCADE,
  tier                 TEXT NOT NULL,
  per_call_cap_tokens  BIGINT NOT NULL,
  daily_pool_tokens    BIGINT NOT NULL,
  monthly_pool_tokens  BIGINT NOT NULL,
  model_cost_calibration JSONB NOT NULL,
  effective_from       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  effective_until      TIMESTAMPTZ
);
```

Tier defaults populate via migration; per-tenant overrides (Enterprise) added by operator.

## §7 48h cache-hit-rate baseline

### Methodology

V1 framing: NO PAYING CUSTOMERS exist yet. The 48h baseline measures hit rate AGAINST DAVE'S OWN TRAFFIC (post-A9 migration). Honest framing: pre-paying-customer baselines are best-case + small-sample; refine after first 3 paying customers.

### Instrumentation

1. Cache lookup metric (per §4) → Better Stack
2. Token-cost metric per LLM call → metering pipeline (PR #1137) extension to attribute "cache-hit-avoided-cost"
3. 48h observation window starts post-A9 migration validation gate

### Reported metrics

| Metric | Source | Interpretation |
|---|---|---|
| Valkey cache hit rate (per tenant, per tool) | Better Stack | Hit rate >40% = healthy; <10% = poor canonicalisation (tune buckets) |
| Anthropic prompt-cache hit rate | Anthropic API response usage block (`cache_creation_input_tokens` vs `cache_read_input_tokens`) | Read >50% of input = good; <20% = breakpoint placement misaligned with actual call shape |
| Avoided cost USD/AUD (Valkey) | `hits × avg_uncached_tokens × model_unit_cost` | Reports against monthly budget pool |
| Avoided cost USD/AUD (Anthropic prompt cache) | `cache_read_input_tokens × 0.9 × input_cost` | The 0.10× -> 0.90× savings on cache reads |

### Honest framing

Report MUST state: "N=1 tenant (Dave), 48h window, post-A9-migration only. Not representative of production multi-tenant scale." First 3 paying customers + their first month of traffic = real calibration data; until then, baselines are directional only.

## §8 Per-tier behaviour variation

| Tier | Anthropic cache | Valkey | Token budget | Per-tier multiplier (proposal) |
|---|---|---|---|---|
| Sandbox | Limited (small prompts often under 1024 token breakpoint threshold) | Aggressive caching; long TTL on read-mostly tools | 50K/day cap per amendment 2 | 0.5× |
| Solo | Standard | Standard TTL | 1M/day pool | 1.0× |
| Pro | Standard + per-thread cache (multi-thread chats) | Per-thread cache key namespacing | 5M/day pool | 1.5× |
| Team | Standard + per-user cache keys | Per-user cache key namespacing | 20M/day pool | 2.0× |
| Enterprise | Custom — per-tenant Valkey instance possible (Topology A) | Per-tenant Valkey for compliance verticals | Custom pools | custom |

## §9 Per-agent-type variation

| Agent type | Cache profile | LiteLLM routing |
|---|---|---|
| Chat agent (Keira, Tier 1 ephemeral) | Heavy Anthropic prompt cache (system + persona is structurally stable); Valkey for repetitive customer queries | Customer's BYOK key via per-tenant virtual key |
| Deliberators (Tier 2) | Light prompt cache (each deliberator's prompt is structurally stable but per-PR content varies); minimal Valkey hits | Internal Gemini routing per `reference_model_routing` — Keiracom-funded |
| Worker agents (Tier 3) | Tool-result cache via Valkey (HubSpot company lookup cacheable for N seconds); minimal prompt cache | Customer's BYOK key |

Ephemeral-agent caveat (per `cost.cache_post_ephemeral_validity` Aiden §3.C nit):
- Each agent spawn = NEW Anthropic prompt cache miss on first call (5-min TTL doesn't survive spawn cycles + the cache is per-API-key-per-connection)
- Valkey is SHARED → hits survive across spawns
- Net effect: prompt cache effectiveness DROPS in ephemeral world; Valkey effectiveness UNCHANGED
- Compensation: pre-warm Anthropic prompt cache from a "cache-warmer" workflow on tenant signup OR per-tier health check (LOOSE — file as A7 follow-up bd post-design concur)

## §10 Acceptance criteria

For A7 build dispatch (separate from this design):

1. `src/keiracom_system/cache/constants.py` ships with all 4 Layer 1/Layer 2 constants + per-tier multipliers + per-tool TTL defaults. Unit tests lock the values against `ceo:cache_framework_canonical`.
2. `src/keiracom_system/cache/valkey_client.py` ships with `canonical_cache_key()` + `get()` / `set()` / `instrument()` methods. Unit tests cover key canonicalisation determinism + cross-tenant isolation (cache key namespace prefix).
3. `src/keiracom_system/cache/token_budget_policy.py` ships with `TenantBudgetPolicy` dataclass + `from_db(db, tenant_id)` factory. Unit tests cover all 5 tier defaults + Enterprise custom path.
4. LiteLLM config update (`litellm_config.yaml`) ships with Dave's virtual key + cache_control_enabled flag.
5. Postgres migration creates `keiracom_tenant_budgets` table + seeds 5 tier-default rows.
6. Better Stack chart for `keiracom.cache.valkey.lookup` metric exists (Layer 12 follow-up; design names the metric shape).
7. 48h observation report posted to `keiracom.elliot.inbox` after A9 migration validation.

## §11 LOOSE items / open questions

1. **Embedding bucket count** — V1 PROPOSAL 4096 buckets; Phase 2 tune from measured collision rate. Need empirical data to calibrate.
2. **Pre-warm cache-warmer workflow** — ephemeral-agent prompt cache misses on every spawn. Spec a "warmer" workflow that issues a sentinel call on tenant signup OR per-tier health check. LOOSE.
3. **Token-budget enforcement timing** — `token_gate` checks the cap pre-call; what about mid-call streaming overruns? Anthropic streaming reports tokens incrementally; we'd need mid-stream cancellation logic. Phase 2.
4. **Per-tool TTL granularity** — V1 uses 3 broad categories (read-mostly / definition / mutation). Phase 2 may need per-integration TTL (HubSpot vs Salesforce TTL may differ based on update frequency norms).
5. **Cache invalidation on Composio webhook** — Composio offers webhooks for data changes. Not in A7 scope; Layer 8 LOOSE per Layer 11 deep-dive §6 nit 7.
6. **$AUD translation** — DEFERRED per `cost.metering.provider_billing_api` P3. Dashboard reports token-counts only until then.
7. **Per-tenant Valkey for Enterprise** — Topology A per-tenant Valkey instance increases ops surface (N tenants = N Valkey hosts). Compliance verticals may require it. Phase 2 sub-deliberation.
8. **Cache poisoning on tool errors** — if a tool call errors and the error is cached, subsequent calls return the cached error. Need negative-result TTL (likely 0 or very low — 5s).

## §12 Engineer-tier build sequencing

Build dispatch (separate from this design) sequencing:

1. **Sub-task 1**: `constants.py` + `valkey_client.py` core + unit tests (~150 LoC). Independent of Temporal/LiteLLM.
2. **Sub-task 2**: `token_budget_policy.py` + Postgres migration + unit tests (~100 LoC). Independent.
3. **Sub-task 3**: LiteLLM config update for Dave's virtual key + `cache_control` enablement (~50 LoC config; 0 code change).
4. **Sub-task 4**: Better Stack instrumentation hook in `valkey_client.py` + metric registration (~50 LoC). Needs Layer 12 alignment.
5. **Sub-task 5**: 48h baseline observation script + report template (~50 LoC). Runs post-A9.

Total: ~400 LoC across 4 sub-builds + 1 config update + 1 migration. Atlas reviews each; engineer-tier (could be me OR Atlas) implements.

**Dependency on workflow #2 (LLM-call migration)**: token_budget_policy module + Postgres seed land in A7. Workflow #2 IMPORTS this module + calls `from_db(db, tenant_id)` at activity start, then enforces the cap. A7 doesn't ship the gate; A7 ships the policy data the gate enforces against.

**Dependency on contract V2 amendment 3** (cache-hit short-circuit re-ordering, `Agency_OS-ucf8`): A7 build SHOULD wait for contract V2 ratify so the cache-check ordering is canonical. If V2 stalls, A7 builds under V1 sequence + we accept the inefficient `token_gate` firing on cache hits as a known V1 cost; refactor when V2 lands.

## §13 Build clarifications (post-design-review fold-in)

Added post-PR-#1156-merge per **Max review** (10 observations, [REVIEW:approve:max] 2026-05-26T00:10:58Z) + **Atlas NIT** (defence-in-depth tenant_id prefix guard, NATS 2026-05-26 ~00:08 UTC). Both reviews concurred substantively on the design; these are engineer-tier-blocker resolutions for the build dispatch.

Original §1-§12 stand as the architectural design; §13 supersedes-where-conflict for build-time decisions.

### CB-1 — Valkey Python client library + version pin (Max obs #1, sub-task 1)

**Decision: `redis>=5.0.0,<6.0`** (existing repo dep — already in `requirements.txt` per Cat 4 `cost.semantic_cache_valkey` "Valkey running today"). Valkey is Redis-protocol-compatible; `redis-py` is the mature client.

**Rationale:**
- `redis-py` is in production use by Keiracom for KEI-117 rate limiting + KV state (per existing `requirements.txt` and KEI-205 boundary)
- `valkey-py` (Valkey's official client) exists but is newer + smaller community. Adopting now adds dep without proven win.
- Migration path: if Valkey-specific features ever needed (CLUSTER pubsub differences etc.), swap to `valkey-py` as a separate PR with version-pinned override

**No requirements.txt change needed** — this is the win vs PR #1154's `temporalio` gap. Engineer should verify via `grep -E '^redis' requirements.txt` before code commit + flag if absent.

### CB-2 — TEI sidecar integration shape for `canonical_cache_key()` (Max obs #2, sub-task 1)

**Decision: dependency-injection at `valkey_client.py.__init__()`.** Mirrors PR #1133 `TEIClient` injectable-transport pattern + PR #1132 `KeiracomTenantExtension` injectable `_DBProtocol`.

```python
# src/keiracom_system/cache/valkey_client.py (sketch)
from src.keiracom_system.embeddings import TEIClient  # PR #1133

class ValkeyClient:
    def __init__(
        self,
        redis_client: redis.Redis,
        tei_client: TEIClient,
        tenant_id: str,
    ):
        self._redis = redis_client
        self._tei = tei_client
        self._tenant_id = tenant_id

    def canonical_cache_key(self, *, tool_name: str, args: dict, query_text: str | None = None) -> str:
        # ... uses self._tei.embed(...) when query_text is set ...
```

**Rationale:** caller (workflow #2 activity factory) constructs both `redis.Redis` + `TEIClient` from env and passes in. Test path uses fakes (matches PR #1132 / PR #1133 / PR #1146 testability pattern).

**Lazy-import** at module level — keeps `valkey_client.py` importable on hosts without the embeddings module loaded (test env safety).

### CB-3 — `keiracom_tenant_budgets` schema contradiction (Max obs #3, sub-task 2)

**Decision: option (a) — POINT-IN-TIME only.** Drop `effective_from` + `effective_until` columns. Schema becomes:

```sql
CREATE TABLE keiracom_tenant_budgets (
  tenant_id              UUID         PRIMARY KEY REFERENCES keiracom_tenants(tenant_id) ON DELETE CASCADE,
  tier                   TEXT         NOT NULL CHECK (tier IN ('sandbox','solo','pro','team','enterprise')),
  per_call_cap_tokens    BIGINT       NOT NULL,
  daily_pool_tokens      BIGINT       NOT NULL,
  monthly_pool_tokens    BIGINT       NOT NULL,
  model_cost_calibration JSONB        NOT NULL,
  updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_keiracom_tenant_budgets_tier
  ON keiracom_tenant_budgets (tier);
```

Plus a trigger (or app-layer UPSERT) to `updated_at = NOW()` on policy change.

**Rationale:**
- V1 pre-revenue — historical "what was Pro's per-call-cap in March?" queries are not customer-facing requirements yet
- Historical audit STILL POSSIBLE via the metering pipeline (PR #1137 `keiracom_tenant_metering` rolls up by day; effective-budget-at-time can be reconstructed from rollup + budget UPDATE events)
- Simpler schema; smaller storage; lower error surface
- If time-travel becomes needed later: separate `keiracom_tenant_budgets_history` table + trigger to log diffs. Pure additive change, no V1 schema migration

**Folds Max obs #9** (CHECK constraint on tier) — already in the SQL above.

**Index decision per Max obs #3:** `idx_keiracom_tenant_budgets_tier` for "all Pro tenants" queries. No index on `(effective_until IS NULL)` needed — column removed per option (a).

### CB-4 — Verify LiteLLM `cache_control_enabled` is real (Max obs #4, sub-task 3)

**Decision: UNVERIFIED — sub-task 3 scope GROWS to include caller-side cache_control marker injection. ~30-50 LoC code addition. NOT config-only.**

Per Anthropic API spec, `cache_control: {"type": "ephemeral"}` is set per content block at message-construction time. LiteLLM transparently passes through any per-call `extra_headers` and per-block `cache_control` fields, but does NOT have a global "auto-inject breakpoints on stable prefix" YAML option I recognise.

**Sub-task 3 actually contains:**
1. ~20-30 LoC LiteLLM YAML config (Dave's tenant virtual key + rate limits + budget) — UNCHANGED from original §5
2. ~30-50 LoC NEW Python helper `inject_cache_control_markers(messages, breakpoint_policy)` at the caller layer (lives in `src/keiracom_system/cache/litellm_helpers.py`)
3. Engineer step: verify by grepping LiteLLM source / docs whether `cache_control_enabled` is a real upstream option (may have landed in a recent release I don't track). If yes, ditch the helper; if no, ship the helper.

**Total sub-task 3: ~50-80 LoC** (was originally claimed "~50 LoC config / 0 code change").

### CB-5 — Anthropic prompt cache hit rate metric name for Better Stack (Max obs #5, sub-task 4)

**Decision: `keiracom.cache.anthropic.input_tokens{type=create|read|standard, tenant_id, model}`** parallel to existing Valkey metric.

`type` enum semantics:
- `create` → Anthropic API response `usage.cache_creation_input_tokens` (cache breakpoint populated this call)
- `read` → Anthropic API response `usage.cache_read_input_tokens` (cache breakpoint hit this call → 0.10× cost saving)
- `standard` → Anthropic API response `usage.input_tokens` (uncached portion of input)

Sub-task 4 hooks the metric emission at the LiteLLM response-processing layer (after each LLM call returns). Sums attributable to Better Stack chart query.

§7 baseline interpretation thresholds:
- `read / (create + read + standard) > 50%` → healthy prompt-cache utilisation
- `read / (...) < 20%` → breakpoint placement misaligned with actual call shape (re-tune)

**Cardinality flag per Max:** `tenant_id × tool_name × outcome` at 200+ tenants × 50 tools × 2 outcomes = 20K active series. Better Stack billing-limit risk at scale. **Pre-aggregation hook needed for production scale** — file as Phase 2 follow-up bd post-A7-build. V1 (Dave N=1) is unaffected.

### CB-6 — LoC re-estimates (Max obs #6, all sub-tasks)

Updated estimates per Max's quality-lens re-estimate. Build dispatch acceptance criteria use these:

| Sub-task | Original | Revised | Notes |
|---|---|---|---|
| 1 constants.py + valkey_client.py | ~150 LoC | **~250 LoC** | constants ~40 + Valkey client (incl. write-time prefix guard per Atlas NIT) ~120 + tests ~90 |
| 2 token_budget_policy.py + Postgres migration | ~100 LoC | **~150 LoC** | dataclass+factory ~50 + SQL migration+seeds+CHECK ~60 + tests ~40 |
| 3 LiteLLM config + cache_control helper | ~50 LoC config / 0 code | **~50-80 LoC** | YAML ~25 + helper ~30-50 if cache_control_enabled is not real (verify first) |
| 4 Better Stack instrumentation | ~50 LoC | **~50 LoC** | Unchanged |
| 5 48h baseline observation script | ~50 LoC | **~50 LoC** | Unchanged |
| **Total** | **~400 LoC** | **~550-580 LoC** | Engineer scopes accordingly |

### CB-7 — LAW II currency translation (Max obs #7, §5)

**Decision: bilingual format `$X USD = $Y AUD` in all dollar-denominated fields.**

§5 LiteLLM virtual key updated:

```yaml
virtual_keys:
  - key_alias: "dave-v1-dogfooding"
    tenant_id: "dave-internal"
    models: [...]
    rate_limit_rpm: 60
    rate_limit_tpm: 200000
    budget:
      daily_usd: 50      # = $77.50 AUD (per Dave LAW II — 1 USD = 1.55 AUD)
      monthly_usd: 1000  # = $1,550 AUD
    cache_control_enabled: true   # NOTE: per CB-4 above, this flag is UNVERIFIED — engineer must verify in build dispatch
    metadata:
      tier: "team"
```

LiteLLM's `daily_usd` field name is platform-native (we don't change the field), but the inline comment shows AUD per LAW II.

### CB-8 — 48h baseline action thresholds (Max obs #8, §7)

**Decision: `<10% Valkey hit rate = BLOCKING-V1`.**

Verbatim addition to §7: "If 48h baseline reports Valkey hit rate <10% for any tool category, V1 customer onboard is BLOCKED until `_quantise_to_bucket` num_buckets is re-tuned and a follow-up 48h baseline reports >=10%. Engineer-discipline gate before first-paying-customer."

`<10% < hit rate < 40%` is the TRACK-AND-IMPROVE band (not blocking, but flagged).

Anthropic prompt-cache hit rate threshold (`<20% = breakpoint misaligned`) is TRACK-AND-IMPROVE (Anthropic-side measurement; non-customer-facing).

### CB-9 — Schema CHECK constraint (Max obs #9)

**Folded into CB-3 SQL** — `CHECK (tier IN ('sandbox','solo','pro','team','enterprise'))` is in the schema definition above.

### CB-10 — Valkey key construction hard rule + PR-linter (Max obs #10, §4)

**Decision: ratified as hard rule + PR-linter pattern.**

Hard rule (engineer discipline): "All Valkey key construction MUST go through `ValkeyClient.canonical_cache_key()`. Direct `redis.set / redis.get` calls outside `src/keiracom_system/cache/valkey_client.py` are forbidden."

PR-linter pattern (CI check):
```bash
# scripts/ci/check_no_raw_valkey_outside_client.sh
violations=$(grep -rE '\b(redis|valkey)\.(set|get|hset|hget|delete)\s*\(' \
  --include='*.py' \
  --exclude-dir=tests \
  src/ scripts/ \
  | grep -v 'src/keiracom_system/cache/valkey_client.py' \
  || true)
if [ -n "$violations" ]; then
  echo "ERROR: direct redis/valkey calls outside valkey_client.py — must use ValkeyClient.canonical_cache_key()"
  echo "$violations"
  exit 1
fi
```

Test additions for sub-task 1:
- Unit test that `ValkeyClient.set()` rejects any key not starting with `v1:{self._tenant_id}:` (CB-Atlas defence-in-depth — see below)
- Grep-based test in `tests/keiracom_system/cache/test_no_raw_valkey_outside_client.py` that scans repo for violations

### CB-Atlas — Write-time tenant_id prefix guard (Atlas NIT 2026-05-26 ~00:08 UTC)

**Decision: ratified.** Folded into sub-task 1 acceptance:

```python
# src/keiracom_system/cache/valkey_client.py
class ValkeyClient:
    # ... __init__ as in CB-2 ...

    def _enforce_tenant_prefix(self, key: str) -> None:
        """Reject any key not matching v1:{self._tenant_id}:* at the read/write boundary.
        Defence-in-depth: even if a caller bypasses canonical_cache_key(), this guard catches it."""
        expected_prefix = f"v1:{self._tenant_id}:"
        if not key.startswith(expected_prefix):
            raise ValueError(
                f"valkey key {key!r} does not match expected tenant prefix {expected_prefix!r} — "
                "all keys MUST go through canonical_cache_key()"
            )

    def get(self, key: str) -> str | None:
        self._enforce_tenant_prefix(key)
        return self._redis.get(key)

    def set(self, key: str, value: str, ttl: int = 0) -> None:
        self._enforce_tenant_prefix(key)
        if ttl > 0:
            self._redis.setex(key, ttl, value)
        else:
            self._redis.set(key, value)
```

Test coverage (sub-task 1 acceptance criterion 2 extension):
- `test_valkey_get_rejects_wrong_tenant_prefix` — different tenant_id prefix → ValueError
- `test_valkey_get_rejects_missing_prefix` — raw key without `v1:` → ValueError
- `test_valkey_get_accepts_canonical_key` — key from canonical_cache_key() passes

Atlas's reasoning: closes the "future code path bypasses canonicalisation + writes raw" hole at the write/read boundary, complementing the PR-linter pattern from CB-10. Two-layer defence: linter catches at PR-review time; runtime guard catches at runtime if the linter is bypassed.

### Summary of §13 deltas for engineer-tier dispatch

| Item | Affects | Effort delta |
|---|---|---|
| CB-1 redis>=5.0.0 verify | sub-task 1 | 0 (already in repo) |
| CB-2 DI tei_client at ValkeyClient.__init__ | sub-task 1 | minor — clarifies constructor signature |
| CB-3 schema drop effective_from/until | sub-task 2 | -10 LoC (simpler schema) |
| CB-4 cache_control helper code | sub-task 3 | +30-50 LoC (if cache_control_enabled unverified) |
| CB-5 Anthropic prompt cache metric name | sub-task 4 | 0 (naming clarification) |
| CB-6 LoC re-estimates | scope tracking | n/a — for resource planning |
| CB-7 currency bilingual | doc only | 0 |
| CB-8 <10% blocking threshold | sub-task 5 acceptance | 0 |
| CB-9 schema CHECK constraint | sub-task 2 | folded into CB-3 |
| CB-10 PR-linter pattern + hard rule | sub-task 1 (test) + CI scripts/ | +10 LoC linter script + 1 unit test |
| CB-Atlas write-time prefix guard | sub-task 1 | +5-10 LoC + 3 unit tests |

Net updated total: **~550-600 LoC** for the full A7 build (Max's re-estimate + CB-4 verify-then-grow path + CB-10 linter + CB-Atlas guard).

## Sources

- `ceo:cache_framework_canonical` (queried 2026-05-26)
- `ceo:keiracom_architecture_v2_locked` Cat 4 + Cat 5
- `ceo:dave_decisions_2026_05_26.decision_5_temporal_ephemeral_instance` (A6 substrate live)
- `ceo:dave_migration_sequence.phase_a_extended.a7`
- Inventory rows Cat 4 (cost.*) + Cat 5 (temp.inline.cache_check + temp.inline.token_gate)
- PR #1137 — metering pipeline (Orion, prior session window) — A7 extends this for cache-avoided-cost attribution
- PR #1128 — BYOK LLM routing spike (Orion) — token budget Viktor 4-component model + provider-billing-API deferral
- PR #1133 — TEI sidecar (Orion) — embedding service for Valkey semantic bucket assignment
- PR #1146 — Vault Transit envelope (Orion) — per-tenant BYOK key resolution; LiteLLM router fetches via VaultDecryptor
- PR #1150 — Layer 11 cost optimization deep-dive (Orion)
- PR #1152 — Temporal contract V1 (Elliot)
- PR #1155 — Phase A6 first-workflow Temporal Signal mechanics (Orion, awaiting Max final concur as of design draft)
- `Agency_OS-ucf8` — Phase 2 amendment 3 (cache-hit short-circuit) — A7 build dep
- `Agency_OS-tpxj` — Phase 2 amendment 2 (Sandbox token_gate calibration) — A7 token budget policy connects
- `reference_model_routing.md` — internal Gemini routing memo
