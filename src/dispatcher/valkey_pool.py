"""KEI-117A — Valkey connection pool + per-tenant key namespace.

Foundation for the Part 17 dispatcher rate limiter (KEI-117B / KEI-171).
Valkey speaks the Redis wire protocol so we reuse ``redis.asyncio`` —
no new client dependency. Pool is separate from the agency-side
``src/integrations/redis.py`` because the dispatcher product layer is a
distinct tenancy (customer_id), not the agency's client_id model.

Key namespace contract (documented here as the canonical spec — DO NOT
duplicate in callers):

    rl:<tenant_id>:<window_start_unix>

* ``rl:`` — rate-limit family prefix. Other dispatcher families (e.g.
  ``q:`` for queues, ``ses:`` for sessions) will sit alongside without
  collision.
* ``<tenant_id>`` — customer UUID string. Caller is responsible for
  passing a validated id; the helper does not authenticate.
* ``<window_start_unix>`` — INT seconds since epoch at the start of the
  fixed-or-sliding window. Granularity is the caller's choice (minute,
  hour, day). The sliding-window limiter (KEI-171) uses 60-second buckets.

Smoke health check: ``await smoke_incr()`` runs ``INCR <smoke_key>`` +
``EXPIRE <smoke_key> 60`` against the pool to confirm the connection is
live. Returns the integer post-increment value (≥ 1 on a healthy
connection). Smoke keys are namespaced ``rl:_smoke:<process_pid>`` so
concurrent smokes don't collide and the bucket auto-evicts.
"""

from __future__ import annotations

import logging
import os

from redis.asyncio import ConnectionPool, Redis

logger = logging.getLogger(__name__)

VALKEY_URL_ENV = "VALKEY_URL"
FALLBACK_URL_ENV = "REDIS_URL"
DEFAULT_VALKEY_URL = "redis://127.0.0.1:6379/0"
DEFAULT_MAX_CONNECTIONS = 20
SMOKE_KEY_TTL_SECONDS = 60

RL_NAMESPACE_PREFIX = "rl"

_pool: ConnectionPool | None = None


def _resolve_url() -> str:
    """Prefer VALKEY_URL, fall back to REDIS_URL, fall back to local default.

    The fallback chain lets the dispatcher run against the existing
    agency-side Redis in dev without needing a second binary, while keeping
    a knob for prod to split the two tenancies onto separate instances.
    """
    return os.environ.get(VALKEY_URL_ENV) or os.environ.get(FALLBACK_URL_ENV) or DEFAULT_VALKEY_URL


def get_valkey_pool() -> ConnectionPool:
    """Lazy-init the dispatcher Valkey pool. Same instance for the lifetime
    of the process — pool reset is handled by `reset_valkey_pool()` (test
    fixtures only).

    Sync because pool creation is in-memory (no I/O until first command).
    `redis.asyncio.ConnectionPool.from_url` doesn't open sockets — those
    are minted lazily per command by the Redis client.
    """
    global _pool
    if _pool is None:
        url = _resolve_url()
        _pool = ConnectionPool.from_url(
            url,
            decode_responses=True,
            max_connections=DEFAULT_MAX_CONNECTIONS,
        )
        logger.info("valkey pool created url=%s max=%d", url, DEFAULT_MAX_CONNECTIONS)
    return _pool


def get_valkey_client() -> Redis:
    """Get a Redis client bound to the dispatcher pool. Caller is
    responsible for `await client.aclose()` when done (or use as
    `async with`)."""
    return Redis(connection_pool=get_valkey_pool())


async def reset_valkey_pool() -> None:
    """Tear down the cached pool. Tests use this between cases; production
    code should never call it. Safe to call when no pool exists."""
    global _pool
    if _pool is not None:
        try:
            await _pool.aclose()
        except Exception as exc:  # noqa: BLE001 — teardown must not raise
            logger.warning("valkey pool aclose failed (non-fatal): %s", exc)
        _pool = None


def tenant_rl_key(tenant_id: str, window_start_unix: int | float) -> str:
    """Build a per-tenant rate-limit key.

    Args:
        tenant_id: Customer UUID string. Must be non-empty.
        window_start_unix: Unix seconds at the start of the window. Accepts
            ``int`` or ``float`` (e.g. ``time.time()``) and truncates to int.

    Returns:
        ``rl:<tenant_id>:<window_start_unix>``

    Raises:
        ValueError: ``tenant_id`` is empty / whitespace. We refuse to mint
            an unscoped namespace because that would silently bucket ALL
            tenants into one counter.
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id must be a non-empty string")
    return f"{RL_NAMESPACE_PREFIX}:{tenant_id.strip()}:{int(window_start_unix)}"


async def smoke_incr() -> int:
    """Health probe — INCR a per-process smoke key and set 60s TTL so the
    bucket auto-evicts. Returns the integer post-increment value.

    Use from boot checks / readiness probes. Returns ``>= 1`` when the
    pool is live; raises whatever ``redis.asyncio`` raises on transport
    failure so the caller can decide whether to treat it as degraded vs
    fatal.
    """
    client = get_valkey_client()
    try:
        smoke_key = f"{RL_NAMESPACE_PREFIX}:_smoke:{os.getpid()}"
        value = await client.incr(smoke_key)
        await client.expire(smoke_key, SMOKE_KEY_TTL_SECONDS)
        return int(value)
    finally:
        await client.aclose()
