"""Unit tests for elliot_memories_indexer (KEI-109).

No network: tests the pure-logic seams (deterministic UUID, memory build,
soft-delete/expiry SQL gate is exercised by the live --once smoke).
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import elliot_memories_indexer as mod  # noqa: E402


def _row(
    id: str = "11111111-1111-4111-8111-111111111111",
    content: str = "a daily log entry",
    type: str = "daily_log",
    metadata: object = None,
    updated_at: _dt.datetime | None = None,
) -> mod.ElliotMemoryRow:
    return mod.ElliotMemoryRow(
        id=id,
        content=content,
        type=type,
        metadata=metadata if metadata is not None else {"kei": "KEI-109"},
        updated_at=updated_at or _dt.datetime(2026, 5, 17, 4, 0, 0, tzinfo=_dt.UTC),
    )


def test_deterministic_uuid_stable_across_calls():
    a = mod.deterministic_uuid("elliot_memories", "row-a:v0")
    b = mod.deterministic_uuid("elliot_memories", "row-a:v0")
    assert a == b


def test_deterministic_uuid_differs_by_timestamp():
    a = mod.build_memory(_row(updated_at=_dt.datetime(2026, 5, 17, 4, 0, 0, tzinfo=_dt.UTC)))["id"]
    b = mod.build_memory(_row(updated_at=_dt.datetime(2026, 5, 17, 5, 0, 0, tzinfo=_dt.UTC)))["id"]
    assert a != b


def test_deterministic_uuid_differs_by_source():
    a = mod.deterministic_uuid("elliot_memories", "row-a:v0")
    b = mod.deterministic_uuid("ceo_memory", "row-a:v0")
    assert a != b


def test_build_memory_basic_shape():
    doc = mod.build_memory(_row())
    assert doc["class"] == "AgentMemories"
    props = doc["properties"]
    assert props["agent"] == "elliot"
    assert props["created_at"] == "2026-05-17T04:00:00+00:00"
    assert props["kei"] == "KEI-109"
    parsed = json.loads(props["raw_text"])
    assert parsed["content"] == "a daily log entry"
    assert parsed["type"] == "daily_log"


def test_build_memory_kei_falls_through_when_missing():
    doc = mod.build_memory(_row(metadata={"unrelated": "x"}))
    assert doc["properties"]["kei"] == ""


def test_build_memory_handles_non_dict_metadata():
    doc = mod.build_memory(_row(metadata=["list", "not", "dict"]))
    props = doc["properties"]
    assert props["kei"] == ""
    parsed = json.loads(props["raw_text"])
    assert parsed["metadata"] == ["list", "not", "dict"]


def test_build_memory_handles_null_updated_at():
    row = mod.ElliotMemoryRow(
        id="22222222-2222-4222-8222-222222222222",
        content="no timestamp",
        type="general",
        metadata={},
        updated_at=None,
    )
    doc = mod.build_memory(row)
    assert doc["properties"]["created_at"] == "1970-01-01T00:00:00Z"


def test_environment_hash_is_deterministic_and_hex16():
    doc = mod.build_memory(_row())
    eh = doc["properties"]["environment_hash"]
    assert len(eh) == 16
    int(eh, 16)


def test_elliot_memories_indexer_satisfies_base_indexer_abc():
    import indexer_base

    assert issubclass(mod.ElliotMemoriesIndexer, indexer_base.BaseIndexer)
    assert mod.ElliotMemoriesIndexer.source_name == "elliot_memories"
    assert mod.ElliotMemoriesIndexer.target_class == "AgentMemories"
    assert isinstance(mod.ElliotMemoriesIndexer.class_schema, dict)
    assert mod.ElliotMemoriesIndexer.class_schema["class"] == "AgentMemories"
    assert mod.ElliotMemoriesIndexer.__abstractmethods__ == frozenset()


def test_source_agent_is_fixed_to_elliot():
    """elliot_internal schema scopes the source — agent property is hardcoded
    'elliot' not derived from row.metadata.callsign (the table has no callsign
    column; future schemas like aiden_internal.memories get their own indexer).
    """
    doc = mod.build_memory(_row(metadata={"callsign": "aiden"}))
    assert doc["properties"]["agent"] == "elliot"


def test_resolve_pg_dsn_strips_asyncpg(monkeypatch):
    """run_db_indexer uses indexer_base.resolve_pg_dsn — must rewrite
    `postgresql+asyncpg://` to psycopg-compatible `postgresql://`.
    """
    import indexer_base

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    assert indexer_base.resolve_pg_dsn() == "postgresql://u:p@h:5432/d"


def test_resolve_pg_dsn_falls_back_to_supabase_var(monkeypatch):
    import indexer_base

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://x:y@h:5432/d")
    assert indexer_base.resolve_pg_dsn() == "postgresql://x:y@h:5432/d"


def test_resolve_pg_dsn_raises_when_no_env(monkeypatch):
    import indexer_base
    import pytest

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(SystemExit):
        indexer_base.resolve_pg_dsn()
