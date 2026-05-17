"""KEI-117B — tests for src/dispatcher/rate_limiter.

The valkey client is AsyncMock'd so no live Valkey is required. Clock
is fully controllable via the now_unix parameter — no time.sleep needed
to exercise window-rollover scenarios.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.dispatcher import rate_limiter, valkey_pool
from src.dispatcher.rate_limiter import (
    DEFAULT_LIMIT,
    DEFAULT_WINDOW_SIZE_S,
    RateLimitDecision,
    RateLimitExceededError,
    check_and_increment,
    enforce,
)


def _client_with_counter(initial: int = 0) -> AsyncMock:
    """Build a fake Redis async client whose INCR returns a monotonic
    counter starting just above ``initial``. Tracks calls for assertions."""
    state = {"n": initial}

    async def fake_incr(key: str) -> int:
        state["n"] += 1
        return state["n"]

    mock = AsyncMock()
    mock.incr = AsyncMock(side_effect=fake_incr)
    mock.expire = AsyncMock(return_value=True)
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
def fake_client(monkeypatch):
    """Stub get_valkey_client with a per-test counter mock."""
    client = _client_with_counter()

    async def fake_get_client():
        return client

    monkeypatch.setattr(rate_limiter, "get_valkey_client", fake_get_client)
    return client


# ─── check_and_increment ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_and_increment_allows_first_request(fake_client):
    """First request in a fresh window — allowed=True, current=1."""
    decision = await check_and_increment(
        tenant_id="cust-1", limit=10, window_size_s=60, now_unix=1715904030
    )
    assert decision.allowed is True
    assert decision.current == 1
    assert decision.limit == 10
    assert decision.window_size_s == 60
    # window_start snaps DOWN to nearest 60s boundary
    assert decision.window_start_unix == 1715904000


@pytest.mark.asyncio
async def test_check_and_increment_allows_up_to_limit(fake_client):
    """Requests 1..limit all allowed; 101st in a 100-limit refused."""
    for _ in range(100):
        d = await check_and_increment(
            tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000
        )
        assert d.allowed is True
    # 101st request — refused
    d = await check_and_increment(tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000)
    assert d.allowed is False
    assert d.current == 101


@pytest.mark.asyncio
async def test_check_and_increment_refuses_at_boundary(fake_client):
    """``current > limit`` is the refusal condition (101st > 100). The
    100th request must still be allowed."""
    # Pump 99 through
    for _ in range(99):
        await check_and_increment(tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000)
    # 100th — allowed
    d100 = await check_and_increment(
        tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000
    )
    assert d100.allowed is True
    assert d100.current == 100
    # 101st — refused
    d101 = await check_and_increment(
        tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000
    )
    assert d101.allowed is False
    assert d101.current == 101


@pytest.mark.asyncio
async def test_check_and_increment_uses_different_key_per_tenant(monkeypatch):
    """Two tenants in the same window must hit different keys — no
    cross-tenant counter sharing."""
    keys_incremented: list[str] = []

    async def fake_incr(key):
        keys_incremented.append(key)
        return 1

    client = AsyncMock()
    client.incr = AsyncMock(side_effect=fake_incr)
    client.expire = AsyncMock()
    client.aclose = AsyncMock()

    async def fake_get_client():
        return client

    monkeypatch.setattr(rate_limiter, "get_valkey_client", fake_get_client)
    await check_and_increment(tenant_id="alpha", limit=10, window_size_s=60, now_unix=1715904000)
    await check_and_increment(tenant_id="beta", limit=10, window_size_s=60, now_unix=1715904000)
    assert keys_incremented == ["rl:alpha:1715904000", "rl:beta:1715904000"]


@pytest.mark.asyncio
async def test_check_and_increment_uses_different_key_per_window(monkeypatch):
    """Same tenant in two different windows must hit two keys —
    the counter MUST reset across window boundaries."""
    keys: list[str] = []
    client = AsyncMock()
    client.incr = AsyncMock(side_effect=lambda key: keys.append(key) or 1)
    client.expire = AsyncMock()
    client.aclose = AsyncMock()

    async def fake_get_client():
        return client

    monkeypatch.setattr(rate_limiter, "get_valkey_client", fake_get_client)
    await check_and_increment(tenant_id="t", limit=10, window_size_s=60, now_unix=1715904030)
    # 61 seconds later → next window
    await check_and_increment(tenant_id="t", limit=10, window_size_s=60, now_unix=1715904091)
    assert keys == ["rl:t:1715904000", "rl:t:1715904060"]


@pytest.mark.asyncio
async def test_check_and_increment_sets_expire(fake_client):
    """EXPIRE must be set with ttl = 2× window_size_s so the bucket
    auto-evicts cleanly after one full window has passed."""
    await check_and_increment(tenant_id="t", limit=10, window_size_s=60, now_unix=1715904030)
    fake_client.expire.assert_awaited_once()
    args = fake_client.expire.await_args.args
    assert args[0] == "rl:t:1715904000"
    assert args[1] == 120


@pytest.mark.asyncio
async def test_check_and_increment_closes_client(fake_client):
    """Connection must be returned to the pool on success AND on
    transport failure — leak guard."""
    await check_and_increment(tenant_id="t", limit=10, window_size_s=60, now_unix=1715904000)
    fake_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_and_increment_closes_client_on_failure(monkeypatch):
    """If INCR raises, aclose still runs (try/finally guard)."""
    client = AsyncMock()
    client.incr = AsyncMock(side_effect=ConnectionError("valkey down"))
    client.expire = AsyncMock()
    client.aclose = AsyncMock()

    async def fake_get_client():
        return client

    monkeypatch.setattr(rate_limiter, "get_valkey_client", fake_get_client)
    with pytest.raises(ConnectionError):
        await check_and_increment(tenant_id="t", limit=10, window_size_s=60, now_unix=1715904000)
    client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_and_increment_retry_after_decays(fake_client):
    """retry_after_s should equal seconds remaining in the current
    window — decreasing as ``now_unix`` advances."""
    d1 = await check_and_increment(tenant_id="t", limit=1, window_size_s=60, now_unix=1715904000)
    d2 = await check_and_increment(tenant_id="t", limit=1, window_size_s=60, now_unix=1715904045)
    assert d1.retry_after_s == 60
    assert d2.retry_after_s == 15


@pytest.mark.asyncio
async def test_check_and_increment_rejects_zero_window(fake_client):
    with pytest.raises(ValueError, match="window_size_s must be positive"):
        await check_and_increment(tenant_id="t", limit=10, window_size_s=0)


@pytest.mark.asyncio
async def test_check_and_increment_rejects_zero_limit(fake_client):
    with pytest.raises(ValueError, match="limit must be positive"):
        await check_and_increment(tenant_id="t", limit=0, window_size_s=60)


@pytest.mark.asyncio
async def test_check_and_increment_propagates_empty_tenant(fake_client):
    """Empty tenant_id surfaces from tenant_rl_key as ValueError —
    no silent cross-tenant counter."""
    with pytest.raises(ValueError, match="non-empty"):
        await check_and_increment(tenant_id="", limit=10, window_size_s=60)


# ─── enforce wrapper ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enforce_returns_decision_when_allowed(fake_client):
    """enforce() returns the RateLimitDecision unchanged on allow."""
    decision = await enforce(tenant_id="t", limit=10, window_size_s=60, now_unix=1715904000)
    assert isinstance(decision, RateLimitDecision)
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_enforce_raises_when_refused(fake_client):
    """enforce() raises RateLimitExceededError when the limiter refuses,
    carrying tenant + limit + window for upstream 429 mapping."""
    # Pump 100 through to saturate
    for _ in range(100):
        await enforce(tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000)
    with pytest.raises(RateLimitExceededError) as exc_info:
        await enforce(tenant_id="t", limit=100, window_size_s=60, now_unix=1715904000)
    exc = exc_info.value
    assert exc.tenant_id == "t"
    assert exc.limit == 100
    assert exc.window_size_s == 60
    assert exc.current == 101


# ─── defaults ──────────────────────────────────────────────────────────────


def test_defaults_match_linear_acceptance():
    """Linear KEI-171 acceptance specifies '60s window; 100 req/min limit'.
    The module defaults must match so callers can use ``enforce(tenant_id=)``
    without explicitly passing the same numbers."""
    assert DEFAULT_WINDOW_SIZE_S == 60
    assert DEFAULT_LIMIT == 100


# ─── module surface tidy-up (avoid leaking pool state between tests) ──────


@pytest.fixture(autouse=True)
async def _no_leftover_pool():
    """Belt-and-braces — these tests stub get_valkey_client so the real
    pool never gets touched, but reset between cases anyway."""
    yield
    await valkey_pool.reset_valkey_pool()
