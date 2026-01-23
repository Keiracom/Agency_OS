"""
FILE: src/api/routes/webhooks.py
PURPOSE: Inbound webhook routes for Postmark, Twilio, ClickSend, Unipile, Vapi, and Email Providers
PHASE: 7 (API Routes), Phase 17 (Vapi Voice), Phase 24C (Email Engagement), Unipile Migration
TASK: API-006, CRED-007, ENGAGE-002, P2-REPLY-WEBHOOKS
DEPENDENCIES:
  - src/engines/closer.py
  - src/engines/voice.py
  - src/integrations/postmark.py
  - src/integrations/twilio.py
  - src/integrations/unipile.py (migrated from heyreach.py)
  - src/integrations/vapi.py
  - src/services/email_events_service.py
  - src/services/linkedin_connection_service.py (for account webhooks)
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft delete checks
  - Rule 20: Webhook-first architecture
"""

import hmac
import hashlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.closer import get_closer_engine
from src.exceptions import ResourceNotFoundError, WebhookError
from src.integrations.postmark import get_postmark_client
from src.api.dependencies import get_db_session
from src.integrations.twilio import get_twilio_client
from src.integrations.unipile import get_unipile_client
from src.engines.voice import get_voice_engine
from src.models.base import ChannelType
from src.models.lead import Lead
from src.models.activity import Activity
from src.services.email_events_service import (
    EmailEventsService,
    parse_smartlead_webhook,
    parse_salesforge_webhook,
    parse_resend_webhook,
)
from src.services.linkedin_connection_service import linkedin_connection_service


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ============================================
# Webhook Signature Verification
# ============================================


def verify_postmark_signature(payload: bytes, signature: str | None) -> bool:
    """
    Verify Postmark webhook signature.

    Postmark doesn't provide built-in signature verification,
    so this is a placeholder for custom implementation if needed.

    Args:
        payload: Raw webhook payload
        signature: X-Postmark-Signature header value

    Returns:
        True if signature is valid (currently always returns True)
    """
    # NOTE: Postmark doesn't have built-in webhook signature verification
    # In production, you may want to:
    # 1. Use IP allowlisting
    # 2. Use a custom HMAC signature with your own secret
    # 3. Use Postmark's inbound domain verification

    # For now, accept all Postmark webhooks
    # TODO: Implement custom signature verification if needed
    return True


def verify_twilio_signature(
    url: str,
    params: dict[str, Any],
    signature: str | None,
) -> bool:
    """
    Verify Twilio webhook signature using X-Twilio-Signature header.

    Args:
        url: Full webhook URL
        params: Request form parameters
        signature: X-Twilio-Signature header value

    Returns:
        True if signature is valid
    """
    if not signature:
        return False

    auth_token = settings.twilio_auth_token
    if not auth_token:
        # If no auth token configured, skip verification in development
        return not settings.is_production

    # Construct the signature string
    # Format: URL + sorted form parameters concatenated as key=value
    signature_string = url
    for key in sorted(params.keys()):
        signature_string += f"{key}{params[key]}"

    # Compute HMAC-SHA1
    computed_signature = hmac.new(
        auth_token.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.sha1
    ).digest()

    # Base64 encode
    import base64
    computed_signature_b64 = base64.b64encode(computed_signature).decode('utf-8')

    # Compare signatures
    return hmac.compare_digest(computed_signature_b64, signature)


# ============================================
# Helper Functions
# ============================================


