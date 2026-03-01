"""
Contract: src/services/cis_outcome_service.py
Purpose: CIS Learning Engine outcome data access service
Layer: 3 - services
Imports: integrations
Consumers: cis_learning_flow.py

Directive #147: CIS Learning Engine data access layer.

Provides data access functions for:
- Querying outcomes since last CIS run
- Counting meeting booked outcomes
- Logging weight adjustments to cis_adjustment_log
- Fetching/updating weights from ceo_memory
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# =========================================================================
# OUTCOME QUERIES
# =========================================================================


async def get_outcomes_since_last_run(
    db: AsyncSession,
    customer_id: str | None = None,
    days_back: int = 7,
) -> list[dict]:
    """
    Query outcomes for CIS analysis.

    Fetches outcomes since the last CIS run or within days_back window.
    Includes signals_active and propensity_at_send for each outcome.

    Args:
        db: Database session
        customer_id: Optional customer filter (None = global)
        days_back: Days to look back if no last run timestamp

    Returns:
        List of outcome dicts with signals_active, propensity_at_send, outcome_type
    """
    try:
        # First, try to get last run timestamp from cis_run_log
        last_run_query = text("""
            SELECT MAX(completed_at) as last_run
            FROM cis_run_log
            WHERE status = 'complete'
        """)
        last_run_result = await db.execute(last_run_query)
        last_run_row = last_run_result.fetchone()

        if last_run_row and last_run_row.last_run:
            since_date = last_run_row.last_run
        else:
            since_date = datetime.utcnow() - timedelta(days=days_back)

        # Build the outcomes query
        params: dict[str, Any] = {"since_date": since_date}

        customer_filter = ""
        if customer_id:
            customer_filter = "AND o.client_id = :customer_id"
            params["customer_id"] = customer_id

        query = text(f"""
            SELECT
                o.id,
                o.activity_id,
                o.lead_id,
                o.client_id,
                o.channel,
                o.als_score_at_send as propensity_at_send,
                o.als_tier_at_send as tier_at_send,
                o.final_outcome,
                CASE
                    WHEN o.meeting_booked_at IS NOT NULL THEN 'booked'
                    WHEN o.replied_at IS NOT NULL THEN 'replied'
                    WHEN o.opened_at IS NOT NULL THEN 'no_response'
                    WHEN o.delivered_at IS NOT NULL THEN 'bounced'
                    ELSE 'unknown'
                END as outcome_type,
                o.sent_at,
                o.created_at,
                -- Get signals_active from leads table
                l.signals_active
            FROM cis_outreach_outcomes o
            LEFT JOIN leads l ON o.lead_id = l.id
            WHERE o.sent_at >= :since_date
            {customer_filter}
            ORDER BY o.sent_at DESC
            LIMIT 5000
        """)

        result = await db.execute(query, params)
        rows = result.fetchall()

        outcomes = []
        for row in rows:
            outcomes.append({
                "id": str(row.id),
                "activity_id": str(row.activity_id) if row.activity_id else None,
                "lead_id": str(row.lead_id) if row.lead_id else None,
                "client_id": str(row.client_id) if row.client_id else None,
                "channel": row.channel,
                "propensity_at_send": row.propensity_at_send,
                "tier_at_send": row.tier_at_send,
                "final_outcome": row.final_outcome,
                "outcome_type": row.outcome_type,
                "sent_at": row.sent_at.isoformat() if row.sent_at else None,
                "signals_active": row.signals_active or [],
            })

        logger.info(f"CIS: Queried {len(outcomes)} outcomes since {since_date}")
        return outcomes

    except Exception as e:
        logger.error(f"CIS: Failed to query outcomes: {e}")
        return []


async def count_meeting_booked_outcomes(
    db: AsyncSession,
    customer_id: str | None = None,
    days_back: int = 7,
) -> int:
    """
    Count MEETING_BOOKED outcomes for threshold check.

    Args:
        db: Database session
        customer_id: Optional customer filter (None = global)
        days_back: Days to look back

    Returns:
        Count of meeting_booked outcomes
    """
    try:
        since_date = datetime.utcnow() - timedelta(days=days_back)
        params: dict[str, Any] = {"since_date": since_date}

        customer_filter = ""
        if customer_id:
            customer_filter = "AND client_id = :customer_id"
            params["customer_id"] = customer_id

        query = text(f"""
            SELECT COUNT(*) as count
            FROM cis_outreach_outcomes
            WHERE meeting_booked_at IS NOT NULL
            AND sent_at >= :since_date
            {customer_filter}
        """)

        result = await db.execute(query, params)
        row = result.fetchone()

        count = row.count if row else 0
        logger.info(f"CIS: Found {count} meeting_booked outcomes")
        return count

    except Exception as e:
        logger.error(f"CIS: Failed to count meeting outcomes: {e}")
        return 0


# =========================================================================
# WEIGHT ADJUSTMENT LOGGING
# =========================================================================


async def log_weight_adjustment(
    db: AsyncSession,
    customer_id: str | None,
    signal_name: str,
    weight_before: int,
    delta_applied: int,
    weight_after: int,
    confidence_score: float,
    outcome_sample_size: int,
    skipped: bool = False,
    skip_reason: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Log a weight adjustment to cis_adjustment_log.

    Creates an audit trail of all CIS weight changes for compliance
    and debugging.

    Args:
        db: Database session
        customer_id: Customer ID (None = global weights)
        signal_name: Name of the signal being adjusted
        weight_before: Weight value before adjustment
        delta_applied: Delta that was applied (0 if skipped)
        weight_after: Weight value after adjustment
        confidence_score: Claude's confidence score
        outcome_sample_size: Number of outcomes analyzed
        skipped: Whether adjustment was skipped
        skip_reason: Reason for skipping (if applicable)
        run_id: CIS run ID for grouping

    Returns:
        Dict with success status and log_id
    """
    try:
        query = text("""
            INSERT INTO cis_adjustment_log (
                customer_id,
                signal_name,
                weight_before,
                delta_applied,
                weight_after,
                confidence_score,
                outcome_sample_size,
                skipped,
                skip_reason,
                run_id,
                created_at
            ) VALUES (
                :customer_id,
                :signal_name,
                :weight_before,
                :delta_applied,
                :weight_after,
                :confidence_score,
                :outcome_sample_size,
                :skipped,
                :skip_reason,
                :run_id,
                NOW()
            )
            RETURNING id
        """)

        result = await db.execute(query, {
            "customer_id": customer_id,
            "signal_name": signal_name,
            "weight_before": weight_before,
            "delta_applied": delta_applied,
            "weight_after": weight_after,
            "confidence_score": confidence_score,
            "outcome_sample_size": outcome_sample_size,
            "skipped": skipped,
            "skip_reason": skip_reason,
            "run_id": run_id,
        })

        row = result.fetchone()
        await db.commit()

        log_id = str(row.id) if row else None
        action = "skipped" if skipped else "applied"
        logger.info(
            f"CIS: Logged adjustment for {signal_name}: "
            f"{weight_before} → {weight_after} ({action})"
        )

        return {"success": True, "log_id": log_id}

    except Exception as e:
        logger.error(f"CIS: Failed to log weight adjustment: {e}")
        return {"success": False, "error": str(e)}


