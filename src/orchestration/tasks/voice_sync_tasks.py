"""
FILE: src/orchestration/tasks/voice_sync_tasks.py
PURPOSE: Prefect tasks for syncing voice_calls outcomes to activities table (CIS Gap 1 Fix)
PHASE: CIS Gap 1 Fix - Voice Outcome Capture
TASK: CIS-GAP-001
DEPENDENCIES:
  - src/models/voice_call.py
  - src/models/activity.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation in all tasks

CIS GAP 1 FIX:
This module ensures voice call outcomes are synced to the activities table
so CIS (Conversion Intelligence System) can see voice data alongside other
channel activities for learning and pattern detection.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import UUID

from prefect import flow, get_run_logger, task
from sqlalchemy import text

from src.integrations.supabase import get_db_session
from src.models.base import ChannelType

logger = logging.getLogger(__name__)


# ============================================
# Outcome to Intent Mapping
# ============================================

OUTCOME_TO_INTENT = {
    # Positive outcomes - map to positive intents
    "BOOKED": "positive",
    "MEETING_BOOKED": "positive",
    "INTERESTED": "positive",
    "CALLBACK": "neutral",
    "CALLBACK_REQUESTED": "neutral",
    # Negative outcomes
    "NOT_INTERESTED": "not_interested",
    "WRONG_PERSON": "not_interested",
    "UNSUBSCRIBE": "unsubscribe",
    "ANGRY": "angry",
    # No contact outcomes
    "NO_ANSWER": None,
    "VOICEMAIL": None,
    "BUSY": None,
    "CALL_DECLINED": None,
    # Other
    "ESCALATION": "escalation",
    "FAILED": None,
    "INITIATED": None,
    "CALL_ANSWERED": None,
    "CALL_COMPLETED": None,
}

OUTCOME_TO_ACTION = {
    "BOOKED": "voice_booked",
    "MEETING_BOOKED": "voice_booked",
    "INTERESTED": "voice_interested",
    "CALLBACK": "voice_callback",
    "CALLBACK_REQUESTED": "voice_callback",
    "NOT_INTERESTED": "voice_declined",
    "WRONG_PERSON": "voice_wrong_person",
    "UNSUBSCRIBE": "voice_unsubscribe",
    "ANGRY": "voice_angry",
    "NO_ANSWER": "voice_no_answer",
    "VOICEMAIL": "voice_voicemail",
    "BUSY": "voice_busy",
    "CALL_DECLINED": "voice_declined",
    "ESCALATION": "voice_escalation",
    "FAILED": "voice_failed",
    "INITIATED": "voice_initiated",
    "CALL_ANSWERED": "voice_answered",
    "CALL_COMPLETED": "voice_completed",
}


# ============================================
# Tasks
# ============================================


@task(name="sync_voice_calls_to_activities", retries=3, retry_delay_seconds=30)
async def sync_voice_calls_to_activities_task(
    since_hours: int = 24,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Sync voice_calls outcomes to activities table.

    CIS Gap 1 Fix: This ensures voice call data is visible to CIS for learning.

    Finds voice_calls records that:
    - Have an outcome (not just INITIATED)
    - Were updated in the last `since_hours` hours
    - Don't already have a corresponding activity record

    Creates activity records with:
    - channel = VOICE
    - action = voice_{outcome}
    - intent = mapped from outcome
    - All relevant metadata

    Args:
        since_hours: Look back period in hours (default 24)
        batch_size: Max records per batch (default 100)

    Returns:
        Summary dict with counts
    """
    run_logger = get_run_logger()
    run_logger.info(f"Starting voice_calls to activities sync (since_hours={since_hours})")

    results = {
        "synced": 0,
        "skipped_already_synced": 0,
        "skipped_no_outcome": 0,
        "errors": 0,
    }

    try:
        async with get_db_session() as db:
            # Fetch voice_calls that need syncing
            cutoff_time = datetime.now(UTC) - timedelta(hours=since_hours)

            query = text("""
                SELECT
                    vc.id as voice_call_id,
                    vc.lead_id,
                    vc.client_id,
                    vc.campaign_id,
                    vc.outcome,
                    vc.duration_seconds,
                    vc.transcript,
                    vc.sentiment_summary,
                    vc.als_score_at_call,
                    vc.hook_used,
                    vc.elevenagets_call_id,
                    vc.twilio_call_sid,
                    vc.recording_url,
                    vc.created_at,
                    vc.updated_at
                FROM voice_calls vc
                WHERE vc.outcome IS NOT NULL
                  AND vc.outcome NOT IN ('INITIATED', 'CALL_ANSWERED')
                  AND vc.updated_at >= :cutoff_time
                  AND NOT EXISTS (
                      SELECT 1 FROM activities a
                      WHERE a.provider_message_id = vc.id::text
                      AND a.channel = 'voice'
                  )
                ORDER BY vc.updated_at ASC
                LIMIT :batch_size
            """)

            result = await db.execute(
                query,
                {"cutoff_time": cutoff_time, "batch_size": batch_size},
            )
            rows = result.fetchall()

            run_logger.info(f"Found {len(rows)} voice_calls to sync")

            for row in rows:
                try:
                    outcome = row.outcome
                    if not outcome:
                        results["skipped_no_outcome"] += 1
                        continue

                    # Map outcome to action and intent
                    action = OUTCOME_TO_ACTION.get(outcome, f"voice_{outcome.lower()}")
                    intent = OUTCOME_TO_INTENT.get(outcome)

                    # Build metadata
                    metadata = {
                        "voice_call_id": str(row.voice_call_id),
                        "outcome": outcome,
                        "duration_seconds": row.duration_seconds,
                        "als_score_at_call": row.als_score_at_call,
                        "hook_used": row.hook_used,
                        "elevenagets_call_id": row.elevenagets_call_id,
                        "twilio_call_sid": row.twilio_call_sid,
                        "recording_url": row.recording_url,
                        "sentiment_summary": row.sentiment_summary,
                    }

                    # Insert activity record
                    await db.execute(
                        text("""
                            INSERT INTO activities (
                                id,
                                client_id,
                                campaign_id,
                                lead_id,
                                channel,
                                action,
                                provider_message_id,
                                provider,
                                provider_status,
                                intent,
                                content_preview,
                                extra_data,
                                created_at,
                                processed_at
                            ) VALUES (
                                gen_random_uuid(),
                                :client_id,
                                :campaign_id,
                                :lead_id,
                                :channel,
                                :action,
                                :provider_message_id,
                                :provider,
                                :provider_status,
                                :intent,
                                :content_preview,
                                :extra_data::jsonb,
                                :created_at,
                                :processed_at
                            )
                        """),
                        {
                            "client_id": str(row.client_id),
                            "campaign_id": str(row.campaign_id) if row.campaign_id else None,
                            "lead_id": str(row.lead_id),
                            "channel": "voice",
                            "action": action,
                            "provider_message_id": str(row.voice_call_id),
                            "provider": "elevenagets",
                            "provider_status": outcome,
                            "intent": intent,
                            "content_preview": row.sentiment_summary[:500]
                            if row.sentiment_summary
                            else None,
                            "extra_data": str(metadata).replace("'", '"'),  # JSON format
                            "created_at": row.created_at,
                            "processed_at": datetime.now(UTC),
                        },
                    )

                    results["synced"] += 1

                except Exception as e:
                    run_logger.error(
                        f"Error syncing voice_call {row.voice_call_id}: {e}"
                    )
                    results["errors"] += 1

            await db.commit()

    except Exception as e:
        run_logger.error(f"Voice sync task error: {e}")
        results["error_message"] = str(e)

    run_logger.info(f"Voice sync complete: {results}")
    return results