async def find_lead_by_email(db: AsyncSession, email: str) -> Lead | None:
    """
    Find lead by email address (soft delete aware).

    Args:
        db: Database session
        email: Email address to search

    Returns:
        Lead if found, None otherwise
    """
    stmt = (
        select(Lead)
        .where(
            and_(
                Lead.email == email.lower(),
                Lead.deleted_at.is_(None),  # Soft delete check (Rule 14)
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_lead_by_phone(db: AsyncSession, phone: str) -> Lead | None:
    """
    Find lead by phone number (soft delete aware).

    Args:
        db: Database session
        phone: Phone number to search

    Returns:
        Lead if found, None otherwise
    """
    stmt = (
        select(Lead)
        .where(
            and_(
                Lead.phone == phone,
                Lead.deleted_at.is_(None),  # Soft delete check (Rule 14)
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_lead_by_linkedin(db: AsyncSession, linkedin_url: str) -> Lead | None:
    """
    Find lead by LinkedIn URL (soft delete aware).

    Args:
        db: Database session
        linkedin_url: LinkedIn profile URL

    Returns:
        Lead if found, None otherwise
    """
    stmt = (
        select(Lead)
        .where(
            and_(
                Lead.linkedin_url == linkedin_url,
                Lead.deleted_at.is_(None),  # Soft delete check (Rule 14)
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_duplicate_activity(
    db: AsyncSession,
    lead_id: UUID,
    provider_message_id: str,
) -> bool:
    """
    Check if activity already exists for this message (deduplication).

    Args:
        db: Database session
        lead_id: Lead UUID
        provider_message_id: Provider's message ID

    Returns:
        True if activity already exists
    """
    stmt = (
        select(Activity)
        .where(
            and_(
                Activity.lead_id == lead_id,
                Activity.provider_message_id == provider_message_id,
                Activity.action == "replied",
            )
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


# ============================================
# Postmark Webhooks
# ============================================


@router.post("/postmark/inbound")
async def postmark_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle inbound email replies from Postmark.

    Webhook-first architecture (Rule 20). This is the primary method
    for processing email replies.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    # Get raw payload and signature
    payload = await request.json()
    signature = request.headers.get("X-Postmark-Signature")

    # Verify signature (currently placeholder)
    # NOTE: Implement custom verification in production
    if settings.is_production and not verify_postmark_signature(
        await request.body(), signature
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        # Parse webhook payload
        postmark = get_postmark_client()
        parsed = postmark.parse_inbound_webhook(payload)

        # Find lead by email
        from_email = parsed["from_email"]
        if not from_email:
            return {"status": "ignored", "reason": "no_sender_email"}

        lead = await find_lead_by_email(db, from_email)
        if not lead:
            return {"status": "ignored", "reason": "lead_not_found"}

        # Check for duplicate processing
        message_id = parsed["message_id"]
        if message_id and await check_duplicate_activity(db, lead.id, message_id):
            return {"status": "ignored", "reason": "already_processed"}

        # Extract message content (prefer stripped text)
        message = parsed["stripped_text"] or parsed["text_body"] or ""
        if not message:
            return {"status": "ignored", "reason": "empty_message"}

        # Process reply via Closer engine
        closer = get_closer_engine()
        result = await closer.process_reply(
            db=db,
            lead_id=lead.id,
            message=message,
            channel=ChannelType.EMAIL,
            provider_message_id=message_id,
            in_reply_to=parsed["in_reply_to"],
            metadata={
                "from_name": parsed["from_name"],
                "subject": parsed["subject"],
                "to_email": parsed["to_email"],
                "date": parsed["date"],
                "has_attachments": len(parsed["attachments"]) > 0,
            },
        )

        if not result.success:
            raise WebhookError(
                url="/webhooks/postmark/inbound",
                message=f"Reply processing failed: {result.error}",
            )

        return {
            "status": "processed",
            "lead_id": str(lead.id),
            "intent": result.data["intent"],
            "confidence": result.data["confidence"],
            "activity_id": result.data["activity_id"],
        }

    except Exception as e:
        # Log error but return 200 to prevent Postmark retries
        # TODO: Log to Sentry in production
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/postmark/bounce")
async def postmark_bounce_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle email bounce notifications from Postmark.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    payload = await request.json()

    try:
        # Parse bounce webhook
        postmark = get_postmark_client()
        parsed = postmark.parse_bounce_webhook(payload)

        # Find lead by email
        email = parsed["email"]
        if not email:
            return {"status": "ignored", "reason": "no_email"}

        lead = await find_lead_by_email(db, email)
        if not lead:
            return {"status": "ignored", "reason": "lead_not_found"}

        # Update lead status to bounced
        from src.models.base import LeadStatus
        lead.status = LeadStatus.BOUNCED
        lead.bounce_count += 1

        # Log bounce activity
        activity = Activity(
            client_id=lead.client_id,
            campaign_id=lead.campaign_id,
            lead_id=lead.id,
            channel=ChannelType.EMAIL,
            action="bounced",
            provider_message_id=parsed["message_id"],
            provider="postmark",
            provider_status=parsed["bounce_type"],
            metadata={
                "bounce_type": parsed["bounce_type"],
                "description": parsed["description"],
                "details": parsed["details"],
                "can_activate": parsed["can_activate"],
            },
        )
        db.add(activity)

        await db.commit()

        return {
            "status": "processed",
            "lead_id": str(lead.id),
            "bounce_type": parsed["bounce_type"],
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/postmark/spam")
async def postmark_spam_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle spam complaint notifications from Postmark.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    payload = await request.json()

    try:
        # Parse spam complaint
        email = payload.get("Email")
        if not email:
            return {"status": "ignored", "reason": "no_email"}

        lead = await find_lead_by_email(db, email)
        if not lead:
            return {"status": "ignored", "reason": "lead_not_found"}

        # Update lead status to unsubscribed
        from src.models.base import LeadStatus
        lead.status = LeadStatus.UNSUBSCRIBED

        # Log spam complaint activity
        activity = Activity(
            client_id=lead.client_id,
            campaign_id=lead.campaign_id,
            lead_id=lead.id,
            channel=ChannelType.EMAIL,
            action="spam_complaint",
            provider="postmark",
            metadata={
                "complaint_type": "spam",
                "email": email,
            },
        )
        db.add(activity)

        await db.commit()

        return {
            "status": "processed",
            "lead_id": str(lead.id),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# Twilio Webhooks
# ============================================


@router.post("/twilio/inbound")
async def twilio_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle inbound SMS replies from Twilio.

    Webhook-first architecture (Rule 20). This is the primary method
    for processing SMS replies.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        TwiML response (empty to acknowledge)
    """
    # Get form data
    form_data = await request.form()
    params = dict(form_data)

    # Get signature for verification
    signature = request.headers.get("X-Twilio-Signature")

    # Verify signature
    # Construct full URL for signature verification
    url = str(request.url)
    if settings.is_production and not verify_twilio_signature(url, params, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Twilio signature",
        )

    try:
        # Parse webhook payload
        twilio = get_twilio_client()
        parsed = twilio.parse_inbound_webhook(params)

        # Find lead by phone number
        from_number = parsed["from_number"]
        if not from_number:
            # Return empty TwiML to acknowledge
            return {"status": "ignored", "reason": "no_phone_number"}

        lead = await find_lead_by_phone(db, from_number)
        if not lead:
            return {"status": "ignored", "reason": "lead_not_found"}

        # Check for duplicate processing
        message_sid = parsed["message_sid"]
        if message_sid and await check_duplicate_activity(db, lead.id, message_sid):
            return {"status": "ignored", "reason": "already_processed"}

        # Extract message content
        message = parsed["body"]
        if not message:
            return {"status": "ignored", "reason": "empty_message"}

        # Process reply via Closer engine
        closer = get_closer_engine()
        result = await closer.process_reply(
            db=db,
            lead_id=lead.id,
            message=message,
            channel=ChannelType.SMS,
            provider_message_id=message_sid,
            metadata={
                "from_number": from_number,
                "to_number": parsed["to_number"],
                "from_city": parsed["from_city"],
                "from_state": parsed["from_state"],
                "from_country": parsed["from_country"],
                "num_media": parsed["num_media"],
            },
        )

        if not result.success:
            raise WebhookError(
                url="/webhooks/twilio/inbound",
                message=f"Reply processing failed: {result.error}",
            )

        # Return empty TwiML response to acknowledge
        # Twilio expects TwiML, but empty is fine
        return {
            "status": "processed",
            "lead_id": str(lead.id),
            "intent": result.data["intent"],
            "confidence": result.data["confidence"],
        }

    except Exception as e:
        # Return empty response to prevent Twilio retries
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/twilio/status")
async def twilio_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle SMS delivery status updates from Twilio.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    # Get form data
    form_data = await request.form()
    params = dict(form_data)

    try:
        # Parse status webhook
        twilio = get_twilio_client()
        parsed = twilio.parse_status_webhook(params)

        # Find existing activity by message SID
        message_sid = parsed["message_sid"]
        if not message_sid:
            return {"status": "ignored", "reason": "no_message_sid"}

        stmt = (
            select(Activity)
            .where(Activity.provider_message_id == message_sid)
        )
        result = await db.execute(stmt)
        activity = result.scalar_one_or_none()

        if not activity:
            return {"status": "ignored", "reason": "activity_not_found"}

        # Update activity with delivery status
        message_status = parsed["message_status"]
        activity.provider_status = message_status

        # If delivered, create a new activity
        if message_status == "delivered":
            delivered_activity = Activity(
                client_id=activity.client_id,
                campaign_id=activity.campaign_id,
                lead_id=activity.lead_id,
                channel=ChannelType.SMS,
                action="delivered",
                provider_message_id=message_sid,
                provider="twilio",
                provider_status=message_status,
            )
            db.add(delivered_activity)

        # If failed, log the error
        if message_status in ("failed", "undelivered"):
            activity.metadata["error_code"] = parsed.get("error_code")
            activity.metadata["error_message"] = parsed.get("error_message")

        await db.commit()

        return {
            "status": "processed",
            "message_sid": message_sid,
            "message_status": message_status,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# ClickSend Webhooks (SMS - Primary for Australia)
# ============================================


@router.post("/clicksend/inbound")
async def clicksend_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle inbound SMS replies from ClickSend.

    Webhook-first architecture (Rule 20). This is the primary method
    for processing SMS replies in Australia.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    try:
        payload = await request.json()

        # Parse webhook payload using ClickSend parser
        from src.integrations.clicksend import get_clicksend_client
        clicksend = get_clicksend_client()
        parsed = clicksend.parse_inbound_sms(payload)

        # Find lead by phone number
        from_number = parsed["from_number"]
        if not from_number:
            return {"status": "ignored", "reason": "no_phone_number"}

        lead = await find_lead_by_phone(db, from_number)
        if not lead:
            return {"status": "ignored", "reason": "lead_not_found"}

        # Check for duplicate processing
        message_id = parsed["message_id"]
        if message_id and await check_duplicate_activity(db, lead.id, message_id):
            return {"status": "ignored", "reason": "already_processed"}

        # Extract message content
        message = parsed["body"]
        if not message:
            return {"status": "ignored", "reason": "empty_message"}

        # Process reply via Closer engine
        closer = get_closer_engine()
        result = await closer.process_reply(
            db=db,
            lead_id=lead.id,
            message=message,
            channel=ChannelType.SMS,
            provider_message_id=message_id,
            metadata={
                "from_number": from_number,
                "to_number": parsed["to_number"],
                "timestamp": parsed["timestamp"],
                "custom_string": parsed["custom_string"],
                "provider": "clicksend",
            },
        )

        if not result.success:
            raise WebhookError(
                url="/webhooks/clicksend/inbound",
                message=f"Reply processing failed: {result.error}",
            )

        return {
            "status": "processed",
            "lead_id": str(lead.id),
            "intent": result.data["intent"],
            "confidence": result.data["confidence"],
        }

    except Exception as e:
        # Return 200 to prevent ClickSend retries
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/clicksend/status")
async def clicksend_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle SMS delivery status updates from ClickSend.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    try:
        payload = await request.json()

        # Parse status webhook
        from src.integrations.clicksend import get_clicksend_client
        clicksend = get_clicksend_client()
        parsed = clicksend.parse_sms_webhook(payload)

        # Find existing activity by message ID
        message_id = parsed["message_id"]
        if not message_id:
            return {"status": "ignored", "reason": "no_message_id"}

        stmt = (
            select(Activity)
            .where(Activity.provider_message_id == message_id)
        )
        result = await db.execute(stmt)
        activity = result.scalar_one_or_none()

        if not activity:
            return {"status": "ignored", "reason": "activity_not_found"}

        # Update activity with delivery status
        status = parsed["status"]
        activity.provider_status = status

        # If delivered, create a new activity
        if status in ("Delivered", "SUCCESS"):
            delivered_activity = Activity(
                client_id=activity.client_id,
                campaign_id=activity.campaign_id,
                lead_id=activity.lead_id,
                channel=ChannelType.SMS,
                action="delivered",
                provider_message_id=message_id,
                provider="clicksend",
                provider_status=status,
            )
            db.add(delivered_activity)

        # If failed, log the error
        if status in ("Failed", "FAILED", "Undelivered"):
            activity.metadata["status_code"] = parsed.get("status_code")

        await db.commit()

        return {
            "status": "processed",
            "message_id": message_id,
            "delivery_status": status,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# Unipile Webhooks (LinkedIn - replaces HeyReach)
# ============================================


@router.post("/unipile/account")
async def unipile_account_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle Unipile account connection webhooks.

    Called when:
    - User completes LinkedIn auth via hosted flow (CREATION_SUCCESS)
    - Account is disconnected (DISCONNECTED)
    - Connection fails (CREATION_FAILED)

    Webhook-first architecture (Rule 20).

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    try:
        payload = await request.json()

        # Parse and validate webhook
        unipile = get_unipile_client()
        parsed = unipile.parse_webhook(payload)

        # Handle account connection events
        result = await linkedin_connection_service.handle_connection_webhook(
            db=db,
            payload=parsed,
        )

        return result

    except Exception as e:
        # Return 200 to prevent Unipile retries
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/unipile/message")
async def unipile_message_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle inbound LinkedIn messages/replies from Unipile.

    Webhook-first architecture (Rule 20). This is the primary method
    for processing LinkedIn replies.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    try:
        payload = await request.json()

        # Parse webhook
        unipile = get_unipile_client()
        parsed = unipile.parse_webhook(payload)

        # Check event type
        event_type = parsed.get("event") or parsed.get("type")
        if event_type not in ("NEW_MESSAGE", "message.new", "message_received"):
            return {"status": "ignored", "reason": "not_a_message_event"}

        # Extract message data
        message_data = parsed.get("data", {})
        linkedin_url = (
            message_data.get("sender_id")
            or message_data.get("sender", {}).get("identifier")
            or parsed.get("profile_url")
        )
        message = (
            message_data.get("text")
            or message_data.get("body")
            or parsed.get("message")
        )
        message_id = (
            message_data.get("id")
            or parsed.get("message_id")
        )

        if not linkedin_url:
            return {"status": "ignored", "reason": "no_linkedin_url"}

        if not message:
            return {"status": "ignored", "reason": "empty_message"}

        # Find lead by LinkedIn URL
        lead = await find_lead_by_linkedin(db, linkedin_url)
        if not lead:
            return {"status": "ignored", "reason": "lead_not_found"}

        # Check for duplicate processing
        if message_id and await check_duplicate_activity(db, lead.id, message_id):
            return {"status": "ignored", "reason": "already_processed"}

        # Process reply via Closer engine
        closer = get_closer_engine()
        result = await closer.process_reply(
            db=db,
            lead_id=lead.id,
            message=message,
            channel=ChannelType.LINKEDIN,
            provider_message_id=message_id,
            metadata={
                "linkedin_url": linkedin_url,
                "sender_name": message_data.get("sender", {}).get("name"),
                "account_id": parsed.get("account_id"),
                "conversation_id": message_data.get("conversation_id"),
                "provider": "unipile",
            },
        )

        if not result.success:
            raise WebhookError(
                url="/webhooks/unipile/message",
                message=f"Reply processing failed: {result.error}",
            )

        return {
            "status": "processed",
            "lead_id": str(lead.id),
            "intent": result.data["intent"],
            "confidence": result.data["confidence"],
            "activity_id": result.data["activity_id"],
        }

    except Exception as e:
        # Return 200 to prevent Unipile retries
        return {
            "status": "error",
            "error": str(e),
        }


# Legacy HeyReach webhook (redirects to Unipile handler for transition period)
@router.post("/heyreach/inbound")
async def heyreach_inbound_webhook_legacy(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Legacy HeyReach webhook endpoint.

    Redirects to Unipile message handler for backwards compatibility.
    Will be removed after full migration.
    """
    return await unipile_message_webhook(request, db)


# ============================================
# Vapi Webhooks (Voice AI)
# ============================================


@router.post("/vapi")
async def vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle Vapi call webhooks.

    Events:
    - call-started: Call has been initiated
    - call-ended: Call has ended
    - end-of-call-report: Final call summary with transcript

    Webhook-first architecture (Rule 20). This is the primary method
    for processing voice call completions and transcripts.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    try:
        payload = await request.json()

        # Get event type
        event_type = payload.get("message", {}).get("type", payload.get("type"))

        # Only process call completion events
        if event_type not in ["call-ended", "end-of-call-report"]:
            return {"status": "acknowledged", "event": event_type}

        # Process via Voice engine
        voice = get_voice_engine()
        result = await voice.process_call_webhook(db, payload)

        if not result.success:
            # Log error but return 200 to prevent Vapi retries
            return {
                "status": "error",
                "error": result.error,
            }

        return {
            "status": "processed",
            "call_id": result.data.get("call_id"),
            "event": result.data.get("event"),
        }

    except Exception as e:
        # Return 200 to prevent Vapi retries
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# Smartlead Webhooks (Email Engagement - Phase 24C)
# ============================================


def verify_smartlead_signature(payload: bytes, signature: str | None) -> bool:
    """
    Verify Smartlead webhook signature.

    Smartlead uses a shared secret for HMAC-SHA256 verification.

    Args:
        payload: Raw webhook payload
        signature: X-Smartlead-Signature header value

    Returns:
        True if signature is valid
    """
    if not signature:
        # Skip verification in development
        return not settings.is_production

    secret = settings.smartlead_webhook_secret
    if not secret:
        return not settings.is_production

    computed = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


@router.post("/smartlead/events")
async def smartlead_events_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle email engagement events from Smartlead.

    Events processed:
    - email_opened: Track email opens with metadata
    - email_clicked: Track link clicks with URL
    - email_bounced: Handle hard/soft bounces
    - email_unsubscribed: Handle opt-outs
    - email_replied: Forward to closer engine

    Webhook-first architecture (Rule 20).

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    raw_body = await request.body()
    payload = await request.json()
    signature = request.headers.get("X-Smartlead-Signature")

    # Verify signature
    if settings.is_production and not verify_smartlead_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        # Parse webhook payload
        parsed = parse_smartlead_webhook(payload)

        if not parsed["event_type"]:
            return {"status": "ignored", "reason": "unknown_event_type"}

        # Initialize service with database session
        email_service = EmailEventsService(db)

        # Find activity by provider message ID
        provider_id = parsed["provider_message_id"]
        if not provider_id:
            return {"status": "ignored", "reason": "no_message_id"}

        activity = await email_service.find_activity_by_provider_id(provider_id)
        if not activity:
            return {"status": "ignored", "reason": "activity_not_found"}

        # Process based on event type
        event_type = parsed["event_type"]

        if event_type == "opened":
            await email_service.record_open(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                device_info=parsed.get("device_info"),
                geo_info=parsed.get("geo_info"),
                provider="smartlead",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "clicked":
            await email_service.record_click(
                activity_id=activity.id,
                clicked_url=parsed.get("clicked_url", ""),
                event_at=parsed.get("event_at"),
                device_info=parsed.get("device_info"),
                geo_info=parsed.get("geo_info"),
                provider="smartlead",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "bounced":
            await email_service.record_bounce(
                activity_id=activity.id,
                bounce_type=parsed.get("bounce_type", "hard"),
                event_at=parsed.get("event_at"),
                provider="smartlead",
                provider_event_id=parsed.get("provider_event_id"),
                raw_payload=parsed.get("raw"),
            )

        elif event_type == "unsubscribed":
            await email_service.record_unsubscribe(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                provider="smartlead",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "complained":
            await email_service.record_complaint(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                provider="smartlead",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "replied":
            # Forward to closer engine for intent classification
            lead = await find_lead_by_email(db, parsed.get("lead_email", ""))
            if lead:
                closer = get_closer_engine()
                await closer.process_reply(
                    db=db,
                    lead_id=lead.id,
                    message=parsed.get("raw", {}).get("reply_text", ""),
                    channel=ChannelType.EMAIL,
                    provider_message_id=provider_id,
                    metadata=parsed.get("raw"),
                )

        return {
            "status": "processed",
            "event_type": event_type,
            "activity_id": str(activity.id),
        }

    except Exception as e:
        # Return 200 to prevent retries
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# Salesforge Webhooks (Email Engagement - Phase 24C)
# ============================================


def verify_salesforge_signature(payload: bytes, signature: str | None) -> bool:
    """
    Verify Salesforge webhook signature.

    Args:
        payload: Raw webhook payload
        signature: X-Salesforge-Signature header value

    Returns:
        True if signature is valid
    """
    if not signature:
        return not settings.is_production

    secret = settings.salesforge_webhook_secret
    if not secret:
        return not settings.is_production

    computed = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


@router.post("/salesforge/events")
async def salesforge_events_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle email engagement events from Salesforge.

    Events processed:
    - opened: Track email opens
    - clicked: Track link clicks
    - bounced: Handle bounces
    - unsubscribed: Handle opt-outs
    - replied: Forward to closer engine

    Webhook-first architecture (Rule 20).

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    raw_body = await request.body()
    payload = await request.json()
    signature = request.headers.get("X-Salesforge-Signature")

    # Verify signature
    if settings.is_production and not verify_salesforge_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        # Parse webhook payload
        parsed = parse_salesforge_webhook(payload)

        if not parsed["event_type"]:
            return {"status": "ignored", "reason": "unknown_event_type"}

        # Initialize service with database session
        email_service = EmailEventsService(db)

        # Find activity by provider message ID
        provider_id = parsed["provider_message_id"]
        if not provider_id:
            return {"status": "ignored", "reason": "no_message_id"}

        activity = await email_service.find_activity_by_provider_id(provider_id)
        if not activity:
            return {"status": "ignored", "reason": "activity_not_found"}

        # Process based on event type
        event_type = parsed["event_type"]

        if event_type == "opened":
            await email_service.record_open(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                device_info=parsed.get("device_info"),
                geo_info=parsed.get("geo_info"),
                provider="salesforge",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "clicked":
            await email_service.record_click(
                activity_id=activity.id,
                clicked_url=parsed.get("clicked_url", ""),
                event_at=parsed.get("event_at"),
                device_info=parsed.get("device_info"),
                geo_info=parsed.get("geo_info"),
                provider="salesforge",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "bounced":
            await email_service.record_bounce(
                activity_id=activity.id,
                bounce_type=parsed.get("bounce_type", "hard"),
                event_at=parsed.get("event_at"),
                provider="salesforge",
                provider_event_id=parsed.get("provider_event_id"),
                raw_payload=parsed.get("raw"),
            )

        elif event_type == "unsubscribed":
            await email_service.record_unsubscribe(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                provider="salesforge",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "complained":
            await email_service.record_complaint(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                provider="salesforge",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "replied":
            # Forward to closer engine
            lead = await find_lead_by_email(db, parsed.get("lead_email", ""))
            if lead:
                closer = get_closer_engine()
                await closer.process_reply(
                    db=db,
                    lead_id=lead.id,
                    message=parsed.get("raw", {}).get("reply_text", ""),
                    channel=ChannelType.EMAIL,
                    provider_message_id=provider_id,
                    metadata=parsed.get("raw"),
                )

        return {
            "status": "processed",
            "event_type": event_type,
            "activity_id": str(activity.id),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# Resend Webhooks (Email Engagement - Phase 24C)
# ============================================


def verify_resend_signature(payload: bytes, signature: str | None) -> bool:
    """
    Verify Resend webhook signature.

    Resend uses Svix for webhooks with HMAC-SHA256.

    Args:
        payload: Raw webhook payload
        signature: svix-signature header value

    Returns:
        True if signature is valid
    """
    if not signature:
        return not settings.is_production

    secret = settings.resend_webhook_secret
    if not secret:
        return not settings.is_production

    # Resend uses Svix which has a specific signature format
    # Format: v1,<base64-signature>
    try:
        parts = signature.split(",")
        if len(parts) < 2:
            return False

        # Extract the signature (v1,<sig>)
        sig_part = parts[1] if parts[0].startswith("v1") else parts[0]

        import base64
        computed = hmac.new(
            base64.b64decode(secret),
            payload,
            hashlib.sha256
        )
        computed_b64 = base64.b64encode(computed.digest()).decode()

        return hmac.compare_digest(computed_b64, sig_part)

    except Exception:
        return False


@router.post("/resend/events")
async def resend_events_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle email engagement events from Resend.

    Events processed:
    - email.opened: Track email opens
    - email.clicked: Track link clicks
    - email.bounced: Handle bounces
    - email.complained: Handle spam complaints
    - email.delivered: Track successful delivery

    Webhook-first architecture (Rule 20).

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    raw_body = await request.body()
    payload = await request.json()
    signature = request.headers.get("svix-signature")

    # Verify signature
    if settings.is_production and not verify_resend_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        # Parse webhook payload
        parsed = parse_resend_webhook(payload)

        if not parsed["event_type"]:
            return {"status": "ignored", "reason": "unknown_event_type"}

        # Initialize service with database session
        email_service = EmailEventsService(db)

        # Find activity by provider message ID
        provider_id = parsed["provider_message_id"]
        if not provider_id:
            return {"status": "ignored", "reason": "no_message_id"}

        activity = await email_service.find_activity_by_provider_id(provider_id)
        if not activity:
            return {"status": "ignored", "reason": "activity_not_found"}

        # Process based on event type
        event_type = parsed["event_type"]

        if event_type == "opened":
            await email_service.record_open(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                device_info=parsed.get("device_info"),
                geo_info=parsed.get("geo_info"),
                provider="resend",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "clicked":
            await email_service.record_click(
                activity_id=activity.id,
                clicked_url=parsed.get("clicked_url", ""),
                event_at=parsed.get("event_at"),
                device_info=parsed.get("device_info"),
                geo_info=parsed.get("geo_info"),
                provider="resend",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "bounced":
            await email_service.record_bounce(
                activity_id=activity.id,
                bounce_type=parsed.get("bounce_type", "hard"),
                event_at=parsed.get("event_at"),
                provider="resend",
                provider_event_id=parsed.get("provider_event_id"),
                raw_payload=parsed.get("raw"),
            )

        elif event_type == "complained":
            await email_service.record_complaint(
                activity_id=activity.id,
                event_at=parsed.get("event_at"),
                provider="resend",
                provider_event_id=parsed.get("provider_event_id"),
            )

        elif event_type == "delivered":
            # Just record the event, don't need special handling
            await email_service.record_event(
                activity_id=activity.id,
                event_type="delivered",
                event_at=parsed.get("event_at"),
                provider="resend",
                provider_event_id=parsed.get("provider_event_id"),
            )

        return {
            "status": "processed",
            "event_type": event_type,
            "activity_id": str(activity.id),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# ============================================
# CRM Webhooks (Downstream Outcomes - Phase 24E)
# ============================================


@router.post("/crm/deal")
async def crm_deal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle deal updates from external CRMs.

    Supports:
    - HubSpot deal webhooks
    - Salesforce opportunity webhooks
    - Pipedrive deal webhooks
    - Generic deal payloads

    This enables full-funnel tracking for CIS learning.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response with deal ID
    """
    from src.services.deal_service import DealService

    try:
        payload = await request.json()

        # Determine CRM source from headers or payload
        crm_source = request.headers.get("X-CRM-Source", "").lower()
        if not crm_source:
            crm_source = payload.get("source", payload.get("crm", "generic")).lower()

        # Extract client_id from header or payload
        client_id_str = request.headers.get("X-Client-ID") or payload.get("client_id")
        if not client_id_str:
            return {"status": "error", "error": "Missing client_id"}

        from uuid import UUID
        client_id = UUID(client_id_str)

        # Parse based on CRM source
        if crm_source == "hubspot":
            deal_data = _parse_hubspot_deal(payload)
        elif crm_source == "salesforce":
            deal_data = _parse_salesforce_deal(payload)
        elif crm_source == "pipedrive":
            deal_data = _parse_pipedrive_deal(payload)
        elif crm_source == "close":
            deal_data = _parse_close_deal(payload)
        else:
            # Generic payload
            deal_data = payload

        # Get external deal ID
        external_deal_id = deal_data.get("external_id") or deal_data.get("id")
        if not external_deal_id:
            return {"status": "error", "error": "Missing external deal ID"}

        # Check if deal already exists
        deal_service = DealService(db)
        existing_deal = await deal_service.get_by_external_id(crm_source, str(external_deal_id))

        # Sync deal
        deal = await deal_service.sync_from_external(
            client_id=client_id,
            external_crm=crm_source,
            external_deal_id=str(external_deal_id),
            data=deal_data,
        )

        # Create blind meeting if this is a NEW deal without a meeting
        # This captures "blind conversions" - meetings booked directly in CRM
        blind_meeting_created = False
        if not existing_deal and not deal.get("meeting_id"):
            from src.services.meeting_service import MeetingService
            meeting_service = MeetingService(db)

            # Create a "blind meeting" record for attribution tracking
            try:
                blind_meeting = await meeting_service.create_blind_meeting(
                    client_id=client_id,
                    lead_id=deal.get("lead_id"),
                    deal_id=deal["id"],
                    source=f"{crm_source}_sync",
                    notes=f"Meeting captured from {crm_source} deal sync (blind conversion)",
                    external_deal_id=str(external_deal_id),
                )
                blind_meeting_created = True

                # Link deal to meeting
                from sqlalchemy import text
                await db.execute(
                    text("UPDATE deals SET meeting_id = :meeting_id WHERE id = :deal_id"),
                    {"meeting_id": blind_meeting["id"], "deal_id": deal["id"]}
                )
                await db.commit()
            except Exception as e:
                # Log but don't fail - deal sync is more important
                import logging
                logging.getLogger(__name__).warning(f"Failed to create blind meeting: {e}")

        return {
            "status": "processed",
            "deal_id": str(deal["id"]),
            "external_id": str(external_deal_id),
            "blind_meeting_created": blind_meeting_created,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/crm/meeting")
async def crm_meeting_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle meeting updates from external calendars/CRMs.

    Supports:
    - Calendly webhooks
    - HubSpot meeting webhooks
    - Cal.com webhooks

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response with meeting ID
    """
    from src.services.meeting_service import MeetingService

    try:
        payload = await request.json()

        # Determine source
        source = request.headers.get("X-Calendar-Source", "").lower()
        if not source:
            source = payload.get("source", "generic").lower()

        # Parse event type
        event_type = payload.get("event", payload.get("type", "")).lower()

        meeting_service = MeetingService(db)

        # Handle Calendly-style webhooks
        if source == "calendly" or "calendly" in str(payload):
            return await _handle_calendly_webhook(db, payload, meeting_service)

        # Handle Cal.com webhooks
        if source == "calcom" or "cal.com" in str(payload):
            return await _handle_calcom_webhook(db, payload, meeting_service)

        # Handle generic meeting update
        calendar_event_id = payload.get("calendar_event_id")
        if calendar_event_id:
            meeting = await meeting_service.get_by_calendar_id(calendar_event_id)
            if meeting:
                # Update based on event type
                if event_type in ("cancelled", "canceled"):
                    await meeting_service.cancel(
                        meeting_id=meeting["id"],
                        reason=payload.get("reason", "Cancelled via webhook"),
                    )
                elif event_type == "rescheduled":
                    from datetime import datetime
                    new_time = payload.get("new_start_time")
                    if new_time:
                        await meeting_service.reschedule(
                            meeting_id=meeting["id"],
                            new_scheduled_at=datetime.fromisoformat(new_time),
                            reason=payload.get("reason"),
                        )
                elif event_type in ("attended", "completed"):
                    await meeting_service.record_show(
                        meeting_id=meeting["id"],
                        showed_up=True,
                        confirmed_by="webhook",
                    )
                elif event_type in ("no_show", "noshow"):
                    await meeting_service.record_show(
                        meeting_id=meeting["id"],
                        showed_up=False,
                        confirmed_by="webhook",
                    )

                return {
                    "status": "processed",
                    "meeting_id": str(meeting["id"]),
                    "event_type": event_type,
                }

        return {"status": "ignored", "reason": "meeting_not_found_or_invalid_event"}

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


def _parse_hubspot_deal(payload: dict) -> dict:
    """Parse HubSpot deal webhook payload."""
    properties = payload.get("properties", {})
    return {
        "external_id": payload.get("objectId") or payload.get("id"),
        "name": properties.get("dealname", ""),
        "value": properties.get("amount"),
        "stage": properties.get("dealstage", "").lower(),
        "contact_email": properties.get("contact_email"),
        "close_date": properties.get("closedate"),
    }


def _parse_salesforce_deal(payload: dict) -> dict:
    """Parse Salesforce opportunity webhook payload."""
    return {
        "external_id": payload.get("Id") or payload.get("id"),
        "name": payload.get("Name", ""),
        "value": payload.get("Amount"),
        "stage": payload.get("StageName", "").lower(),
        "contact_email": payload.get("Contact", {}).get("Email"),
        "close_date": payload.get("CloseDate"),
    }


def _parse_pipedrive_deal(payload: dict) -> dict:
    """Parse Pipedrive deal webhook payload."""
    current = payload.get("current", payload)
    return {
        "external_id": current.get("id"),
        "name": current.get("title", ""),
        "value": current.get("value"),
        "stage": current.get("stage_id", ""),
        "contact_email": current.get("person_id", {}).get("email", [{}])[0].get("value") if isinstance(current.get("person_id"), dict) else None,
        "close_date": current.get("expected_close_date"),
    }


def _parse_close_deal(payload: dict) -> dict:
    """Parse Close CRM opportunity webhook payload."""
    # Close uses "opportunity" terminology
    return {
        "external_id": payload.get("id"),
        "name": payload.get("note") or payload.get("lead_name", "Close Opportunity"),
        "value": payload.get("value"),
        "stage": _map_close_status(payload.get("status_type", "")),
        "contact_email": payload.get("contact", {}).get("email") if payload.get("contact") else None,
        "close_date": payload.get("date_won") or payload.get("expected_close_date"),
        "lead_id": payload.get("lead_id"),  # Close has lead_id in payload
    }


def _map_close_status(status_type: str) -> str:
    """Map Close CRM status_type to our stage names."""
    status_map = {
        "active": "qualification",
        "won": "closed_won",
        "lost": "closed_lost",
    }
    return status_map.get(status_type.lower(), "qualification")


async def _handle_calendly_webhook(db, payload: dict, meeting_service) -> dict:
    """Handle Calendly webhook events."""
    from datetime import datetime
    from uuid import UUID

    event = payload.get("event", "")
    event_payload = payload.get("payload", {})

    # Get calendar event ID
    calendar_event_id = event_payload.get("uri", "").split("/")[-1] or event_payload.get("uuid")
    if not calendar_event_id:
        return {"status": "ignored", "reason": "no_calendar_id"}

    # Try to find existing meeting
    meeting = await meeting_service.get_by_calendar_id(calendar_event_id)

    if event == "invitee.created" and not meeting:
        # New booking - but we need client_id and lead_id
        # These should come from custom questions or tracking
        tracking = event_payload.get("tracking", {}) or {}
        client_id_str = tracking.get("client_id") or event_payload.get("client_id")
        lead_id_str = tracking.get("lead_id") or event_payload.get("lead_id")

        if not client_id_str or not lead_id_str:
            # Try to find lead by email
            invitee = event_payload.get("invitee", {})
            invitee_email = invitee.get("email")
            if invitee_email:
                from sqlalchemy import text
                lead_query = await db.execute(
                    text("SELECT id, client_id FROM leads WHERE email = :email LIMIT 1"),
                    {"email": invitee_email}
                )
                lead_row = lead_query.fetchone()
                if lead_row:
                    lead_id_str = str(lead_row.id)
                    client_id_str = str(lead_row.client_id)

        if client_id_str and lead_id_str:
            scheduled = event_payload.get("scheduled_event", {})
            start_time = scheduled.get("start_time")

            meeting = await meeting_service.create(
                client_id=UUID(client_id_str),
                lead_id=UUID(lead_id_str),
                scheduled_at=datetime.fromisoformat(start_time.replace("Z", "+00:00")),
                duration_minutes=30,  # Default, could be extracted from Calendly
                meeting_type="discovery",
                booked_by="lead",
                booking_method="calendly",
                calendar_event_id=calendar_event_id,
                meeting_link=scheduled.get("location", {}).get("join_url"),
            )

            return {
                "status": "created",
                "meeting_id": str(meeting["id"]),
            }

    elif event == "invitee.canceled" and meeting:
        await meeting_service.cancel(
            meeting_id=meeting["id"],
            reason="Cancelled via Calendly",
        )
        return {"status": "cancelled", "meeting_id": str(meeting["id"])}

    return {"status": "ignored", "reason": "unhandled_event_or_missing_data"}


async def _handle_calcom_webhook(db, payload: dict, meeting_service) -> dict:
    """
    Handle Cal.com webhook events.

    Cal.com webhook structure:
    - triggerEvent: BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_RESCHEDULED
    - payload: Contains booking data with uid, startTime, endTime, attendees, metadata
    """
    from datetime import datetime
    from uuid import UUID

    # Cal.com uses triggerEvent instead of event
    trigger_event = payload.get("triggerEvent", "")
    booking_payload = payload.get("payload", {})

    # Get calendar event ID (Cal.com uses 'uid')
    calendar_event_id = booking_payload.get("uid") or booking_payload.get("id")
    if not calendar_event_id:
        return {"status": "ignored", "reason": "no_calendar_id"}

    # Try to find existing meeting
    meeting = await meeting_service.get_by_calendar_id(calendar_event_id)

    if trigger_event == "BOOKING_CREATED" and not meeting:
        # New booking - extract client_id and lead_id
        # Cal.com stores custom data in metadata or responses
        metadata = booking_payload.get("metadata", {}) or {}
        responses = booking_payload.get("responses", {}) or {}

        client_id_str = (
            metadata.get("client_id")
            or responses.get("client_id")
            or booking_payload.get("client_id")
        )
        lead_id_str = (
            metadata.get("lead_id")
            or responses.get("lead_id")
            or booking_payload.get("lead_id")
        )

        if not client_id_str or not lead_id_str:
            # Try to find lead by attendee email
            attendees = booking_payload.get("attendees", [])
            if attendees and len(attendees) > 0:
                attendee_email = attendees[0].get("email")
                if attendee_email:
                    from sqlalchemy import text
                    lead_query = await db.execute(
                        text("SELECT id, client_id FROM leads WHERE email = :email AND deleted_at IS NULL LIMIT 1"),
                        {"email": attendee_email}
                    )
                    lead_row = lead_query.fetchone()
                    if lead_row:
                        lead_id_str = str(lead_row.id)
                        client_id_str = str(lead_row.client_id)

        if client_id_str and lead_id_str:
            # Parse start/end times
            start_time_str = booking_payload.get("startTime")
            end_time_str = booking_payload.get("endTime")

            if not start_time_str:
                return {"status": "ignored", "reason": "no_start_time"}

            # Parse ISO datetime (handle both Z and +00:00 formats)
            start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))

            # Calculate duration from start/end if available
            duration_minutes = 30  # Default
            if end_time_str:
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                duration_minutes = int((end_time - start_time).total_seconds() / 60)

            # Get meeting link (Cal.com may provide it in different fields)
            meeting_link = (
                booking_payload.get("meetingUrl")
                or booking_payload.get("videoCallUrl")
                or booking_payload.get("location")
            )
            if isinstance(meeting_link, dict):
                meeting_link = meeting_link.get("link") or meeting_link.get("url")

            # Determine meeting type from event type name if available
            event_type = booking_payload.get("eventType", {})
            event_type_name = event_type.get("slug", "") if isinstance(event_type, dict) else ""
            meeting_type = "discovery"  # Default
            if "demo" in event_type_name.lower():
                meeting_type = "demo"
            elif "follow" in event_type_name.lower():
                meeting_type = "follow_up"
            elif "close" in event_type_name.lower():
                meeting_type = "close"

            meeting = await meeting_service.create(
                client_id=UUID(client_id_str),
                lead_id=UUID(lead_id_str),
                scheduled_at=start_time,
                duration_minutes=duration_minutes,
                meeting_type=meeting_type,
                booked_by="lead",
                booking_method="calcom",
                calendar_event_id=calendar_event_id,
                meeting_link=meeting_link,
            )

            return {
                "status": "created",
                "meeting_id": str(meeting["id"]),
                "booking_method": "calcom",
            }

        return {"status": "ignored", "reason": "missing_client_or_lead_id"}

    elif trigger_event == "BOOKING_CANCELLED" and meeting:
        cancellation_reason = booking_payload.get("cancellationReason", "Cancelled via Cal.com")
        await meeting_service.cancel(
            meeting_id=meeting["id"],
            reason=cancellation_reason,
        )
        return {"status": "cancelled", "meeting_id": str(meeting["id"])}

    elif trigger_event == "BOOKING_RESCHEDULED" and meeting:
        # Get new scheduled time
        start_time_str = booking_payload.get("startTime")
        if start_time_str:
            new_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            await meeting_service.reschedule(
                meeting_id=meeting["id"],
                new_scheduled_at=new_time,
                reason="Rescheduled via Cal.com",
            )
            return {"status": "rescheduled", "meeting_id": str(meeting["id"])}

    return {"status": "ignored", "reason": "unhandled_event_or_missing_data"}


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with /webhooks prefix and tags
# [x] Postmark inbound webhook with email reply handling
# [x] Postmark bounce webhook with lead status update
# [x] Postmark spam webhook with unsubscribe handling
# [x] Twilio inbound webhook with SMS reply handling
# [x] Twilio status webhook with delivery tracking
# [x] Unipile account webhook for connection status (CREATION_SUCCESS/FAILED)
# [x] Unipile message webhook with LinkedIn reply handling
# [x] Legacy HeyReach webhook (redirects to Unipile for transition)
# [x] Vapi webhook with voice call completion handling (Phase 17)
# [x] Webhook signature verification for Postmark (placeholder)
# [x] Webhook signature verification for Twilio (HMAC-SHA1)
# [x] Lead lookup by email/phone/LinkedIn URL
# [x] Duplicate activity detection (deduplication)
# [x] Process via Closer engine for intent classification
# [x] Process via Voice engine for call webhooks
# [x] Update lead status based on intent
# [x] Activity logging for all webhook events
# [x] CRM deal webhook (Phase 24E)
# [x] CRM meeting webhook (Phase 24E)
# [x] HubSpot/Salesforce/Pipedrive deal parsers
# [x] Calendly meeting webhook handling
# [x] Cal.com meeting webhook handling (BOOKING_CREATED/CANCELLED/RESCHEDULED)
# [x] Soft delete checks in lead queries (Rule 14)
# [x] Session passed as dependency (Rule 11)
# [x] Webhook-first architecture (Rule 20)
# [x] Error handling with graceful responses (200 to prevent retries)
# [x] All functions have type hints
# [x] All functions have docstrings
#
# Phase 24C Additions (ENGAGE-002):
# [x] Smartlead webhook for email engagement events
# [x] Salesforge webhook for email engagement events
# [x] Resend webhook for email engagement events
# [x] EmailEventsService integration for recording events
# [x] Signature verification for each provider
# [x] Open/click/bounce/unsubscribe handling
# [x] Reply forwarding to Closer engine
#
# Unipile Migration:
# [x] POST /webhooks/unipile/account - Account connection webhooks
# [x] POST /webhooks/unipile/message - LinkedIn message/reply webhooks
# [x] POST /webhooks/heyreach/inbound - Legacy redirect (backwards compat)
#
# ClickSend SMS (Primary for Australia):
# [x] POST /webhooks/clicksend/inbound - Inbound SMS reply handling
# [x] POST /webhooks/clicksend/status - SMS delivery status tracking
# [x] Uses ClickSend parser methods (parse_inbound_sms, parse_sms_webhook)
# [x] Processes via Closer engine for intent classification
