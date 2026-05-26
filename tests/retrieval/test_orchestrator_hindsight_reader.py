"""A3-c2 step 5-B reader cutover (Agency_OS-0zv1) — locks the new contract.

Covers:
- HINDSIGHT_BANK_BY_CLASS parity with the canonical indexer_base.CLASS_TO_BANK
  mapping (catches drift if a future PR adds/removes a class on one side
  only).
- _hindsight_recall: POST shape + happy path + alt response keys.
- _gather_ann_pool: unmapped collection skipped, recall failure swallowed
  per-collection, RetrievedNode build correctness.

Public-API contract (RetrievedNode / RetrievalOutcome / retrieve_with_outcome
shape) is locked by the pre-existing tests in test_agent_query.py + test_
source_id_resolution.py + test_rerankers.py; those continue to pass on the
cutover.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from src.retrieval import orchestrator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _import_indexer_base():
    """Load scripts/orchestrator/indexer_base.py as a module so we can read its
    canonical CLASS_TO_BANK without a sys.path hack baked into the import."""
    path = REPO_ROOT / "scripts" / "orchestrator" / "indexer_base.py"
    spec = importlib.util.spec_from_file_location("_indexer_base_for_parity", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_indexer_base_for_parity"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_bank_mapping_parity_with_indexer_base_canonical():
    """HINDSIGHT_BANK_BY_CLASS (read-side, src/) must equal CLASS_TO_BANK
    (write-side, scripts/). If they drift, dual-write data won't be readable
    by the cutover — silent data loss for the bd-claim hot path."""
    canonical = _import_indexer_base().CLASS_TO_BANK
    assert canonical == orchestrator.HINDSIGHT_BANK_BY_CLASS


def test_hindsight_recall_posts_to_correct_endpoint(monkeypatch):
    captured = []

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def read(self):
            return b'{"memories": [{"content": "x", "score": 0.9}]}'

    def _fake_urlopen(req, timeout=None):
        captured.append(
            {
                "url": req.full_url,
                "method": req.get_method(),
                "body": json.loads(req.data.decode()),
                "timeout": timeout,
            }
        )
        return _FakeResp()

    monkeypatch.setattr(orchestrator.urlrequest, "urlopen", _fake_urlopen)
    out = orchestrator._hindsight_recall("anchor query", "fleet_decisions", top_k=5)
    assert len(captured) == 1
    assert captured[0]["url"].endswith("/v1/default/banks/fleet_decisions/memories/recall")
    assert captured[0]["method"] == "POST"
    assert captured[0]["body"] == {"query": "anchor query", "max_tokens": 2000, "top_k": 5}
    assert out == [{"content": "x", "score": 0.9}]


def test_hindsight_recall_accepts_alt_results_key(monkeypatch):
    """Some Hindsight response shapes nest under 'results' instead of 'memories'."""

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def read(self):
            return b'{"results": [{"content": "y"}]}'

    monkeypatch.setattr(orchestrator.urlrequest, "urlopen", lambda req, timeout=None: _FakeResp())
    out = orchestrator._hindsight_recall("q", "fleet_keis", top_k=3)
    assert out == [{"content": "y"}]


def test_hindsight_recall_empty_response_returns_empty_list(monkeypatch):
    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def read(self):
            return b"{}"

    monkeypatch.setattr(orchestrator.urlrequest, "urlopen", lambda req, timeout=None: _FakeResp())
    assert orchestrator._hindsight_recall("q", "fleet_decisions", top_k=5) == []


def test_gather_ann_pool_skips_unmapped_collection(monkeypatch):
    """Sessions + Global_governance_patterns are not yet mapped (parallel
    Agency_OS-9u2m + Agency_OS-x0p7). Read path should skip them gracefully
    (warn + continue) rather than crash or call Hindsight with a missing bank."""
    called = []

    def _spy_recall(text, bank_id, *, top_k):
        called.append(bank_id)
        return []

    monkeypatch.setattr(orchestrator, "_hindsight_recall", _spy_recall)
    pool = orchestrator._gather_ann_pool(
        text="q",
        collections=("Sessions", "Decisions"),
        k_initial=5,
        weaviate_client=None,
    )
    assert called == ["fleet_decisions"]  # Sessions skipped, Decisions called
    assert pool == []  # spy returned [] for Decisions


def test_gather_ann_pool_swallows_per_collection_failure(monkeypatch):
    """One collection raising must NOT prevent the others from being recalled —
    matches the pre-cutover behavior (failure of one Weaviate collection
    didn't stop the others)."""
    calls = []

    def _flaky_recall(text, bank_id, *, top_k):
        calls.append(bank_id)
        if bank_id == "fleet_decisions":
            raise RuntimeError("simulated failure")
        return [{"content": "ok-from-keis", "score": 0.7}]

    monkeypatch.setattr(orchestrator, "_hindsight_recall", _flaky_recall)
    pool = orchestrator._gather_ann_pool(
        text="q",
        collections=("Decisions", "Keis"),
        k_initial=5,
        weaviate_client=None,
    )
    assert calls == ["fleet_decisions", "fleet_keis"]
    assert len(pool) == 1
    assert pool[0].text == "ok-from-keis"
    assert pool[0].collection == "Keis"


def test_gather_ann_pool_builds_retrieved_nodes_with_correct_collection_tag(monkeypatch):
    """Each returned memory must carry the WEAVIATE class name (not bank id)
    as its `.collection` field so the downstream citation chain stays
    consistent with the pre-cutover identity."""

    def _stub_recall(text, bank_id, *, top_k):
        return [
            {"content": f"from-{bank_id}-1", "score": 0.8, "metadata": {"src": bank_id}},
            {"content": f"from-{bank_id}-2", "score": 0.6, "metadata": {"src": bank_id}},
        ]

    monkeypatch.setattr(orchestrator, "_hindsight_recall", _stub_recall)
    pool = orchestrator._gather_ann_pool(
        text="q",
        collections=("Decisions", "Discoveries"),
        k_initial=5,
        weaviate_client=None,
    )
    assert len(pool) == 4
    collections_seen = {n.collection for n in pool}
    assert collections_seen == {"Decisions", "Discoveries"}
    # Sorted desc by score — both collections' top items lead.
    assert pool[0].score == pytest.approx(0.8)
    assert pool[-1].score == pytest.approx(0.6)


def test_gather_ann_pool_accepts_alt_text_and_relevance_keys(monkeypatch):
    """Memories may carry `text` instead of `content` and `relevance` instead
    of `score` depending on Hindsight response shape. Both keys supported."""

    def _stub_recall(text, bank_id, *, top_k):
        return [{"text": "alt-shape", "relevance": 0.42, "metadata": None}]

    monkeypatch.setattr(orchestrator, "_hindsight_recall", _stub_recall)
    pool = orchestrator._gather_ann_pool(
        text="q",
        collections=("Decisions",),
        k_initial=5,
        weaviate_client=None,
    )
    assert len(pool) == 1
    assert pool[0].text == "alt-shape"
    assert pool[0].score == pytest.approx(0.42)
    assert pool[0].metadata == {}


def test_retrieve_with_outcome_returns_empty_pool_outcome_on_no_memories(monkeypatch):
    """Public-API contract: empty pool surfaces (RetrievalOutcome((),
    bypass_rerank=False, "empty_pool", 0)) — matches the pre-cutover shape so
    agent_query.query()'s anti-hallucination guard fires identically."""
    monkeypatch.setattr(orchestrator, "_hindsight_recall", lambda *a, **kw: [])
    outcome = orchestrator.retrieve_with_outcome(
        "anchor", ("Decisions", "Discoveries", "Keis"), rerank=True
    )
    assert outcome.nodes == ()
    assert outcome.bypass_rerank is False
    assert outcome.rerank_reason == "empty_pool"


def test_retrieve_with_outcome_no_longer_opens_weaviate_connection(monkeypatch):
    """Verify the dead-weight Weaviate connect/close was removed — calling
    retrieve_with_outcome should NEVER hit weaviate_store._connect_client()
    on the cutover path. Catches a future regression that re-adds it."""
    connect_calls = []
    monkeypatch.setattr(
        orchestrator.weaviate_store,
        "_connect_client",
        lambda *a, **kw: connect_calls.append(1),
    )
    monkeypatch.setattr(orchestrator, "_hindsight_recall", lambda *a, **kw: [])
    orchestrator.retrieve_with_outcome("q", ("Decisions",))
    assert connect_calls == []
