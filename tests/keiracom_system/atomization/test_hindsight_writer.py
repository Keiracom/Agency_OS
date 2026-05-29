"""Unit tests for the one-source AtomV1 -> Hindsight item seam.

Locks the serialization format both the live writer (exit_cycle) and the
historical backfill (decisions_backfill) must share, so atoms in the
fleet_decisions bank are indistinguishable by writer.
"""

from __future__ import annotations

import json
from uuid import uuid4

from src.keiracom_system.atomization.hindsight_writer import (
    DEFAULT_BANK,
    atom_to_hindsight_item,
)
from src.keiracom_system.atomization.schema import AtomV1


def _atom() -> AtomV1:
    return AtomV1(
        atom_id=uuid4(),
        tenant_id=uuid4(),
        trigger_condition={"kind": "context_predicate", "params": {"topic": "recall"}},
        content="Use Hindsight Layer 2 for cross-spawn recall.",
        anti_pattern="Do not re-query ceo_memory at spawn time.",
        example="A fresh spawn recalls 3-5 atoms.",
        provenance={
            "source": "live_spawn_exit:face:customer_42",
            "freshness": "2026-05-29",
            "confidence": 0.95,
            "last_validated": "2026-05-29",
        },
        composition_tags={
            "domain": "internal",
            "concern": "compliance",
            "applicable_context": "audit_review",
        },
    )


def test_default_bank_is_fleet_decisions():
    assert DEFAULT_BANK == "fleet_decisions"


def test_item_shape_and_tags():
    item = atom_to_hindsight_item(_atom(), source="live_spawn_exit")
    assert item["content"] == "Use Hindsight Layer 2 for cross-spawn recall."
    assert item["tags"][:3] == ["atom_v1", "state:active", "schema_v1"]
    assert {"internal", "compliance", "audit_review"} <= set(item["tags"])
    assert item["metadata"]["source"] == "live_spawn_exit"


def test_metadata_carries_full_structured_atom():
    atom = _atom()
    item = atom_to_hindsight_item(atom, source="live_spawn_exit")
    md = item["metadata"]
    assert md["atom_id"] == str(atom.atom_id)
    assert md["tenant_id"] == str(atom.tenant_id)
    assert md["schema_version"] == "1"  # Hindsight requires string metadata values
    assert md["state"] == "active"
    assert all(isinstance(v, str) for v in md.values())  # 422-guard: no non-string values
    assert json.loads(md["trigger_condition"])["kind"] == "context_predicate"
    assert json.loads(md["provenance"])["confidence"] == 0.95
    assert json.loads(md["composition_tags"])["domain"] == "internal"
    assert md["anti_pattern"] == "Do not re-query ceo_memory at spawn time."


def test_source_defaults_to_backfill():
    # Backfill writer relies on the default so its provenance stays distinct.
    item = atom_to_hindsight_item(_atom())
    assert item["metadata"]["source"] == "decisions_backfill"


def test_empty_composition_tags_only_base_tags():
    atom = AtomV1(
        atom_id=uuid4(),
        tenant_id=uuid4(),
        trigger_condition={"kind": "system_event", "params": {}},
        content="A decision with no composition tags.",
        anti_pattern=None,
        example=None,
        provenance={
            "source": "x",
            "freshness": "2026-05-29",
            "confidence": 1.0,
            "last_validated": "2026-05-29",
        },
    )
    item = atom_to_hindsight_item(atom, source="live_spawn_exit")
    assert item["tags"] == ["atom_v1", "state:active", "schema_v1"]
    assert item["metadata"]["anti_pattern"] == ""
