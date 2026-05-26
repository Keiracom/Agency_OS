"""Tests for Phase A5 piece 5 — smoke recall validation harness.

Covers:
- score_memory_relevance (threshold logic, token matching, alternative content keys)
- execute_probe (passes/fails/exception paths, returns structured result)
- run() aggregate verdict + rc on per-probe pass/fail mix
- DEFAULT_PROBES coverage (4 probes for 4 A5 backfill sources)

bd: Agency_OS-c23f
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "migrations"))

_mod = importlib.import_module("a5_smoke_recall")


class _StubWrapper:
    """Stub a wrapper for recall — returns canned memories per query.

    Memories are passed via constructor as a list and returned wholesale on
    every .recall() call.
    """

    def __init__(self, memories: list[dict] | Exception):
        self._memories = memories

    def recall(self, *, tenant_id: str, query: str, top_k: int = 5):
        if isinstance(self._memories, Exception):
            raise self._memories
        return self._memories[:top_k]


def test_default_probes_cover_all_four_sources():
    names = {p.name for p in _mod.DEFAULT_PROBES}
    assert names == {
        "piece_1b_ceo_memory",
        "piece_2_weaviate_snapshot",
        "piece_3_drive_manual",
        "piece_4_slack_ceo",
    }


def test_default_probes_use_known_wrappers():
    for p in _mod.DEFAULT_PROBES:
        assert p.wrapper_name in _mod.WRAPPER_BUILDERS


def test_score_memory_relevance_threshold_pass():
    mem = {"content": "Dave A5 backfill landed under fleet tenant"}
    tokens = ("a5", "backfill", "dave")
    rel, matched = _mod.score_memory_relevance(mem, tokens)
    assert rel is True
    assert set(matched) == {"a5", "backfill", "dave"}


def test_score_memory_relevance_threshold_fail():
    mem = {"content": "only one matched token here: dave"}
    tokens = ("a5", "backfill", "dave")
    rel, matched = _mod.score_memory_relevance(mem, tokens)
    assert rel is False
    assert matched == ["dave"]


def test_score_memory_relevance_falls_back_to_text_key():
    mem = {"text": "atlas phase a3 cutover landed"}
    tokens = ("atlas", "a3", "cutover")
    rel, matched = _mod.score_memory_relevance(mem, tokens)
    assert rel is True


def test_score_memory_relevance_case_insensitive():
    mem = {"content": "ATLAS A3 CUTOVER"}
    tokens = ("atlas", "a3", "cutover")
    rel, matched = _mod.score_memory_relevance(mem, tokens)
    assert rel is True


def test_score_memory_relevance_empty_content_returns_false():
    rel, matched = _mod.score_memory_relevance({}, ("a", "b", "c"))
    assert rel is False
    assert matched == []


def test_execute_probe_pass_when_at_least_one_relevant_memory():
    probe = _mod.Probe(
        name="t1",
        wrapper_name="decision",
        query="x",
        expected_signal_tokens=("alpha", "beta"),
    )
    wrapper = _StubWrapper(
        [
            {"content": "alpha beta gamma"},  # relevant (2 tokens)
            {"content": "nothing here"},  # not relevant
        ]
    )
    result = _mod.execute_probe(probe, wrappers={"decision": wrapper})
    assert result["passed"] is True
    assert result["memories_returned"] == 2
    assert result["relevant_memories"] == 1


def test_execute_probe_fail_when_no_relevant_memory():
    probe = _mod.Probe(
        name="t2",
        wrapper_name="decision",
        query="x",
        expected_signal_tokens=("alpha", "beta", "gamma"),
    )
    wrapper = _StubWrapper(
        [
            {"content": "only alpha"},  # 1 token only
            {"content": "no matches"},
        ]
    )
    result = _mod.execute_probe(probe, wrappers={"decision": wrapper})
    assert result["passed"] is False
    assert result["relevant_memories"] == 0


def test_execute_probe_fail_on_empty_recall():
    probe = _mod.Probe(
        name="t3",
        wrapper_name="decision",
        query="x",
        expected_signal_tokens=("a", "b"),
    )
    result = _mod.execute_probe(probe, wrappers={"decision": _StubWrapper([])})
    assert result["passed"] is False
    assert result["memories_returned"] == 0


def test_execute_probe_handles_exception():
    probe = _mod.Probe(
        name="t4",
        wrapper_name="decision",
        query="x",
        expected_signal_tokens=("a", "b"),
    )
    wrapper = _StubWrapper(ConnectionError("hindsight down"))
    result = _mod.execute_probe(probe, wrappers={"decision": wrapper})
    assert result["passed"] is False
    assert "ConnectionError" in result["error"]


def test_execute_probe_handles_non_list_return():
    probe = _mod.Probe(
        name="t5",
        wrapper_name="decision",
        query="x",
        expected_signal_tokens=("a", "b"),
    )

    class _BadShape:
        def recall(self, **kwargs):
            return {"not": "a list"}

    result = _mod.execute_probe(probe, wrappers={"decision": _BadShape()})
    assert result["passed"] is False
    assert "non-list" in result["error"]


def test_run_returns_zero_when_all_probes_pass():
    probes = (
        _mod.Probe("p1", "decision", "q", ("alpha", "beta")),
        _mod.Probe("p2", "taskcontext", "q", ("gamma", "delta")),
    )
    wrappers = {
        "decision": _StubWrapper([{"content": "alpha beta hit"}]),
        "taskcontext": _StubWrapper([{"content": "gamma delta hit"}]),
    }
    rc, results = _mod.run(probes=probes, wrappers=wrappers)
    assert rc == 0
    assert all(r["passed"] for r in results)
    assert len(results) == 2


def test_run_returns_one_when_any_probe_fails():
    probes = (
        _mod.Probe("p1", "decision", "q", ("alpha", "beta")),
        _mod.Probe("p2", "taskcontext", "q", ("gamma", "delta")),
    )
    wrappers = {
        "decision": _StubWrapper([{"content": "alpha beta hit"}]),
        "taskcontext": _StubWrapper([{"content": "only gamma"}]),  # 1 token only
    }
    rc, results = _mod.run(probes=probes, wrappers=wrappers)
    assert rc == 1
    assert results[0]["passed"] is True
    assert results[1]["passed"] is False


def test_run_returns_one_when_all_probes_fail():
    probes = (_mod.Probe("p1", "decision", "q", ("alpha", "beta")),)
    wrappers = {"decision": _StubWrapper([])}
    rc, _ = _mod.run(probes=probes, wrappers=wrappers)
    assert rc == 1
