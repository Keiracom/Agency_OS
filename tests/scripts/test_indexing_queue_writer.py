"""Tests for KEI-61 Phase A indexing_queue_writer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "indexing_queue_writer.py"

_spec = importlib.util.spec_from_file_location("indexing_queue_writer", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["indexing_queue_writer"] = _mod
_spec.loader.exec_module(_mod)

VALID_SOURCES = _mod.VALID_SOURCES
IndexingQueueError = _mod.IndexingQueueError
queue_event = _mod.queue_event


def test_queue_event_rejects_invalid_source():
    with pytest.raises(IndexingQueueError, match="invalid source"):
        queue_event(source="invalid_thing", payload={})


def test_queue_event_accepts_all_valid_sources():
    captured: list = []

    def fake_write(source, payload):
        captured.append((source, payload))
        return "00000000-0000-0000-0000-000000000001"

    for src in VALID_SOURCES:
        row_id = queue_event(source=src, payload={"k": "v"}, write_fn=fake_write)
        assert row_id == "00000000-0000-0000-0000-000000000001"
    assert len(captured) == len(VALID_SOURCES)


def test_queue_event_passes_payload_to_write_fn():
    captured: dict = {}

    def fake_write(source, payload):
        captured["source"] = source
        captured["payload"] = payload
        return "row-uuid-1"

    payload = {"event": "push", "commit": "abc1234", "files": ["a.py", "b.md"]}
    queue_event(source="git", payload=payload, write_fn=fake_write)

    assert captured["source"] == "git"
    assert captured["payload"] == payload


def test_queue_event_wraps_write_failure_in_typed_error():
    def failing_write(source, payload):
        raise RuntimeError("supabase unreachable")

    with pytest.raises(IndexingQueueError, match="queue write failed"):
        queue_event(source="slack", payload={}, write_fn=failing_write)


def test_queue_event_returns_row_uuid():
    expected = "11111111-2222-3333-4444-555555555555"

    def fake_write(source, payload):
        return expected

    assert queue_event(source="linear", payload={"x": 1}, write_fn=fake_write) == expected


def test_valid_sources_enum_complete():
    assert VALID_SOURCES == frozenset({
        "git", "slack", "linear", "ceo_memory", "tool_log",
    })


def test_queue_event_handles_empty_payload():
    captured: dict = {}

    def fake_write(source, payload):
        captured["payload"] = payload
        return "row-uuid-empty"

    queue_event(source="tool_log", payload={}, write_fn=fake_write)
    assert captured["payload"] == {}
