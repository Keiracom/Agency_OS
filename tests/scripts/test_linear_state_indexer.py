"""Unit tests for linear_state_indexer (KEI-85 phase B).

No network: pure-logic tests for build_keis_doc + deterministic UUID +
ABC compliance. End-to-end smoke (live Linear API + live Weaviate) is
in the PR body and runs against the host.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import linear_state_indexer as mod  # noqa: E402


def _issue(updated_at: str = "2026-05-17T08:00:00Z") -> mod.LinearIssue:
    return mod.LinearIssue(
        id="lin-id-abc",
        identifier="KEI-85",
        title="Multi-source auto-indexers",
        description="phase A/B/C/D scaffold",
        state_name="In Progress",
        state_type="started",
        updated_at=updated_at,
        assignee="atlas",
        priority_name="Medium",
    )


def test_deterministic_uuid_stable_for_same_issue_and_ts():
    a = mod.build_keis_doc(_issue())["id"]
    b = mod.build_keis_doc(_issue())["id"]
    assert a == b


def test_deterministic_uuid_differs_when_updated_at_changes():
    a = mod.build_keis_doc(_issue(updated_at="2026-05-17T08:00:00Z"))["id"]
    b = mod.build_keis_doc(_issue(updated_at="2026-05-17T09:00:00Z"))["id"]
    assert a != b


def test_build_keis_doc_basic_shape():
    doc = mod.build_keis_doc(_issue())
    assert doc["class"] == "Keis"
    props = doc["properties"]
    assert props["kei"] == "KEI-85"
    assert props["agent"] == "system"
    assert props["created_at"] == "2026-05-17T08:00:00Z"
    assert "Multi-source" in props["raw_text"]
    assert len(props["environment_hash"]) == 16
    int(props["environment_hash"], 16)


def test_build_keis_doc_handles_empty_updated_at():
    issue = mod.LinearIssue(
        id="x",
        identifier="KEI-X",
        title="t",
        description="",
        state_name="",
        state_type="",
        updated_at="",
        assignee="",
        priority_name="",
    )
    doc = mod.build_keis_doc(issue)
    assert doc["properties"]["created_at"] == "1970-01-01T00:00:00Z"


def test_linear_state_indexer_satisfies_base_indexer_abc():
    import indexer_base

    assert issubclass(mod.LinearStateIndexer, indexer_base.BaseIndexer)
    assert mod.LinearStateIndexer.source_name == "linear"
    assert mod.LinearStateIndexer.target_class == "Keis"
    assert mod.LinearStateIndexer.class_schema["class"] == "Keis"
    assert mod.LinearStateIndexer.__abstractmethods__ == frozenset()


def test_advance_cursor_writes_then_read_cursor_reads(tmp_path, monkeypatch):
    cursor_file = tmp_path / "lin.cursor"
    monkeypatch.setattr(mod, "CURSOR_PATH", cursor_file)

    indexer = mod.LinearStateIndexer(batch_size=5)
    indexer._last_max_updated_at = "2026-05-17T10:00:00Z"
    indexer.advance_cursor()

    assert mod._read_cursor() == "2026-05-17T10:00:00Z"


def test_read_cursor_default_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "CURSOR_PATH", tmp_path / "no-such-file")
    assert mod._read_cursor() == "1970-01-01T00:00:00Z"


def test_read_cursor_default_when_corrupt(tmp_path, monkeypatch):
    bad = tmp_path / "bad.cursor"
    bad.write_text("not-json-content")
    monkeypatch.setattr(mod, "CURSOR_PATH", bad)
    assert mod._read_cursor() == "1970-01-01T00:00:00Z"


def test_parse_retry_after_seconds():
    assert mod._parse_retry_after("30") == 30.0
    assert mod._parse_retry_after("0.5") == 0.5


def test_parse_retry_after_returns_none_on_unparseable():
    assert mod._parse_retry_after(None) is None
    assert mod._parse_retry_after("") is None
    # http-date form — we don't parse those, caller falls back to backoff.
    assert mod._parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None


def test_parse_nodes_handles_missing_optional_fields():
    nodes = [
        {"id": "x1", "identifier": "KEI-1", "title": "t", "updatedAt": "2026-05-17T00:00:00Z"},
        {
            "id": "x2",
            "identifier": "KEI-2",
            "title": "t",
            "description": None,
            "state": None,
            "assignee": None,
            "priorityLabel": "",
            "updatedAt": "2026-05-17T01:00:00Z",
        },
    ]
    parsed = mod._parse_nodes(nodes)
    assert len(parsed) == 2
    assert parsed[0].description == ""
    assert parsed[0].state_name == ""
    assert parsed[1].state_type == ""
    assert parsed[1].assignee == ""
