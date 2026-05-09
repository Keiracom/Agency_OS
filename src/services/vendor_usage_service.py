"""
Contract: src/services/vendor_usage_service.py
Purpose: Log non-token vendor API usage to database for cost tracking
Layer: 3 - services
Imports: sqlalchemy
Consumers: src/integrations/{dataforseo, leadmagic, contactout, brightdata} clients

Mirror of sdk_usage_service for the vendor side. Persists per-call records
to vendor_usage_log. Called after each non-token vendor API hit (DataForSEO
SERP, Leadmagic email find, ContactOut record, Bright Data GMB lookup, etc.).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def log_vendor_usage(
    db: AsyncSession,
    *,
    client_id: UUID,
    vendor: str,
    endpoint: str,
    cost_aud: float = 0.0,
    units: int = 1,
    units_unit: str = "api_calls",
    duration_ms: int = 0,
    success: bool = True,
    error_message: str | None = None,
    lead_id: UUID | None = None,
) -> UUID:
    """Log a non-token vendor API call to vendor_usage_log.

    Args:
        db: Database session
        client_id: Client ID (use SYSTEM_PIPELINE_CLIENT_ID sentinel for pipeline runs)
        vendor: Vendor identifier — "dataforseo" | "leadmagic" | "contactout" | "brightdata"
        endpoint: Vendor endpoint or operation name (e.g. "domain_rank_overview")
        cost_aud: Total cost in Australian dollars (USD × settings.aud_per_usd at write time)
        units: Volume of work charged for (records / credits / api_calls)
        units_unit: Unit type — "records" | "credits" | "api_calls"
        duration_ms: Wall-clock duration of the call
        success: Whether the call succeeded
        error_message: Error message if failed
        lead_id: Optional lead ID context

    Returns:
        UUID of the created log entry
    """
    log_id = uuid4()

    query = text("""
        INSERT INTO vendor_usage_log (
            id, client_id, lead_id,
            vendor, endpoint,
            units, units_unit, cost_aud, duration_ms,
            success, error_message, created_at
        ) VALUES (
            :id, :client_id, :lead_id,
            :vendor, :endpoint,
            :units, :units_unit, :cost_aud, :duration_ms,
            :success, :error_message, :created_at
        )
    """)

    await db.execute(
        query,
        {
            "id": str(log_id),
            "client_id": str(client_id),
            "lead_id": str(lead_id) if lead_id else None,
            "vendor": vendor,
            "endpoint": endpoint,
            "units": units,
            "units_unit": units_unit,
            "cost_aud": cost_aud,
            "duration_ms": duration_ms,
            "success": success,
            "error_message": error_message,
            "created_at": datetime.now(UTC),
        },
    )

    await db.commit()

    logger.info(
        f"Logged vendor usage: {vendor}/{endpoint} ${cost_aud:.4f} AUD",
        extra={
            "log_id": str(log_id),
            "client_id": str(client_id),
            "vendor": vendor,
            "endpoint": endpoint,
            "cost_aud": cost_aud,
            "success": success,
        },
    )

    return log_id


async def get_client_vendor_spend(
    db: AsyncSession,
    client_id: UUID,
    days: int = 30,
) -> dict[str, Any]:
    """Vendor spend summary for a client over the last N days, grouped by vendor."""
    query = text("""
        SELECT
            vendor,
            COUNT(*) AS call_count,
            SUM(cost_aud) AS total_cost,
            SUM(units) AS total_units,
            AVG(cost_aud) AS avg_cost_per_call
        FROM vendor_usage_log
        WHERE client_id = :client_id
          AND created_at >= NOW() - (CAST(:days AS int) * INTERVAL '1 day')
          AND deleted_at IS NULL
        GROUP BY vendor
        ORDER BY total_cost DESC
    """)

    result = await db.execute(query, {"client_id": str(client_id), "days": days})
    rows = result.fetchall()

    breakdown: dict[str, dict[str, Any]] = {}
    total_cost = 0.0
    total_calls = 0
    for row in rows:
        breakdown[row.vendor] = {
            "call_count": row.call_count,
            "total_cost": float(row.total_cost or 0),
            "total_units": int(row.total_units or 0),
            "avg_cost_per_call": float(row.avg_cost_per_call or 0),
        }
        total_cost += float(row.total_cost or 0)
        total_calls += row.call_count

    return {
        "client_id": str(client_id),
        "period_days": days,
        "total_cost_aud": total_cost,
        "total_calls": total_calls,
        "breakdown": breakdown,
    }
