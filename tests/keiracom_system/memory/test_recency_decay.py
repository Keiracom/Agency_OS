"""tests for keiracom_system.memory.recency_decay — Wave 2 CUTOVER GATE 3rpe.

Coverage matrix:
- apply_recency_decay (pure math)  — 3 positive + 3 negative
- decay_scored_memories            — 6 positive + 5 negative
- canonical-tag bypass             — 4 scenarios
- rerank ordering                  — 3 scenarios
"""

from __future__ import annotations

import math

import pytest

from src.keiracom_system.memory.recency_decay import (
    DEFAULT_EXEMPT_TAGS,
    DEFAULT_HALF_LIVES,
    SECONDS_PER_DAY,
    RecencyDecayConfig,
    ScoredMemory,
    apply_recency_decay,
    decay_scored_memories,
    rerank_by_decayed_score,
)

# ============== apply_recency_decay (pure math) ==============


def test_apply_recency_decay_halves_score_at_half_life():
    # At age = half_life, score must halve (2^-1 = 0.5).
    result = apply_recency_decay(score=1.0, age_seconds=86400, half_life_seconds=86400)
    assert math.isclose(result, 0.5, rel_tol=1e-9)


def test_apply_recency_decay_quarters_score_at_two_half_lives():
    result = apply_recency_decay(score=1.0, age_seconds=172800, half_life_seconds=86400)
    assert math.isclose(result, 0.25, rel_tol=1e-9)


def test_apply_recency_decay_returns_original_at_age_zero():
    result = apply_recency_decay(score=0.87, age_seconds=0, half_life_seconds=86400)
    assert math.isclose(result, 0.87, rel_tol=1e-9)


def test_apply_recency_decay_treats_negative_age_as_zero():
    # Clock-skew defensive case: do not penalise a future-dated atom.
    result = apply_recency_decay(score=0.5, age_seconds=-100, half_life_seconds=86400)
    assert math.isclose(result, 0.5, rel_tol=1e-9)


def test_apply_recency_decay_rejects_zero_half_life():
    with pytest.raises(ValueError, match="half_life_seconds must be positive"):
        apply_recency_decay(score=1.0, age_seconds=100, half_life_seconds=0)


def test_apply_recency_decay_rejects_negative_half_life():
    with pytest.raises(ValueError, match="half_life_seconds must be positive"):
        apply_recency_decay(score=1.0, age_seconds=100, half_life_seconds=-86400)


# ============== decay_scored_memories ==============


_NOW = 2_000_000_000.0  # arbitrary fixed epoch


def _mk_memory(
    *,
    memory_id: str,
    score: float,
    topology: str,
    age_seconds: float = 0.0,
    tags: list[str] | None = None,
):
    return {
        "id": memory_id,
        "score": score,
        "topology": topology,
        "created_at": _NOW - age_seconds,
        "tags": tags or [],
    }


