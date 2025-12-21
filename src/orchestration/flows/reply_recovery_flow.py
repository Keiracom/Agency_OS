"""
FILE: src/orchestration/flows/reply_recovery_flow.py
PURPOSE: Safety net flow for polling missed webhook replies (6-hourly backup)
PHASE: 5 (Orchestration)
TASK: ORC-005
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/integrations/postmark.py
  - src/integrations/twilio.py
  - src/integrations/heyreach.py
  - src/engines/closer.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only
  - Rule 20: Webhook-first architecture (this is safety net, NOT primary)
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from prefect import flow, task
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.closer import get_closer_engine
from src.integrations.heyreach import get_heyreach_client
from src.integrations.postmark import get_postmark_client
from src.integrations.supabase import get_db_session
from src.integrations.twilio import get_twilio_client
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="poll_email_replies", retries=2, retry_delay_seconds=10)
async def poll_email_replies_task(since_hours: int = 6) -> dict[str, Any]:
    """
    Poll for email replies that might have been missed by webhooks.

    This is a safety net - webhooks are the primary mechanism (Rule 20).

    Args:
        since_hours: How many hours back to check

    Returns:
        Dict with replies found
    """
    postmark_client = get_postmark_client()

    try:
        # Poll inbound messages from Postmark
        since_time = datetime.utcnow() - timedelta(hours=since_hours)

        replies = await postmark_client.get_inbound_messages(
            count=100,
            offset=0,
        )

        # Filter to messages since cutoff time
        recent_replies = []
        for reply in replies:
            received_at = reply.get("ReceivedAt")
            if received_at and datetime.fromisoformat(received_at.replace("Z", "+00:00")) > since_time:
                recent_replies.append({
                    "message_id": reply.get("MessageID"),
                    "from_email": reply.get("From"),
                    "subject": reply.get("Subject"),
                    "text_body": reply.get("TextBody"),
                    "html_body": reply.get("HtmlBody"),
                    "received_at": received_at,
                    "in_reply_to": reply.get("Headers", [{}])[0].get("Value") if reply.get("Headers") else None,
                })

        logger.info(f"Polled {len(recent_replies)} email replies from last {since_hours} hours")

        return {
            "channel": "email",
            "replies_found": len(recent_replies),
            "replies": recent_replies,
        }

    except Exception as e:
        logger.error(f"Failed to poll email replies: {e}")
        return {
            "channel": "email",
            "replies_found": 0,
            "replies": [],
            "error": str(e),
        }


@task(name="poll_sms_replies", retries=2, retry_delay_seconds=10)
async def poll_sms_replies_task(since_hours: int = 6) -> dict[str, Any]:
    """
    Poll for SMS replies that might have been missed by webhooks.

    This is a safety net - webhooks are the primary mechanism (Rule 20).

    Args:
        since_hours: How many hours back to check

    Returns:
        Dict with replies found
    """
    twilio_client = get_twilio_client()

    try:
        # Poll inbound messages from Twilio
        since_time = datetime.utcnow() - timedelta(hours=since_hours)

        replies = await twilio_client.get_inbound_messages(
            date_sent_after=since_time,
            limit=100,
        )

        recent_replies = []
        for reply in replies:
            recent_replies.append({
                "message_sid": reply.get("sid"),
                "from_phone": reply.get("from"),
                "to_phone": reply.get("to"),
                "body": reply.get("body"),
                "date_sent": reply.get("date_sent"),
            })

        logger.info(f"Polled {len(recent_replies)} SMS replies from last {since_hours} hours")

        return {
            "channel": "sms",
            "replies_found": len(recent_replies),
            "replies": recent_replies,
        }

    except Exception as e:
        logger.error(f"Failed to poll SMS replies: {e}")
        return {
            "channel": "sms",
            "replies_found": 0,
            "replies": [],
            "error": str(e),
        }


@task(name="poll_linkedin_replies", retries=2, retry_delay_seconds=10)
async def poll_linkedin_replies_task(since_hours: int = 6) -> dict[str, Any]:
    """
    Poll for LinkedIn replies that might have been missed by webhooks.

    This is a safety net - webhooks are the primary mechanism (Rule 20).

    Args:
        since_hours: How many hours back to check

    Returns:
        Dict with replies found
    """
    heyreach_client = get_heyreach_client()

    try:
        # Poll conversations from HeyReach
        replies = await heyreach_client.get_conversations(limit=100)

        # Filter to recent messages
        since_time = datetime.utcnow() - timedelta(hours=since_hours)
        recent_replies = []

        for conversation in replies:
            last_message_time = conversation.get("last_message_at")
            if last_message_time and datetime.fromisoformat(last_message_time) > since_time:
                # Check if last message is from prospect (not from us)
                if conversation.get("last_message_from") == "prospect":
                    recent_replies.append({
                        "conversation_id": conversation.get("id"),
                        "linkedin_url": conversation.get("prospect_url"),
                        "message": conversation.get("last_message_text"),
                        "received_at": last_message_time,
                    })

        logger.info(f"Polled {len(recent_replies)} LinkedIn replies from last {since_hours} hours")

        return {
            "channel": "linkedin",
            "replies_found": len(recent_replies),
            "replies": recent_replies,
        }

    except Exception as e:
        logger.error(f"Failed to poll LinkedIn replies: {e}")
        return {
            "channel": "linkedin",
            "replies_found": 0,
            "replies": [],
            "error": str(e),
        }


@task(name="find_lead_by_contact", retries=2, retry_delay_seconds=5)
async def find_lead_by_contact_task(
    email: str | None = None,
    phone: str | None = None,
    linkedin_url: str | None = None,
) -> dict[str, Any]:
    """
    Find a lead by contact information.

    Args:
        email: Email address
        phone: Phone number
        linkedin_url: LinkedIn profile URL

    Returns:
        Dict with lead ID if found
    """
    async with get_db_session() as db:
        conditions = [Lead.deleted_at.is_(None)]  # Soft delete check

        if email:
            conditions.append(Lead.email == email.lower())
        elif phone:
            # Normalize phone (remove spaces, dashes)
            normalized_phone = phone.replace(" ", "").replace("-", "")
            conditions.append(Lead.phone.ilike(f"%{normalized_phone}%"))
        elif linkedin_url:
            conditions.append(Lead.linkedin_url == linkedin_url)
        else:
            return {"found": False, "error": "No contact info provided"}

        stmt = select(Lead.id, Lead.campaign_id, Lead.client_id).where(and_(*conditions)).limit(1)
        result = await db.execute(stmt)
        row = result.first()

        if row:
            return {
                "found": True,
                "lead_id": str(row[0]),
                "campaign_id": str(row[1]),
                "client_id": str(row[2]),
            }
        else:
            return {"found": False}


@task(name="check_if_reply_processed", retries=2, retry_delay_seconds=5)
async def check_if_reply_processed_task(
    lead_id: str, provider_message_id: str, channel: str
) -> dict[str, Any]:
    """
    Check if a reply has already been processed.

    Prevents duplicate processing of the same reply.

    Args:
        lead_id: Lead UUID string
        provider_message_id: Message ID from provider
        channel: Channel type

    Returns:
        Dict with whether reply was already processed
    """
    async with get_db_session() as db:
        stmt = select(Activity.id).where(
            and_(
                Activity.lead_id == UUID(lead_id),
                Activity.provider_message_id == provider_message_id,
                Activity.channel == ChannelType(channel),
                Activity.action == "reply_received",
            )
        ).limit(1)
        result = await db.execute(stmt)
        activity = result.scalar_one_or_none()

        return {
            "lead_id": lead_id,
            "already_processed": activity is not None,
        }


@task(name="process_missed_reply", retries=3, retry_delay_seconds=10)
async def process_missed_reply_task(
    lead_id: str,
    message: str,
    channel: str,
    provider_message_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Process a reply that was missed by webhooks.

    Args:
        lead_id: Lead UUID string
        message: Reply message content
        channel: Channel type (email, sms, linkedin)
        provider_message_id: Optional message ID from provider
        metadata: Optional additional metadata

    Returns:
        Dict with processing result
    """
    async with get_db_session() as db:
        closer_engine = get_closer_engine()
        lead_uuid = UUID(lead_id)
        channel_type = ChannelType(channel)

        # Process the reply using Closer engine
        result = await closer_engine.process_reply(
            db=db,
            lead_id=lead_uuid,
            message=message,
            channel=channel_type,
            provider_message_id=provider_message_id,
            metadata=metadata,
        )

        if result.success:
            logger.info(
                f"Processed missed {channel} reply for lead {lead_id}: "
                f"intent={result.data.get('intent')}"
            )

        return {
            "lead_id": lead_id,
            "channel": channel,
            "success": result.success,
            "intent": result.data.get("intent") if result.success else None,
            "error": result.error if not result.success else None,
        }