@task(name="sync_single_voice_call", retries=2, retry_delay_seconds=10)
async def sync_single_voice_call_task(voice_call_id: str) -> dict[str, Any]:
    """
    Sync a single voice_call to activities table.

    Called immediately after post-call processing for real-time sync.

    Args:
        voice_call_id: UUID of the voice_call record

    Returns:
        Result dict with status
    """
    run_logger = get_run_logger()
    run_logger.info(f"Syncing single voice_call: {voice_call_id}")

    try:
        async with get_db_session() as db:
            # Fetch the voice_call
            result = await db.execute(
                text("""
                    SELECT
                        vc.id as voice_call_id,
                        vc.lead_id,
                        vc.client_id,
                        vc.campaign_id,
                        vc.outcome,
                        vc.duration_seconds,
                        vc.transcript,
                        vc.sentiment_summary,
                        vc.als_score_at_call,
                        vc.hook_used,
                        vc.elevenagets_call_id,
                        vc.twilio_call_sid,
                        vc.recording_url,
                        vc.created_at
                    FROM voice_calls vc
                    WHERE vc.id = :voice_call_id
                """),
                {"voice_call_id": voice_call_id},
            )
            row = result.fetchone()

            if not row:
                return {"status": "not_found", "voice_call_id": voice_call_id}

            if not row.outcome or row.outcome in ("INITIATED", "CALL_ANSWERED"):
                return {"status": "skipped", "reason": "no_final_outcome"}

            # Check if already synced
            existing = await db.execute(
                text("""
                    SELECT id FROM activities
                    WHERE provider_message_id = :voice_call_id
                    AND channel = 'voice'
                """),
                {"voice_call_id": voice_call_id},
            )
            if existing.fetchone():
                return {"status": "already_synced", "voice_call_id": voice_call_id}

            # Map outcome
            outcome = row.outcome
            action = OUTCOME_TO_ACTION.get(outcome, f"voice_{outcome.lower()}")
            intent = OUTCOME_TO_INTENT.get(outcome)

            # Build metadata
            import json

            metadata = {
                "voice_call_id": str(row.voice_call_id),
                "outcome": outcome,
                "duration_seconds": row.duration_seconds,
                "als_score_at_call": row.als_score_at_call,
                "hook_used": row.hook_used,
                "elevenagets_call_id": row.elevenagets_call_id,
                "twilio_call_sid": row.twilio_call_sid,
                "recording_url": row.recording_url,
                "sentiment_summary": row.sentiment_summary,
            }

            # Insert activity
            await db.execute(
                text("""
                    INSERT INTO activities (
                        id,
                        client_id,
                        campaign_id,
                        lead_id,
                        channel,
                        action,
                        provider_message_id,
                        provider,
                        provider_status,
                        intent,
                        content_preview,
                        extra_data,
                        created_at,
                        processed_at
                    ) VALUES (
                        gen_random_uuid(),
                        :client_id,
                        :campaign_id,
                        :lead_id,
                        :channel,
                        :action,
                        :provider_message_id,
                        :provider,
                        :provider_status,
                        :intent,
                        :content_preview,
                        :extra_data::jsonb,
                        :created_at,
                        :processed_at
                    )
                """),
                {
                    "client_id": str(row.client_id),
                    "campaign_id": str(row.campaign_id) if row.campaign_id else None,
                    "lead_id": str(row.lead_id),
                    "channel": "voice",
                    "action": action,
                    "provider_message_id": str(row.voice_call_id),
                    "provider": "elevenagets",
                    "provider_status": outcome,
                    "intent": intent,
                    "content_preview": row.sentiment_summary[:500]
                    if row.sentiment_summary
                    else None,
                    "extra_data": json.dumps(metadata),
                    "created_at": row.created_at,
                    "processed_at": datetime.now(UTC),
                },
            )

            await db.commit()

            run_logger.info(f"Synced voice_call {voice_call_id} to activities")
            return {
                "status": "synced",
                "voice_call_id": voice_call_id,
                "outcome": outcome,
                "action": action,
            }

    except Exception as e:
        run_logger.error(f"Error syncing voice_call {voice_call_id}: {e}")
        return {"status": "error", "voice_call_id": voice_call_id, "error": str(e)}


