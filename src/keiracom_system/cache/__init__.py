"""Keiracom cache layer — Phase A7 cache architecture + cost infrastructure.

Implements the design canonicalised in docs/architecture/design/a7_cache_architecture.md
(PR #1156 merged 2026-05-26) + §13 build clarifications (PR #1165 merged 2026-05-26).

Three substrates, layered:
  - Anthropic prompt cache (Layer 1)  → 0.10x input cost on stable prefix content
  - Valkey semantic cache (Layer N/A) → ~1ms lookup, short-circuits whole LLM call
  - Hindsight beyond-active-window    → memory recall, NOT a perf cache

Canonical key anchor: ceo:cache_framework_canonical.
Module-level public surface re-exported below for callers.
"""

from src.keiracom_system.cache.constants import (
    CACHE_LAYER_1_MULTIPLIER,
    CACHE_LAYER_2_MULTIPLIER,
    TIER_MULTIPLIERS_PROPOSAL,
    VALKEY_TTL_DEFINITION_FETCH,
    VALKEY_TTL_MUTATION,
    VALKEY_TTL_READ_MOSTLY,
)
from src.keiracom_system.cache.litellm_helpers import (
    inject_cache_control_markers,
)
from src.keiracom_system.cache.metrics import (
    emit_anthropic_cache_tokens,
    make_better_stack_emitter,
)
from src.keiracom_system.cache.token_budget_policy import (
    TIER_DEFAULTS,
    TenantBudgetPolicy,
)
from src.keiracom_system.cache.valkey_client import ValkeyClient

__all__ = [
    "CACHE_LAYER_1_MULTIPLIER",
    "CACHE_LAYER_2_MULTIPLIER",
    "TIER_DEFAULTS",
    "TIER_MULTIPLIERS_PROPOSAL",
    "VALKEY_TTL_DEFINITION_FETCH",
    "VALKEY_TTL_MUTATION",
    "VALKEY_TTL_READ_MOSTLY",
    "TenantBudgetPolicy",
    "ValkeyClient",
    "emit_anthropic_cache_tokens",
    "inject_cache_control_markers",
    "make_better_stack_emitter",
]
