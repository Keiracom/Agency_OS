"""Tests for KEI-63 discovery_log deprecation primitive."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "discovery_log.py"

_spec = importlib.util.spec_from_file_location("discovery_log", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["discovery_log"] = _mod
_spec.loader.exec_module(_mod)

load_all = _mod.load_all_discoveries
load_active = _mod.load_active_discoveries
append_discovery = _mod.append_discovery
mark_deprecated = _mod.mark_deprecated
DiscoveryLogError = _mod.DiscoveryLogError


@pytest.fixture
def jsonl_path(tmp_path):
    return tmp_path / "discovery_log.jsonl"


def test_load_all_missing_file_returns_empty(jsonl_path):
    assert load_all(jsonl_path) == []


def test_append_creates_file_and_parent(tmp_path):
    p = tmp_path / "nested" / "dirs" / "log.jsonl"
    append_discovery({"kei": "KEI-1", "context": "test"}, p)
    assert p.exists()
    rows = load_all(p)
    assert len(rows) == 1 and rows[0]["kei"] == "KEI-1"


def test_append_rejects_missing_kei(jsonl_path):
    with pytest.raises(DiscoveryLogError, match="missing required 'kei'"):
        append_discovery({"context": "no kei"}, jsonl_path)


def test_load_all_raises_on_malformed(jsonl_path):
    jsonl_path.write_text('{"kei":"KEI-1"}\nNOT_JSON\n', encoding="utf-8")
    with pytest.raises(DiscoveryLogError, match="malformed jsonl"):
        load_all(jsonl_path)


def test_load_active_excludes_deprecated(jsonl_path):
    for row in [
        {"kei": "KEI-A", "deprecated": False},
        {"kei": "KEI-B", "deprecated": True, "deprecated_reason": "wrong"},
        {"kei": "KEI-C"},
    ]:
        append_discovery(row, jsonl_path)
    active = load_active(jsonl_path)
    assert {r["kei"] for r in active} == {"KEI-A", "KEI-C"}


def test_mark_deprecated_marks_most_recent_with_kei(jsonl_path):
    append_discovery({"kei": "KEI-X", "context": "old", "finding": "v1"}, jsonl_path)
    append_discovery({"kei": "KEI-Y", "context": "other"}, jsonl_path)
    append_discovery({"kei": "KEI-X", "context": "new", "finding": "v2"}, jsonl_path)

    result = mark_deprecated(
        "KEI-X",
        reason="superseded by v3",
        by="max",
        path=jsonl_path,
        now="2026-05-14T08:30:00Z",
    )
    assert result["context"] == "new"
    assert result["deprecated"] is True
    assert result["deprecated_reason"] == "superseded by v3"
    assert result["deprecated_by"] == "max"
    assert result["deprecated_at"] == "2026-05-14T08:30:00Z"

    rows = load_all(jsonl_path)
    assert rows[0]["kei"] == "KEI-X" and rows[0].get("deprecated") is not True
    assert rows[2]["kei"] == "KEI-X" and rows[2]["deprecated"] is True


def test_mark_deprecated_raises_on_missing_kei(jsonl_path):
    append_discovery({"kei": "KEI-A"}, jsonl_path)
    with pytest.raises(DiscoveryLogError, match="no discovery row"):
        mark_deprecated("KEI-MISSING", reason="r", by="max", path=jsonl_path)


def test_mark_deprecated_raises_on_empty_log(jsonl_path):
    with pytest.raises(DiscoveryLogError, match="empty or missing"):
        mark_deprecated("KEI-X", reason="r", by="max", path=jsonl_path)


def test_mark_deprecated_rejects_empty_reason(jsonl_path):
    append_discovery({"kei": "KEI-A"}, jsonl_path)
    with pytest.raises(DiscoveryLogError, match="reason must be a non-empty"):
        mark_deprecated("KEI-A", reason="", by="max", path=jsonl_path)


def test_mark_deprecated_rejects_empty_kei(jsonl_path):
    append_discovery({"kei": "KEI-A"}, jsonl_path)
    with pytest.raises(DiscoveryLogError, match="kei must be a non-empty"):
        mark_deprecated("", reason="r", by="max", path=jsonl_path)


def test_load_active_after_deprecate_excludes_target(jsonl_path):
    append_discovery({"kei": "KEI-A", "finding": "v1"}, jsonl_path)
    append_discovery({"kei": "KEI-B", "finding": "stays"}, jsonl_path)
    mark_deprecated("KEI-A", reason="bad", by="max", path=jsonl_path)
    active = load_active(jsonl_path)
    assert [r["kei"] for r in active] == ["KEI-B"]


def test_mark_deprecated_idempotent_remark_updates_reason_and_timestamp(jsonl_path):
    append_discovery({"kei": "KEI-A", "finding": "v1"}, jsonl_path)
    mark_deprecated("KEI-A", reason="first", by="max", path=jsonl_path, now="2026-05-14T08:00:00Z")
    second = mark_deprecated(
        "KEI-A", reason="second", by="max", path=jsonl_path, now="2026-05-14T09:00:00Z"
    )
    assert second["deprecated_reason"] == "second"
    assert second["deprecated_at"] == "2026-05-14T09:00:00Z"
    rows = load_all(jsonl_path)
    assert len(rows) == 1


def test_jsonl_file_is_atomic_rewrite(jsonl_path):
    append_discovery({"kei": "KEI-A"}, jsonl_path)
    append_discovery({"kei": "KEI-B"}, jsonl_path)
    mark_deprecated("KEI-A", reason="r", by="max", path=jsonl_path)
    tmp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp")
    assert not tmp_path.exists()
    rows = load_all(jsonl_path)
    assert len(rows) == 2 and rows[0]["deprecated"] is True
