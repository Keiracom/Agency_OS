"""Per-tenant concurrency ceiling lookup for the work-loop consumer.

Reads `keiracom_tenants.max_concurrent_tasks` (added 2026-05-28). Fail-open and
cost-safe: any lookup failure returns the smallest ceiling (DEFAULT_CEILING)
rather than 0 (which would stall the loop) or unbounded (which would over-spawn
and burn budget). Tier fallbacks cover a NULL column.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

# Dispatch tiers: Solo=2, Pro=6, Team=20. Schema enum is solo/pro/scale, so the
# dispatch's "Team" maps to 'scale'. 'team' kept too in case a budgets-tier value
# (sandbox/solo/pro/team/enterprise) ever reaches this path.
TIER_DEFAULTS: dict[str, int] = {"solo": 2, "pro": 6, "scale": 20, "team": 20, "enterprise": 20}
DEFAULT_CEILING = 2  # cost-safe fallback when tenant/tier is unknown

# Operator-uncap (Agency_OS-w667): the fleet/operator runs under the
# FLEET_TENANT_ID slug, which has NO keiracom_tenants row (that table is
# UUID-keyed) — so it would fail-open to DEFAULT_CEILING and gate Dave-as-operator
# at 2. Treat that slug as effectively uncapped. A real tenant_id is always a
# UUID, so the slug uniquely identifies the operator (no collision risk).
DEFAULT_FLEET_TENANT_ID = "default"
FLEET_OPERATOR_CEILING = 1000


def _fleet_tenant_id() -> str:
    return os.environ.get("FLEET_TENANT_ID") or DEFAULT_FLEET_TENANT_ID


TenantRow = tuple[int | None, str | None]  # (max_concurrent_tasks, tier)
CeilingFetch = Callable[[str], Awaitable[TenantRow | None]]


def _dsn() -> str | None:
    dsn = os.environ.get("SUPABASE_DB_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


async def _db_fetch(tenant_id: str) -> TenantRow | None:
    dsn = _dsn()
    if not dsn:
        return None
    from src.utils.asyncpg_connection import get_asyncpg_connection

    conn = await get_asyncpg_connection(dsn)
    try:
        row: Any = await conn.fetchrow(
            "SELECT max_concurrent_tasks, tier::text AS tier "
            "FROM public.keiracom_tenants WHERE tenant_id = $1",
            tenant_id,
        )
    finally:
        await conn.close()
    return (row["max_concurrent_tasks"], row["tier"]) if row else None


async def get_ceiling(tenant_id: str, *, fetch: CeilingFetch | None = None) -> int:
    """Resolve the tenant's concurrent-spawn ceiling. Fail-open to DEFAULT_CEILING.

    The fleet/operator slug returns FLEET_OPERATOR_CEILING so Dave-as-operator is
    never gated (Agency_OS-w667) — it has no DB row to read a ceiling from.
    """
    if tenant_id == _fleet_tenant_id():
        return FLEET_OPERATOR_CEILING
    try:
        row = await (fetch or _db_fetch)(tenant_id)
    except Exception:  # noqa: BLE001 — never block the loop on a lookup error
        logger.warning("work-loop: ceiling lookup failed for tenant=%s", tenant_id, exc_info=True)
        return DEFAULT_CEILING
    if row is None:
        return DEFAULT_CEILING
    max_concurrent, tier = row
    if max_concurrent and max_concurrent > 0:
        return int(max_concurrent)
    return TIER_DEFAULTS.get((tier or "").lower(), DEFAULT_CEILING)