def test_decay_decays_score_per_topology_half_life():
    config = RecencyDecayConfig()  # uses DEFAULT_HALF_LIVES
    # fleet_keis half-life = 7 days. Age = 7 days. Score halves.
    mem = _mk_memory(
        memory_id="m1", score=1.0, topology="fleet_keis", age_seconds=7 * SECONDS_PER_DAY
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert len(out) == 1
    assert out[0].decay_applied
    assert math.isclose(out[0].score, 0.5, rel_tol=1e-9)
    assert out[0].original_score == 1.0


def test_decay_respects_per_topology_half_life_difference():
    # fleet_codebase half-life = 90 days; fleet_keis = 7 days.
    config = RecencyDecayConfig()
    age = 14 * SECONDS_PER_DAY
    codebase = _mk_memory(memory_id="c1", score=1.0, topology="fleet_codebase", age_seconds=age)
    keis = _mk_memory(memory_id="k1", score=1.0, topology="fleet_keis", age_seconds=age)
    out = decay_scored_memories([codebase, keis], config=config, now=_NOW)
    codebase_out = next(m for m in out if m.memory_id == "c1")
    keis_out = next(m for m in out if m.memory_id == "k1")
    # Same age, slower-decay topology must hold higher score.
    assert codebase_out.score > keis_out.score


def test_decay_falls_back_to_default_half_life_for_unknown_topology():
    config = RecencyDecayConfig(default_half_life_days=30.0)
    mem = _mk_memory(
        memory_id="m1",
        score=1.0,
        topology="unknown_topology",
        age_seconds=30 * SECONDS_PER_DAY,
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert out[0].decay_applied
    assert math.isclose(out[0].score, 0.5, rel_tol=1e-9)


def test_decay_passes_through_when_default_half_life_is_none():
    config = RecencyDecayConfig(half_lives={}, default_half_life_days=None)
    mem = _mk_memory(
        memory_id="m1",
        score=0.7,
        topology="unknown_topology",
        age_seconds=30 * SECONDS_PER_DAY,
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert not out[0].decay_applied
    assert out[0].exempt_reason == "no_half_life"
    assert out[0].score == 0.7


def test_decay_passes_through_when_atom_has_no_timestamp():
    config = RecencyDecayConfig()
    mem = {
        "id": "m1",
        "score": 0.8,
        "topology": "fleet_keis",
        "tags": [],
        "created_at": None,
    }
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert not out[0].decay_applied
    assert out[0].exempt_reason == "no_timestamp"
    assert out[0].score == 0.8


def test_decay_applies_score_floor():
    config = RecencyDecayConfig(score_floor=0.05)
    # Very old atom; raw decay would drop near zero. Floor catches it.
    mem = _mk_memory(
        memory_id="m1", score=1.0, topology="fleet_keis", age_seconds=365 * SECONDS_PER_DAY
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert out[0].decay_applied
    assert out[0].score == 0.05


def test_decay_parses_iso_8601_created_at():
    config = RecencyDecayConfig()
    mem = {
        "id": "m1",
        "score": 1.0,
        "topology": "fleet_keis",
        "tags": [],
        "created_at": "2025-01-01T00:00:00Z",
    }
    # now > created_at so age is positive; decay should apply.
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert out[0].decay_applied
    assert out[0].score < 1.0


# ============== Negative tests for decay_scored_memories ==============


def test_decay_rejects_non_dict_entry():
    config = RecencyDecayConfig()
    with pytest.raises(ValueError, match="must be dict"):
        decay_scored_memories(["not-a-dict"], config=config, now=_NOW)  # type: ignore[list-item]


def test_decay_rejects_missing_id():
    config = RecencyDecayConfig()
    with pytest.raises(ValueError, match="missing id"):
        decay_scored_memories(
            [{"score": 1.0, "topology": "fleet_keis", "tags": [], "created_at": _NOW}],
            config=config,
            now=_NOW,
        )


def test_decay_rejects_missing_score():
    config = RecencyDecayConfig()
    with pytest.raises(ValueError, match="missing score"):
        decay_scored_memories(
            [{"id": "m1", "topology": "fleet_keis", "tags": [], "created_at": _NOW}],
            config=config,
            now=_NOW,
        )


def test_decay_rejects_missing_topology():
    config = RecencyDecayConfig()
    with pytest.raises(ValueError, match="missing topology"):
        decay_scored_memories(
            [{"id": "m1", "score": 1.0, "tags": [], "created_at": _NOW}],
            config=config,
            now=_NOW,
        )


def test_decay_rejects_unparseable_tags_type():
    config = RecencyDecayConfig()
    with pytest.raises(ValueError, match="tags must be"):
        decay_scored_memories(
            [
                {
                    "id": "m1",
                    "score": 1.0,
                    "topology": "fleet_keis",
                    "tags": 42,  # not str/list/tuple/set
                    "created_at": _NOW,
                }
            ],
            config=config,
            now=_NOW,
        )


def test_decay_rejects_zero_half_life_in_config():
    config = RecencyDecayConfig(half_lives={"fleet_keis": 0.0})
    mem = _mk_memory(memory_id="m1", score=1.0, topology="fleet_keis", age_seconds=SECONDS_PER_DAY)
    with pytest.raises(ValueError, match="must be positive days"):
        decay_scored_memories([mem], config=config, now=_NOW)


# ============== Canonical-tag bypass ==============


def test_canonical_tag_exempts_memory_from_decay():
    config = RecencyDecayConfig()
    mem = _mk_memory(
        memory_id="ratified-fact",
        score=1.0,
        topology="fleet_decisions",
        age_seconds=4 * 365 * SECONDS_PER_DAY,  # 4 years
        tags=["canonical"],
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert not out[0].decay_applied
    assert out[0].exempt_reason == "canonical"
    assert out[0].score == 1.0  # original, unchanged


def test_ceo_ratified_tag_also_exempts():
    config = RecencyDecayConfig()
    mem = _mk_memory(
        memory_id="dave-ratified",
        score=0.9,
        topology="fleet_decisions",
        age_seconds=365 * SECONDS_PER_DAY,
        tags=["ceo_ratified"],
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert not out[0].decay_applied
    assert out[0].score == 0.9


def test_governance_locked_tag_also_exempts():
    config = RecencyDecayConfig()
    mem = _mk_memory(
        memory_id="g1",
        score=0.8,
        topology="fleet_decisions",
        age_seconds=365 * SECONDS_PER_DAY,
        tags=["governance_locked"],
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert not out[0].decay_applied
    assert out[0].score == 0.8


def test_exempt_tags_configurable_per_deploy():
    # Custom exempt set replaces defaults entirely.
    config = RecencyDecayConfig(exempt_tags=frozenset({"my_canonical"}))
    mem = _mk_memory(
        memory_id="m1",
        score=1.0,
        topology="fleet_keis",
        age_seconds=7 * SECONDS_PER_DAY,
        tags=["canonical"],  # would exempt under defaults; not under custom
    )
    out = decay_scored_memories([mem], config=config, now=_NOW)
    assert out[0].decay_applied  # default 'canonical' no longer exempt


# ============== rerank_by_decayed_score ==============


def test_rerank_orders_by_decayed_score_descending():
    items = [
        ScoredMemory(
            memory_id="a",
            score=0.4,
            original_score=0.4,
            age_seconds=0,
            topology="x",
            decay_applied=False,
        ),
        ScoredMemory(
            memory_id="b",
            score=0.9,
            original_score=0.9,
            age_seconds=0,
            topology="x",
            decay_applied=False,
        ),
        ScoredMemory(
            memory_id="c",
            score=0.6,
            original_score=0.6,
            age_seconds=0,
            topology="x",
            decay_applied=False,
        ),
    ]
    out = rerank_by_decayed_score(items)
    assert [m.memory_id for m in out] == ["b", "c", "a"]


def test_rerank_demonstrates_recency_flip():
    """Old high-similarity loses to slightly-less-similar fresh.

    Acceptance test for the cutover-gate requirement: at equal-ish similarity,
    newer must win — exactly the failure mode 3rpe fixes.
    """
    config = RecencyDecayConfig(half_lives={"fleet_keis": 7.0}, default_half_life_days=30.0)
    old_high = _mk_memory(
        memory_id="old-high",
        score=0.95,
        topology="fleet_keis",
        age_seconds=21 * SECONDS_PER_DAY,  # 3 half-lives -> 0.125x
    )
    fresh_lower = _mk_memory(
        memory_id="fresh-lower", score=0.6, topology="fleet_keis", age_seconds=0
    )
    decayed = decay_scored_memories([old_high, fresh_lower], config=config, now=_NOW)
    ranked = rerank_by_decayed_score(decayed)
    # Fresh wins despite originally being lower-similarity.
    assert ranked[0].memory_id == "fresh-lower"
    assert ranked[1].memory_id == "old-high"


def test_rerank_preserves_canonical_bypass_at_high_age():
    """A canonical 4-year-old memory must still beat a fresh low-similarity
    chatter — proves the bypass + ranking interaction."""
    config = RecencyDecayConfig()
    canonical_old = _mk_memory(
        memory_id="ratified",
        score=0.95,
        topology="fleet_decisions",
        age_seconds=4 * 365 * SECONDS_PER_DAY,
        tags=["canonical"],
    )
    fresh_chatter = _mk_memory(
        memory_id="chatter", score=0.30, topology="fleet_keis", age_seconds=0
    )
    decayed = decay_scored_memories([canonical_old, fresh_chatter], config=config, now=_NOW)
    ranked = rerank_by_decayed_score(decayed)
    assert ranked[0].memory_id == "ratified"
    assert ranked[0].score == 0.95


# ============== Module-level constants sanity ==============


def test_default_half_lives_covers_known_topologies():
    # Regression guard: if the canonical bank list grows, the test fails so
    # someone has to consciously pick a half-life rather than silently
    # defaulting.
    required = {"fleet_keis", "fleet_decisions", "fleet_codebase", "fleet_discoveries"}
    missing = required - DEFAULT_HALF_LIVES.keys()
    assert not missing, f"DEFAULT_HALF_LIVES missing topologies: {missing}"


def test_default_exempt_tags_contains_canonical_and_ceo_ratified():
    assert "canonical" in DEFAULT_EXEMPT_TAGS
    assert "ceo_ratified" in DEFAULT_EXEMPT_TAGS
