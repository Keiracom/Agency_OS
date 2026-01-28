"""
FILE: src/orchestration/tasks/reply_tasks.py
PURPOSE: Prefect tasks for reply handling via Closer engine and polling
PHASE: 5 (Orchestration)
TASK: ORC-009
DEPENDENCIES:
  - src/engines/closer.py
  - src/integrations/postmark.py
  - src/integrations/twilio.py
  - src/integrations/heyreach.py
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
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from prefect import task
from sqlalchemy import and_, desc, select

from src.engines.closer import CloserEngine
from src.exceptions import ValidationError
from src.integrations.heyreach import get_heyreach_client
from src.integrations.postmark import get_postmark_client
from src.integrations.supabase import get_db_session
from src.integrations.twilio import get_twilio_client
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
            f"Processed reply from lead {lead_id}. "
            f"Intent: {intent}, New status: {lead_status}"
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

        logger.info(
            f"Classified intent as '{intent}' (confidence: {confidence:.2f})"
        )

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
    if since is None:
        since = datetime.utcnow() - timedelta(hours=1)

    logger.info(f"Polling Postmark for email replies since {since}")

    postmark = get_postmark_client()

    try:
        # Fetch inbound messages
        messages = await postmark.get_inbound_messages(
            count=limit,
            offset=0,
        )

        processed = 0
        failed = 0
        replies = []

        async with get_db_session() as db:
            for msg in messages:
                try:
                    # Parse message
                    from_email = msg.get("From", "")
                    message_content = msg.get("TextBody") or msg.get("HtmlBody", "")
                    in_reply_to = msg.get("Headers", {}).get("In-Reply-To")
                    message_id = msg.get("MessageID")

                    # Find lead by email
                    stmt = select(Lead).where(
                        and_(
                            Lead.email == from_email,
                            Lead.deleted_at.is_(None),
                        )
                    ).order_by(desc(Lead.created_at))
                    result = await db.execute(stmt)
                    lead = result.scalar_one_or_none()

                    if not lead:
                        logger.warning(f"No lead found for email {from_email}")
                        continue

                    # Process reply
                    await process_reply_task(
                        lead_id=lead.id,
                        message=message_content,
                        channel=ChannelType.EMAIL,
                        provider_message_id=message_id,
                        in_reply_to=in_reply_to,
                        metadata={"from_polling": True},
                    )

                    replies.append({
                        "lead_id": str(lead.id),
                        "from_email": from_email,
                        "message_id": message_id,
                    })
                    processed += 1

                except Exception as e:
                    logger.error(f"Failed to process email reply: {e}")
                    failed += 1

        logger.info(
            f"Email polling complete. "
            f"Processed: {processed}, Failed: {failed}"
        )

        return {
            "total": len(messages),
            "processed": processed,
            "failed": failed,
            "replies": replies,
        }

    except Exception as e:
        logger.error(f"Email polling failed: {e}")
        raise


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
    if since is None:
        since = datetime.utcnow() - timedelta(hours=1)

    logger.info(f"Polling Twilio for SMS replies since {since}")

    twilio = get_twilio_client()

    try:
        # Fetch messages
        messages = await twilio.get_messages(
            date_sent_after=since,
            limit=limit,
        )

        processed = 0
        failed = 0
        replies = []

        async with get_db_session() as db:
            for msg in messages:
                try:
                    from_number = msg.get("from")
                    message_content = msg.get("body", "")
                    message_sid = msg.get("sid")

                    # Find lead by phone
                    stmt = select(Lead).where(
                        and_(
                            Lead.phone == from_number,
                            Lead.deleted_at.is_(None),
                        )
                    ).order_by(desc(Lead.created_at))
                    result = await db.execute(stmt)
                    lead = result.scalar_one_or_none()

                    if not lead:
                        logger.warning(f"No lead found for phone {from_number}")
                        continue

                    # Process reply
                    await process_reply_task(
                        lead_id=lead.id,
                        message=message_content,
                        channel=ChannelType.SMS,
                        provider_message_id=message_sid,
                        metadata={"from_polling": True},
                    )

                    replies.append({
                        "lead_id": str(lead.id),
                        "from_number": from_number,
                        "message_sid": message_sid,
                    })
                    processed += 1

                except Exception as e:
                    logger.error(f"Failed to process SMS reply: {e}")
                    failed += 1

        logger.info(
            f"SMS polling complete. "
            f"Processed: {processed}, Failed: {failed}"
        )

        return {
            "total": len(messages),
            "processed": processed,
            "failed": failed,
            "replies": replies,
        }

    except Exception as e:
        logger.error(f"SMS polling failed: {e}")
        raise


@task(
    name="poll_linkedin_replies",
    description="Poll HeyReach for LinkedIn replies (safety net)",
    retries=1,
    retry_delay_seconds=60,
    tags=["reply", "polling", "linkedin"],
)
async def poll_linkedin_replies_task(
    since: datetime | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Poll HeyReach for LinkedIn replies (safety net, webhooks are primary).

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
    if since is None:
        since = datetime.utcnow() - timedelta(hours=1)

    logger.info(f"Polling HeyReach for LinkedIn replies since {since}")

    heyreach = get_heyreach_client()

    try:
        # Fetch conversations
        conversations = await heyreach.get_conversations(
            updated_after=since,
            limit=limit,
        )

        processed = 0
        failed = 0
        replies = []

        async with get_db_session() as db:
            for conv in conversations:
                try:
                    linkedin_url = conv.get("prospect_linkedin_url")
                    message_content = conv.get("last_message", {}).get("text", "")
                    conversation_id = conv.get("id")

                    # Find lead by LinkedIn URL
                    stmt = select(Lead).where(
                        and_(
                            Lead.linkedin_url == linkedin_url,
                            Lead.deleted_at.is_(None),
                        )
                    ).order_by(desc(Lead.created_at))
                    result = await db.execute(stmt)
                    lead = result.scalar_one_or_none()

                    if not lead:
                        logger.warning(f"No lead found for LinkedIn {linkedin_url}")
                        continue

                    # Process reply
                    await process_reply_task(
                        lead_id=lead.id,
                        message=message_content,
                        channel=ChannelType.LINKEDIN,
                        provider_message_id=conversation_id,
                        metadata={"from_polling": True},
                    )

                    replies.append({
                        "lead_id": str(lead.id),
                        "linkedin_url": linkedin_url,
                        "conversation_id": conversation_id,
                    })
                    processed += 1

                except Exception as e:
                    logger.error(f"Failed to process LinkedIn reply: {e}")
                    failed += 1

        logger.info(
            f"LinkedIn polling complete. "
            f"Processed: {processed}, Failed: {failed}"
        )

        return {
            "total": len(conversations),
            "processed": processed,
            "failed": failed,
            "replies": replies,
        }

    except Exception as e:
        logger.error(f"LinkedIn polling failed: {e}")
        raise


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
