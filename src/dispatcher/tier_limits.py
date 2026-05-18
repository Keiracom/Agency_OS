"""KEI-117C — load tier limits + apply per-tenant rate limits.

Builds on KEI-117B's sliding-window primitive. Maps each customer to a
subscription tier (Basic / Pro / Enterprise) and enforces the tier's
configured req-per-window limit via ``rate_limiter.enforce``.

Tier configuration (Linear KEI-172 acceptance):
    Basic       = 60 req / 60s window
    Pro         = 300 req / 60s window
    Enterprise  = 1000 req / 60s window

Tier lookup is pluggable via ``set_tenant_tier_lookup(callable)``. The
default lookup returns ``"basic"`` for all tenants — adequate until
KEI-112B (subscriptions table) lands. Once the billing schema exists,
the consumer swaps in a DB-backed lookup with one call; no rate-limiter
contract change needed.

Override via env var ``DISPATCHER_TIER_OVERRIDES`` (JSON
``{"<tenant_id>": "pro", ...}``) for dev/staging without standing up
the subscriptions table. Empty / missing → default lookup.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import Literal

from src.dispatcher import rate_limiter
from src.dispatcher.rate_limiter import RateLimitDecision

logger = logging.getLogger(__name__)

Tier = Literal["basic", "pro", "enterprise"]
TenantTierLookup = Callable[[str], Tier]

DEFAULT_TIER: Tier = "basic"
TIER_OVERRIDES_ENV = "DISPATCHER_TIER_OVERRIDES"

# (limit, window_size_s) per tier — matches Linear KEI-172 acceptance.
TIER_LIMITS: dict[Tier, tuple[int, int]] = {
    "basic": (60, 60),
    "pro": (300, 60),
    "enterprise": (1000, 60),
}


class UnknownTierError(ValueError):
    """A tier lookup returned a value not in TIER_LIMITS — caller bug."""


def _env_override_lookup(tenant_id: str) -> Tier:
    """Read DISPATCHER_TIER_OVERRIDES JSON for tenant_id, fall through to
    DEFAULT_TIER. Used by the default lookup so dev/staging can simulate
    Pro/Enterprise tenants without the subscriptions table existing."""
    raw = os.environ.get(TIER_OVERRIDES_ENV, "").strip()
    if not raw:
        return DEFAULT_TIER
    try:
        overrides = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning(
            "%s contains invalid JSON (%s) — falling back to %s",
            TIER_OVERRIDES_ENV,
            exc,
            DEFAULT_TIER,
        )
        return DEFAULT_TIER
    value = overrides.get(tenant_id)
    if value in TIER_LIMITS:
        return value  # type: ignore[return-value]
    return DEFAULT_TIER


_lookup: TenantTierLookup = _env_override_lookup


def set_tenant_tier_lookup(lookup: TenantTierLookup) -> None:
    """Swap the tier-lookup implementation. KEI-112B (billing schema)
    consumer wires its DB-backed lookup via this once subscriptions land.
    Tests use this to inject deterministic tiers."""
    global _lookup
    _lookup = lookup


def reset_tenant_tier_lookup() -> None:
    """Restore the default env-override lookup. Tests call this between
    cases so a leftover injection doesn't bleed into the next test."""
    global _lookup
    _lookup = _env_override_lookup


def get_tenant_tier(tenant_id: str) -> Tier:
    """Resolve a tenant's tier via the active lookup. Defaults to basic
    if the lookup raises or returns an unknown value — rate limiting
    must NOT be bypassed because of a tier-store outage."""
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id must be a non-empty string")
    try:
        tier = _lookup(tenant_id.strip())
    except Exception as exc:  # noqa: BLE001 — tier lookup must fail-closed
        logger.warning(
            "tier lookup raised for tenant %s (%s) — defaulting to %s",
            tenant_id.replace("\n", "").replace("\r", ""),
            str(exc).replace("\n", "").replace("\r", ""),
            DEFAULT_TIER,
        )
        return DEFAULT_TIER
    if tier not in TIER_LIMITS:
        logger.warning(
            "tier lookup returned unknown tier %r for %s — defaulting to %s",
            str(tier).replace("\n", "").replace("\r", ""),
            tenant_id.replace("\n", "").replace("\r", ""),
            DEFAULT_TIER,
        )
        return DEFAULT_TIER
    return tier


def limits_for(tier: Tier) -> tuple[int, int]:
    """Return ``(limit, window_size_s)`` for a tier. Raises
    UnknownTierError when ``tier`` is not in TIER_LIMITS — caller bug,
    not a runtime fall-back case."""
    if tier not in TIER_LIMITS:
        raise UnknownTierError(f"unknown tier: {tier!r}")
    return TIER_LIMITS[tier]


async def enforce_for_tenant(
    *,
    tenant_id: str,
    now_unix: float | None = None,
) -> RateLimitDecision:
    """Look up tenant tier, fetch tier limits, enforce via rate_limiter.

    Convenience entry point for dispatcher API/proxy code — one call
    handles tier lookup + limit application. Raises
    ``RateLimitExceededError`` (re-raised from rate_limiter.enforce)
    when the tenant is over their per-window limit; caller maps to 429.
    """
    tier = get_tenant_tier(tenant_id)
    limit, window_size_s = limits_for(tier)
    return await rate_limiter.enforce(
        tenant_id=tenant_id,
        limit=limit,
        window_size_s=window_size_s,
        now_unix=now_unix,
    )
