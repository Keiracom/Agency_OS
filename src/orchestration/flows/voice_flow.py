"""
FILE: src/orchestration/flows/voice_flow.py
PURPOSE: Voice outreach flow with compliance validation and ElevenLabs integration
PHASE: 7 (Voice Outreach)
TASK: FLOW-029

VOICE STACK: ElevenAgents + Twilio AU
  - Vapi deprecated and removed (2026-02-25)
  - Active client: src/integrations/elevenagets_client.py
  - Twilio AU number: +61240126220 (voice-only)
  - Morgan assistant in Vapi dashboard is STALE - do not use

DEPENDENCIES:
  - src/integrations/supabase.py
  - src/integrations/elevenagets_client.py
  - src/services/voice_compliance_validator.py
  - src/services/voice_context_builder.py
  - src/models/lead.py
  - src/models/campaign.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation before every outreach
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits
CONCURRENCY:
  - Max 3 simultaneous calls per agency (spam signal avoidance)
SCHEDULE:
  - Monday-Friday: 09:00-20:00 AEST (every 30 min)
  - Saturday: 09:00-17:00 AEST (every 30 min)
  - Sunday/Public Holidays: DISABLED
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from prefect import flow, get_run_logger, task
from prefect.concurrency.asyncio import concurrency as prefect_concurrency
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import text

from src.integrations.supabase import get_db_session
from src.models.base import (
    CampaignStatus,
)

logger = logging.getLogger(__name__)

# ============================================
# CONSTANTS
# ============================================

# Concurrency limits
MAX_CONCURRENT_CALLS_PER_AGENCY = 3

# Timeout for monitoring call outcomes
CALL_OUTCOME_TIMEOUT_SECONDS = 600  # 10 minutes

# SDK spend cap per lead for context building
SDK_SPEND_CAP_PER_LEAD = 0.05

# Retry configuration
RETRY_DELAY_MINUTES = 60
MAX_RETRY_ATTEMPTS = 2

# Compliance statuses
COMPLIANCE_OK = "OK"
COMPLIANCE_OUTSIDE_HOURS = "OUTSIDE_HOURS"

# Call statuses
CALL_STATUS_INITIATED = "INITIATED"
CALL_STATUS_DIAL_FAILED = "DIAL_FAILED"
CALL_STATUS_COMPLETED = "COMPLETED"
CALL_STATUS_NO_ANSWER = "NO_ANSWER"
CALL_STATUS_BUSY = "BUSY"
CALL_STATUS_FAILED = "FAILED"


# ============================================
# TASKS
# ============================================


@task(name="fetch_voice_queue", retries=2, retry_delay_seconds=10)
async def fetch_voice_queue_task(agency_id: str | None = None) -> list[dict[str, Any]]:
    """
    Query lead_pool for leads due for voice touch.

    Criteria:
    - ALS (Adjusted Lead Score) >= 85
    - Campaign active
    - Voice channel enabled
    - Not suppressed
    - Not currently in an active call

    Args:
        agency_id: Optional filter by specific agency

    Returns:
        List of lead dicts with lead_id and related info
    """
    run_logger = get_run_logger()

    async with get_db_session() as db:
        query = text("""
            SELECT
                lp.id as lead_pool_id,
                lp.lead_id,
                lp.campaign_id,
                lp.agency_id,
                lp.als_score as reachability_score,
                l.first_name,
                l.last_name,
                l.phone,
                l.email,
                l.company,
                l.title,
                c.name as campaign_name,
                c.client_id
            FROM lead_pool lp
            INNER JOIN leads l ON lp.lead_id = l.id
            INNER JOIN campaigns c ON lp.campaign_id = c.id
            WHERE lp.als_score >= 85  -- reachability threshold
              AND c.status = :campaign_status
              AND lp.voice_enabled = TRUE
              AND lp.suppressed = FALSE
              AND lp.deleted_at IS NULL
              AND l.deleted_at IS NULL
              AND l.phone IS NOT NULL
              AND l.phone != ''
              AND NOT EXISTS (
                  SELECT 1 FROM voice_calls vc
                  WHERE vc.lead_id = lp.lead_id
                  AND vc.status IN ('INITIATED', 'RINGING', 'IN_PROGRESS')
              )
              AND (
                  lp.last_voice_attempt IS NULL
                  OR lp.last_voice_attempt < NOW() - INTERVAL '24 hours'
              )
              -- TEST MODE: Only dial leads with test_record=true in enrichment_data
              -- Remove this filter when moving to production
              AND (lp.enrichment_data->>'test_record')::boolean = true
        """)

        params = {"campaign_status": CampaignStatus.ACTIVE.value}

        if agency_id:
            query = text(str(query) + " AND lp.agency_id = :agency_id")
            params["agency_id"] = agency_id

        query = text(str(query) + " ORDER BY lp.als_score DESC LIMIT 50")  # ordered by reachability

        result = await db.execute(query, params)
        rows = result.fetchall()

        leads = []
        for row in rows:
            leads.append(
                {
                    "lead_pool_id": str(row.lead_pool_id),
                    "lead_id": str(row.lead_id),
                    "campaign_id": str(row.campaign_id),
                    "agency_id": str(row.agency_id),
                    "reachability_score": row.reachability_score,
                    "first_name": row.first_name,
                    "last_name": row.last_name,
                    "phone": row.phone,
                    "email": row.email,
                    "company": row.company,
                    "title": row.title,
                    "campaign_name": row.campaign_name,
                    "client_id": str(row.client_id),
                }
            )

        run_logger.info(f"Fetched {len(leads)} leads for voice queue")
        return leads


@task(name="validate_call", retries=1, retry_delay_seconds=5)
async def validate_call_task(lead: dict[str, Any]) -> dict[str, Any] | None:
    """
    Run voice compliance validation for a lead.

    Checks:
    - Phone number validity
    - Calling hours compliance (AEST timezone)
    - DNC (Do Not Call) registry
    - Consent status

    Args:
        lead: Lead dict from fetch_voice_queue

    Returns:
        Lead dict with compliance info if valid, None if not compliant
    """
    run_logger = get_run_logger()

    try:
        # Import here to avoid circular imports
        from src.services.voice_compliance_validator import validate_call

        # validate_call expects (lead_id, phone, agency_id)
        # client_id is the agency_id in our data model
        result = await validate_call(
            lead_id=lead["lead_id"],
            phone=lead["phone"],
            agency_id=lead["client_id"],  # client_id = agency_id
        )

        # ValidationResult is a dataclass with .valid, .reason, .next_valid_window
        if result.valid:
            lead["compliance_status"] = COMPLIANCE_OK
            return lead
        elif result.reason == "OUTSIDE_HOURS":
            # Schedule for next valid window
            next_window = result.next_valid_window
            run_logger.info(
                f"Lead {lead['lead_id']} outside calling hours, next window: {next_window}"
            )

            # Update lead_pool with next scheduled time
            async with get_db_session() as db:
                await db.execute(
                    text("""
                        UPDATE lead_pool
                        SET next_voice_attempt = :next_window
                        WHERE lead_id = :lead_id
                    """),
                    {"next_window": next_window, "lead_id": lead["lead_id"]},
                )
                await db.commit()

            return None
        else:
            run_logger.warning(f"Lead {lead['lead_id']} failed compliance: {result.reason}")
            return None

    except Exception as e:
        run_logger.error(f"Compliance validation error for lead {lead['lead_id']}: {e}")
        return None


@task(name="build_context", retries=2, retry_delay_seconds=5)
async def build_context_task(lead: dict[str, Any]) -> dict[str, Any] | None:
    """
    Build call context for the lead using voice_context_builder.

    Compiles:
    - Lead information
    - Campaign context
    - Talking points
    - Objection handling
    - Personalization data

    SDK spend capped at $0.05/lead.

    Args:
        lead: Validated lead dict

    Returns:
        Context dict for the call, or None on failure
    """
    run_logger = get_run_logger()

    try:
        from src.services.voice_context_builder import build_call_context

        # voice_context_builder.build_call_context expects (lead_id, agency_id)
        # client_id is the agency_id in our data model
        context = await build_call_context(
            lead_id=lead["lead_id"],
            agency_id=lead["client_id"],  # client_id = agency_id
        )

        if context:
            context["lead_id"] = lead["lead_id"]
            context["campaign_id"] = lead["campaign_id"]
            context["agency_id"] = lead["agency_id"]
            context["phone"] = lead["phone"]
            run_logger.info(f"Built context for lead {lead['lead_id']}")
            return context
        else:
            run_logger.warning(f"Failed to build context for lead {lead['lead_id']}")
            return None

    except Exception as e:
        run_logger.error(f"Context build error for lead {lead['lead_id']}: {e}")
        return None


@task(name="log_context", retries=2, retry_delay_seconds=5)
async def log_context_task(context: dict[str, Any]) -> str | None:
    """
    Write context to voice_call_context table and create voice_calls record.

    Args:
        context: Compiled context dict

    Returns:
        voice_call_id (UUID string) or None on failure
    """
    run_logger = get_run_logger()

    try:
        async with get_db_session() as db:
            voice_call_id = str(uuid4())
            context_id = str(uuid4())
            now = datetime.utcnow()

            # Create voice_calls record as INITIATED
            await db.execute(
                text("""
                    INSERT INTO voice_calls (
                        id, lead_id, campaign_id, agency_id, phone,
                        status, initiated_at, created_at, updated_at
                    ) VALUES (
                        :id, :lead_id, :campaign_id, :agency_id, :phone,
                        :status, :initiated_at, :created_at, :updated_at
                    )
                """),
                {
                    "id": voice_call_id,
                    "lead_id": context["lead_id"],
                    "campaign_id": context["campaign_id"],
                    "agency_id": context["agency_id"],
                    "phone": context["phone"],
                    "status": CALL_STATUS_INITIATED,
                    "initiated_at": now,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            # Create voice_call_context record
            await db.execute(
                text("""
                    INSERT INTO voice_call_context (
                        id, voice_call_id, context_data, created_at
                    ) VALUES (
                        :id, :voice_call_id, :context_data::jsonb, :created_at
                    )
                """),
                {
                    "id": context_id,
                    "voice_call_id": voice_call_id,
                    "context_data": str(context),  # Will be JSON serialized
                    "created_at": now,
                },
            )

            await db.commit()

            run_logger.info(
                f"Logged context for voice_call {voice_call_id}, lead {context['lead_id']}"
            )

            # Add voice_call_id to context for later use
            context["voice_call_id"] = voice_call_id
            return voice_call_id

    except Exception as e:
        run_logger.error(f"Failed to log context for lead {context['lead_id']}: {e}")
        return None


@task(name="initiate_call", retries=1, retry_delay_seconds=30)
async def initiate_call_task(
    context: dict[str, Any],
    voice_call_id: str,
) -> str | None:
    """
    Initiate voice call via ElevenLabs Conversational AI.

    Uses agency-level concurrency limit (max 3 simultaneous calls).

    Args:
        context: Call context dict
        voice_call_id: ID of the voice_calls record

    Returns:
        call_sid from ElevenLabs or None on failure
    """
    run_logger = get_run_logger()
    agency_id = context.get("agency_id", "default")

    try:
        # Use Prefect concurrency to limit calls per agency
        async with prefect_concurrency(
            f"voice-calls-{agency_id}",
            occupy=1,
        ):
            from src.integrations.elevenagets_client import get_elevenagets_client

            client = await get_elevenagets_client()

            result = await client.initiate_call(
                phone=context["phone"],
                voice_call_id=voice_call_id,
                context=context,
            )

            call_sid = result.get("call_sid")

            if call_sid:
                # Update voice_calls with call_sid
                async with get_db_session() as db:
                    await db.execute(
                        text("""
                            UPDATE voice_calls
                            SET call_sid = :call_sid, updated_at = :updated_at
                            WHERE id = :voice_call_id
                        """),
                        {
                            "call_sid": call_sid,
                            "voice_call_id": voice_call_id,
                            "updated_at": datetime.utcnow(),
                        },
                    )
                    await db.commit()

                run_logger.info(f"Initiated call {call_sid} for lead {context['lead_id']}")
                return call_sid
            else:
                await _handle_dial_failure(
                    voice_call_id, context["lead_id"], "No call_sid returned"
                )
                return None

    except Exception as e:
        run_logger.error(f"Failed to initiate call for lead {context['lead_id']}: {e}")
        await _handle_dial_failure(voice_call_id, context["lead_id"], str(e))
        return None


@task(name="monitor_outcomes", retries=1)
async def monitor_outcomes_task(
    call_sids: list[str],
    timeout_seconds: int = CALL_OUTCOME_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Poll voice_calls for completion.

    Note: Actual status updates are handled by webhooks.
    This task monitors for timeout scenarios.

    Args:
        call_sids: List of call SIDs to monitor
        timeout_seconds: Max time to wait (default 10 minutes)

    Returns:
        Summary of call outcomes
    """
    run_logger = get_run_logger()

    if not call_sids:
        return {"monitored": 0, "completed": 0, "failed": 0}

    start_time = datetime.utcnow()
    completed_calls = set()
    failed_calls = set()

    while True:
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        if elapsed >= timeout_seconds:
            run_logger.warning(
                f"Monitoring timeout reached. {len(call_sids) - len(completed_calls) - len(failed_calls)} "
                f"calls still pending"
            )
            break

        async with get_db_session() as db:
            result = await db.execute(
                text("""
                    SELECT call_sid, status
                    FROM voice_calls
                    WHERE call_sid = ANY(:call_sids)
                """),
                {"call_sids": call_sids},
            )
            rows = result.fetchall()

            for row in rows:
                if row.status in (
                    CALL_STATUS_COMPLETED,
                    CALL_STATUS_NO_ANSWER,
                    CALL_STATUS_BUSY,
                ):
                    completed_calls.add(row.call_sid)
                elif row.status in (CALL_STATUS_DIAL_FAILED, CALL_STATUS_FAILED):
                    failed_calls.add(row.call_sid)

        # Check if all calls are resolved
        if len(completed_calls) + len(failed_calls) >= len(call_sids):
            run_logger.info("All calls resolved")
            break

        # Wait before next poll
        await asyncio.sleep(10)

    summary = {
        "monitored": len(call_sids),
        "completed": len(completed_calls),
        "failed": len(failed_calls),
        "pending": len(call_sids) - len(completed_calls) - len(failed_calls),
    }

    run_logger.info(f"Monitoring complete: {summary}")
    return summary


