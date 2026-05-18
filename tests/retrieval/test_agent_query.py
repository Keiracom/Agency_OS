"""Unit tests for src/retrieval/agent_query.

Mocks the orchestrator so tests run without Weaviate or the embedding
model. The intent here is to lock the contract on the public `query()`
entry — anti-hallucination guard, citation extraction, observability
fields. Integration is covered by scripts/retrieval_smoke.py + the
test_smoke module which expect a real Weaviate.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.retrieval import agent_query, orchestrator


def _mk_node(text: str, score: float, *, source_id: str = "doc-1") -> orchestrator.RetrievedNode:
    return orchestrator.RetrievedNode(
        text=text,
        score=score,
        metadata={"source_id": source_id, "agent": "test", "kei": "KEI-49"},
        collection="Discoveries",
    )


def _outcome(
    nodes: tuple[orchestrator.RetrievedNode, ...],
    *,
    bypass_rerank: bool = True,
    reason: str = "test",
    elapsed_ms: int = 0,
) -> orchestrator.RetrievalOutcome:
    return orchestrator.RetrievalOutcome(
        nodes=nodes,
        bypass_rerank=bypass_rerank,
        rerank_reason=reason,
        rerank_elapsed_ms=elapsed_ms,
    )


def test_query_returns_top_citation_when_above_min_score():
    nodes = (_mk_node("the quick brown fox jumps over the lazy dog", 0.92),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("fox?", agent="test", min_score=0.5)
    assert result.citations
    assert result.citations[0].source_id == "doc-1"
    assert result.citations[0].score == pytest.approx(0.92)
    assert "fox" in result.answer
    assert result.bypass_rerank is True


def test_low_score_citations_still_returned_post_kei198():
    """KEI-198: low scores (non-zero) no longer get filtered by the prior
    hard min_score floor. The distribution-aware top-N selection surfaces
    them regardless of absolute value."""
    nodes = (_mk_node("low-quality match", 0.20),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query(
            "anything?", agent="test", citation_required=True, min_score=0.50
        )
    # KEI-198: low-but-nonzero scores now SURFACE (was empty pre-KEI-198).
    assert result.citations
    assert result.citations[0].score == pytest.approx(0.20)
    assert result.answer != ""


def test_citation_required_false_returns_low_score_answer():
    nodes = (_mk_node("still useful even if score is low", 0.20),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query(
            "anything?", agent="test", citation_required=False, min_score=0.50
        )
    assert result.answer != ""
    assert result.citations


def test_kei198_all_zero_scores_returns_empty_when_citation_required():
    """KEI-198 sentinel: ALL scores exactly 0.0 = vectorizer regression.
    With citation_required=True (default), return answer="" so callers
    can detect the regression instead of getting silent vectorless results."""
    nodes = (_mk_node("vectorless object 1", 0.0), _mk_node("vectorless object 2", 0.0))
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("anything?", agent="test", citation_required=True)
    assert result.answer == ""
    assert result.citations == ()


def test_kei198_all_zero_scores_returns_top_n_when_citation_not_required():
    """KEI-198: with citation_required=False, even all-zero-score nodes are
    surfaced. Caller has opted into best-available regardless of confidence."""
    nodes = (
        _mk_node("vectorless object 1", 0.0, source_id="doc-a"),
        _mk_node("vectorless object 2", 0.0, source_id="doc-b"),
    )
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("anything?", agent="test", citation_required=False)
    assert len(result.citations) == 2
    assert {c.source_id for c in result.citations} == {"doc-a", "doc-b"}


def test_kei198_top_n_sorted_by_score_descending():
    """KEI-198: distribution-aware top-N picker returns highest-scored first."""
    nodes = (
        _mk_node("mid", 0.4, source_id="mid"),
        _mk_node("hi", 0.9, source_id="hi"),
        _mk_node("lo", 0.1, source_id="lo"),
    )
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("anything?", agent="test")
    ids = [c.source_id for c in result.citations]
    assert ids == ["hi", "mid", "lo"]
    assert result.citations[0].score == pytest.approx(0.9)


def test_kei198_min_score_parameter_is_noop():
    """KEI-198: explicit min_score parameter retained for back-compat but
    no longer filters. A min_score=0.99 against nodes with scores <0.99 still
    returns the nodes (pre-KEI-198 this would have returned empty)."""
    nodes = (_mk_node("decent match", 0.50),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        # Caller passes a high min_score; KEI-198 treats it as no-op
        result = agent_query.query(
            "anything?", agent="test", citation_required=True, min_score=0.99
        )
    assert result.citations
    assert result.citations[0].score == pytest.approx(0.50)


def test_excerpt_is_capped_to_80_chars():
    long_text = "x" * 200
    nodes = (_mk_node(long_text, 0.90),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("anything?", agent="test", min_score=0.0)
    assert len(result.citations[0].excerpt) == 80


def test_empty_retrieve_returns_empty_when_citation_required():
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(()),
    ):
        result = agent_query.query("anything?", agent="test")
    assert result.answer == ""
    assert result.citations == ()


def test_synthesised_answer_carries_source_marker():
    nodes = (_mk_node("relevant fact about raspberries", 0.85, source_id="probe-123"),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("raspberries?", agent="test", min_score=0.0)
    assert "[probe-123]" in result.answer


def test_max_tokens_bounds_answer_length():
    long_text = "alpha " * 200
    nodes = (_mk_node(long_text, 0.90, source_id="long-doc"),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes),
    ):
        result = agent_query.query("q?", agent="test", min_score=0.0, max_tokens=10)
    assert len(result.answer) <= 10 * 4 + 1


def test_bypass_rerank_propagates_from_outcome():
    nodes = (_mk_node("hit", 0.90),)
    with patch(
        "src.retrieval.agent_query.orchestrator.retrieve_with_outcome",
        return_value=_outcome(nodes, bypass_rerank=False, reason="reranked"),
    ):
        result = agent_query.query("q?", agent="test", min_score=0.0)
    assert result.bypass_rerank is False


def test_record_event_strips_asyncpg_dialect_from_dsn(monkeypatch):
    """KEI-103 — `_record_event` must rewrite `postgresql+asyncpg://` DSNs
    to plain `postgresql://` so psycopg3 can parse the Supabase pooler URL.
    Without the strip, psycopg.ProgrammingError fires and retrieval_events
    silently stays at 0 (the actual KEI-103 root cause).
    """
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres",
    )
    monkeypatch.delenv("RETRIEVAL_EVENTS_DSN", raising=False)

    captured = {}

    class _FakeCur:
        def execute(self, *_a, **_k):
            captured["executed"] = True

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    class _FakeConn:
        def cursor(self):
            return _FakeCur()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def _fake_connect(dsn, **_kw):
        captured["dsn"] = dsn
        return _FakeConn()

    import importlib  # noqa: PLC0415
    import sys  # noqa: PLC0415
    import types  # noqa: PLC0415

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = _fake_connect
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    importlib.reload(agent_query)

    agent_query._record_event(
        agent="test",
        query_text="q",
        collections=("Discoveries",),
        k_initial=1,
        k_returned=1,
        elapsed_ms=0,
        bypass_rerank=True,
        top_citation=None,
    )
    assert captured.get("executed") is True
    # The DSN reaching psycopg.connect must be the stripped form, not the
    # `postgresql+asyncpg://` raw env value.
    assert captured["dsn"].startswith("postgresql://")
    assert "+asyncpg" not in captured["dsn"]
