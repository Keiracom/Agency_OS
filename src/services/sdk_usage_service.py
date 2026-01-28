"""
Contract: src/services/sdk_usage_service.py
Purpose: Log SDK agent usage to database for cost tracking
Layer: 3 - services
Imports: models
Consumers: sdk_agents, orchestration

This service persists SDK Brain usage to the sdk_usage_log table.
Called after every SDK agent execution to track:
- Token usage and costs (AUD)
- Execution metrics (turns, duration)
- Tool calls made
- Success/failure status
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def log_sdk_usage(
    db: AsyncSession,
    *,
    client_id: UUID,
    agent_type: str,
    model_used: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    cost_aud: float = 0.0,
    turns_used: int = 1,
    duration_ms: int = 0,
    tool_calls: list[dict] | None = None,
    success: bool = True,
    error_message: str | None = None,
    lead_id: UUID | None = None,
    campaign_id: UUID | None = None,
    user_id: UUID | None = None,
) -> UUID:
    """
    Log SDK usage to database.

    Call this after every SDK agent execution to persist cost tracking.

    Args:
        db: Database session
        client_id: Client ID (required)
        agent_type: Type of agent (icp_extraction, enrichment, email, voice_kb, objection)
        model_used: Model ID used (e.g., claude-sonnet-4-20250514)
        input_tokens: Input tokens used
        output_tokens: Output tokens used
        cached_tokens: Cached tokens (prompt caching)
        cost_aud: Total cost in AUD
        turns_used: Number of agent turns
        duration_ms: Execution duration in milliseconds
        tool_calls: List of tool calls made
        success: Whether execution succeeded
        error_message: Error message if failed
        lead_id: Optional lead ID
        campaign_id: Optional campaign ID
        user_id: Optional user ID

    Returns:
        UUID of the created log entry
    """
    log_id = uuid4()
    tool_calls_json = tool_calls or []

    query = text("""
        INSERT INTO sdk_usage_log (
            id, client_id, lead_id, campaign_id, user_id,
            agent_type, model_used,
            input_tokens, output_tokens, cached_tokens, cost_aud,
            turns_used, duration_ms, tool_calls,
            success, error_message, created_at
        ) VALUES (
            :id, :client_id, :lead_id, :campaign_id, :user_id,
            :agent_type, :model_used,
            :input_tokens, :output_tokens, :cached_tokens, :cost_aud,
            :turns_used, :duration_ms, :tool_calls::jsonb,
            :success, :error_message, :created_at
        )
    """)

    await db.execute(
        query,
        {
            "id": str(log_id),
            "client_id": str(client_id),
            "lead_id": str(lead_id) if lead_id else None,
            "campaign_id": str(campaign_id) if campaign_id else None,
            "user_id": str(user_id) if user_id else None,
            "agent_type": agent_type,
            "model_used": model_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost_aud": cost_aud,
            "turns_used": turns_used,
            "duration_ms": duration_ms,
            "tool_calls": str(tool_calls_json).replace("'", '"'),  # Convert to JSON string
            "success": success,
            "error_message": error_message,
            "created_at": datetime.utcnow(),
        },
    )

    await db.commit()

    logger.info(
        f"Logged SDK usage: {agent_type} ${cost_aud:.4f} AUD",
        extra={
            "log_id": str(log_id),
            "client_id": str(client_id),
            "agent_type": agent_type,
            "cost_aud": cost_aud,
            "turns_used": turns_used,
            "success": success,
        },
    )

    return log_id


async def log_sdk_result(
    db: AsyncSession,
    result: Any,  # SDKBrainResult
    *,
    client_id: UUID,
    agent_type: str,
    lead_id: UUID | None = None,
    campaign_id: UUID | None = None,
    user_id: UUID | None = None,
) -> UUID:
    """
    Log SDK result directly from SDKBrainResult object.

    Convenience function that extracts fields from result.

    Args:
        db: Database session
        result: SDKBrainResult from sdk_brain.run()
        client_id: Client ID (required)
        agent_type: Type of agent
        lead_id: Optional lead ID
        campaign_id: Optional campaign ID
        user_id: Optional user ID

    Returns:
        UUID of the created log entry
    """
    return await log_sdk_usage(
        db,
        client_id=client_id,
        agent_type=agent_type,
        model_used=result.model_used or "unknown",
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cached_tokens=result.cached_tokens,
        cost_aud=result.cost_aud,
        turns_used=result.turns_used,
        duration_ms=result.duration_ms,
        tool_calls=result.tool_calls,
        success=result.success,
        error_message=result.error,
        lead_id=lead_id,
        campaign_id=campaign_id,
        user_id=user_id,
    )


async def get_client_sdk_spend(
    db: AsyncSession,
    client_id: UUID,
    days: int = 30,
) -> dict[str, Any]:
    """
    Get SDK spend summary for a client.

    Args:
        db: Database session
        client_id: Client ID
        days: Number of days to look back

    Returns:
        Dict with spend breakdown by agent type
    """
    query = text("""
        SELECT
            agent_type,
            COUNT(*) as call_count,
            SUM(cost_aud) as total_cost,
            SUM(input_tokens) as total_input_tokens,
            SUM(output_tokens) as total_output_tokens,
            AVG(cost_aud) as avg_cost_per_call
        FROM sdk_usage_log
        WHERE client_id = :client_id
        AND created_at >= NOW() - INTERVAL :days DAY
        AND deleted_at IS NULL
        GROUP BY agent_type
        ORDER BY total_cost DESC
    """)

    result = await db.execute(
        query,
        {
            "client_id": str(client_id),
            "days": f"{days} days",
        },
    )
    rows = result.fetchall()

    breakdown = {}
    total_cost = 0.0
    total_calls = 0

    for row in rows:
        breakdown[row.agent_type] = {
            "call_count": row.call_count,
            "total_cost": float(row.total_cost or 0),
            "total_input_tokens": row.total_input_tokens,
            "total_output_tokens": row.total_output_tokens,
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


async def get_daily_sdk_spend(
    db: AsyncSession,
    client_id: UUID | None = None,
    days: int = 7,
) -> list[dict[str, Any]]:
    """
    Get daily SDK spend (optionally filtered by client).

    Args:
        db: Database session
        client_id: Optional client ID filter
        days: Number of days to look back

    Returns:
        List of daily spend records
    """
    if client_id:
        query = text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as call_count,
                SUM(cost_aud) as total_cost
            FROM sdk_usage_log
            WHERE client_id = :client_id
            AND created_at >= NOW() - INTERVAL :days DAY
            AND deleted_at IS NULL
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        params = {"client_id": str(client_id), "days": f"{days} days"}
    else:
        query = text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as call_count,
                SUM(cost_aud) as total_cost
            FROM sdk_usage_log
            WHERE created_at >= NOW() - INTERVAL :days DAY
            AND deleted_at IS NULL
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        params = {"days": f"{days} days"}

    result = await db.execute(query, params)
    rows = result.fetchall()

    return [
        {
            "date": str(row.date),
            "call_count": row.call_count,
            "total_cost_aud": float(row.total_cost or 0),
        }
        for row in rows
    ]
