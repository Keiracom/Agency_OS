"""Tests for RerankerClient — Wave 2 dispatch Agency_OS-0thg.

Mirrors tests/keiracom_system/embeddings/test_tei_client.py: unit tests use
injected HTTP transports so no live TEI container is required. The
integration test (skip unless KEIRACOM_RERANKER_INTEGRATION=1) hits a real
running sidecar — same opt-in pattern as the embeddings tests.
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest

from src.keiracom_system.reranker import (
    DEFAULT_BASE_URL,
    EXPECTED_MODEL_ID,
    RerankClientError,
    RerankerClient,
    RerankHit,
)
from src.keiracom_system.reranker.reranker_client import _HTTPResponse


def _ok(body: Any) -> _HTTPResponse:
    return _HTTPResponse(status_code=200, body=json.dumps(body).encode())


def _err(status: int, body: str = "") -> _HTTPResponse:
    return _HTTPResponse(status_code=status, body=body.encode())


# ---------- healthy ----------


def test_healthy_true_on_200():
    c = RerankerClient(http_get=lambda url, t: _ok(None))
    assert c.healthy() is True


def test_healthy_false_on_500():
    c = RerankerClient(http_get=lambda url, t: _err(500, "boom"))
    assert c.healthy() is False


def test_healthy_false_on_transport_error():
    def raises(url: str, t: float) -> _HTTPResponse:
        raise RuntimeError("connection refused")

    c = RerankerClient(http_get=raises)
    assert c.healthy() is False


# ---------- info + verify_model_lineage ----------


def test_info_returns_payload():
    payload = {"model_id": EXPECTED_MODEL_ID, "model_type": "Reranker"}
    c = RerankerClient(http_get=lambda url, t: _ok(payload))
    assert c.info() == payload


def test_info_raises_on_5xx():
    c = RerankerClient(http_get=lambda url, t: _err(503, "down"))
    with pytest.raises(RerankClientError, match="503"):
        c.info()


def test_verify_model_lineage_ok():
    c = RerankerClient(http_get=lambda url, t: _ok({"model_id": EXPECTED_MODEL_ID}))
    c.verify_model_lineage()  # no raise


def test_verify_model_lineage_mismatch():
    c = RerankerClient(http_get=lambda url, t: _ok({"model_id": "other/model"}))
    with pytest.raises(RerankClientError, match="reranker loaded"):
        c.verify_model_lineage()


# ---------- rerank input validation ----------


def test_rerank_empty_texts_returns_empty():
    c = RerankerClient()
    assert c.rerank("query", []) == []


def test_rerank_rejects_empty_query():
    c = RerankerClient()
    with pytest.raises(RerankClientError, match="non-empty string"):
        c.rerank("", ["doc"])


def test_rerank_rejects_non_str_in_texts():
    c = RerankerClient()
    with pytest.raises(RerankClientError, match="list\\[str\\]"):
        c.rerank("q", ["ok", 42])  # type: ignore[list-item]


def test_rerank_rejects_top_k_zero():
    c = RerankerClient()
    with pytest.raises(RerankClientError, match="top_k must be >= 1"):
        c.rerank("q", ["doc"], top_k=0)


# ---------- rerank success path ----------


def test_rerank_sorts_by_score_desc_and_limits_top_k():
    response = [
        {"index": 0, "score": 0.1},
        {"index": 1, "score": 0.9},
        {"index": 2, "score": 0.5},
    ]
    posted: dict[str, Any] = {}

    def post(url: str, payload: dict[str, Any], t: float) -> _HTTPResponse:
        posted["url"] = url
        posted["payload"] = payload
        return _ok(response)

    c = RerankerClient(http_post=post)
    hits = c.rerank("query", ["a", "b", "c"], top_k=2)
    assert hits == [RerankHit(index=1, score=0.9), RerankHit(index=2, score=0.5)]
    assert posted["url"].endswith("/rerank")
    assert posted["payload"]["query"] == "query"
    assert posted["payload"]["texts"] == ["a", "b", "c"]


def test_rerank_returns_text_field_when_returned():
    response = [{"index": 0, "score": 0.7, "text": "the doc"}]
    c = RerankerClient(http_post=lambda url, p, t: _ok(response))
    hits = c.rerank("q", ["the doc"], return_text=True)
    assert hits == [RerankHit(index=0, score=0.7, text="the doc")]


# ---------- rerank error paths ----------


def test_rerank_raises_on_5xx():
    c = RerankerClient(http_post=lambda url, p, t: _err(502, "bad gateway"))
    with pytest.raises(RerankClientError, match="502"):
        c.rerank("q", ["doc"])


def test_rerank_raises_on_non_list_response():
    c = RerankerClient(http_post=lambda url, p, t: _ok({"unexpected": "shape"}))
    with pytest.raises(RerankClientError, match="not a list"):
        c.rerank("q", ["doc"])


def test_rerank_raises_on_out_of_range_index():
    response = [{"index": 5, "score": 0.5}]
    c = RerankerClient(http_post=lambda url, p, t: _ok(response))
    with pytest.raises(RerankClientError, match="out of range"):
        c.rerank("q", ["doc"])


def test_rerank_raises_on_non_numeric_score():
    response = [{"index": 0, "score": "nope"}]
    c = RerankerClient(http_post=lambda url, p, t: _ok(response))
    with pytest.raises(RerankClientError, match="not numeric"):
        c.rerank("q", ["doc"])


def test_rerank_raises_on_transport_error():
    def raises(url: str, payload: dict[str, Any], t: float) -> _HTTPResponse:
        raise ConnectionError("dropped")

    c = RerankerClient(http_post=raises)
    with pytest.raises(RerankClientError, match="transport error"):
        c.rerank("q", ["doc"])


# ---------- defaults ----------


def test_default_base_url_constant():
    assert DEFAULT_BASE_URL == "http://reranker:80"


def test_default_expected_model_id_constant():
    assert EXPECTED_MODEL_ID == "BAAI/bge-reranker-base"


# ---------- live integration test (opt-in) ----------


@pytest.mark.skipif(
    os.environ.get("KEIRACOM_RERANKER_INTEGRATION") != "1",
    reason="set KEIRACOM_RERANKER_INTEGRATION=1 to run against a live sidecar",
)
def test_integration_rerank_round_trip():
    url = os.environ.get("KEIRACOM_RERANKER_URL", "http://localhost:8090")
    c = RerankerClient(base_url=url)
    assert c.healthy(), "reranker sidecar not healthy at " + url
    c.verify_model_lineage()
    hits = c.rerank(
        "what is rust",
        ["rust is a programming language", "cats meow", "rustic furniture"],
        top_k=2,
    )
    assert len(hits) == 2
    assert hits[0].score >= hits[1].score
