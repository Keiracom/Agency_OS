"""KEI-212 — Per-tenant API spend tracker for the Dispatcher.

Called by ``interceptor_proxy`` (KEI-210) on every model-call completion.
Each ``record()`` call:

1. Writes one row to ``public.infra_spend_metrics`` (Supabase) for billing
   and audit. Fail-open: the Valkey side still runs even if the SQL leg
   raises — counters must stay accurate for budget enforcement.
2. Increments Valkey counters ``spend:<tenant_id>:daily`` and
   ``spend:<tenant_id>:monthly`` using ``INCRBY``. TTLs are set on the
   first write so the bucket auto-evicts at midnight UTC (daily) and
   month boundary UTC (monthly). No cron / reset job required.
3. If the tenant has a non-NULL ``tenants.daily_budget_aud_cents`` and the
   running daily total exceeds it, publishes a fail-open warn to NATS
   subject ``keiracom.dispatcher.spend.warn.<tenant_id>`` and writes a
   ``public.budget_warn_audit`` row. **No session kill at this stage —
   warn-only per KEI-212 spec.**

**Currency (LAW II — Australia First):** every monetary field is integer
``$AUD cents``. LiteLLM returns USD; ``cost_aud_cents_from_usd()`` is the
canonical conversion (multiplier ``USD_TO_AUD_RATE`` per CLAUDE.md). The
public ``record()`` signature takes ``cost_aud_cents: int`` so the caller
(interceptor_proxy) owns the conversion at ingress and we never store USD.

Key namespace follows the KEI-117A contract documented in
``valkey_pool.py`` (``<family>:<tenant_id>:<period>``).
"""

from __future__ import annotations

import calendar
import json
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Literal

from src.dispatcher.valkey_pool import get_valkey_client

logger = logging.getLogger(__name__)

SPEND_NAMESPACE_PREFIX = "spend"
NATS_URL_ENV = "NATS_URL"
DEFAULT_NATS_URL = "nats://127.0.0.1:4222"
SUPABASE_DSN_ENV = "SUPABASE_DB_DSN"

# LAW II — Australia First. 1 USD = 1.55 AUD per CLAUDE.md.
USD_TO_AUD_RATE = 1.55

Period = Literal["daily", "monthly"]


