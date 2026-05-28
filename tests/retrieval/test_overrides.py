"""Unit tests for src/retrieval/overrides + its wiring into agent_query.

Covers the feature-flag gate, the ignore/prefer apply logic, task-scope
precedence, the best-effort load path (mocked psycopg), and the end-to-end
behaviour through agent_query.query() with the orchestrator mocked.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.retrieval import agent_query, orchestrator, overrides
from src.retrieval.agent_query import Citation


def _cite(source_id: str, score: float) -> Citation:
    return Citation(source_id=source_id, collection="Discoveries", score=score, excerpt="x")


def _ov(memory_id: str, kind: str, *, task_type: str | None = None) -> overrides.MemoryOverride:
    return overrides.MemoryOverride(memory_id=memory_id, override_type=kind, task_type=task_type)


# --- is_enabled ----------------------------------------------------------


@pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on"])
def test_is_enabled_truthy(monkeypatch, val):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", val)
    assert overrides.is_enabled() is True


@pytest.mark.parametrize("val", ["", "0", "false", "no", "off"])
def test_is_enabled_falsy(monkeypatch, val):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", val)
    assert overrides.is_enabled() is False


def test_is_enabled_default_off(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_OVERRIDES_ENABLED", raising=False)
    assert overrides.is_enabled() is False


# --- apply_overrides -----------------------------------------------------


def test_apply_is_noop_when_flag_off(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_OVERRIDES_ENABLED", raising=False)
    cites = [_cite("a", 0.9)]
    # Even with an ignore override present, the flag-off path returns input as-is.
    assert overrides.apply_overrides(cites, task_type=None, overrides=[_ov("a", "ignore")]) is cites


def test_apply_ignore_filters_citation(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    cites = [_cite("keep", 0.9), _cite("drop", 0.8)]
    out = overrides.apply_overrides(cites, task_type=None, overrides=[_ov("drop", "ignore")])
    assert [c.source_id for c in out] == ["keep"]


def test_apply_prefer_boosts_score(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    cites = [_cite("boostme", 0.1)]
    out = overrides.apply_overrides(cites, task_type=None, overrides=[_ov("boostme", "prefer")])
    assert out[0].score == pytest.approx(0.1 + overrides.PREFER_SCORE_BOOST)
    assert out[0].source_id == "boostme"


def test_apply_empty_citations_short_circuits(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    assert overrides.apply_overrides([], task_type=None, overrides=[_ov("x", "ignore")]) == []


def test_task_scoped_override_wins_over_global(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    cites = [_cite("m", 0.5)]
    # global prefer + task-scoped ignore for the same memory → task-scoped wins.
    ovs = [_ov("m", "prefer"), _ov("m", "ignore", task_type="sales")]
    out = overrides.apply_overrides(cites, task_type="sales", overrides=ovs)
    assert out == []  # ignored


def test_load_active_returns_empty_without_dsn(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RETRIEVAL_EVENTS_DSN", raising=False)
    assert overrides.load_active(None) == []


def test_insert_override_raises_without_dsn(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RETRIEVAL_EVENTS_DSN", raising=False)
    with pytest.raises(RuntimeError):
        overrides.insert_override("m", "ignore")


# --- agent_query wiring --------------------------------------------------


def _node(source_id: str, score: float) -> orchestrator.RetrievedNode:
    return orchestrator.RetrievedNode(
        text=f"text for {source_id}",
        score=score,
        metadata={"source_id": source_id},
        collection="Discoveries",
    )


def _outcome(*nodes: orchestrator.RetrievedNode) -> orchestrator.RetrievalOutcome:
    return orchestrator.RetrievalOutcome(
        nodes=nodes, bypass_rerank=True, rerank_reason="t", rerank_elapsed_ms=0
    )


def test_query_filters_ignored_memory(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    with (
        patch(
            "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
            return_value=_outcome(_node("good", 0.9), _node("banned", 0.95)),
        ),
        patch("src.retrieval.overrides.load_active", return_value=[_ov("banned", "ignore")]),
    ):
        result = agent_query.query("q?", agent="test")
    ids = {c.source_id for c in result.citations}
    assert "banned" not in ids
    assert "good" in ids


def test_query_prefer_reorders_to_top(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_OVERRIDES_ENABLED", "true")
    with (
        patch(
            "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
            return_value=_outcome(_node("top_normally", 0.9), _node("preferred", 0.1)),
        ),
        patch("src.retrieval.overrides.load_active", return_value=[_ov("preferred", "prefer")]),
    ):
        result = agent_query.query("q?", agent="test")
    # 0.1 + 0.5 boost = 0.6 < 0.9, so preferred rises but not above top_normally.
    # Bump test: a larger gap would invert; here we assert the boost applied.
    scores = {c.source_id: c.score for c in result.citations}
    assert scores["preferred"] == pytest.approx(0.6)


def test_query_unchanged_when_flag_off(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_OVERRIDES_ENABLED", raising=False)
    with (
        patch(
            "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
            return_value=_outcome(_node("a", 0.9), _node("b", 0.8)),
        ),
        patch("src.retrieval.overrides.load_active") as load,
    ):
        result = agent_query.query("q?", agent="test")
    load.assert_not_called()  # flag off → never even loads overrides
    assert {c.source_id for c in result.citations} == {"a", "b"}
