"""Wave 3 (Agency_OS-0thg) — orchestrator ↔ cross-encoder reranker sidecar wiring.

Locks the contract that replaces the in-process FlashRank path with
RerankerClient (TEI /rerank). Covers:
  - flag off (default): raw-ANN passthrough, bypass_rerank=True
  - flag on + healthy sidecar: reorders by cross-encoder score, scores replace
    the (0.0) ANN scores, reason="sidecar_reranked"
  - flag on + sidecar error: fail-open to raw-ANN, bypass_rerank=True
  - sidecar returns fewer than k_returned: raw-ANN backfill preserves k
  - p95 latency < 200ms over the fixture (Aiden Wave 3 acceptance gate)

The sidecar is exercised through a real RerankerClient with an injected HTTP
transport, so the client's own parse/sort/validate path runs too — no live
TEI container needed. _gather_ann_pool is stubbed so no live Hindsight needed.
"""

from __future__ import annotations

import json
import time

import pytest

from src.keiracom_system.reranker import RerankerClient
from src.keiracom_system.reranker.reranker_client import _HTTPResponse
from src.retrieval import orchestrator
from src.retrieval.orchestrator import RetrievedNode

TENANT = orchestrator.FLEET_TENANT_SLUG


def _node(i: int) -> RetrievedNode:
    return RetrievedNode(
        text=f"candidate text {i}",
        score=0.0,  # Hindsight recall exposes no numeric score (see baseline doc)
        metadata={"chunk_id": f"chunk-{i}"},
        collection="Decisions",
    )


def _pool(n: int) -> list[RetrievedNode]:
    return [_node(i) for i in range(n)]


def _client_returning(scores_by_index: dict[int, float]) -> RerankerClient:
    """Real RerankerClient whose injected transport returns a TEI /rerank body.

    `scores_by_index` maps a pool index → cross-encoder score; the client
    sorts by score desc and truncates to top_k, exactly as the live sidecar.
    """

    def _fake_post(url: str, payload: dict, timeout: float) -> _HTTPResponse:
        body = [{"index": idx, "score": score} for idx, score in scores_by_index.items()]
        return _HTTPResponse(status_code=200, body=json.dumps(body).encode("utf-8"))

    return RerankerClient(http_post=_fake_post)


def _client_raising() -> RerankerClient:
    def _boom(url: str, payload: dict, timeout: float) -> _HTTPResponse:
        raise ConnectionError("sidecar down")

    return RerankerClient(http_post=_boom)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Reset the module client + force a known pool for every test."""
    monkeypatch.setattr(orchestrator, "_reranker_client", None)
    monkeypatch.setattr(
        orchestrator,
        "_gather_ann_pool",
        lambda *a, **k: _pool(6),
    )
    yield
    orchestrator._set_reranker_client(None)


def test_flag_off_is_raw_ann_passthrough(monkeypatch):
    monkeypatch.setattr(orchestrator, "reranker_enabled", False)
    out = orchestrator.retrieve_with_outcome("q", ("Decisions",), k_returned=5, tenant_id=TENANT)
    assert out.bypass_rerank is True
    assert out.rerank_reason == "reranker_flag_off"
    assert [n.metadata["chunk_id"] for n in out.nodes] == [f"chunk-{i}" for i in range(5)]


def test_flag_on_reorders_by_sidecar_score(monkeypatch):
    monkeypatch.setattr(orchestrator, "reranker_enabled", True)
    # Cross-encoder prefers index 3, then 1, 5, 0, 2 (index 4 lowest, dropped).
    scores = {0: 0.40, 1: 0.80, 2: 0.20, 3: 0.95, 4: 0.05, 5: 0.60}
    orchestrator._set_reranker_client(_client_returning(scores))
    out = orchestrator.retrieve_with_outcome("q", ("Decisions",), k_returned=5, tenant_id=TENANT)
    assert out.bypass_rerank is False
    assert out.rerank_reason == "sidecar_reranked"
    assert [n.metadata["chunk_id"] for n in out.nodes] == [
        "chunk-3",
        "chunk-1",
        "chunk-5",
        "chunk-0",
        "chunk-2",
    ]
    # Sidecar relevance scores replace the 0.0 ANN scores on surviving nodes.
    assert out.nodes[0].score == pytest.approx(0.95)
    assert out.nodes[1].score == pytest.approx(0.80)


def test_sidecar_error_fails_open_to_raw_ann(monkeypatch):
    monkeypatch.setattr(orchestrator, "reranker_enabled", True)
    orchestrator._set_reranker_client(_client_raising())
    out = orchestrator.retrieve_with_outcome("q", ("Decisions",), k_returned=5, tenant_id=TENANT)
    assert out.bypass_rerank is True
    assert out.rerank_reason == "sidecar_unavailable"
    assert [n.metadata["chunk_id"] for n in out.nodes] == [f"chunk-{i}" for i in range(5)]


def test_partial_sidecar_result_backfills_to_k(monkeypatch):
    monkeypatch.setattr(orchestrator, "reranker_enabled", True)
    # Sidecar only scores two candidates; the rest backfill in raw-ANN order.
    orchestrator._set_reranker_client(_client_returning({4: 0.9, 2: 0.7}))
    out = orchestrator.retrieve_with_outcome("q", ("Decisions",), k_returned=5, tenant_id=TENANT)
    assert out.bypass_rerank is False
    assert len(out.nodes) == 5
    keys = [n.metadata["chunk_id"] for n in out.nodes]
    assert keys[:2] == ["chunk-4", "chunk-2"]  # reranked
    assert keys[2:] == ["chunk-0", "chunk-1", "chunk-3"]  # raw-ANN backfill, no dupes
    assert len(set(keys)) == 5


def test_p95_latency_under_200ms(monkeypatch):
    """Aiden Wave 3 acceptance gate: p95 of the rerank path < 200ms.

    Measures the client + orchestrator wiring overhead with an instant
    transport — it guards the mapping/parse cost, NOT the sidecar model's
    own inference SLA (that is the sidecar's separate budget).
    """
    monkeypatch.setattr(orchestrator, "reranker_enabled", True)
    scores = {0: 0.4, 1: 0.8, 2: 0.2, 3: 0.95, 4: 0.05, 5: 0.6}
    orchestrator._set_reranker_client(_client_returning(scores))

    samples_ms: list[float] = []
    for _ in range(200):
        started = time.perf_counter()
        orchestrator.retrieve_with_outcome("q", ("Decisions",), k_returned=5, tenant_id=TENANT)
        samples_ms.append((time.perf_counter() - started) * 1000)

    samples_ms.sort()
    p95 = samples_ms[int(0.95 * len(samples_ms)) - 1]
    assert p95 < 200.0, f"p95 rerank-path latency {p95:.2f}ms exceeds 200ms budget"
