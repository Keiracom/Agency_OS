"""Unit tests for agent_memories_indexer (Agency_OS-lsyd).

No network: tests pure-logic seams (deterministic UUID, build_memory,
multi-callsign mapping, archived/expired filter SQL is exercised by live
--once smoke).

Companion to test_elliot_memories_indexer (KEI-109) — sister indexer over
public.agent_memories (multi-callsign, 7400+ rows) vs elliot_internal.memories
(single-source, 1665 rows). Same target Weaviate class (AgentMemories);
different source_name in deterministic UUID so the two indexers' UUIDs
do not collide.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import agent_memories_indexer as mod  # noqa: E402

# Sentinel so callers can pass an explicit `None` without the helper
# substituting a default. Distinguishes "not provided" from "explicitly None".
_UNSET = object()


def _row(
    id: str = "22222222-2222-4222-8222-222222222222",
    callsign: str = "elliot",
    source_type: str = "decision",
    content: str = "a decision row",
    typed_metadata=_UNSET,
    tags=_UNSET,
    created_at=_UNSET,
) -> mod.AgentMemoryRow:
    return mod.AgentMemoryRow(
        id=id,
        callsign=callsign,
        source_type=source_type,
        content=content,
        typed_metadata={"kei": "KEI-lsyd"} if typed_metadata is _UNSET else typed_metadata,
        tags=["tag-a", "tag-b"] if tags is _UNSET else tags,
        created_at=(
            _dt.datetime(2026, 5, 18, 4, 0, 0, tzinfo=_dt.UTC)
            if created_at is _UNSET
            else created_at
        ),
    )


def test_deterministic_uuid_stable_across_calls():
    a = mod.deterministic_uuid("agent_memories", "row-a:v0")
    b = mod.deterministic_uuid("agent_memories", "row-a:v0")
    assert a == b


def test_deterministic_uuid_differs_by_created_at():
    a = mod.build_memory(_row(created_at=_dt.datetime(2026, 5, 18, 4, 0, 0, tzinfo=_dt.UTC)))["id"]
    b = mod.build_memory(_row(created_at=_dt.datetime(2026, 5, 18, 5, 0, 0, tzinfo=_dt.UTC)))["id"]
    assert a != b


def test_deterministic_uuid_does_not_collide_with_elliot_memories():
    """Both indexers target the same Weaviate AgentMemories class. If their
    deterministic UUIDs ever collided, one indexer's writes would overwrite
    the other's. Different source_name in deterministic_uuid prevents this.
    """
    a = mod.deterministic_uuid("agent_memories", "row-a:v0")
    b = mod.deterministic_uuid("elliot_memories", "row-a:v0")
    assert a != b


def test_build_memory_sets_agent_from_callsign_per_row():
    """elliot_memories_indexer hardcodes agent='elliot'; this indexer reads
    per-row callsign so retrieval can scope by who wrote it."""
    for callsign in ("elliot", "aiden", "max", "dave", "system", "unknown"):
        obj = mod.build_memory(_row(callsign=callsign))
        assert obj["properties"]["agent"] == callsign


def test_build_memory_falls_back_to_unknown_on_empty_callsign():
    """Defensive — public.agent_memories.callsign is NOT NULL per schema, but
    handle empty-string just in case (would otherwise write blank agent
    property which breaks retrieval scoping)."""
    obj = mod.build_memory(_row(callsign=""))
    assert obj["properties"]["agent"] == "unknown"


def test_build_memory_extracts_kei_from_typed_metadata():
    obj = mod.build_memory(_row(typed_metadata={"kei": "KEI-208"}))
    assert obj["properties"]["kei"] == "KEI-208"


def test_build_memory_extracts_directive_kei_fallback():
    obj = mod.build_memory(_row(typed_metadata={"directive_kei": "KEI-70st"}))
    assert obj["properties"]["kei"] == "KEI-70st"


def test_build_memory_handles_missing_metadata():
    """typed_metadata is NOT NULL per schema but may be {} — must not crash."""
    obj = mod.build_memory(_row(typed_metadata={}))
    assert obj["properties"]["kei"] == ""


def test_build_memory_serialises_tags_as_list():
    """tags is TEXT[] in Postgres; psycopg returns list. JSON should preserve it."""
    obj = mod.build_memory(_row(tags=["alpha", "beta"]))
    rt = json.loads(obj["properties"]["raw_text"])
    assert rt["tags"] == ["alpha", "beta"]


def test_build_memory_handles_empty_tags():
    obj = mod.build_memory(_row(tags=[]))
    rt = json.loads(obj["properties"]["raw_text"])
    assert rt["tags"] == []


def test_build_memory_handles_null_tags():
    """tags column is NOT NULL but psycopg may pass None for an empty array
    in edge cases — must coerce to []."""
    obj = mod.build_memory(_row(tags=None))
    rt = json.loads(obj["properties"]["raw_text"])
    assert rt["tags"] == []


def test_build_memory_raw_text_includes_source_type():
    """source_type is one of the load-bearing distinguishers in agent_memories
    (identity_fact / decision / lesson / milestone / pattern / ceo_instruction
    / daily_log etc) — must be in raw_text for retrieval to surface it."""
    obj = mod.build_memory(_row(source_type="ceo_instruction"))
    rt = json.loads(obj["properties"]["raw_text"])
    assert rt["source_type"] == "ceo_instruction"


def test_build_memory_environment_hash_stable():
    """environment_hash is sha256 over raw_text — same row → same hash."""
    h1 = mod.build_memory(_row())["properties"]["environment_hash"]
    h2 = mod.build_memory(_row())["properties"]["environment_hash"]
    assert h1 == h2
    assert len(h1) == 16


def test_build_memory_environment_hash_changes_on_content_change():
    h1 = mod.build_memory(_row(content="alpha"))["properties"]["environment_hash"]
    h2 = mod.build_memory(_row(content="beta"))["properties"]["environment_hash"]
    assert h1 != h2


def test_build_memory_falls_back_to_epoch_on_null_created_at():
    obj = mod.build_memory(_row(created_at=None))
    assert obj["properties"]["created_at"] == "1970-01-01T00:00:00Z"


def test_target_class_is_agent_memories():
    """Sanity: same Weaviate class as elliot_memories_indexer — they coexist."""
    assert mod.AGENT_MEMORIES_CLASS == "AgentMemories"


def test_source_name_distinct_from_elliot_memories():
    """Prevents deterministic UUID collision in the shared AgentMemories class."""
    assert mod.SOURCE_NAME == "agent_memories"
    assert mod.SOURCE_NAME != "elliot_memories"


def test_class_schema_matches_elliot_memories_schema():
    """Both indexers MUST emit the same Weaviate class schema since the class
    is created once by whichever indexer ensure_target_class fires first."""
    import elliot_memories_indexer as elliot_mod  # noqa: PLC0415

    assert mod.AGENT_MEMORIES_SCHEMA == elliot_mod.AGENT_MEMORIES_SCHEMA
