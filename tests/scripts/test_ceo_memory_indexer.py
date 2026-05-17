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
