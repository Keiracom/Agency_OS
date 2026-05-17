"""Unit tests for ceo_memory_indexer.

No network: tests the pure-logic seams (deterministic UUID, decision build).
End-to-end smoke (live Weaviate + live Postgres) lives in
`infra/weaviate/smoke_ceo_memory_indexer.py` and is invoked by the install
runbook + KEI-108 CI gate.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import ceo_memory_indexer as mod  # noqa: E402


def _row(key: str = "ceo:test", value: object = None, version: int = 1) -> mod.CeoMemoryRow:
    return mod.CeoMemoryRow(
        key=key,
        value=value if value is not None else {"kei": "KEI-85", "note": "smoke"},
        updated_at=_dt.datetime(2026, 5, 17, 4, 0, 0, tzinfo=_dt.UTC),
        version=version,
    )


def test_deterministic_uuid_stable_across_calls():
    a = mod.deterministic_uuid("ceo_memory", "ceo:test:v1")
    b = mod.deterministic_uuid("ceo_memory", "ceo:test:v1")
    assert a == b


def test_deterministic_uuid_differs_by_version():
    a = mod.deterministic_uuid("ceo_memory", "ceo:test:v1")
    b = mod.deterministic_uuid("ceo_memory", "ceo:test:v2")
    assert a != b


def test_deterministic_uuid_differs_by_source():
    a = mod.deterministic_uuid("ceo_memory", "ceo:test:v1")
    b = mod.deterministic_uuid("git", "ceo:test:v1")
    assert a != b


def test_build_decision_basic_shape():
    doc = mod.build_decision(_row())
    assert doc["class"] == "Decisions"
    assert doc["id"] == mod.deterministic_uuid("ceo_memory", "ceo:test:v1")
    props = doc["properties"]
    assert props["agent"] == "system"
    assert props["created_at"] == "2026-05-17T04:00:00+00:00"
    assert props["kei"] == "KEI-85"
    parsed = json.loads(props["raw_text"])
    assert parsed["key"] == "ceo:test"


def test_build_decision_kei_falls_through_when_missing():
    doc = mod.build_decision(_row(value={"unrelated": "x"}))
    assert doc["properties"]["kei"] == ""


def test_build_decision_handles_non_dict_value():
    doc = mod.build_decision(_row(value="bare string"))
    props = doc["properties"]
    assert props["kei"] == ""
    parsed = json.loads(props["raw_text"])
    assert parsed["value"] == "bare string"


def test_build_decision_handles_null_updated_at():
    row = mod.CeoMemoryRow(key="ceo:no-ts", value={"x": 1}, updated_at=None, version=1)
    doc = mod.build_decision(row)
    assert doc["properties"]["created_at"] == "1970-01-01T00:00:00Z"


def test_environment_hash_is_deterministic_and_hex16():
    doc = mod.build_decision(_row())
    eh = doc["properties"]["environment_hash"]
    assert len(eh) == 16
    int(eh, 16)  # raises if not hex


def test_ceo_memory_indexer_satisfies_base_indexer_abc():
    """ABC contract: CeoMemoryIndexer is a concrete BaseIndexer subclass with
    all abstract methods implemented + the three required class attributes set.
    """
    import indexer_base

    assert issubclass(mod.CeoMemoryIndexer, indexer_base.BaseIndexer)
    assert mod.CeoMemoryIndexer.source_name == "ceo_memory"
    assert mod.CeoMemoryIndexer.target_class == "Decisions"
    assert isinstance(mod.CeoMemoryIndexer.class_schema, dict)
    assert mod.CeoMemoryIndexer.class_schema["class"] == "Decisions"
    # Abstract methods must be overridden — instantiating with a None conn
    # would otherwise fail if any @abstractmethod is unfulfilled.
    # `__abstractmethods__` is empty when all abstracts are implemented.
    assert mod.CeoMemoryIndexer.__abstractmethods__ == frozenset()


def test_base_indexer_cannot_be_instantiated_directly():
    """Architectural contract — the ABC must refuse direct instantiation
    so subclasses are forced to provide the abstract methods.
    """
    import indexer_base
    import pytest

    with pytest.raises(TypeError):
        indexer_base.BaseIndexer()  # type: ignore[abstract]


def test_batch_outcome_to_dict_shape():
    """BatchOutcome -> dict shape is the API logged in production —
    keep it stable so downstream parsers don't break.
    """
    import indexer_base

    outcome = indexer_base.BatchOutcome(selected=10, success=8, failed=2)
    assert outcome.to_dict() == {"selected": 10, "success": 8, "failed": 2}