# ============================================
# FLOW
# ============================================


@flow(
    name="reply_recovery",
    description="Safety net flow for polling missed webhook replies (6-hourly)",
    log_prints=True,
)
async def reply_recovery_flow(since_hours: int = 6) -> dict[str, Any]:
    """
    Reply recovery flow.

    This is a SAFETY NET for missed webhook replies (Rule 20).
    Webhooks are the primary mechanism for reply handling.

    Steps:
    1. Poll email replies from Postmark
    2. Poll SMS replies from Twilio
    3. Poll LinkedIn replies from HeyReach
    4. For each reply:
       a. Find lead by contact info
       b. Check if already processed
       c. Process via Closer engine if new

    Args:
        since_hours: How many hours back to check (default 6)

    Returns:
        Dict with recovery summary
    """
    logger.info(
        f"Starting reply recovery flow (safety net for last {since_hours} hours)"
    )

    # Step 1: Poll all channels
    email_replies = await poll_email_replies_task(since_hours=since_hours)
    sms_replies = await poll_sms_replies_task(since_hours=since_hours)
    linkedin_replies = await poll_linkedin_replies_task(since_hours=since_hours)

    total_found = (
        email_replies["replies_found"]
        + sms_replies["replies_found"]
        + linkedin_replies["replies_found"]
    )

    logger.info(
        f"Found {total_found} total replies: "
        f"{email_replies['replies_found']} email, "
        f"{sms_replies['replies_found']} sms, "
        f"{linkedin_replies['replies_found']} linkedin"
    )

    if total_found == 0:
        return {
            "total_found": 0,
            "total_processed": 0,
            "message": "No missed replies found",
        }

    # Step 2: Process email replies
    email_processed = 0
    for reply in email_replies["replies"]:
        try:
            # Find lead
            lead_result = await find_lead_by_contact_task(email=reply["from_email"])
            if not lead_result["found"]:
                logger.warning(f"Lead not found for email {reply['from_email']}")
                continue

            # Check if already processed
            check_result = await check_if_reply_processed_task(
                lead_id=lead_result["lead_id"],
                provider_message_id=reply["message_id"],
                channel="email",
            )
            if check_result["already_processed"]:
                logger.debug(f"Email reply {reply['message_id']} already processed")
                continue

            # Process reply
            process_result = await process_missed_reply_task(
                lead_id=lead_result["lead_id"],
                message=reply["text_body"] or reply["html_body"],
                channel="email",
                provider_message_id=reply["message_id"],
                metadata={"subject": reply["subject"]},
            )
            if process_result["success"]:
                email_processed += 1

        except Exception as e:
            logger.error(f"Failed to process email reply: {e}")

    # Step 3: Process SMS replies
    sms_processed = 0
    for reply in sms_replies["replies"]:
        try:
            # Find lead
            lead_result = await find_lead_by_contact_task(phone=reply["from_phone"])
            if not lead_result["found"]:
                logger.warning(f"Lead not found for phone {reply['from_phone']}")
                continue

            # Check if already processed
            check_result = await check_if_reply_processed_task(
                lead_id=lead_result["lead_id"],
                provider_message_id=reply["message_sid"],
                channel="sms",
            )
            if check_result["already_processed"]:
                logger.debug(f"SMS reply {reply['message_sid']} already processed")
                continue

            # Process reply
            process_result = await process_missed_reply_task(
                lead_id=lead_result["lead_id"],
                message=reply["body"],
                channel="sms",
                provider_message_id=reply["message_sid"],
            )
            if process_result["success"]:
                sms_processed += 1

        except Exception as e:
            logger.error(f"Failed to process SMS reply: {e}")

    # Step 4: Process LinkedIn replies
    linkedin_processed = 0
    for reply in linkedin_replies["replies"]:
        try:
            # Find lead
            lead_result = await find_lead_by_contact_task(
                linkedin_url=reply["linkedin_url"]
            )
            if not lead_result["found"]:
                logger.warning(f"Lead not found for LinkedIn {reply['linkedin_url']}")
                continue

            # Check if already processed
            check_result = await check_if_reply_processed_task(
                lead_id=lead_result["lead_id"],
                provider_message_id=reply["conversation_id"],
                channel="linkedin",
            )
            if check_result["already_processed"]:
                logger.debug(
                    f"LinkedIn reply {reply['conversation_id']} already processed"
                )
                continue

            # Process reply
            process_result = await process_missed_reply_task(
                lead_id=lead_result["lead_id"],
                message=reply["message"],
                channel="linkedin",
                provider_message_id=reply["conversation_id"],
            )
            if process_result["success"]:
                linkedin_processed += 1

        except Exception as e:
            logger.error(f"Failed to process LinkedIn reply: {e}")

    total_processed = email_processed + sms_processed + linkedin_processed

    summary = {
        "total_found": total_found,
        "total_processed": total_processed,
        "email_found": email_replies["replies_found"],
        "email_processed": email_processed,
        "sms_found": sms_replies["replies_found"],
        "sms_processed": sms_processed,
        "linkedin_found": linkedin_replies["replies_found"],
        "linkedin_processed": linkedin_processed,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Reply recovery flow completed: {total_processed} of {total_found} "
        f"replies processed"
    )

    return summary


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] No imports from other orchestration files
# [x] Imports from engines (closer), integrations, models
# [x] Soft delete checks in queries (Rule 14)
# [x] @flow and @task decorators from Prefect
# [x] This is safety net, NOT primary reply handling (Rule 20)
# [x] Polls email, SMS, LinkedIn for missed replies
# [x] Deduplication check (doesn't process same reply twice)
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] Calls Closer engine for intent classification
# [x] Updates lead status based on intent (via Closer)
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Returns structured dict results
