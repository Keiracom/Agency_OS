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


def test_query_returns_top_citation_when_above_min_score():
    nodes = (_mk_node("the quick brown fox jumps over the lazy dog", 0.92),)
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=nodes):
        result = agent_query.query("fox?", agent="test", min_score=0.5)
    assert result.citations
    assert result.citations[0].source_id == "doc-1"
    assert result.citations[0].score == pytest.approx(0.92)
    assert "fox" in result.answer
    assert result.bypass_rerank is True


def test_citation_required_returns_empty_answer_when_below_threshold():
    nodes = (_mk_node("low-quality match", 0.20),)
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=nodes):
        result = agent_query.query("anything?", agent="test", citation_required=True, min_score=0.50)
    assert result.answer == ""
    assert result.citations == ()


def test_citation_required_false_returns_low_score_answer():
    nodes = (_mk_node("still useful even if score is low", 0.20),)
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=nodes):
        result = agent_query.query("anything?", agent="test", citation_required=False, min_score=0.50)
    assert result.answer != ""
    assert result.citations


def test_excerpt_is_capped_to_80_chars():
    long_text = "x" * 200
    nodes = (_mk_node(long_text, 0.90),)
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=nodes):
        result = agent_query.query("anything?", agent="test", min_score=0.0)
    assert len(result.citations[0].excerpt) == 80


def test_empty_retrieve_returns_empty_when_citation_required():
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=()):
        result = agent_query.query("anything?", agent="test")
    assert result.answer == ""
    assert result.citations == ()


def test_synthesised_answer_carries_source_marker():
    nodes = (_mk_node("relevant fact about raspberries", 0.85, source_id="probe-123"),)
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=nodes):
        result = agent_query.query("raspberries?", agent="test", min_score=0.0)
    assert "[probe-123]" in result.answer


def test_max_tokens_bounds_answer_length():
    long_text = "alpha " * 200
    nodes = (_mk_node(long_text, 0.90, source_id="long-doc"),)
    with patch("src.retrieval.agent_query.orchestrator.retrieve_nodes", return_value=nodes):
        result = agent_query.query("q?", agent="test", min_score=0.0, max_tokens=10)
    assert len(result.answer) <= 10 * 4 + 1