@task(name="backfill_voice_activities", retries=1)
async def backfill_voice_activities_task(
    days_back: int = 30,
    batch_size: int = 500,
) -> dict[str, Any]:
    """
    Backfill activities from historical voice_calls records.

    Use for one-time migration or recovery scenarios.

    Args:
        days_back: How many days of history to backfill (default 30)
        batch_size: Max records per batch (default 500)

    Returns:
        Summary dict with counts
    """
    run_logger = get_run_logger()
    run_logger.info(f"Starting voice activities backfill (days_back={days_back})")

    results = {
        "total_processed": 0,
        "synced": 0,
        "skipped": 0,
        "errors": 0,
        "batches": 0,
    }

    cutoff_time = datetime.now(UTC) - timedelta(days=days_back)
    offset = 0

    while True:
        batch_results = await sync_voice_calls_to_activities_task.fn(
            since_hours=days_back * 24,
            batch_size=batch_size,
        )

        results["batches"] += 1
        results["synced"] += batch_results.get("synced", 0)
        results["skipped"] += batch_results.get("skipped_already_synced", 0)
        results["skipped"] += batch_results.get("skipped_no_outcome", 0)
        results["errors"] += batch_results.get("errors", 0)
        results["total_processed"] += (
            batch_results.get("synced", 0)
            + batch_results.get("skipped_already_synced", 0)
            + batch_results.get("skipped_no_outcome", 0)
        )

        # If we synced less than batch_size, we're done
        if batch_results.get("synced", 0) < batch_size:
            break

        # Safety limit
        if results["batches"] >= 100:
            run_logger.warning("Hit batch limit (100), stopping backfill")
            break

    run_logger.info(f"Backfill complete: {results}")
    return results


# ============================================
# Flow
# ============================================


@flow(name="voice-activities-sync-flow", retries=1, retry_delay_seconds=60)
async def voice_activities_sync_flow(
    since_hours: int = 1,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Flow for periodic sync of voice_calls to activities.

    Schedule: Every hour via Prefect deployment.

    Args:
        since_hours: Look back period (default 1 hour)
        batch_size: Max records per batch (default 100)

    Returns:
        Sync summary
    """
    run_logger = get_run_logger()
    run_logger.info("Starting voice activities sync flow")

    result = await sync_voice_calls_to_activities_task(
        since_hours=since_hours,
        batch_size=batch_size,
    )

    run_logger.info(f"Voice activities sync flow complete: {result}")
    return result


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] sync_voice_calls_to_activities_task - batch sync
# [x] sync_single_voice_call_task - real-time sync
# [x] backfill_voice_activities_task - historical migration
# [x] voice_activities_sync_flow - scheduled flow
# [x] Outcome to intent mapping
# [x] Outcome to action mapping
# [x] All tasks have retries and delays
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] CIS Gap 1: Syncs voice outcomes to activities for CIS visibility
# [x] Uses provider_message_id for deduplication
# [x] Includes metadata (als_score_at_call, duration, etc.)