# ============================================
# HELPER FUNCTIONS
# ============================================


async def _handle_dial_failure(
    voice_call_id: str,
    lead_id: str,
    reason: str,
) -> None:
    """Handle a failed dial attempt with retry logic."""
    logger.error(f"Dial failed for voice_call {voice_call_id}: {reason}")

    async with get_db_session() as db:
        # Get current retry count
        result = await db.execute(
            text("""
                SELECT retry_count FROM voice_calls WHERE id = :voice_call_id
            """),
            {"voice_call_id": voice_call_id},
        )
        row = result.fetchone()
        retry_count = (row.retry_count or 0) if row else 0

        if retry_count < MAX_RETRY_ATTEMPTS - 1:
            # Schedule retry
            next_retry = datetime.utcnow() + timedelta(minutes=RETRY_DELAY_MINUTES)
            await db.execute(
                text("""
                    UPDATE voice_calls
                    SET status = :status,
                        retry_count = retry_count + 1,
                        next_retry_at = :next_retry,
                        failure_reason = :reason,
                        updated_at = :updated_at
                    WHERE id = :voice_call_id
                """),
                {
                    "status": CALL_STATUS_DIAL_FAILED,
                    "next_retry": next_retry,
                    "reason": reason,
                    "updated_at": datetime.utcnow(),
                    "voice_call_id": voice_call_id,
                },
            )
            logger.info(f"Scheduled retry for voice_call {voice_call_id} at {next_retry}")
        else:
            # Max retries reached, log to audit
            await db.execute(
                text("""
                    UPDATE voice_calls
                    SET status = :status,
                        failure_reason = :reason,
                        updated_at = :updated_at
                    WHERE id = :voice_call_id
                """),
                {
                    "status": CALL_STATUS_FAILED,
                    "reason": f"Max retries exceeded: {reason}",
                    "updated_at": datetime.utcnow(),
                    "voice_call_id": voice_call_id,
                },
            )

            # Log to audit_logs
            await db.execute(
                text("""
                    INSERT INTO audit_logs (
                        id, entity_type, entity_id, action, details, created_at
                    ) VALUES (
                        :id, 'voice_call', :entity_id, 'DIAL_FAILED_MAX_RETRIES',
                        :details::jsonb, :created_at
                    )
                """),
                {
                    "id": str(uuid4()),
                    "entity_id": voice_call_id,
                    "details": f'{{"lead_id": "{lead_id}", "reason": "{reason}"}}',
                    "created_at": datetime.utcnow(),
                },
            )
            logger.warning(f"Max retries exceeded for voice_call {voice_call_id}")

        await db.commit()


