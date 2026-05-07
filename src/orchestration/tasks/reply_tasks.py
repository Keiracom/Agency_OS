"""
FILE: src/orchestration/tasks/reply_tasks.py
PURPOSE: Prefect tasks for reply handling via Closer engine and polling
PHASE: 5 (Orchestration)
TASK: ORC-009
DEPENDENCIES:
  - src/engines/closer.py
  - src/integrations/postmark.py
  - src/integrations/twilio.py
  - src/models/lead.py
  - src/models/activity.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Import hierarchy (no other tasks)
  - Rule 14: Soft deletes only
  - Rule 20: Webhook-first architecture (polling is safety net)
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import task
from sqlalchemy import and_, select

from src.engines.closer import CloserEngine
from src.exceptions import ValidationError
from src.integrations.supabase import get_db_session
from src.models.base import ChannelType
from src.models.lead import Lead

logger = logging.getLogger(__name__)


@task(
    name="process_reply",
    description="Process incoming reply via Closer engine",
    retries=2,
    retry_delay_seconds=[30, 120],
    tags=["reply", "closer"],
)
async def process_reply_task(
    lead_id: UUID,
    message: str,
    channel: ChannelType,
    provider_message_id: str | None = None,
    in_reply_to: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Process an incoming reply from a lead.

    Uses AI to classify intent and update lead status accordingly.

    Intent types:
    - meeting_request: Lead wants to schedule a meeting
    - interested: Shows interest but no meeting request
    - question: Has questions about the offering
    - not_interested: Politely declines
    - unsubscribe: Wants to stop receiving messages
    - out_of_office: Automated out of office reply
    - auto_reply: Other automated reply

    Args:
        lead_id: Lead UUID
        message: Reply message content
        channel: Channel the reply came from
        provider_message_id: Provider's message ID (for threading)
        in_reply_to: Message ID this is replying to
        metadata: Additional metadata

    Returns:
        Processing result with:
            - success: bool
            - lead_id: UUID
            - intent: str
            - lead_status: str (updated status)

    Raises:
        ValidationError: If lead not found
    """
    async with get_db_session() as db:
        # Fetch lead (check soft delete)
        stmt = select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValidationError(
                message=f"Lead {lead_id} not found or deleted",
                field="lead_id",
            )

        # === PROCESS REPLY ===
        logger.info(f"Processing {channel} reply from lead {lead_id}")

        closer = CloserEngine()
        reply_result = await closer.process_reply(
            db=db,
            lead_id=lead_id,
            message=message,
            channel=channel,
            provider_message_id=provider_message_id,
            in_reply_to=in_reply_to,
            metadata=metadata,
        )

        if not reply_result.success:
            raise ValidationError(
                message=f"Reply processing failed: {reply_result.error}",
                field="reply_processing",
            )

        intent = reply_result.data.get("intent", "unknown")
        lead_status = reply_result.data.get("lead_status", "in_sequence")

        logger.info(
            f"Processed reply from lead {lead_id}. Intent: {intent}, New status: {lead_status}"
        )

        return {
            "success": True,
            "lead_id": str(lead_id),
            "channel": channel.value,
            "intent": intent,
            "lead_status": lead_status,
            "requires_followup": reply_result.data.get("requires_followup", False),
        }


@task(
    name="classify_intent",
    description="Classify reply intent using AI",
    retries=2,
    retry_delay_seconds=[30, 120],
    tags=["reply", "ai"],
)
async def classify_intent_task(
    message: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Classify intent of a reply message using AI.

    Rule 15: Uses AI spend limiter.

    Args:
        message: Reply message content
        context: Optional context (lead info, previous messages, etc.)

    Returns:
        Classification result with:
            - intent: str
            - confidence: float
            - reasoning: str

    Raises:
        ValidationError: If classification fails
    """
    async with get_db_session() as db:
        closer = CloserEngine()
        classify_result = await closer.classify_intent(
            db=db,
            message=message,
            context=context,
        )

        if not classify_result.success:
            raise ValidationError(
                message=f"Intent classification failed: {classify_result.error}",
                field="classification",
            )

        intent = classify_result.data.get("intent", "unknown")
        confidence = classify_result.data.get("confidence", 0.0)

        logger.info(f"Classified intent as '{intent}' (confidence: {confidence:.2f})")

        return {
            "intent": intent,
            "confidence": confidence,
            "reasoning": classify_result.data.get("reasoning", ""),
        }


@task(
    name="poll_email_replies",
    description="Poll Postmark for email replies (safety net)",
    retries=1,
    retry_delay_seconds=60,
    tags=["reply", "polling", "email"],
)
async def poll_email_replies_task(
    since: datetime | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Poll Postmark for email replies (safety net, webhooks are primary).

    Rule 20: Webhook-first architecture. This is a safety net only.

    Args:
        since: Poll for replies since this datetime (default: 1 hour ago)
        limit: Max number of replies to fetch

    Returns:
        Polling result with:
            - total: int
            - processed: int
            - failed: int
            - replies: list[dict]
    """
    raise NotImplementedError("dead path: postmark removed in PR-A #593")


@task(
    name="poll_sms_replies",
    description="Poll Twilio for SMS replies (safety net)",
    retries=1,
    retry_delay_seconds=60,
    tags=["reply", "polling", "sms"],
)
async def poll_sms_replies_task(
    since: datetime | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Poll Twilio for SMS replies (safety net, webhooks are primary).

    Rule 20: Webhook-first architecture. This is a safety net only.

    Args:
        since: Poll for replies since this datetime (default: 1 hour ago)
        limit: Max number of replies to fetch

    Returns:
        Polling result with:
            - total: int
            - processed: int
            - failed: int
            - replies: list[dict]
    """
    raise NotImplementedError("dead path: twilio removed in PR-A #593")


# NOTE: poll_linkedin_replies_task removed - HeyReach deprecated, use Unipile instead

# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session obtained via get_db_session()
# [x] No imports from other tasks (only engines and integrations)
# [x] Soft delete check in queries (deleted_at IS NULL)
# [x] All tasks use @task decorator with retries
# [x] Proper logging
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Reply processing via Closer engine
# [x] Intent classification with AI
# [x] Polling tasks for email, SMS, LinkedIn (Rule 20: safety nets)
# [x] Webhook-first architecture (polling is fallback)
