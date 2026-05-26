"""Cache framework canonical constants — Phase A7 sub-task 1.

CANONICAL KEY ANCHOR — ceo:cache_framework_canonical (queried 2026-05-26, verbatim):

  layer_1_anthropic_prompt_cache:
    content:    "structurally stable per-domain content"
    multiplier: "0.10x input cost"
  layer_2_uncached:
    content:    "per-call dynamic content"
    multiplier: "1.0x"
  per_tier_multipliers_proposal:
    sandbox: 0.5x
    solo:    1.0x
    pro:     1.5x
    team:    2.0x
    enterprise: custom
  tier_multipliers_status: "PROPOSAL — pressure-test in Phase 2"

These constants are the single source-of-truth for consumers. If
ceo:cache_framework_canonical changes, this module is the load-bearing fix
and a test in tests/keiracom_system/cache/test_constants.py locks the values.

Status: PROPOSAL on tier multipliers — see design doc §11 LOOSE items #4, #6.
"""

from __future__ import annotations

# Multiplier on standard input cost when Anthropic prompt cache HITS.
# Source: ceo:cache_framework_canonical.layer_1_anthropic_prompt_cache.multiplier
CACHE_LAYER_1_MULTIPLIER: float = 0.10

# Multiplier when no cache (baseline / uncached).
# Source: ceo:cache_framework_canonical.layer_2_uncached.multiplier
CACHE_LAYER_2_MULTIPLIER: float = 1.0

# Per-tier multipliers PROPOSAL (pressure-test in Phase 2 with real traffic).
# Source: ceo:cache_framework_canonical.per_tier_multipliers_proposal
# Enterprise: "custom" sentinel; resolved at per-tenant onboarding time.
TIER_MULTIPLIERS_PROPOSAL: dict[str, float | str] = {
    "sandbox": 0.5,
    "solo": 1.0,
    "pro": 1.5,
    "team": 2.0,
    "enterprise": "custom",
}

# Per-tool-type Valkey TTL (seconds). Conservative V1 defaults; refine post 48h
# baseline per design §6 + §11 LOOSE item #4.
#
# Read-mostly: HubSpot company lookup, Slack channel list, etc. Short TTL keeps
# reads fresh against upstream changes.
VALKEY_TTL_READ_MOSTLY: int = 60

# Definition fetches: tools/list catalog, mental-model lookups — these rarely
# change within a day. Long TTL is fine.
VALKEY_TTL_DEFINITION_FETCH: int = 24 * 3600

# Mutation tools (HubSpot company create, Slack message send): TTL 0 = no cache.
# Mutations always hit the LLM with no Valkey check. Caching mutations is a
# correctness bug, not a perf optimisation.
VALKEY_TTL_MUTATION: int = 0

# Valkey key namespace prefix. All keys MUST start with v1:{tenant_id}: per
# design §4 cross-tenant isolation invariant. ValkeyClient enforces this at
# the read/write boundary (defence-in-depth per CB-Atlas).
VALKEY_KEY_NAMESPACE_PREFIX: str = "v1:"

# Embedding bucket count for canonical_cache_key semantic component. V1
# PROPOSAL per design §4 + §11 LOOSE item #1; tune from measured collision
# rate post-baseline. 4096 = 12 bits.
EMBEDDING_BUCKET_COUNT: int = 4096