def _is_within_calling_hours() -> bool:
    """
    Check if current time is within permitted calling hours (AEST).

    Schedule:
    - Monday-Friday: 09:00-20:00 AEST
    - Saturday: 09:00-17:00 AEST
    - Sunday/Public Holidays: DISABLED
    """
    from zoneinfo import ZoneInfo

    aest = ZoneInfo("Australia/Sydney")
    now = datetime.now(aest)

    # Sunday is disabled
    if now.weekday() == 6:
        return False

    hour = now.hour

    # Saturday: 09:00-17:00
    if now.weekday() == 5:
        return 9 <= hour < 17

    # Monday-Friday: 09:00-20:00
    return 9 <= hour < 20


# ============================================
# MAIN FLOW
# ============================================


@flow(
    name="voice-outreach-flow",
    task_runner=ConcurrentTaskRunner(max_workers=5),
    retries=1,
    retry_delay_seconds=300,
    log_prints=True,
)
async def voice_outreach_flow(agency_id: str | None = None) -> dict[str, Any]:
    """
    Voice outreach flow with compliance validation and ElevenLabs integration.

    Runs every 30 minutes during permitted calling hours.
    Max 3 simultaneous calls per agency.

    Args:
        agency_id: Optional filter by specific agency

    Returns:
        Flow execution summary
    """
    run_logger = get_run_logger()
    flow_start = datetime.utcnow()

    # Pre-check: Verify we're within calling hours
    if not _is_within_calling_hours():
        run_logger.info("Outside permitted calling hours. Skipping flow execution.")
        return {
            "status": "skipped",
            "reason": "outside_calling_hours",
            "timestamp": flow_start.isoformat(),
        }

    run_logger.info(f"Starting voice outreach flow (agency_id={agency_id})")

    results = {
        "status": "completed",
        "flow_start": flow_start.isoformat(),
        "leads_fetched": 0,
        "leads_validated": 0,
        "contexts_built": 0,
        "calls_initiated": 0,
        "call_outcomes": {},
        "errors": [],
    }

    try:
        # Step 1: Fetch voice queue
        leads = await fetch_voice_queue_task(agency_id=agency_id)
        results["leads_fetched"] = len(leads)

        if not leads:
            run_logger.info("No leads in voice queue")
            return results

        # Step 2: Validate calls (parallel)
        validated_leads = []
        validation_tasks = [validate_call_task(lead) for lead in leads]
        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)

        for result in validation_results:
            if isinstance(result, Exception):
                results["errors"].append(str(result))
            elif result is not None:
                validated_leads.append(result)

        results["leads_validated"] = len(validated_leads)

        if not validated_leads:
            run_logger.info("No leads passed validation")
            return results

        # Step 3: Build contexts (parallel)
        contexts = []
        context_tasks = [build_context_task(lead) for lead in validated_leads]
        context_results = await asyncio.gather(*context_tasks, return_exceptions=True)

        for result in context_results:
            if isinstance(result, Exception):
                results["errors"].append(str(result))
            elif result is not None:
                contexts.append(result)

        results["contexts_built"] = len(contexts)

        if not contexts:
            run_logger.info("No contexts built successfully")
            return results

        # Step 4: Log contexts and create voice_calls records
        voice_call_ids = []
        for context in contexts:
            voice_call_id = await log_context_task(context)
            if voice_call_id:
                context["voice_call_id"] = voice_call_id
                voice_call_ids.append(voice_call_id)

        # Step 5: Initiate calls (with concurrency limit)
        call_sids = []
        for context in contexts:
            if "voice_call_id" in context:
                call_sid = await initiate_call_task(
                    context=context,
                    voice_call_id=context["voice_call_id"],
                )
                if call_sid:
                    call_sids.append(call_sid)

        results["calls_initiated"] = len(call_sids)

        # Step 6: Monitor outcomes
        if call_sids:
            outcomes = await monitor_outcomes_task(call_sids)
            results["call_outcomes"] = outcomes

        results["flow_end"] = datetime.utcnow().isoformat()
        run_logger.info(f"Voice outreach flow completed: {results}")

        return results

    except Exception as e:
        run_logger.error(f"Voice outreach flow error: {e}")
        results["status"] = "error"
        results["errors"].append(str(e))
        return results


# ============================================
# DEPLOYMENT CONFIGURATION
# ============================================

if __name__ == "__main__":
    # For local testing
    import asyncio

    asyncio.run(voice_outreach_flow())
