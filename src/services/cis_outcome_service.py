"""
Contract: src/services/cis_outcome_service.py
Purpose: CIS Learning Engine outcome data access service
Layer: 3 - services
Imports: integrations
Consumers: cis_learning_flow.py

Directive #147: CIS Learning Engine data access layer.
Directive #157 Gap 3: Timing Signal Extraction

Provides data access functions for:
- Querying outcomes since last CIS run
- Counting meeting booked outcomes
- Logging weight adjustments to cis_adjustment_log
- Fetching/updating weights from ceo_memory
- Extracting timing signals from activities (Gap 3)
- Aggregating timing data to platform_timing_signals (Gap 3)
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

        # Gap 2 fix (Directive #157): Include negative signal timestamps and outcomes
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
                    -- Gap 2: Check negative signal outcomes BEFORE positive engagement
                    WHEN o.final_outcome = 'data_quality_failure' THEN 'data_quality_failure'
                    WHEN o.final_outcome = 'targeting_failure' THEN 'targeting_failure'
                    WHEN o.final_outcome = 'soft_rejection' THEN 'soft_rejection'
                    WHEN o.bounced_at IS NOT NULL THEN 'bounced'
                    WHEN o.complained_at IS NOT NULL THEN 'complained'
                    WHEN o.unsubscribed_at IS NOT NULL THEN 'unsubscribed'
                    WHEN o.opened_at IS NOT NULL THEN 'no_response'
                    WHEN o.delivered_at IS NOT NULL THEN 'delivered_only'
                    ELSE 'unknown'
                END as outcome_type,
                o.sent_at,
                o.created_at,
                -- Negative signal timestamps (Gap 2)
                o.bounced_at,
                o.complained_at,
                o.unsubscribed_at,
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
                # Gap 2: Include negative signal timestamps
                "bounced_at": row.bounced_at.isoformat() if row.bounced_at else None,
                "complained_at": row.complained_at.isoformat() if row.complained_at else None,
                "unsubscribed_at": row.unsubscribed_at.isoformat() if row.unsubscribed_at else None,
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


# =========================================================================
# TIMING SIGNAL EXTRACTION (Directive #157 - Gap 3)
# =========================================================================


def _convert_dow_to_iso(pg_dow: int | None) -> int:
    """
    Convert PostgreSQL day of week to ISO 8601.

    PostgreSQL DOW: 0=Sunday, 6=Saturday
    ISO 8601: 0=Monday, 6=Sunday

    Args:
        pg_dow: PostgreSQL day of week value

    Returns:
        ISO 8601 day of week (0=Monday)
    """
    if pg_dow is None:
        return 1  # Default to Tuesday (common business day)
    # PG: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
    # ISO: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    return (pg_dow - 1) % 7 if pg_dow > 0 else 6


def _derive_company_size(employee_count: int | str | None) -> str:
    """
    Derive company size bucket from employee count.

    Args:
        employee_count: Number of employees or range string

    Returns:
        Size bucket: 'smb', 'mid_market', or 'enterprise'
    """
    if employee_count is None:
        return "smb"  # Default to SMB

    # Handle range strings like "11-50", "51-200"
    if isinstance(employee_count, str):
        if "-" in employee_count:
            try:
                employee_count = int(employee_count.split("-")[1])
            except (ValueError, IndexError):
                return "smb"
        else:
            try:
                employee_count = int(employee_count.replace("+", ""))
            except ValueError:
                return "smb"

    if employee_count < 50:
        return "smb"
    elif employee_count < 500:
        return "mid_market"
    else:
        return "enterprise"


async def extract_timing_from_activity(
    db: AsyncSession,
    activity_id: str,
) -> dict[str, Any] | None:
    """
    Extract timing signals from an activity record.

    Reads the activity's timing columns (lead_local_day_of_week,
    lead_local_time, touch_number) which are set by DB trigger
    on activity creation.

    Args:
        db: Database session
        activity_id: ID of the activity to extract timing from

    Returns:
        Dict with day_of_week (0=Monday), hour_of_day (0-23), touch_number
        or None if activity not found
    """
    try:
        query = text("""
            SELECT
                a.id,
                a.lead_id,
                a.client_id,
                a.channel,
                a.lead_local_day_of_week,
                a.lead_local_time,
                a.touch_number,
                a.created_at,
                l.industry,
                l.employee_count,
                l.company_name
            FROM activities a
            LEFT JOIN leads l ON a.lead_id = l.id
            WHERE a.id = :activity_id
        """)

        result = await db.execute(query, {"activity_id": activity_id})
        row = result.fetchone()

        if not row:
            logger.warning(f"CIS Timing: Activity {activity_id} not found")
            return None

        # Convert PostgreSQL DOW (0=Sunday) to ISO 8601 (0=Monday)
        day_of_week = _convert_dow_to_iso(row.lead_local_day_of_week)

        # Extract hour from lead_local_time
        hour_of_day = 10  # Default business hour
        if row.lead_local_time is not None:
            hour_of_day = row.lead_local_time.hour

        # Touch number defaults to 1
        touch_number = row.touch_number if row.touch_number else 1

        # Derive company size
        company_size = _derive_company_size(row.employee_count)

        # Get channel value
        channel = row.channel
        if hasattr(channel, "value"):
            channel = channel.value

        timing_data = {
            "activity_id": str(row.id),
            "lead_id": str(row.lead_id) if row.lead_id else None,
            "client_id": str(row.client_id) if row.client_id else None,
            "day_of_week": day_of_week,  # 0=Monday, 6=Sunday (ISO 8601)
            "hour_of_day": hour_of_day,  # 0-23
            "touch_number": touch_number,
            "channel": channel or "email",
            "industry": row.industry or "unknown",
            "company_size": company_size,
            "company_name": row.company_name,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

        logger.debug(
            f"CIS Timing: Extracted from activity {activity_id}: "
            f"day={day_of_week}, hour={hour_of_day}, touch={touch_number}"
        )
        return timing_data

    except Exception as e:
        logger.error(f"CIS Timing: Failed to extract from activity {activity_id}: {e}")
        return None


async def record_timing_signal(
    db: AsyncSession,
    industry: str,
    channel: str,
    company_size: str,
    day_of_week: int,
    hour_of_day: int,
    touch_number: int,
    is_conversion: bool,
) -> dict[str, Any]:
    """
    Record a timing signal to platform_timing_signals.

    Uses the update_platform_timing_signal database function
    which handles upsert and aggregation.

    Args:
        db: Database session
        industry: Lead's industry
        channel: Outreach channel (email, linkedin, etc.)
        company_size: Size bucket (smb, mid_market, enterprise)
        day_of_week: 0=Monday, 6=Sunday (ISO 8601)
        hour_of_day: 0-23 in lead's local time
        touch_number: Which touch in sequence (1, 2, 3...)
        is_conversion: Whether this activity resulted in conversion

    Returns:
        Dict with success status
    """
    try:
        # Normalize inputs
        industry = (industry or "unknown").lower().strip()
        channel = (channel or "email").lower().strip()
        company_size = company_size or "smb"

        # Validate ranges
        day_of_week = max(0, min(6, day_of_week))
        hour_of_day = max(0, min(23, hour_of_day))
        touch_number = max(1, min(10, touch_number))  # Cap at 10 touches

        query = text("""
            SELECT update_platform_timing_signal(
                :industry,
                :channel,
                :company_size,
                :day_of_week,
                :hour_of_day,
                :touch_number,
                :is_conversion
            )
        """)

        await db.execute(query, {
            "industry": industry,
            "channel": channel,
            "company_size": company_size,
            "day_of_week": day_of_week,
            "hour_of_day": hour_of_day,
            "touch_number": touch_number,
            "is_conversion": is_conversion,
        })

        await db.commit()

        action = "conversion" if is_conversion else "attempt"
        logger.info(
            f"CIS Timing: Recorded {action} for {industry}/{channel}/{company_size} "
            f"(day={day_of_week}, hour={hour_of_day}, touch={touch_number})"
        )

        return {"success": True}

    except Exception as e:
        logger.error(f"CIS Timing: Failed to record signal: {e}")
        return {"success": False, "error": str(e)}


async def process_conversion_timing(
    db: AsyncSession,
    activity_id: str,
) -> dict[str, Any]:
    """
    Process timing signals from a converting activity.

    Called when a MEETING_BOOKED outcome is recorded.
    Extracts timing data and records to platform_timing_signals.

    Args:
        db: Database session
        activity_id: ID of the converting activity

    Returns:
        Dict with timing data extracted and success status
    """
    # Extract timing from activity
    timing = await extract_timing_from_activity(db, activity_id)

    if not timing:
        return {
            "success": False,
            "error": "Could not extract timing from activity",
        }

    # Record the conversion timing signal
    result = await record_timing_signal(
        db=db,
        industry=timing["industry"],
        channel=timing["channel"],
        company_size=timing["company_size"],
        day_of_week=timing["day_of_week"],
        hour_of_day=timing["hour_of_day"],
        touch_number=timing["touch_number"],
        is_conversion=True,
    )

    return {
        "success": result.get("success", False),
        "timing": timing,
        "error": result.get("error"),
    }


async def get_timing_insights(
    db: AsyncSession,
    industry: str,
    channel: str | None = None,
    company_size: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query timing insights for a segment.

    Returns pre-computed timing patterns from platform_timing_signals.

    Args:
        db: Database session
        industry: Industry to query
        channel: Optional channel filter
        company_size: Optional size filter

    Returns:
        List of timing insight dicts
    """
    try:
        query = text("""
            SELECT * FROM get_timing_insights(:industry, :channel, :company_size)
        """)

        result = await db.execute(query, {
            "industry": industry.lower().strip(),
            "channel": channel.lower().strip() if channel else None,
            "company_size": company_size,
        })

        rows = result.fetchall()
        insights = []

        for row in rows:
            insights.append({
                "industry": row.industry,
                "channel": row.channel,
                "company_size": row.company_size,
                "best_day": row.best_day,
                "best_hour": row.best_hour,
                "best_touchpoint": row.best_touchpoint,
                "avg_touchpoint": float(row.avg_touchpoint) if row.avg_touchpoint else None,
                "conversion_rate": float(row.conversion_rate) if row.conversion_rate else None,
                "total_conversions": row.total_conversions,
                "confidence": row.confidence,
            })

        logger.info(f"CIS Timing: Found {len(insights)} insights for {industry}")
        return insights

    except Exception as e:
        logger.error(f"CIS Timing: Failed to get insights: {e}")
        return []


