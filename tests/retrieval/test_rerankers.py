"""Unit tests for src/retrieval/rerankers.

FlashRank is mocked so tests run in any environment. The intent is to lock
the contract under all four observable states: dep missing, latency-budget
exceeded, empty input, healthy rerank.
"""

from __future__ import annotations

import builtins
import sys
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval import rerankers


@pytest.fixture(autouse=True)
def _reset_singleton():
    rerankers.reset_reranker()
    yield
    rerankers.reset_reranker()


def _mk_node(text: str, score: float = 0.5) -> SimpleNamespace:
    return SimpleNamespace(text=text, score=score)


def test_empty_input_returns_empty_outcome_with_no_bypass():
    outcome = rerankers.rerank_top_k("q?", ())
    assert outcome.nodes == ()
    assert outcome.bypassed is False
    assert outcome.reason == "empty_input"


def test_missing_dep_bypasses_with_raw_topk():
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "flashrank":
            raise ImportError("flashrank not installed in test env")
        return real_import(name, *args, **kwargs)

    nodes = tuple(_mk_node(f"node-{i}") for i in range(8))
    with patch("builtins.__import__", side_effect=fake_import):
        outcome = rerankers.rerank_top_k("q?", nodes, top_k=3)
    assert outcome.bypassed is True
    assert outcome.reason == "flashrank_not_available"
    assert outcome.nodes == nodes[:3]


def test_healthy_rerank_returns_reranked_ordering():
    nodes = tuple(_mk_node(f"node-{i}") for i in range(5))
    fake_module = MagicMock()
    fake_ranker_instance = MagicMock()
    fake_ranker_instance.rerank.return_value = [
        {"id": 3, "score": 0.91},
        {"id": 1, "score": 0.82},
        {"id": 0, "score": 0.55},
    ]
    fake_module.Ranker.return_value = fake_ranker_instance
    fake_module.RerankRequest = lambda query, passages: {"query": query, "passages": passages}

    with patch.dict(sys.modules, {"flashrank": fake_module}):
        outcome = rerankers.rerank_top_k("q?", nodes, top_k=3)
    assert outcome.bypassed is False
    assert outcome.reason == "reranked"
    assert outcome.nodes == (nodes[3], nodes[1], nodes[0])


def test_latency_budget_triggers_bypass():
    nodes = tuple(_mk_node(f"node-{i}") for i in range(5))
    fake_module = MagicMock()
    fake_ranker_instance = MagicMock()

    def slow_rerank(request):
        time.sleep(0.05)
        return [{"id": 0, "score": 0.9}]

    fake_ranker_instance.rerank.side_effect = slow_rerank
    fake_module.Ranker.return_value = fake_ranker_instance
    fake_module.RerankRequest = lambda query, passages: {"query": query, "passages": passages}

    with patch.dict(sys.modules, {"flashrank": fake_module}):
        outcome = rerankers.rerank_top_k("q?", nodes, top_k=3, latency_budget_ms=10)
    assert outcome.bypassed is True
    assert outcome.reason.startswith("latency_exceeded_")
    assert outcome.nodes == nodes[:3]


def test_rerank_call_failure_bypasses_safely():
    nodes = tuple(_mk_node(f"node-{i}") for i in range(3))
    fake_module = MagicMock()
    fake_ranker_instance = MagicMock()
    fake_ranker_instance.rerank.side_effect = RuntimeError("model crashed")
    fake_module.Ranker.return_value = fake_ranker_instance
    fake_module.RerankRequest = lambda query, passages: {"query": query, "passages": passages}

    with patch.dict(sys.modules, {"flashrank": fake_module}):
        outcome = rerankers.rerank_top_k("q?", nodes, top_k=2)
    assert outcome.bypassed is True
    assert outcome.reason == "rerank_call_failed"
    assert outcome.nodes == nodes[:2]


def test_reranker_singleton_reused_across_calls():
    nodes = tuple(_mk_node(f"n-{i}") for i in range(3))
    fake_module = MagicMock()
    fake_ranker_instance = MagicMock()
    fake_ranker_instance.rerank.return_value = [{"id": 0, "score": 0.5}]
    fake_module.Ranker.return_value = fake_ranker_instance
    fake_module.RerankRequest = lambda query, passages: {"query": query, "passages": passages}

    with patch.dict(sys.modules, {"flashrank": fake_module}):
        rerankers.rerank_top_k("q1", nodes, top_k=1)
        rerankers.rerank_top_k("q2", nodes, top_k=1)
    assert fake_module.Ranker.call_count == 1
