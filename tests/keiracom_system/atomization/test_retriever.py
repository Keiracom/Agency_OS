"""MalRetriever unit tests — Week 2 atomization pilot."""

from typing import Any
from uuid import uuid4

import pytest

from src.keiracom_system.atomization.retriever import (
    DEFAULT_SCORE_THRESHOLD,
    MAX_TOP_K,
    MalRetriever,
    RetrieverError,
)
from src.keiracom_system.atomization.schema import AtomV1
from src.keiracom_system.embeddings.tei_client import TEIClient, _HTTPResponse


def _fake_tei() -> TEIClient:
    def fake_post(url, payload, timeout):
        n = len(payload["inputs"])
        body = (
            b"["
            + b",".join(b"[" + b",".join(b"0.1" for _ in range(384)) + b"]" for _ in range(n))
            + b"]"
        )
        return _HTTPResponse(200, body)

    def fake_get(url, timeout):
        return _HTTPResponse(200, b'{"status": "ok"}')

    return TEIClient(http_get=fake_get, http_post=fake_post)


class _FakeStore:
    """Drop-in AtomStore replacement returning canned atoms."""

    def __init__(self, *, tenant_id: str, atoms: list[AtomV1]):
        self._tenant_id = tenant_id
        self._atoms = atoms
        self.retrieve_calls: list[tuple[str, int]] = []

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def retrieve_top_k(self, query_text: str, top_k: int = 10) -> list[AtomV1]:
        self.retrieve_calls.append((query_text, top_k))
        return self._atoms[:top_k]


def _make_atom(
    *,
    tenant_id,
    content: str = "test content",
    composition_tags: dict[str, Any] | None = None,
) -> AtomV1:
    return AtomV1(
        atom_id=uuid4(),
        tenant_id=tenant_id,
        trigger_condition={"kind": "request_shape", "params": {"x": 1}},
        content=content,
        anti_pattern=None,
        example=None,
        provenance={
            "source": "test",
            "freshness": "2026-05-26T11:00:00Z",
            "confidence": 0.9,
            "last_validated": "2026-05-26T11:00:00Z",
        },
        composition_tags=composition_tags or {},
    )


# ---- Input validation ------------------------------------------------------


def test_retrieve_rejects_empty_query_text():
    tid = uuid4()
    store = _FakeStore(tenant_id=str(tid), atoms=[])
    retriever = MalRetriever(store=store)
    with pytest.raises(RetrieverError, match="query_text must be non-empty"):
        retriever.retrieve(query_text="", top_k=5)


def test_retrieve_rejects_non_positive_top_k():
    tid = uuid4()
    store = _FakeStore(tenant_id=str(tid), atoms=[])
    retriever = MalRetriever(store=store)
    with pytest.raises(RetrieverError, match="top_k must be > 0"):
        retriever.retrieve(query_text="q", top_k=0)


def test_retrieve_rejects_excessive_top_k():
    tid = uuid4()
    store = _FakeStore(tenant_id=str(tid), atoms=[])
    retriever = MalRetriever(store=store)
    with pytest.raises(RetrieverError, match=f"exceeds MAX_TOP_K {MAX_TOP_K}"):
        retriever.retrieve(query_text="q", top_k=MAX_TOP_K + 1)


# ---- Tenant + delegation ---------------------------------------------------


def test_retriever_tenant_id_property():
    tid = uuid4()
    store = _FakeStore(tenant_id=str(tid), atoms=[])
    retriever = MalRetriever(store=store)
    assert retriever.tenant_id == str(tid)


def test_retrieve_calls_atom_store_with_top_k():
    tid = uuid4()
    store = _FakeStore(tenant_id=str(tid), atoms=[])
    retriever = MalRetriever(store=store)
    retriever.retrieve(query_text="anchor", top_k=7)
    assert store.retrieve_calls == [("anchor", 7)]


# ---- Result shape + scoring ------------------------------------------------


def test_retrieve_returns_retrieval_results_ordered_by_score():
    tid = uuid4()
    atoms = [_make_atom(tenant_id=tid, content=f"atom {i}") for i in range(3)]
    store = _FakeStore(tenant_id=str(tid), atoms=atoms)
    retriever = MalRetriever(store=store)
    results = retriever.retrieve(query_text="anchor", top_k=3)
    assert len(results) == 3
    # Placeholder scoring is 1/(rank+1); should be monotonically decreasing.
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_returns_empty_when_store_empty():
    tid = uuid4()
    store = _FakeStore(tenant_id=str(tid), atoms=[])
    retriever = MalRetriever(store=store)
    assert retriever.retrieve(query_text="q", top_k=5) == []