# =========================================================================
# CEO MEMORY WEIGHT ACCESS
# =========================================================================


async def get_propensity_weights(db: AsyncSession) -> dict:
    """
    Fetch current propensity weights from ceo_memory.

    Weights are stored at key 'ceo:propensity_weights_v3'.

    Args:
        db: Database session

    Returns:
        Weights dict with 'weights' and 'negative' sections
    """
    try:
        query = text("""
            SELECT value
            FROM ceo_memory
            WHERE key = 'ceo:propensity_weights_v3'
        """)

        result = await db.execute(query)
        row = result.fetchone()

        if row and row.value:
            import json
            weights = json.loads(row.value) if isinstance(row.value, str) else row.value
            logger.info(f"CIS: Loaded propensity weights: {len(weights.get('weights', {}))} signals")
            return weights

        # Return default weights if not found
        logger.warning("CIS: No weights found in ceo_memory, using defaults")
        return {
            "weights": {
                "no_seo": 10,
                "new_dm_6mo": 15,
                "low_gmb_rating": 10,
                "active_ad_spend": 15,
                "growing_signals": 10,
                "pain_point_post": 20,
                "hiring_marketing": 10,
                "outdated_website": 10,
                "poor_digital_presence": 20,
                "negative_marketing_review": 10,
            },
            "negative": {
                "competitor": -25,
                "enterprise_200plus": -15,
                "large_internal_team": -20,
                "recently_signed_agency": -15,
            },
        }

    except Exception as e:
        logger.error(f"CIS: Failed to get propensity weights: {e}")
        return {"weights": {}, "negative": {}}