async def backfill_timing_signals_from_outcomes(
    db: AsyncSession,
    days_back: int = 90,
    limit: int = 1000,
) -> dict[str, Any]:
    """
    Backfill timing signals from historical conversion outcomes.

    One-time migration helper to populate platform_timing_signals
    from existing cis_outreach_outcomes with meeting_booked_at.

    Args:
        db: Database session
        days_back: How many days back to look
        limit: Max outcomes to process

    Returns:
        Dict with processed count and errors
    """
    try:
        # Get converting outcomes with activity IDs
        query = text("""
            SELECT
                o.id,
                o.activity_id,
                o.channel,
                a.lead_local_day_of_week,
                a.lead_local_time,
                a.touch_number,
                l.industry,
                l.employee_count
            FROM cis_outreach_outcomes o
            JOIN activities a ON o.activity_id = a.id
            LEFT JOIN leads l ON o.lead_id = l.id
            WHERE o.meeting_booked_at IS NOT NULL
            AND o.sent_at >= NOW() - :days_back * INTERVAL '1 day'
            ORDER BY o.meeting_booked_at DESC
            LIMIT :limit
        """)

        result = await db.execute(query, {"days_back": days_back, "limit": limit})
        rows = result.fetchall()

        processed = 0
        errors = 0

        for row in rows:
            try:
                # Convert timing data
                day_of_week = _convert_dow_to_iso(row.lead_local_day_of_week)
                hour_of_day = row.lead_local_time.hour if row.lead_local_time else 10
                touch_number = row.touch_number or 1
                company_size = _derive_company_size(row.employee_count)

                channel = row.channel
                if hasattr(channel, "value"):
                    channel = channel.value

                await record_timing_signal(
                    db=db,
                    industry=row.industry or "unknown",
                    channel=channel or "email",
                    company_size=company_size,
                    day_of_week=day_of_week,
                    hour_of_day=hour_of_day,
                    touch_number=touch_number,
                    is_conversion=True,
                )
                processed += 1

            except Exception as e:
                logger.warning(f"CIS Timing: Error backfilling outcome {row.id}: {e}")
                errors += 1

        logger.info(f"CIS Timing: Backfill complete - {processed} processed, {errors} errors")
        return {"processed": processed, "errors": errors, "success": True}

    except Exception as e:
        logger.error(f"CIS Timing: Backfill failed: {e}")
        return {"processed": 0, "errors": 1, "success": False, "error": str(e)}