# ---- Score threshold filter -----------------------------------------------


def test_retrieve_filters_by_score_threshold():
    tid = uuid4()
    # 5 atoms → scores 1.0, 0.5, 0.333, 0.25, 0.2
    atoms = [_make_atom(tenant_id=tid, content=f"a{i}") for i in range(5)]
    store = _FakeStore(tenant_id=str(tid), atoms=atoms)
    retriever = MalRetriever(store=store)
    # Threshold 0.3 should keep ranks 0, 1, 2 (scores 1.0, 0.5, 0.333)
    results = retriever.retrieve(query_text="q", top_k=5, score_threshold=0.3)
    assert len(results) == 3


def test_retrieve_with_min_score_convenience_wrapper():
    tid = uuid4()
    atoms = [_make_atom(tenant_id=tid, content=f"a{i}") for i in range(3)]
    store = _FakeStore(tenant_id=str(tid), atoms=atoms)
    retriever = MalRetriever(store=store)
    r1 = retriever.retrieve(query_text="q", top_k=3, score_threshold=0.5)
    r2 = retriever.retrieve_with_min_score(query_text="q", top_k=3, min_score=0.5)
    assert len(r1) == len(r2)


def test_default_score_threshold_does_not_filter():
    tid = uuid4()
    atoms = [_make_atom(tenant_id=tid) for _ in range(3)]
    store = _FakeStore(tenant_id=str(tid), atoms=atoms)
    retriever = MalRetriever(store=store)
    results = retriever.retrieve(query_text="q", top_k=3)
    # DEFAULT_SCORE_THRESHOLD=0.0 — all 3 included regardless
    assert len(results) == 3
    assert DEFAULT_SCORE_THRESHOLD == 0.0


# ---- Composition-tag filter -----------------------------------------------


def test_composition_filter_narrows_to_matching_axes():
    tid = uuid4()
    atom_a = _make_atom(
        tenant_id=tid,
        content="sales atom",
        composition_tags={
            "domain": "sales",
            "concern": "compliance",
            "applicable_context": "chat_realtime",
        },
    )
    atom_b = _make_atom(
        tenant_id=tid,
        content="support atom",
        composition_tags={
            "domain": "support",
            "concern": "compliance",
            "applicable_context": "chat_realtime",
        },
    )
    store = _FakeStore(tenant_id=str(tid), atoms=[atom_a, atom_b])
    retriever = MalRetriever(store=store)
    results = retriever.retrieve(query_text="q", top_k=5, composition_filter={"domain": "sales"})
    assert len(results) == 1
    assert results[0].atom.content == "sales atom"


def test_composition_filter_requires_all_specified_axes():
    tid = uuid4()
    atom = _make_atom(
        tenant_id=tid,
        content="match-or-not",
        composition_tags={
            "domain": "sales",
            "concern": "compliance",
            "applicable_context": "chat_realtime",
        },
    )
    store = _FakeStore(tenant_id=str(tid), atoms=[atom])
    retriever = MalRetriever(store=store)
    # Mismatch on `concern` — excluded.
    results = retriever.retrieve(
        query_text="q",
        top_k=5,
        composition_filter={"domain": "sales", "concern": "performance"},
    )
    assert results == []


def test_composition_filter_unconstrained_axes_ignored():
    tid = uuid4()
    atom = _make_atom(
        tenant_id=tid,
        composition_tags={
            "domain": "sales",
            "concern": "compliance",
            "applicable_context": "chat_realtime",
        },
    )
    store = _FakeStore(tenant_id=str(tid), atoms=[atom])
    retriever = MalRetriever(store=store)
    # Only filter on `domain` — `concern` + `applicable_context` unconstrained.
    results = retriever.retrieve(query_text="q", top_k=5, composition_filter={"domain": "sales"})
    assert len(results) == 1


def test_empty_composition_filter_no_op():
    """Empty dict + None both behave as 'no filter'."""
    tid = uuid4()
    atom = _make_atom(tenant_id=tid, composition_tags={})
    store = _FakeStore(tenant_id=str(tid), atoms=[atom])
    retriever = MalRetriever(store=store)
    assert len(retriever.retrieve(query_text="q", top_k=5)) == 1
    assert len(retriever.retrieve(query_text="q", top_k=5, composition_filter={})) == 1
    assert len(retriever.retrieve(query_text="q", top_k=5, composition_filter=None)) == 1
