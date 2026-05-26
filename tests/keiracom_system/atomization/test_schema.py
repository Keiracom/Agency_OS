"""AtomV1 + frozen-vocabulary unit tests — atomization pilot Week 1."""

from uuid import uuid4

import pytest

from src.keiracom_system.atomization.schema import (
    PROVENANCE_REQUIRED_KEYS,
    SCHEMA_VERSION,
    VALID_COMPOSITION_TAG_CONCERNS,
    VALID_COMPOSITION_TAG_CONTEXTS,
    VALID_COMPOSITION_TAG_DOMAINS,
    VALID_COMPOSITION_TAGS,
    VALID_RELATIONSHIP_TYPES,
    VALID_SOURCE_KINDS,
    VALID_STATES,
    VALID_TRIGGER_KINDS,
    AtomV1,
    SupersessionEdgeV1,
    is_valid_composition_tag,
    is_valid_uuid_str,
)


def _good_provenance() -> dict:
    return {
        "source": "skills/test.md@abc123",
        "freshness": "2026-05-26T11:25:00Z",
        "confidence": 0.85,
        "last_validated": "2026-05-26T11:25:00Z",
    }


def _good_atom_kwargs() -> dict:
    return {
        "atom_id": uuid4(),
        "tenant_id": uuid4(),
        "trigger_condition": {"kind": "request_shape", "params": {"matches": "summarize"}},
        "content": "When the user asks to summarize, return 3 bullet points.",
        "anti_pattern": None,
        "example": None,
        "provenance": _good_provenance(),
        "composition_tags": {},
    }


# ----- Vocabulary cardinality + identity locks -----------------------------


def test_schema_version_is_one():
    assert SCHEMA_VERSION == 1


def test_valid_states_set():
    assert frozenset({"active", "superseded", "cold_archive"}) == VALID_STATES


def test_valid_source_kinds_set():
    assert (
        frozenset({"skill", "manual", "governance_doc", "discovery_log", "session"})
        == VALID_SOURCE_KINDS
    )


def test_valid_trigger_kinds_six():
    """Pilot placeholder vocabulary cardinality — 6 kinds per schema.py."""
    assert len(VALID_TRIGGER_KINDS) == 6


def test_valid_relationship_types_capped_single_digit():
    """Hard constraint: relationship-type vocabulary capped single-digit V1."""
    assert len(VALID_RELATIONSHIP_TYPES) < 10
    assert "supersedes" in VALID_RELATIONSHIP_TYPES


def test_composition_tags_288_combinations():
    """Dispatch reference: 288 composition tag combinations.

    Cardinality = len(domain) × len(concern) × len(context).
    Placeholder values: 8 × 6 × 6 = 288 (matches dispatch reference exactly).
    """
    expected = (
        len(VALID_COMPOSITION_TAG_DOMAINS)
        * len(VALID_COMPOSITION_TAG_CONCERNS)
        * len(VALID_COMPOSITION_TAG_CONTEXTS)
    )
    assert expected == 288
    assert len(VALID_COMPOSITION_TAGS) == 288


def test_provenance_required_keys():
    """Provenance JSONB must carry source + freshness + confidence + last_validated."""
    assert (
        frozenset({"source", "freshness", "confidence", "last_validated"})
        == PROVENANCE_REQUIRED_KEYS
    )


def test_is_valid_composition_tag_accepts_canonical():
    tag = {
        "domain": next(iter(VALID_COMPOSITION_TAG_DOMAINS)),
        "concern": next(iter(VALID_COMPOSITION_TAG_CONCERNS)),
        "applicable_context": next(iter(VALID_COMPOSITION_TAG_CONTEXTS)),
    }
    assert is_valid_composition_tag(tag) is True


def test_is_valid_composition_tag_rejects_unknown_axis():
    bad = {
        "domain": "_not_a_domain",
        "concern": "compliance",
        "applicable_context": "chat_realtime",
    }
    assert is_valid_composition_tag(bad) is False


def test_is_valid_uuid_str_accepts_valid():
    assert is_valid_uuid_str("00000000-0000-0000-0000-000000000001") is True


def test_is_valid_uuid_str_rejects_invalid():
    assert is_valid_uuid_str("not-a-uuid") is False


# ----- AtomV1 invariants ----------------------------------------------------


def test_atom_v1_valid_construction():
    atom = AtomV1(**_good_atom_kwargs())
    assert atom.schema_version == SCHEMA_VERSION
    assert atom.state == "active"


