"""Lock cache constants against ceo:cache_framework_canonical — Phase A7 sub-task 1.

If ceo:cache_framework_canonical changes upstream, this test breaks and the
constants module is the load-bearing fix.
"""

from src.keiracom_system.cache.constants import (
    CACHE_LAYER_1_MULTIPLIER,
    CACHE_LAYER_2_MULTIPLIER,
    EMBEDDING_BUCKET_COUNT,
    TIER_MULTIPLIERS_PROPOSAL,
    VALKEY_KEY_NAMESPACE_PREFIX,
    VALKEY_TTL_DEFINITION_FETCH,
    VALKEY_TTL_MUTATION,
    VALKEY_TTL_READ_MOSTLY,
)


def test_layer_1_multiplier_matches_canonical():
    assert CACHE_LAYER_1_MULTIPLIER == 0.10


def test_layer_2_multiplier_matches_canonical():
    assert CACHE_LAYER_2_MULTIPLIER == 1.0


def test_tier_multipliers_match_canonical_proposal():
    assert TIER_MULTIPLIERS_PROPOSAL["sandbox"] == 0.5
    assert TIER_MULTIPLIERS_PROPOSAL["solo"] == 1.0
    assert TIER_MULTIPLIERS_PROPOSAL["pro"] == 1.5
    assert TIER_MULTIPLIERS_PROPOSAL["team"] == 2.0
    assert TIER_MULTIPLIERS_PROPOSAL["enterprise"] == "custom"


def test_valkey_ttl_read_mostly_seconds():
    assert VALKEY_TTL_READ_MOSTLY == 60


def test_valkey_ttl_definition_fetch_24h():
    assert VALKEY_TTL_DEFINITION_FETCH == 24 * 3600


def test_valkey_ttl_mutation_zero():
    """Mutations must not cache — TTL=0 sentinel."""
    assert VALKEY_TTL_MUTATION == 0


def test_valkey_namespace_prefix():
    """All keys must start with v1: per cross-tenant isolation invariant."""
    assert VALKEY_KEY_NAMESPACE_PREFIX == "v1:"


def test_embedding_bucket_count_v1_proposal():
    """4096 buckets = 12 bits per design §4 + CB §13. Tune in Phase 2."""
    assert EMBEDDING_BUCKET_COUNT == 4096
