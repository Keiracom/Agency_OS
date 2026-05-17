"""KEI-117A — tests for src/dispatcher/valkey_pool.

Redis client is mocked via AsyncMock so no live Valkey/Redis required
for CI. Pool state is reset between cases so tests stay independent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.dispatcher import valkey_pool
from src.dispatcher.valkey_pool import (
    DEFAULT_VALKEY_URL,
    RL_NAMESPACE_PREFIX,
    SMOKE_KEY_TTL_SECONDS,
    reset_valkey_pool,
    smoke_incr,
    tenant_rl_key,
)


@pytest.fixture(autouse=True)
async def _clean_pool_each_test():
    """Tear down the module-level pool before AND after each case so URL
    resolution + caching tests don't bleed into each other."""
    await reset_valkey_pool()
    yield
    await reset_valkey_pool()


# ─── tenant_rl_key ─────────────────────────────────────────────────────────


def test_tenant_rl_key_format():
    """Key shape is exactly ``rl:<tenant>:<window>``."""
    key = tenant_rl_key("cust-abc", 1715900000)
    assert key == f"{RL_NAMESPACE_PREFIX}:cust-abc:1715900000"


def test_tenant_rl_key_coerces_window_to_int():
    """A float window (e.g. ``time.time()``) is truncated, not rounded —
    matches the int() cast in the helper."""
    key = tenant_rl_key("t", 1715900000.987)
    assert key.endswith(":1715900000")


def test_tenant_rl_key_strips_whitespace():
    """Trailing whitespace on tenant_id is stripped to prevent invisible
    duplicate buckets ('cust-1 ' vs 'cust-1')."""
    assert tenant_rl_key("  cust-1  ", 0) == f"{RL_NAMESPACE_PREFIX}:cust-1:0"


def test_tenant_rl_key_refuses_empty_tenant():
    """An empty / whitespace-only tenant_id would silently bucket all
    requests into one counter — refuse it."""
    with pytest.raises(ValueError, match="non-empty"):
        tenant_rl_key("", 0)
    with pytest.raises(ValueError, match="non-empty"):
        tenant_rl_key("   ", 0)


# ─── pool URL resolution ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_prefers_valkey_url(monkeypatch):
    """VALKEY_URL wins over REDIS_URL."""
    monkeypatch.setenv("VALKEY_URL", "redis://valkey-host:6380/3")
    monkeypatch.setenv("REDIS_URL", "redis://redis-host:6379/0")

    captured: dict = {}

    def fake_from_url(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return AsyncMock()

    monkeypatch.setattr(valkey_pool.ConnectionPool, "from_url", fake_from_url)
    await valkey_pool.get_valkey_pool()
    assert captured["url"] == "redis://valkey-host:6380/3"
    assert captured["kwargs"]["decode_responses"] is True
    assert captured["kwargs"]["max_connections"] == 20


@pytest.mark.asyncio
async def test_pool_falls_back_to_redis_url(monkeypatch):
    """No VALKEY_URL → REDIS_URL is used."""
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://shared:6379/1")
    captured: dict = {}
    monkeypatch.setattr(
        valkey_pool.ConnectionPool,
        "from_url",
        lambda url, **kw: captured.setdefault("url", url) or AsyncMock(),
    )
    await valkey_pool.get_valkey_pool()
    assert captured["url"] == "redis://shared:6379/1"


@pytest.mark.asyncio
async def test_pool_falls_back_to_default(monkeypatch):
    """No env vars → the local default URL."""
    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    captured: dict = {}
    monkeypatch.setattr(
        valkey_pool.ConnectionPool,
        "from_url",
        lambda url, **kw: captured.setdefault("url", url) or AsyncMock(),
    )
    await valkey_pool.get_valkey_pool()
    assert captured["url"] == DEFAULT_VALKEY_URL


# ─── pool caching ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pool_is_cached_across_calls(monkeypatch):
    """get_valkey_pool() returns the same pool instance on subsequent
    calls — ConnectionPool.from_url is invoked exactly once."""
    calls = {"n": 0}

    def fake_from_url(url, **kw):
        calls["n"] += 1
        return AsyncMock()

    monkeypatch.setattr(valkey_pool.ConnectionPool, "from_url", fake_from_url)
    p1 = await valkey_pool.get_valkey_pool()
    p2 = await valkey_pool.get_valkey_pool()
    p3 = await valkey_pool.get_valkey_pool()
    assert p1 is p2 is p3
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_reset_pool_invalidates_cache(monkeypatch):
    """After reset_valkey_pool, the next call rebuilds the pool."""
    calls = {"n": 0}

    def fake_from_url(url, **kw):
        calls["n"] += 1
        mock_pool = AsyncMock()
        mock_pool.aclose = AsyncMock()
        return mock_pool

    monkeypatch.setattr(valkey_pool.ConnectionPool, "from_url", fake_from_url)
    await valkey_pool.get_valkey_pool()
    await reset_valkey_pool()
    await valkey_pool.get_valkey_pool()
    assert calls["n"] == 2


# ─── smoke_incr ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_smoke_incr_runs_incr_and_expire(monkeypatch):
    """smoke_incr issues INCR then EXPIRE on a per-process namespaced key
    and returns the post-INCR integer."""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.aclose = AsyncMock()

    async def fake_get_client():
        return mock_client

    monkeypatch.setattr(valkey_pool, "get_valkey_client", fake_get_client)

    value = await smoke_incr()
    assert value == 1
    mock_client.incr.assert_awaited_once()
    incr_key = mock_client.incr.await_args.args[0]
    assert incr_key.startswith(f"{RL_NAMESPACE_PREFIX}:_smoke:")
    mock_client.expire.assert_awaited_once()
    exp_args = mock_client.expire.await_args.args
    assert exp_args[0] == incr_key
    assert exp_args[1] == SMOKE_KEY_TTL_SECONDS
    mock_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_smoke_incr_returns_post_increment_value(monkeypatch):
    """If the smoke key already had 5 (impossible in practice — it has
    60s TTL — but covered for safety), smoke_incr returns 6."""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=6)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.aclose = AsyncMock()

    async def fake_get_client():
        return mock_client

    monkeypatch.setattr(valkey_pool, "get_valkey_client", fake_get_client)
    assert await smoke_incr() == 6


@pytest.mark.asyncio
async def test_smoke_incr_closes_client_even_on_failure(monkeypatch):
    """If INCR raises (e.g. transport failure), the client.aclose() must
    still run so we don't leak a connection from the pool."""
    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(side_effect=ConnectionError("valkey unreachable"))
    mock_client.expire = AsyncMock()
    mock_client.aclose = AsyncMock()

    async def fake_get_client():
        return mock_client

    monkeypatch.setattr(valkey_pool, "get_valkey_client", fake_get_client)
    with pytest.raises(ConnectionError):
        await smoke_incr()
    mock_client.aclose.assert_awaited_once()
