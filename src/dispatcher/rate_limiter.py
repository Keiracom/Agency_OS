"""KEI-117B — sliding-window rate limiter for per-tenant enforcement.

Builds on KEI-117A's Valkey pool + tenant key namespace. Implements a
**fixed-window** counter strategy variant of "sliding window" — each
window_size_s seconds gets its own INCR bucket keyed by
``rl:<tenant_id>:<window_start_unix>``, with TTL = 2× window_size_s so
the bucket auto-evicts after one full window has passed (Linear KEI-171
acceptance "counter resets after window" is satisfied by the TTL).

This is the simplest correct rate-limit primitive for the dispatcher
product layer:
* O(1) per request — INCR + EXPIRE.
* Counter resets without manual cleanup (TTL).
* Per-tenant isolation enforced at the key level (KEI-117A guard
  refuses empty tenant_id).

True log-of-events sliding-window (Redis ZSET / Lua) is OUT of scope
here — the dispatcher's first-customer requirement is "block obvious
abuse", not "millisecond-accurate burst smoothing". The ratified
acceptance ("60s window; 100 req/min returns 429 on 101st") is
satisfied by fixed windows; we can upgrade to ZSET-based sliding if a
real customer complains about the bucket-edge effect.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.dispatcher.valkey_pool import get_valkey_client, tenant_rl_key

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SIZE_S = 60
DEFAULT_LIMIT = 100

# TTL is 2× the window so the bucket is alive long enough for any
# straggler probe within the window AND auto-evicts cleanly afterwards.
_TTL_MULTIPLIER = 2


class RateLimitExceededError(RuntimeError):
    """Raised when ``check_and_increment`` would push the tenant past
    their configured per-window limit. The caller surfaces this as a 429
    to the customer (dispatcher proxy / API layer does the mapping)."""

    def __init__(self, tenant_id: str, limit: int, window_size_s: int, current: int):
        self.tenant_id = tenant_id
        self.limit = limit
        self.window_size_s = window_size_s
        self.current = current
        super().__init__(
            f"rate limit exceeded for tenant {tenant_id}: "
            f"{current} >= {limit} per {window_size_s}s window"
        )


@dataclass(frozen=True)
class RateLimitDecision:
    """Result of a check_and_increment call. ``allowed=True`` means the
    increment landed and the caller may proceed. ``allowed=False`` means
    the counter was at or above limit BEFORE increment and the caller
    must refuse — the limiter does NOT roll back the increment in that
    case (over-counting is preferred to under-blocking for security)."""

    allowed: bool
    current: int
    limit: int
    window_start_unix: int
    window_size_s: int
    retry_after_s: int


def _window_start(now_unix: float, window_size_s: int) -> int:
    """Snap ``now_unix`` down to the nearest window boundary so all calls
    within the same window agree on the bucket key."""
    return (int(now_unix) // window_size_s) * window_size_s


async def check_and_increment(
    *,
    tenant_id: str,
    limit: int = DEFAULT_LIMIT,
    window_size_s: int = DEFAULT_WINDOW_SIZE_S,
    now_unix: float | None = None,
) -> RateLimitDecision:
    """Atomically INCR the tenant's current-window counter and decide
    whether the request should be allowed.

    Args:
        tenant_id: Customer UUID. Empty → ValueError from tenant_rl_key.
        limit: Max requests per window before subsequent requests are
            refused. The 101st request in a 100/window limit is refused.
        window_size_s: Fixed window length in seconds.
        now_unix: Override clock for tests. Defaults to ``time.time()``.

    Returns:
        RateLimitDecision with allowed/current/limit/window metadata.

    Raises:
        ValueError: tenant_id is empty/whitespace.
        Whatever redis.asyncio raises: transport failure. Caller decides
            whether to fail-open (allow) or fail-closed (refuse). This
            module does NOT swallow transport errors because for
            security-sensitive paths the operator must choose the policy.
    """
    if window_size_s <= 0:
        raise ValueError(f"window_size_s must be positive (got {window_size_s})")
    if limit <= 0:
        raise ValueError(f"limit must be positive (got {limit})")

    clock = time.time() if now_unix is None else now_unix
    window_start = _window_start(clock, window_size_s)
    key = tenant_rl_key(tenant_id, window_start)
    ttl_s = window_size_s * _TTL_MULTIPLIER

    client = get_valkey_client()
    try:
        # INCR returns the post-increment value. EXPIRE is idempotent —
        # safe to call every request even though we only need it on the
        # first increment of each window (negligible cost vs the round-trip
        # to add WATCH/MULTI for a "only on first" guard).
        current = int(await client.incr(key))
        await client.expire(key, ttl_s)
    finally:
        await client.aclose()

    allowed = current <= limit
    retry_after_s = max(0, window_start + window_size_s - int(clock))
    if not allowed:
        logger.info(
            "rate limit hit tenant=%s window=%d current=%d limit=%d retry_after=%ds",
            tenant_id,
            window_start,
            current,
            limit,
            retry_after_s,
        )
    return RateLimitDecision(
        allowed=allowed,
        current=current,
        limit=limit,
        window_start_unix=window_start,
        window_size_s=window_size_s,
        retry_after_s=retry_after_s,
    )


async def enforce(
    *,
    tenant_id: str,
    limit: int = DEFAULT_LIMIT,
    window_size_s: int = DEFAULT_WINDOW_SIZE_S,
    now_unix: float | None = None,
) -> RateLimitDecision:
    """Convenience wrapper — calls check_and_increment, raises
    RateLimitExceededError when the decision is ``allowed=False``.
    Returns the decision on success so the caller can attach headers
    (X-RateLimit-Remaining, Retry-After) to the customer response."""
    decision = await check_and_increment(
        tenant_id=tenant_id,
        limit=limit,
        window_size_s=window_size_s,
        now_unix=now_unix,
    )
    if not decision.allowed:
        raise RateLimitExceededError(
            tenant_id=tenant_id,
            limit=decision.limit,
            window_size_s=decision.window_size_s,
            current=decision.current,
        )
    return decision
