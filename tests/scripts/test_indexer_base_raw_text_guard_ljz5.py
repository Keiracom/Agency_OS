"""Regression: BaseIndexer.index_once drops empty/NULL raw_text BEFORE POST.

Agency_OS-ljz5 / KEI-103: NULL raw_text in Weaviate-indexed objects crashes
llama-index TextNode validation in src.retrieval.orchestrator with:
    text Input should be a valid string [input_value=None]
Result: retrieve_with_outcome returns 0 nodes even when ANN matched, looking
like a zero-hit miss when it was actually a malformed-row miss.

Scout's PR #992 (KEI-197) ships writer-side guards at submit_discovery + a
cleanup script (--class flag). This file locks in the indexer-side
belt-and-suspenders guard at BaseIndexer.index_once so no future indexer
(or refactor) can post NULL/empty raw_text to a retrieval-path collection.

Empirical baseline 2026-05-18 21:50 UTC (atlas worktree probe):
    Discoveries     14166    9390 NULL    0 empty   <- Scout's PR #992 territory
    Keis              313       0 NULL    0 empty   <- clean
    AgentMemories     192       0 NULL    0 empty   <- clean
    Decisions         300       0 NULL    0 empty   <- clean
    Codebase           94       0 NULL    0 empty   <- clean
The 4 BaseIndexer-backed collections are clean today; this PR keeps them
clean against future regressions.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import indexer_base as ib  # noqa: E402

# ─── _has_valid_raw_text unit ─────────────────────────────────────────────


def test_valid_raw_text_passes():
    obj = {"id": "1", "class": "Keis", "properties": {"raw_text": "real content"}}
    assert ib._has_valid_raw_text(obj) is True


def test_null_raw_text_rejected():
    obj = {"id": "1", "class": "Keis", "properties": {"raw_text": None}}
    assert ib._has_valid_raw_text(obj) is False


def test_empty_string_raw_text_rejected():
    obj = {"id": "1", "class": "Keis", "properties": {"raw_text": ""}}
    assert ib._has_valid_raw_text(obj) is False


def test_whitespace_only_raw_text_rejected():
    obj = {"id": "1", "class": "Keis", "properties": {"raw_text": "   \t\n  "}}
    assert ib._has_valid_raw_text(obj) is False


def test_missing_raw_text_property_passes():
    """drive_strategic uses 'content' not 'raw_text' — its target class isn't
    on the raw_text retrieval contract. The guard must not block its POSTs."""
    obj = {"id": "1", "class": "StrategicDocuments", "properties": {"content": "section text"}}
    assert ib._has_valid_raw_text(obj) is True


def test_no_properties_at_all_passes():
    """Defensive: malformed obj with no properties at all — let post_object
    fail on its own with a real HTTP error, not a silent guard skip."""
    obj = {"id": "1", "class": "Keis"}
    assert ib._has_valid_raw_text(obj) is True


# ─── index_once integration — fake indexer ────────────────────────────────


class _FakeIndexer(ib.BaseIndexer[dict]):
    source_name = "fake"
    target_class = "Keis"
    class_schema = {"class": "Keis"}

    def __init__(self, rows):
        self._rows = rows

    def fetch_batch(self, batch_size):
        return self._rows[:batch_size]

    def build_object(self, row):
        return row


def test_index_once_skips_null_raw_text_no_post(monkeypatch):
    posted = []
    monkeypatch.setattr(ib, "post_object", lambda obj: posted.append(obj) or True)

    indexer = _FakeIndexer(
        [
            {"id": "good-1", "class": "Keis", "properties": {"raw_text": "valid"}},
            {"id": "bad-null", "class": "Keis", "properties": {"raw_text": None}},
            {"id": "bad-empty", "class": "Keis", "properties": {"raw_text": ""}},
            {"id": "good-2", "class": "Keis", "properties": {"raw_text": "also valid"}},
        ]
    )
    outcome = indexer.index_once(batch_size=10)

    assert outcome.selected == 4
    assert outcome.success == 2, f"only good rows should POST; got success={outcome.success}"
    assert outcome.failed == 2, f"bad rows should count as failed; got failed={outcome.failed}"
    assert [o["id"] for o in posted] == ["good-1", "good-2"], (
        f"only valid raw_text rows should reach Weaviate; got {[o['id'] for o in posted]}"
    )


def test_index_once_passes_through_non_raw_text_indexer(monkeypatch):
    """Drive-style indexer uses 'content' not 'raw_text' — guard must be a no-op."""
    posted = []
    monkeypatch.setattr(ib, "post_object", lambda obj: posted.append(obj) or True)

    indexer = _FakeIndexer(
        [
            {"id": "drive-1", "class": "StrategicDocuments", "properties": {"content": "x"}},
            {"id": "drive-2", "class": "StrategicDocuments", "properties": {"content": "y"}},
        ]
    )
    outcome = indexer.index_once(batch_size=10)

    assert outcome.success == 2
    assert outcome.failed == 0
    assert [o["id"] for o in posted] == ["drive-1", "drive-2"]


def test_index_once_propagates_post_failure(monkeypatch):
    """Real HTTP failure (post_object returns False) is counted, not silently skipped."""
    monkeypatch.setattr(ib, "post_object", lambda _obj: False)

    indexer = _FakeIndexer(
        [{"id": "x", "class": "Keis", "properties": {"raw_text": "valid"}}],
    )
    outcome = indexer.index_once(batch_size=10)
    assert outcome.success == 0
    assert outcome.failed == 1