async def save_propensity_weights(
    db: AsyncSession,
    weights: dict,
) -> dict[str, Any]:
    """
    Save updated propensity weights to ceo_memory.

    Performs an upsert to ceo:propensity_weights_v3.

    Args:
        db: Database session
        weights: Updated weights dict

    Returns:
        Dict with success status
    """
    try:
        import json

        query = text("""
            INSERT INTO ceo_memory (key, value, updated_at)
            VALUES ('ceo:propensity_weights_v3', :value, NOW())
            ON CONFLICT (key) DO UPDATE
            SET value = :value, updated_at = NOW()
            RETURNING key
        """)

        result = await db.execute(query, {
            "value": json.dumps(weights),
        })

        await db.commit()

        logger.info(f"CIS: Saved updated propensity weights")
        return {"success": True}

    except Exception as e:
        logger.error(f"CIS: Failed to save propensity weights: {e}")
        return {"success": False, "error": str(e)}


# =========================================================================
# CIS RUN LOGGING
# =========================================================================


async def log_cis_run_start(
    db: AsyncSession,
    run_type: str = "weekly",
    customer_id: str | None = None,
) -> str:
    """
    Log start of a CIS run.

    Args:
        db: Database session
        run_type: Type of run (weekly, manual, etc.)
        customer_id: Customer ID (None = global)

    Returns:
        Run ID
    """
    try:
        query = text("""
            INSERT INTO cis_run_log (
                run_type,
                customer_id,
                status,
                started_at,
                created_at
            ) VALUES (
                :run_type,
                :customer_id,
                'running',
                NOW(),
                NOW()
            )
            RETURNING id
        """)

        result = await db.execute(query, {
            "run_type": run_type,
            "customer_id": customer_id,
        })

        row = result.fetchone()
        await db.commit()

        run_id = str(row.id) if row else None
        logger.info(f"CIS: Started run {run_id} (type={run_type})")
        return run_id

    except Exception as e:
        logger.error(f"CIS: Failed to log run start: {e}")
        return ""


async def log_cis_run_complete(
    db: AsyncSession,
    run_id: str,
    status: str,
    outcomes_analyzed: int = 0,
    adjustments_applied: int = 0,
    summary: str = "",
) -> dict[str, Any]:
    """
    Log completion of a CIS run.

    Args:
        db: Database session
        run_id: Run ID from log_cis_run_start
        status: Final status (complete, pending, failed)
        outcomes_analyzed: Number of outcomes analyzed
        adjustments_applied: Number of adjustments applied
        summary: Analysis summary

    Returns:
        Dict with success status
    """
    try:
        query = text("""
            UPDATE cis_run_log
            SET
                status = :status,
                completed_at = NOW(),
                outcomes_analyzed = :outcomes_analyzed,
                adjustments_applied = :adjustments_applied,
                summary = :summary
            WHERE id = :run_id
        """)

        await db.execute(query, {
            "run_id": run_id,
            "status": status,
            "outcomes_analyzed": outcomes_analyzed,
            "adjustments_applied": adjustments_applied,
            "summary": summary,
        })

        await db.commit()

        logger.info(f"CIS: Completed run {run_id} (status={status})")
        return {"success": True}

    except Exception as e:
        logger.error(f"CIS: Failed to log run completion: {e}")
        return {"success": False, "error": str(e)}
