"""KEI-117C — tests for src/dispatcher/tier_limits.

The underlying rate_limiter is mocked at the valkey-client boundary so
tier-aware enforcement can be tested end-to-end without a live Valkey.
Tier lookup is fully overrideable via set_tenant_tier_lookup so tests
don't need to read env vars or hit a DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.dispatcher import rate_limiter
from src.dispatcher.rate_limiter import RateLimitExceededError
from src.dispatcher.tier_limits import (
    DEFAULT_TIER,
    TIER_LIMITS,
    TIER_OVERRIDES_ENV,
    UnknownTierError,
    enforce_for_tenant,
    get_tenant_tier,
    limits_for,
    reset_tenant_tier_lookup,
    set_tenant_tier_lookup,
)


@pytest.fixture(autouse=True)
def _restore_lookup():
    """Tests must not leak lookup overrides into each other."""
    yield
    reset_tenant_tier_lookup()


@pytest.fixture
def fake_valkey(monkeypatch):
    """Stub the rate limiter's valkey client so enforce_for_tenant runs
    end-to-end without a live Valkey."""
    mock_client = AsyncMock()
    state = {"n": 0}

    def fake_incr(_key):
        state["n"] += 1
        return state["n"]

    mock_client.incr = AsyncMock(side_effect=fake_incr)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.aclose = AsyncMock()
    monkeypatch.setattr(rate_limiter, "get_valkey_client", lambda: mock_client)
    return mock_client


# ─── TIER_LIMITS canonical values (Linear acceptance) ─────────────────────


def test_tier_limits_match_linear_acceptance():
    """Linear KEI-172 specifies Basic=60/min, Pro=300/min, Enterprise=1000/min."""
    assert TIER_LIMITS["basic"] == (60, 60)
    assert TIER_LIMITS["pro"] == (300, 60)
    assert TIER_LIMITS["enterprise"] == (1000, 60)


# ─── limits_for ────────────────────────────────────────────────────────────


def test_limits_for_returns_tier_tuple():
    assert limits_for("basic") == (60, 60)
    assert limits_for("pro") == (300, 60)
    assert limits_for("enterprise") == (1000, 60)


def test_limits_for_raises_on_unknown_tier():
    """Unknown tier is caller bug (not runtime drift) — must raise loudly."""
    with pytest.raises(UnknownTierError, match="unknown tier"):
        limits_for("ultra")  # type: ignore[arg-type]


# ─── get_tenant_tier — default lookup ─────────────────────────────────────


def test_get_tenant_tier_defaults_to_basic(monkeypatch):
    """No DISPATCHER_TIER_OVERRIDES, no custom lookup → basic."""
    monkeypatch.delenv(TIER_OVERRIDES_ENV, raising=False)
    assert get_tenant_tier("anyone") == "basic"


def test_get_tenant_tier_reads_env_overrides(monkeypatch):
    """DISPATCHER_TIER_OVERRIDES JSON map honored per-tenant."""
    monkeypatch.setenv(TIER_OVERRIDES_ENV, '{"cust-pro": "pro", "cust-ent": "enterprise"}')
    assert get_tenant_tier("cust-pro") == "pro"
    assert get_tenant_tier("cust-ent") == "enterprise"
    # tenants not in the map fall back to default
    assert get_tenant_tier("cust-unknown") == DEFAULT_TIER


def test_get_tenant_tier_falls_back_when_env_invalid_json(monkeypatch, caplog):
    """Malformed JSON in env → warning + default tier. NEVER raise."""
    monkeypatch.setenv(TIER_OVERRIDES_ENV, "this is not json")
    with caplog.at_level("WARNING"):
        tier = get_tenant_tier("cust-x")
    assert tier == DEFAULT_TIER
    assert any("invalid JSON" in r.message for r in caplog.records)


def test_get_tenant_tier_ignores_unknown_tier_in_env(monkeypatch):
    """An env override pointing at an unrecognized tier silently degrades
    to the default — defensive against typos / future tier removals."""
    monkeypatch.setenv(TIER_OVERRIDES_ENV, '{"cust-x": "platinum"}')
    assert get_tenant_tier("cust-x") == DEFAULT_TIER


def test_get_tenant_tier_strips_whitespace():
    """Whitespace-padded tenant_id resolves like the trimmed form so
    callers can't accidentally bypass an override via a trailing space."""
    set_tenant_tier_lookup(lambda tid: "pro" if tid == "cust-1" else "basic")
    assert get_tenant_tier("  cust-1  ") == "pro"


