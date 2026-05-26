"""Unit tests for scripts/migrations/global_governance_patterns_hand_migration.py.

Covers the pure-function surface (no HTTP):
- build_hindsight_item shape matches indexer_base._post_object_hindsight_mirror
- load_state / append_state round-trip + skips on re-run
- migrate_one error-path returns (False, ...) on non-2xx

End-to-end HTTP path is exercised by operator dry-run before --execute, not
re-mocked here (would duplicate indexer_base mirror tests).

bd: Agency_OS-x0p7
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mig = importlib.import_module("global_governance_patterns_hand_migration")


def test_build_hindsight_item_carries_raw_text_as_content():
    obj = {
        "id": "ggp-1",
        "class": "Global_governance_patterns",
        "properties": {
            "raw_text": "pattern: deliberator concur required for merge",
            "agent": "aiden",
            "kei": "Agency_OS-x0p7",
        },
    }
    item = _mig.build_hindsight_item(obj)
    assert item["content"] == "pattern: deliberator concur required for merge"
    assert "weaviate_class:Global_governance_patterns" in item["tags"]
    assert item["metadata"]["external_id"] == "ggp-1"
    assert item["metadata"]["mirror_source"] == "global_governance_patterns_hand_migration"
    assert item["metadata"]["weaviate_class"] == "Global_governance_patterns"
    assert item["metadata"]["agent"] == "aiden"
    assert "raw_text" not in item["metadata"]


def test_build_hindsight_item_falls_back_to_content_then_json():
    obj = {
        "id": "ggp-2",
        "class": "Global_governance_patterns",
        "properties": {"content": "fallback-1"},
    }
    assert _mig.build_hindsight_item(obj)["content"] == "fallback-1"
    obj2 = {"id": "ggp-3", "class": "Global_governance_patterns", "properties": {"x": "y"}}
    item = _mig.build_hindsight_item(obj2)
    assert '"x"' in item["content"]
    assert '"y"' in item["content"]


def test_state_roundtrip_skips_seen_ids(tmp_path: Path):
    state = tmp_path / "state.jsonl"
    assert _mig.load_state(state) == set()
    _mig.append_state(state, {"external_id": "ggp-A", "ok": True, "info": "ok"})
    _mig.append_state(state, {"external_id": "ggp-B", "ok": False, "info": "rc=500"})
    _mig.append_state(state, {"external_id": "ggp-C", "ok": True, "info": "ok"})
    seen = _mig.load_state(state)
    assert seen == {"ggp-A", "ggp-C"}  # only ok=True rows count as migrated


def test_migrate_one_returns_false_on_non_2xx(monkeypatch):
    """Non-2xx response from Hindsight must be classified as failure."""
    monkeypatch.setattr(_mig, "_http_post", lambda base, path, body: (500, {"error": "boom"}))
    ok, info = _mig.migrate_one(
        {"id": "x", "class": "Global_governance_patterns", "properties": {}}
    )
    assert ok is False
    assert "rc=500" in info


def test_migrate_one_returns_true_on_2xx(monkeypatch):
    monkeypatch.setattr(_mig, "_http_post", lambda base, path, body: (200, {"id": "h-123"}))
    ok, info = _mig.migrate_one(
        {"id": "x", "class": "Global_governance_patterns", "properties": {}}
    )
    assert ok is True
    assert "h-123" in info


def test_run_aborts_when_weaviate_count_unavailable(monkeypatch, tmp_path: Path):
    """If we can't get a baseline count, we refuse to run (safety guard)."""
    monkeypatch.setattr(_mig, "weaviate_count", lambda *a, **kw: None)
    rc = _mig.run(execute=True, state_path=tmp_path / "s.jsonl")
    assert rc == 2


def test_run_dry_run_does_not_call_migrate_one(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_mig, "weaviate_count", lambda *a, **kw: 3)
    monkeypatch.setattr(
        _mig,
        "iter_weaviate_objects",
        lambda *a, **kw: iter(
            [
                {"id": f"ggp-{i}", "class": "Global_governance_patterns", "properties": {}}
                for i in range(3)
            ]
        ),
    )
    called = []
    monkeypatch.setattr(_mig, "migrate_one", lambda obj: called.append(obj) or (True, ""))
    rc = _mig.run(execute=False, state_path=tmp_path / "s.jsonl")
    assert rc == 0
    assert called == []  # dry-run skips writes


def test_run_execute_writes_state_and_returns_zero_on_clean(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_mig, "weaviate_count", lambda *a, **kw: 2)
    monkeypatch.setattr(
        _mig,
        "iter_weaviate_objects",
        lambda *a, **kw: iter(
            [
                {"id": "a", "class": "Global_governance_patterns", "properties": {}},
                {"id": "b", "class": "Global_governance_patterns", "properties": {}},
            ]
        ),
    )
    monkeypatch.setattr(_mig, "migrate_one", lambda obj: (True, "ok"))
    state = tmp_path / "s.jsonl"
    rc = _mig.run(execute=True, state_path=state)
    assert rc == 0
    assert _mig.load_state(state) == {"a", "b"}


def test_run_execute_returns_one_on_any_failure(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_mig, "weaviate_count", lambda *a, **kw: 2)
    monkeypatch.setattr(
        _mig,
        "iter_weaviate_objects",
        lambda *a, **kw: iter(
            [
                {"id": "a", "class": "Global_governance_patterns", "properties": {}},
                {"id": "b", "class": "Global_governance_patterns", "properties": {}},
            ]
        ),
    )
    seq = iter([(True, "ok"), (False, "rc=500")])
    monkeypatch.setattr(_mig, "migrate_one", lambda obj: next(seq))
    rc = _mig.run(execute=True, state_path=tmp_path / "s.jsonl")
    assert rc == 1


def test_run_skips_already_migrated_ids(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(_mig, "weaviate_count", lambda *a, **kw: 2)
    state = tmp_path / "s.jsonl"
    _mig.append_state(state, {"external_id": "a", "ok": True, "info": "ok"})
    monkeypatch.setattr(
        _mig,
        "iter_weaviate_objects",
        lambda *a, **kw: iter(
            [
                {"id": "a", "class": "Global_governance_patterns", "properties": {}},
                {"id": "b", "class": "Global_governance_patterns", "properties": {}},
            ]
        ),
    )
    called = []
    monkeypatch.setattr(_mig, "migrate_one", lambda obj: called.append(obj["id"]) or (True, "ok"))
    rc = _mig.run(execute=True, state_path=state)
    assert rc == 0
    assert called == ["b"]  # "a" skipped per state file