def test_atom_v1_rejects_free_text_trigger():
    """Hard constraint: atomizer rejects free-text triggers."""
    kwargs = _good_atom_kwargs()
    kwargs["trigger_condition"] = "when the user does X"  # string, not dict
    with pytest.raises(ValueError, match="structured predicate dict"):
        AtomV1(**kwargs)


def test_atom_v1_rejects_unknown_trigger_kind():
    kwargs = _good_atom_kwargs()
    kwargs["trigger_condition"] = {"kind": "_bogus_kind", "params": {}}
    with pytest.raises(ValueError, match="not in"):
        AtomV1(**kwargs)


def test_atom_v1_rejects_missing_trigger_params():
    kwargs = _good_atom_kwargs()
    kwargs["trigger_condition"] = {"kind": "request_shape"}  # no params
    with pytest.raises(ValueError, match="params"):
        AtomV1(**kwargs)


def test_atom_v1_rejects_empty_content():
    kwargs = _good_atom_kwargs()
    kwargs["content"] = ""
    with pytest.raises(ValueError, match="content must be non-empty"):
        AtomV1(**kwargs)


def test_atom_v1_rejects_missing_provenance_keys():
    kwargs = _good_atom_kwargs()
    kwargs["provenance"] = {"source": "x"}  # only 1 of 4 required keys
    with pytest.raises(ValueError, match="provenance missing"):
        AtomV1(**kwargs)


def test_atom_v1_rejects_provenance_confidence_out_of_range():
    kwargs = _good_atom_kwargs()
    kwargs["provenance"]["confidence"] = 1.5
    with pytest.raises(ValueError, match="confidence must be a float"):
        AtomV1(**kwargs)


def test_atom_v1_rejects_unknown_composition_tag():
    kwargs = _good_atom_kwargs()
    kwargs["composition_tags"] = {
        "domain": "_unknown",
        "concern": "compliance",
        "applicable_context": "chat_realtime",
    }
    with pytest.raises(ValueError, match="composition_tags"):
        AtomV1(**kwargs)


def test_atom_v1_accepts_empty_composition_tags():
    """Empty dict is allowed (some sources may not carry tags yet)."""
    kwargs = _good_atom_kwargs()
    kwargs["composition_tags"] = {}
    atom = AtomV1(**kwargs)
    assert atom.composition_tags == {}


def test_atom_v1_rejects_unknown_state():
    kwargs = _good_atom_kwargs()
    kwargs["state"] = "_not_a_state"
    with pytest.raises(ValueError, match="state"):
        AtomV1(**kwargs)


def test_atom_v1_is_frozen():
    """Atoms are immutable; edits produce supersession edges."""
    atom = AtomV1(**_good_atom_kwargs())
    with pytest.raises((AttributeError, Exception)):
        atom.content = "mutated"  # type: ignore[misc]


# ----- SupersessionEdgeV1 invariants ----------------------------------------


def test_supersession_edge_valid():
    edge = SupersessionEdgeV1(
        edge_id=uuid4(),
        tenant_id=uuid4(),
        predecessor_atom=uuid4(),
        successor_atom=uuid4(),
        relationship_type="supersedes",
        confidence=0.9,
    )
    assert edge.relationship_type == "supersedes"


def test_supersession_edge_rejects_same_atom():
    aid = uuid4()
    with pytest.raises(ValueError, match="must differ"):
        SupersessionEdgeV1(
            edge_id=uuid4(),
            tenant_id=uuid4(),
            predecessor_atom=aid,
            successor_atom=aid,
            relationship_type="supersedes",
            confidence=0.9,
        )


def test_supersession_edge_rejects_unknown_relationship_type():
    with pytest.raises(ValueError, match="relationship_type"):
        SupersessionEdgeV1(
            edge_id=uuid4(),
            tenant_id=uuid4(),
            predecessor_atom=uuid4(),
            successor_atom=uuid4(),
            relationship_type="_bogus",
            confidence=0.9,
        )


def test_supersession_edge_rejects_confidence_out_of_range():
    with pytest.raises(ValueError, match="confidence"):
        SupersessionEdgeV1(
            edge_id=uuid4(),
            tenant_id=uuid4(),
            predecessor_atom=uuid4(),
            successor_atom=uuid4(),
            relationship_type="supersedes",
            confidence=1.5,
        )
