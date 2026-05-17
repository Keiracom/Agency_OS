"""KEI-179 — tests for src/dispatcher/app.

The rate limiter + LLM router are mocked at the function-import boundary
so /dispatch can be exercised end-to-end without live Valkey or LiteLLM.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.dispatcher import app as dispatcher_app
from src.dispatcher.app import app
from src.dispatcher.llm_router import LiteLLMRateLimitExhaustedError, LiteLLMRouterError
from src.dispatcher.rate_limiter import RateLimitDecision, RateLimitExceededError


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _decision(allowed: bool = True, current: int = 1, limit: int = 60, retry_after: int = 60):
    return RateLimitDecision(
        allowed=allowed,
        current=current,
        limit=limit,
        window_start_unix=1715904000,
        window_size_s=60,
        retry_after_s=retry_after,
    )


def _llm_response(text: str = "hello"):
    return {
        "model": "claude-sonnet-4-6",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "response_cost": 0.0001,
        "choices": [{"message": {"role": "assistant", "content": text}}],
    }


# ─── /health ──────────────────────────────────────────────────────────────


def test_health_returns_200(client):
    """Liveness probe is no-auth, no-DB — always 200 if process is alive."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "dispatcher"


def test_health_does_not_call_rate_limiter(client):
    """Health probe MUST NOT touch the rate-limiter / Valkey — downstream
    outages can't take the service out of LB rotation."""

    async def boom(*_a, **_kw):
        raise RuntimeError("rate limiter should not be called from /health")

    with patch.object(dispatcher_app, "enforce_for_tenant", boom):
        resp = client.get("/health")
    assert resp.status_code == 200


# ─── /dispatch happy path ─────────────────────────────────────────────────


def test_dispatch_happy_path(client):
    """Rate limit OK + LLM 2xx → 200 with the model response embedded."""

    fake_enforce = AsyncMock(return_value=_decision())

    def fake_forward(*, body, customer_id, task_id, cost_sink=None, **_kw):
        if cost_sink:
            from src.dispatcher.llm_router import CostEvent

            cost_sink(
                CostEvent(
                    customer_id=customer_id,
                    task_id=task_id,
                    model="claude-sonnet-4-6",
                    input_tokens=10,
                    output_tokens=5,
                    cost_aud=0.0001,
                    retry_count=0,
                    duration_ms=42,
                    success=True,
                )
            )
        return _llm_response("hi from dispatcher")

    with (
        patch.object(dispatcher_app, "enforce_for_tenant", fake_enforce),
        patch.object(dispatcher_app, "forward", fake_forward),
    ):
        resp = client.post(
            "/dispatch",
            json={
                "customer_id": "cust-1",
                "task_id": "KEI-179",
                "body": {"model": "claude-sonnet-4-6", "messages": []},
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["customer_id"] == "cust-1"
    assert body["task_id"] == "KEI-179"
    assert body["rate_limit_decision"]["limit"] == 60
    assert body["rate_limit_decision"]["current"] == 1
    assert body["response"]["choices"][0]["message"]["content"] == "hi from dispatcher"


# ─── /dispatch rate-limit branches ────────────────────────────────────────


def test_dispatch_returns_429_when_tenant_rate_limited(client):
    """RateLimitExceededError from enforce_for_tenant → 429 with Retry-After."""

    async def fake_enforce(*, tenant_id, now_unix=None):
        raise RateLimitExceededError(tenant_id=tenant_id, limit=60, window_size_s=60, current=61)

    with patch.object(dispatcher_app, "enforce_for_tenant", fake_enforce):
        resp = client.post(
            "/dispatch",
            json={"customer_id": "cust-1", "task_id": "t-1", "body": {}},
        )
    assert resp.status_code == 429
    assert resp.headers.get("retry-after") == "60"
    assert "rate limit exceeded" in resp.json()["detail"]


def test_dispatch_does_not_call_llm_when_rate_limited(client):
    """If rate-limit refuses, the LLM forward MUST NOT run (would cost $)."""

    async def fake_enforce(*, tenant_id, now_unix=None):
        raise RateLimitExceededError(tenant_id=tenant_id, limit=60, window_size_s=60, current=61)

    called = {"forward": False}

    def boom_forward(**_kw):
        called["forward"] = True
        return _llm_response()

    with (
        patch.object(dispatcher_app, "enforce_for_tenant", fake_enforce),
        patch.object(dispatcher_app, "forward", boom_forward),
    ):
        client.post("/dispatch", json={"customer_id": "c", "task_id": "t", "body": {}})
    assert called["forward"] is False


# ─── /dispatch upstream branches ──────────────────────────────────────────


def test_dispatch_returns_429_on_upstream_litellm_rate_exhaust(client):
    """LiteLLMRateLimitExhaustedError → 429 with longer Retry-After (60s)
    so customer doesn't immediately retry into the same upstream issue."""

    fake_enforce = AsyncMock(return_value=_decision())

    def upstream_429(**_kw):
        raise LiteLLMRateLimitExhaustedError("litellm 429 after 3 retries")

    with (
        patch.object(dispatcher_app, "enforce_for_tenant", fake_enforce),
        patch.object(dispatcher_app, "forward", upstream_429),
    ):
        resp = client.post("/dispatch", json={"customer_id": "c", "task_id": "t", "body": {}})
    assert resp.status_code == 429
    assert resp.headers.get("retry-after") == "60"


def test_dispatch_returns_502_on_litellm_router_error(client):
    """Generic LiteLLMRouterError (5xx upstream, transport failure) → 502."""

    fake_enforce = AsyncMock(return_value=_decision())

    def upstream_500(**_kw):
        raise LiteLLMRouterError("litellm status 500: upstream outage")

    with (
        patch.object(dispatcher_app, "enforce_for_tenant", fake_enforce),
        patch.object(dispatcher_app, "forward", upstream_500),
    ):
        resp = client.post("/dispatch", json={"customer_id": "c", "task_id": "t", "body": {}})
    assert resp.status_code == 502
    assert "litellm status 500" in resp.json()["detail"]


# ─── /dispatch input validation ───────────────────────────────────────────


def test_dispatch_rejects_empty_customer_id(client):
    """Pydantic min_length=1 enforces non-empty tenant — caller bug, 422."""
    resp = client.post("/dispatch", json={"customer_id": "", "task_id": "t", "body": {}})
    assert resp.status_code == 422


def test_dispatch_rejects_empty_task_id(client):
    resp = client.post("/dispatch", json={"customer_id": "c", "task_id": "", "body": {}})
    assert resp.status_code == 422


def test_dispatch_rejects_missing_body(client):
    """body is required — Pydantic 422 before any handler logic runs."""
    resp = client.post("/dispatch", json={"customer_id": "c", "task_id": "t"})
    assert resp.status_code == 422