def tenant_spend_key(tenant_id: str, period: Period) -> str:
    """Build a per-tenant spend key: ``spend:<tenant_id>:<period>``.

    Refuses empty/whitespace tenant_id (matches valkey_pool.tenant_rl_key
    semantics — no unscoped namespaces).
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id must be a non-empty string")
    if period not in ("daily", "monthly"):
        raise ValueError(f"period must be 'daily' or 'monthly', got {period!r}")
    return f"{SPEND_NAMESPACE_PREFIX}:{tenant_id.strip()}:{period}"


def cost_aud_cents_from_usd(cost_usd: float) -> int:
    """Convert a USD float (e.g. ``litellm.cost_per_token`` output) to
    integer $AUD cents. Always rounds half-away-from-zero so a 0.001-cent
    fragment never disappears from billing totals.
    """
    if cost_usd < 0:
        raise ValueError(f"cost_usd must be non-negative, got {cost_usd}")
    return int(round(cost_usd * USD_TO_AUD_RATE * 100))


def _seconds_until_midnight_utc(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - now).total_seconds()), 1)


def _seconds_until_month_boundary_utc(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    last_day = calendar.monthrange(now.year, now.month)[1]
    next_month = now.replace(
        day=last_day, hour=23, minute=59, second=59, microsecond=0
    ) + timedelta(seconds=1)
    return max(int((next_month - now).total_seconds()), 1)


def _compute_cost_aud_cents(model: str, tokens_in: int, tokens_out: int) -> int | None:
    """Return computed cost via litellm converted to $AUD cents; ``None``
    if litellm is unavailable or the model is unknown. Caller falls back
    to its own ``cost_aud_cents`` in that case (interceptor_proxy already
    holds the upstream-API cost).
    """
    try:
        from litellm import cost_per_token  # noqa: PLC0415 — optional dep
    except ImportError:
        logger.debug("litellm not installed — caller cost_aud_cents will be used verbatim")
        return None
    try:
        prompt_cost_usd, completion_cost_usd = cost_per_token(
            model=model,
            prompt_tokens=tokens_in,
            completion_tokens=tokens_out,
        )
        total_usd = float(prompt_cost_usd) + float(completion_cost_usd)
        return cost_aud_cents_from_usd(total_usd)
    except Exception as exc:  # noqa: BLE001 — model unknown / litellm internal error
        logger.warning("litellm.cost_per_token failed for model=%s: %s", model, exc)
        return None


async def _publish_nats_warn(
    tenant_id: str, daily_spend_aud_cents: int, budget_aud_cents: int
) -> bool:
    """Fail-open publish to ``keiracom.dispatcher.spend.warn.<tenant_id>``.

    Returns True on publish success, False on any failure. Mirrors the
    fleet_supervisor._nats_publish_state pattern. Payload monetary fields
    are integer $AUD cents.
    """
    try:
        import nats.aio.client as nats_client  # noqa: PLC0415 — optional dep

        url = os.environ.get(NATS_URL_ENV, DEFAULT_NATS_URL)
        subject = f"keiracom.dispatcher.spend.warn.{tenant_id}"
        payload = json.dumps(
            {
                "tenant_id": tenant_id,
                "daily_spend_aud_cents": daily_spend_aud_cents,
                "budget_aud_cents": budget_aud_cents,
                "ts": int(time.time()),
            }
        ).encode()
        nc = nats_client.Client()
        await nc.connect(url, connect_timeout=2)
        try:
            await nc.publish(subject, payload)
            await nc.flush()
        finally:
            await nc.close()
        logger.info(
            "NATS PUBLISH spend.warn tenant=%s daily_aud_cents=%d budget_aud_cents=%d",
            tenant_id,
            daily_spend_aud_cents,
            budget_aud_cents,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — NATS down / nats-py missing
        logger.warning("NATS spend.warn publish failed (non-fatal): %s", exc)
        return False


async def _write_spend_row(
    tenant_id: int,
    callsign: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_aud_cents: int,
    metadata: dict,
) -> bool:
    """Insert one row into ``public.infra_spend_metrics``. Fail-open
    (returns False on failure but never raises) so Valkey counters stay
    accurate even when the SQL leg is degraded.
    """
    dsn = os.environ.get(SUPABASE_DSN_ENV)
    if not dsn:
        logger.warning("SUPABASE_DB_DSN unset — skipping infra_spend_metrics write")
        return False
    try:
        import asyncpg  # noqa: PLC0415 — optional in some test envs

        dsn = dsn.replace("+asyncpg", "")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(
                """
                INSERT INTO public.infra_spend_metrics
                    (tenant_id, callsign, model, tokens_in, tokens_out,
                     cost_aud_cents, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                """,
                tenant_id,
                callsign,
                model,
                tokens_in,
                tokens_out,
                cost_aud_cents,
                json.dumps(metadata),
            )
        finally:
            await conn.close()
        return True
    except Exception as exc:  # noqa: BLE001 — Supabase degraded
        logger.warning("infra_spend_metrics insert failed (non-fatal): %s", exc)
        return False


async def _write_budget_warn_audit(
    tenant_id: int,
    daily_spend_aud_cents: int,
    budget_aud_cents: int,
    nats_published: bool,
) -> None:
    dsn = os.environ.get(SUPABASE_DSN_ENV)
    if not dsn:
        return
    try:
        import asyncpg  # noqa: PLC0415

        dsn = dsn.replace("+asyncpg", "")
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(
                """
                INSERT INTO public.budget_warn_audit
                    (tenant_id, daily_spend_aud_cents, budget_aud_cents, nats_published)
                VALUES ($1, $2, $3, $4)
                """,
                tenant_id,
                daily_spend_aud_cents,
                budget_aud_cents,
                nats_published,
            )
        finally:
            await conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("budget_warn_audit insert failed (non-fatal): %s", exc)


async def _read_daily_budget_aud_cents(tenant_id: int) -> int | None:
    """Read ``tenants.daily_budget_aud_cents`` for tenant. None = no budget set."""
    dsn = os.environ.get(SUPABASE_DSN_ENV)
    if not dsn:
        return None
    try:
        import asyncpg  # noqa: PLC0415

        dsn = dsn.replace("+asyncpg", "")
        conn = await asyncpg.connect(dsn)
        try:
            row = await conn.fetchrow(
                "SELECT daily_budget_aud_cents FROM public.tenants WHERE id = $1",
                tenant_id,
            )
            if not row or row["daily_budget_aud_cents"] is None:
                return None
            return int(row["daily_budget_aud_cents"])
        finally:
            await conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("tenants.daily_budget_aud_cents read failed (non-fatal): %s", exc)
        return None


async def _incrby_with_ttl(client, key: str, amount: int, ttl_seconds: int) -> int:
    """Atomically INCRBY + EXPIRE (only set TTL on first write so the
    bucket actually evicts at the period boundary). Returns the post-incr
    counter as int $AUD cents.
    """
    pipe = client.pipeline(transaction=False)
    pipe.exists(key)
    pipe.incrby(key, amount)
    existed, new_value = await pipe.execute()
    if not existed:
        await client.expire(key, ttl_seconds)
    return int(new_value)


async def record(
    *,
    tenant_id: int,
    callsign: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_aud_cents: int,
    metadata: dict | None = None,
) -> dict:
    """Record one model-call completion.

    Args:
        tenant_id: integer tenant id (KEI-181 schema).
        callsign: agent that triggered the call (elliot/aiden/max/...).
        model: model name as understood by litellm (e.g. ``claude-sonnet-4-5``).
        tokens_in: prompt token count.
        tokens_out: completion token count.
        cost_aud_cents: caller-computed cost in integer $AUD cents (LAW II).
            ``record()`` re-computes via ``litellm.cost_per_token`` when
            available and uses the LiteLLM value when within 1% of the
            caller value (acceptance criterion). On larger divergence the
            LiteLLM value is recorded and a warning is logged.
        metadata: optional jsonb payload (request id, route, etc.).

    Returns:
        Dict with the recorded ``cost_aud_cents``, post-incr daily total
        (cents), post-incr monthly total (cents), and whether a budget warn
        fired. Never raises — all external legs are fail-open.
    """
    metadata = metadata or {}
    litellm_cost_cents = _compute_cost_aud_cents(model, tokens_in, tokens_out)
    if litellm_cost_cents is not None and cost_aud_cents > 0:
        divergence = abs(litellm_cost_cents - cost_aud_cents) / cost_aud_cents
        if divergence > 0.01:
            logger.warning(
                "cost divergence > 1%% model=%s caller_aud_cents=%d litellm_aud_cents=%d",
                model,
                cost_aud_cents,
                litellm_cost_cents,
            )
        recorded_cents = litellm_cost_cents
    elif litellm_cost_cents is not None:
        recorded_cents = litellm_cost_cents
    else:
        recorded_cents = cost_aud_cents

    await _write_spend_row(
        tenant_id, callsign, model, tokens_in, tokens_out, recorded_cents, metadata
    )

    tenant_key = str(tenant_id)
    daily_key = tenant_spend_key(tenant_key, "daily")
    monthly_key = tenant_spend_key(tenant_key, "monthly")
    client = get_valkey_client()
    try:
        daily_total = await _incrby_with_ttl(
            client, daily_key, recorded_cents, _seconds_until_midnight_utc()
        )
        monthly_total = await _incrby_with_ttl(
            client, monthly_key, recorded_cents, _seconds_until_month_boundary_utc()
        )
    finally:
        await client.aclose()

    warn_fired = False
    budget_cents = await _read_daily_budget_aud_cents(tenant_id)
    if budget_cents is not None and daily_total > budget_cents:
        published = await _publish_nats_warn(tenant_key, daily_total, budget_cents)
        await _write_budget_warn_audit(tenant_id, daily_total, budget_cents, published)
        warn_fired = True

    return {
        "cost_aud_cents": recorded_cents,
        "daily_total_aud_cents": daily_total,
        "monthly_total_aud_cents": monthly_total,
        "budget_warn_fired": warn_fired,
    }


async def get_spend(tenant_id: int, period: Period = "daily") -> int:
    """Return the current Valkey-tracked spend for a tenant in integer
    $AUD cents. Returns 0 if the key is absent (no spend yet this period).
    """
    key = tenant_spend_key(str(tenant_id), period)
    client = get_valkey_client()
    try:
        raw = await client.get(key)
    finally:
        await client.aclose()
    return int(raw) if raw else 0
