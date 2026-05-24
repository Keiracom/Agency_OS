"""Tests for src/keiracom_system/embeddings/tei_client.py — Phase 2 build wave 2 item 2.

Two test surfaces:

  (A) Unit tests with injected HTTP transports — fast, no network, run in all CI.
      Cover: happy-path embed, healthy(), info(), error paths (transport / HTTP
      status / shape mismatch / dimension mismatch / non-list input / empty input),
      verify_model_lineage positive + negative.

  (B) Integration test against live TEI sidecar — skipped unless
      KEIRACOM_TEI_INTEGRATION=1 env is set (same opt-in pattern as
      tests/governance/test_ceo_memory_context_constraint.py). Runs against
      whatever TEI URL is exposed (defaults to http://localhost:8080).

Negative-path discipline per Aiden's gate-validator gate
(feedback_negative_path_test_before_approve): client validates response shape +
dimension on every call — these guards need explicit negative coverage on
synthetic offenders before approve.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.keiracom_system.embeddings.tei_client import (  # noqa: E402
    DEFAULT_MODEL_DIM,
    EXPECTED_MODEL_ID,
    TEIClient,
    TEIClientError,
    _HTTPResponse,
)


def _resp(status: int, body) -> _HTTPResponse:
    """Build a fake _HTTPResponse for injection."""
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode("utf-8")
    elif isinstance(body, str):
        body = body.encode("utf-8")
    return _HTTPResponse(status_code=status, body=body)


def _make_post(response: _HTTPResponse | Exception):
    """Build an http_post stub that returns `response` (or raises if Exception)."""
    calls: list[tuple] = []

    def _post(url: str, payload: dict, timeout: float) -> _HTTPResponse:
        calls.append((url, payload, timeout))
        if isinstance(response, Exception):
            raise response
        return response

    _post.calls = calls  # type: ignore[attr-defined]
    return _post


def _make_get(response: _HTTPResponse | Exception):
    calls: list[tuple] = []

    def _get(url: str, timeout: float) -> _HTTPResponse:
        calls.append((url, timeout))
        if isinstance(response, Exception):
            raise response
        return response

    _get.calls = calls  # type: ignore[attr-defined]
    return _get


# ─────────────────────────────────────────────────────────────────────────────
# (A) Unit tests — injected HTTP transports.
# ─────────────────────────────────────────────────────────────────────────────


def test_embed_happy_path_returns_vectors():
    """(1) happy-path: 2 inputs → 2 384-dim vectors."""
    vectors = [[0.1] * 384, [0.2] * 384]
    post = _make_post(_resp(200, vectors))
    client = TEIClient(base_url="http://test", http_post=post)
    result = client.embed(["one", "two"])
    assert result == vectors
    assert len(post.calls) == 1  # type: ignore[attr-defined]
    url, payload, _ = post.calls[0]  # type: ignore[attr-defined]
    assert url == "http://test/embed"
    assert payload == {"inputs": ["one", "two"]}


def test_embed_empty_input_returns_empty_no_http_call():
    """(2) empty input → empty output, no HTTP call (avoid useless network)."""
    post = _make_post(_resp(500, "should not be called"))
    client = TEIClient(base_url="http://test", http_post=post)
    assert client.embed([]) == []
    assert len(post.calls) == 0  # type: ignore[attr-defined]


def test_embed_non_list_input_raises_client_error():
    """(3) defensive: caller passes wrong type → TEIClientError (no HTTP call)."""
    post = _make_post(_resp(500, "should not be called"))
    client = TEIClient(base_url="http://test", http_post=post)
    # Route bad input through `Any` so static type checkers (and Sonar S5655)
    # don't flag the intentionally-wrong type that the runtime guard catches.
    bad_input: Any = "not-a-list"
    with pytest.raises(TEIClientError, match="texts must be list"):
        client.embed(bad_input)
    assert len(post.calls) == 0  # type: ignore[attr-defined]


def test_embed_http_500_raises_client_error_with_body_preview():
    """(4) HTTP 500 → TEIClientError with status + body preview."""
    post = _make_post(_resp(500, "internal server error"))
    client = TEIClient(base_url="http://test", http_post=post)
    with pytest.raises(TEIClientError, match="HTTP 500.*internal server error"):
        client.embed(["text"])


def test_embed_response_count_mismatch_raises_client_error():
    """(5) server returns wrong number of vectors → TEIClientError."""
    # Asked for 2, got 1 — shape mismatch.
    post = _make_post(_resp(200, [[0.1] * 384]))
    client = TEIClient(base_url="http://test", http_post=post)
    with pytest.raises(TEIClientError, match="response shape mismatch"):
        client.embed(["one", "two"])


def test_embed_wrong_dimension_raises_client_error():
    """(6) server returns 768-dim vectors but client expects 384 → TEIClientError.

    Catches accidental model swap on TEI side (different model = different
    dimension = silent schema drift on Hindsight's pgvector column).
    """
    post = _make_post(_resp(200, [[0.1] * 768]))
    client = TEIClient(base_url="http://test", http_post=post, expected_dim=384)
    with pytest.raises(TEIClientError, match="dimension 768.*expected 384"):
        client.embed(["text"])


def test_embed_transport_error_wrapped_as_client_error():
    """(7) underlying httpx/urllib error → TEIClientError (not raw exception)."""
    post = _make_post(ConnectionRefusedError("no listener"))
    client = TEIClient(base_url="http://test", http_post=post)
    with pytest.raises(TEIClientError, match="transport error"):
        client.embed(["text"])


def test_healthy_returns_true_on_200():
    """(8) GET /health → 200 → healthy() True."""
    get = _make_get(_resp(200, b"ok"))
    client = TEIClient(base_url="http://test", http_get=get)
    assert client.healthy() is True
    assert get.calls[0][0] == "http://test/health"  # type: ignore[attr-defined]


def test_healthy_returns_false_on_non_200_or_error():
    """(9) /health 503 or transport error → healthy() False (fail-closed)."""
    # 503 case
    client_503 = TEIClient(base_url="http://test", http_get=_make_get(_resp(503, b"")))
    assert client_503.healthy() is False
    # Transport error case
    client_err = TEIClient(base_url="http://test", http_get=_make_get(ConnectionRefusedError("x")))
    assert client_err.healthy() is False


def test_info_returns_model_metadata():
    """(10) GET /info → JSON dict {model_id, ...}."""
    get = _make_get(_resp(200, {"model_id": EXPECTED_MODEL_ID, "model_type": "embedding"}))
    client = TEIClient(base_url="http://test", http_get=get)
    info = client.info()
    assert info["model_id"] == EXPECTED_MODEL_ID
    assert info["model_type"] == "embedding"


def test_info_http_error_raises_client_error():
    """(11) /info HTTP 500 → TEIClientError."""
    get = _make_get(_resp(500, "boom"))
    client = TEIClient(base_url="http://test", http_get=get)
    with pytest.raises(TEIClientError, match="HTTP 500"):
        client.info()


def test_verify_model_lineage_passes_on_expected_model():
    """(12) verify_model_lineage no-raise when /info reports expected model_id."""
    get = _make_get(_resp(200, {"model_id": EXPECTED_MODEL_ID}))
    client = TEIClient(base_url="http://test", http_get=get)
    client.verify_model_lineage()  # should not raise


def test_verify_model_lineage_raises_on_mismatch():
    """(13) verify_model_lineage raises when TEI loaded wrong model.

    Defence-in-depth: catches accidental docker-compose model swap. Vector
    lineage divergence would silently break Hindsight's pgvector dimension.
    """
    get = _make_get(_resp(200, {"model_id": "BAAI/bge-large-en-v1.5"}))  # 1024-dim, not 384
    client = TEIClient(base_url="http://test", http_get=get)
    with pytest.raises(TEIClientError, match="lineage diverged"):
        client.verify_model_lineage()


def test_client_defaults_match_canonical_key():
    """(14) constructor defaults align with canonical key position 1.

    Pins the dimension constant + expected model id against the
    ceo:memory_abstraction_layer_v1 contract to catch silent regressions.
    """
    assert DEFAULT_MODEL_DIM == 384  # BGE-small-en-v1.5
    assert EXPECTED_MODEL_ID == "BAAI/bge-small-en-v1.5"
    client = TEIClient()  # all defaults
    assert client.dimension == 384
    assert client.base_url == "http://embed:80"


# ─────────────────────────────────────────────────────────────────────────────
# (B) Integration test — live TEI sidecar. Opt-in via env.
# ─────────────────────────────────────────────────────────────────────────────


_INTEGRATION_ENABLED = os.environ.get("KEIRACOM_TEI_INTEGRATION", "").strip() == "1"


@pytest.mark.skipif(
    not _INTEGRATION_ENABLED,
    reason="KEIRACOM_TEI_INTEGRATION=1 not set — live TEI sidecar test skipped",
)
def test_integration_live_tei_embed_round_trip():
    """(integration) — real TEI sidecar embed round-trip.

    Requires: TEI container running (bash infra/.../install_tei_sidecar.sh).
    Verifies the full path real consumer code takes.
    """
    base_url = os.environ.get("KEIRACOM_TEI_URL", "http://localhost:8080")
    client = TEIClient(base_url=base_url)
    assert client.healthy(), f"TEI not healthy at {base_url}"
    client.verify_model_lineage()  # raises if not BGE-small-en-v1.5
    vectors = client.embed(["hello world", "embeddings integration test"])
    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)
    assert all(isinstance(f, float) for f in vectors[0])
