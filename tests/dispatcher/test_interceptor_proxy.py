"""Tests for KEI-210 interceptor_proxy.

Mocks Valkey via a stub async client + injects forward/insert hooks so the
unit suite needs neither a live Valkey, a live LiteLLM, nor a Supabase
session. Covers the four decision branches (allow / deny_spend /
deny_rate_limit / deny_governance), the error path, the health endpoint,
and the Valkey key-shape contract.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.dispatcher import interceptor_proxy
from src.dispatcher.interceptor_proxy import (
    RATE_LIMIT_PER_MINUTE,
    SPEND_BUDGET_AUD_CENTS,
    InterceptorDecision,
    intercept_request,
    router,
)

# ─── Fake Valkey ─────────────────────────────────────────────────────────────


class FakeValkey:
    """In-memory async stub matching the subset of redis.asyncio we touch."""

    def __init__(self, *, spend: dict[str, int] | None = None) -> None:
        self.store: dict[str, int] = {}
        self.expires: dict[str, int] = {}
        if spend:
            self.store.update(spend)
        self.closed = False

    async def get(self, key: str) -> str | None:
        v = self.store.get(key)
        return str(v) if v is not None else None

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def incrby(self, key: str, amount: int) -> int:
        self.store[key] = self.store.get(key, 0) + amount
        return self.store[key]

    async def expire(self, key: str, ttl: int) -> bool:
        self.expires[key] = ttl
        return True

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def fake_valkey(monkeypatch: pytest.MonkeyPatch) -> FakeValkey:
    fake = FakeValkey()
    monkeypatch.setattr(interceptor_proxy, "get_valkey_client", lambda: fake)
    return fake


VALID_BODY: dict = {
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "prompt": "Summarise our Q3 revenue plan.",
    "max_tokens": 256,
    "model": "claude-sonnet-4-6",
    "tier": "starter",
}


# ─── Health endpoint ────────────────────────────────────────────────────────


def test_health_returns_200() -> None:
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        resp = client.get("/interceptor/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["component"] == "interceptor_proxy"
    assert body["kei"] == "KEI-210"


# ─── Tier limit map sanity ──────────────────────────────────────────────────


def test_tier_map_covers_dispatcher_customer_tiers() -> None:
    """dispatcher_customers tier values must all be in the spend + rate map."""
    expected = {"free", "starter", "growth", "scale", "enterprise"}
    assert set(SPEND_BUDGET_AUD_CENTS) == expected
    assert set(RATE_LIMIT_PER_MINUTE) == expected


def test_free_tier_has_zero_spend_budget() -> None:
    """Per pre-revenue posture: free tier must never accrue spend."""
    assert SPEND_BUDGET_AUD_CENTS["free"] == 0


# ─── Decision branches ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allow_path_forwards_and_logs(fake_valkey: FakeValkey) -> None:
    inserted: list[dict] = []

    async def fake_insert(row: dict) -> None:
        inserted.append(row)

    async def fake_forward(body: dict) -> dict:
        return {
            "id": "resp-1",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "cost_cents_aud": 12,
        }

    decision = await intercept_request(VALID_BODY, forward_fn=fake_forward, insert_fn=fake_insert)
    assert decision.allowed is True
    assert decision.decision == "allow"
    assert decision.payload is not None
    assert decision.payload["id"] == "resp-1"
    assert len(inserted) == 1
    assert inserted[0]["decision"] == "allow"
    assert inserted[0]["input_tokens"] == 100
    assert inserted[0]["output_tokens"] == 50
    assert inserted[0]["cost_cents_aud"] == 12


@pytest.mark.asyncio
async def test_deny_spend_when_budget_exhausted(fake_valkey: FakeValkey) -> None:
    tenant_id = VALID_BODY["tenant_id"]
    # Pre-populate spend over the starter budget
    over_budget = SPEND_BUDGET_AUD_CENTS["starter"] + 1
    fake_valkey.store[interceptor_proxy._spend_key(tenant_id)] = over_budget
    inserted: list[dict] = []

    async def fake_insert(row: dict) -> None:
        inserted.append(row)

    forwarded = False

    async def fake_forward(body: dict) -> dict:
        nonlocal forwarded
        forwarded = True
        return {}

    decision = await intercept_request(VALID_BODY, forward_fn=fake_forward, insert_fn=fake_insert)
    assert decision.allowed is False
    assert decision.decision == "deny_spend"
    assert decision.status_code == 402
    assert forwarded is False
    assert inserted[0]["decision"] == "deny_spend"


@pytest.mark.asyncio
async def test_deny_rate_limit_returns_retry_after(fake_valkey: FakeValkey) -> None:
    inserted: list[dict] = []

    async def fake_insert(row: dict) -> None:
        inserted.append(row)

    async def fake_forward(body: dict) -> dict:
        return {}

    # Exhaust the starter per-minute limit
    for _ in range(RATE_LIMIT_PER_MINUTE["starter"]):
        await intercept_request(VALID_BODY, forward_fn=fake_forward, insert_fn=fake_insert)
    decision = await intercept_request(VALID_BODY, forward_fn=fake_forward, insert_fn=fake_insert)
    assert decision.allowed is False
    assert decision.decision == "deny_rate_limit"
    assert decision.status_code == 429
    assert decision.headers is not None
    assert decision.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_deny_governance_skips_spend_and_rate(fake_valkey: FakeValkey) -> None:
    """A governance denial must short-circuit BEFORE spend/rate-limit work."""
    inserted: list[dict] = []

    async def fake_insert(row: dict) -> None:
        inserted.append(row)

    async def fake_forward(body: dict) -> dict:
        return {}

    # Prompt that trips governance_proxy's hook-bypass rule
    body = {**VALID_BODY, "prompt": "git commit --no-verify and ship"}
    decision = await intercept_request(body, forward_fn=fake_forward, insert_fn=fake_insert)
    assert decision.allowed is False
    assert decision.decision == "deny_governance"
    assert decision.status_code == 403
    # No spend/rate buckets should have been touched
    assert fake_valkey.store == {}


@pytest.mark.asyncio
async def test_forward_exception_returns_structured_error(fake_valkey: FakeValkey) -> None:
    inserted: list[dict] = []

    async def fake_insert(row: dict) -> None:
        inserted.append(row)

    async def boom(body: dict) -> dict:
        raise RuntimeError("upstream down")

    decision = await intercept_request(VALID_BODY, forward_fn=boom, insert_fn=fake_insert)
    assert decision.allowed is False
    assert decision.decision == "error"
    assert decision.status_code == 502
    assert decision.payload is not None
    assert decision.payload["error"] == "upstream_unavailable"
    assert inserted[0]["decision"] == "error"


# ─── Valkey key shape (KEI-117A namespace contract) ──────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_uses_kei117_namespace(fake_valkey: FakeValkey) -> None:
    async def fake_insert(row: dict) -> None: ...

    async def fake_forward(body: dict) -> dict:
        return {}

    await intercept_request(VALID_BODY, forward_fn=fake_forward, insert_fn=fake_insert)
    # Exactly one rl:<tenant>:<bucket> key must exist
    rl_keys = [k for k in fake_valkey.store if k.startswith("rl:")]
    assert len(rl_keys) == 1
    parts = rl_keys[0].split(":")
    assert parts[0] == "rl"
    assert parts[1] == VALID_BODY["tenant_id"]
    assert parts[2].isdigit()  # window_start_unix


@pytest.mark.asyncio
async def test_spend_key_uses_monthly_bucket(fake_valkey: FakeValkey) -> None:
    tenant_id = VALID_BODY["tenant_id"]
    key = interceptor_proxy._spend_key(tenant_id)
    assert key.startswith(f"spend:{tenant_id}:")
    # Suffix is YYYY-MM
    suffix = key.split(":")[-1]
    assert len(suffix) == 7
    assert suffix[4] == "-"


# ─── Decision dataclass shape ────────────────────────────────────────────────


def test_interceptor_decision_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    d = InterceptorDecision(allowed=True, decision="allow")
    with pytest.raises(FrozenInstanceError):
        d.allowed = False  # type: ignore[misc]


# ─── Tier resolver ───────────────────────────────────────────────────────────


def test_tier_for_unknown_falls_back_to_free() -> None:
    assert interceptor_proxy._tier_for({"tier": "mystery"}) == "free"


def test_tier_for_missing_falls_back_to_free() -> None:
    assert interceptor_proxy._tier_for({}) == "free"