def test_get_tenant_tier_refuses_empty_tenant():
    """Empty tenant_id is a caller bug — refuse loudly so the rate-limit
    bucket doesn't collapse to a single shared counter."""
    with pytest.raises(ValueError, match="non-empty"):
        get_tenant_tier("")
    with pytest.raises(ValueError, match="non-empty"):
        get_tenant_tier("   ")


# ─── get_tenant_tier — pluggable lookup ───────────────────────────────────


def test_set_tenant_tier_lookup_overrides_default():
    """Custom lookup replaces the env-override lookup until reset."""
    set_tenant_tier_lookup(lambda _t: "enterprise")
    assert get_tenant_tier("cust-x") == "enterprise"


def test_reset_tenant_tier_lookup_restores_default(monkeypatch):
    """After reset, the env-override lookup is back in place."""
    set_tenant_tier_lookup(lambda _t: "enterprise")
    reset_tenant_tier_lookup()
    monkeypatch.delenv(TIER_OVERRIDES_ENV, raising=False)
    assert get_tenant_tier("cust-x") == "basic"


def test_get_tenant_tier_fails_closed_when_lookup_raises(caplog):
    """A buggy / down-store lookup must NOT bypass rate limiting — fall
    back to DEFAULT_TIER (most restrictive) and log."""

    def boom(_t):
        raise RuntimeError("tier store down")

    set_tenant_tier_lookup(boom)
    with caplog.at_level("WARNING"):
        tier = get_tenant_tier("cust-x")
    assert tier == DEFAULT_TIER
    assert any("tier store down" in r.message for r in caplog.records)


def test_get_tenant_tier_fails_closed_when_lookup_returns_unknown(caplog):
    """Lookup returns a tier not in TIER_LIMITS → degrade to default."""
    set_tenant_tier_lookup(lambda _t: "platinum")  # type: ignore[arg-type,return-value]
    with caplog.at_level("WARNING"):
        tier = get_tenant_tier("cust-x")
    assert tier == DEFAULT_TIER
    assert any("unknown tier" in r.message for r in caplog.records)


# ─── enforce_for_tenant ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enforce_for_tenant_applies_basic_limit(fake_valkey):
    """Basic tier → 60/min: 60 allowed, 61st refused."""
    set_tenant_tier_lookup(lambda _t: "basic")
    # Pump exactly the basic limit
    for _ in range(60):
        await enforce_for_tenant(tenant_id="cust-basic", now_unix=1715904000)
    with pytest.raises(RateLimitExceededError) as exc_info:
        await enforce_for_tenant(tenant_id="cust-basic", now_unix=1715904000)
    assert exc_info.value.limit == 60
    assert exc_info.value.window_size_s == 60


@pytest.mark.asyncio
async def test_enforce_for_tenant_applies_pro_limit_higher_ceiling(fake_valkey):
    """Pro tier raises the ceiling to 300/min — first 61 reqs that would
    refuse Basic must all succeed under Pro."""
    set_tenant_tier_lookup(lambda _t: "pro")
    for _ in range(61):
        decision = await enforce_for_tenant(tenant_id="cust-pro", now_unix=1715904000)
        assert decision.allowed is True
    assert decision.limit == 300


@pytest.mark.asyncio
async def test_enforce_for_tenant_applies_enterprise_limit_highest(fake_valkey):
    """Enterprise tier — limit value reaches RateLimitDecision."""
    set_tenant_tier_lookup(lambda _t: "enterprise")
    decision = await enforce_for_tenant(tenant_id="cust-ent", now_unix=1715904000)
    assert decision.limit == 1000
    assert decision.window_size_s == 60


@pytest.mark.asyncio
async def test_enforce_for_tenant_uses_per_tenant_tier(fake_valkey):
    """Two tenants with different tiers in the same call cycle resolve
    independently — the lookup is called per-tenant, not once per cycle."""
    tier_map = {"cust-basic": "basic", "cust-pro": "pro"}
    set_tenant_tier_lookup(lambda tid: tier_map.get(tid, "basic"))  # type: ignore[arg-type,return-value]
    d_basic = await enforce_for_tenant(tenant_id="cust-basic", now_unix=1715904000)
    d_pro = await enforce_for_tenant(tenant_id="cust-pro", now_unix=1715904000)
    assert d_basic.limit == 60
    assert d_pro.limit == 300
