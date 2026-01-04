"""
FILE: src/api/routes/webhooks.py
PURPOSE: Inbound webhook routes for Postmark, Twilio, HeyReach, and Vapi
PHASE: 7 (API Routes), Phase 17 (Vapi Voice)
TASK: API-006, CRED-007
DEPENDENCIES:
  - src/engines/closer.py
  - src/engines/voice.py
  - src/integrations/postmark.py
  - src/integrations/twilio.py
  - src/integrations/heyreach.py
  - src/integrations/vapi.py
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
from src.integrations.supabase import get_db_session
from src.integrations.twilio import get_twilio_client
from src.integrations.heyreach import get_heyreach_client
from src.engines.voice import get_voice_engine
from src.models.base import ChannelType
from src.models.lead import Lead
from src.models.activity import Activity


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
# HeyReach Webhooks
# ============================================


@router.post("/heyreach/inbound")
async def heyreach_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle inbound LinkedIn replies from HeyReach.

    Webhook-first architecture (Rule 20). This is the primary method
    for processing LinkedIn replies.

    NOTE: HeyReach webhook format is vendor-specific. Adjust parsing
    based on actual webhook payload structure.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success response
    """
    payload = await request.json()

    # NOTE: HeyReach doesn't provide signature verification
    # Consider IP allowlisting in production

    try:
        # Parse webhook payload
        # NOTE: Adjust field names based on actual HeyReach webhook format
        event_type = payload.get("event_type")
        if event_type != "message_received":
            return {"status": "ignored", "reason": "not_a_reply"}

        linkedin_url = payload.get("profile_url")
        message = payload.get("message")
        message_id = payload.get("message_id")

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
                "sender_name": payload.get("sender_name"),
                "seat_id": payload.get("seat_id"),
                "conversation_id": payload.get("conversation_id"),
            },
        )

        if not result.success:
            raise WebhookError(
                url="/webhooks/heyreach/inbound",
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
        # Return 200 to prevent HeyReach retries
        return {
            "status": "error",
            "error": str(e),
        }


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
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with /webhooks prefix and tags
# [x] Postmark inbound webhook with email reply handling
# [x] Postmark bounce webhook with lead status update
# [x] Postmark spam webhook with unsubscribe handling
# [x] Twilio inbound webhook with SMS reply handling
# [x] Twilio status webhook with delivery tracking
# [x] HeyReach inbound webhook with LinkedIn reply handling
# [x] Vapi webhook with voice call completion handling (Phase 17)
# [x] Webhook signature verification for Postmark (placeholder)
# [x] Webhook signature verification for Twilio (HMAC-SHA1)
# [x] Lead lookup by email/phone/LinkedIn URL
# [x] Duplicate activity detection (deduplication)
# [x] Process via Closer engine for intent classification
# [x] Process via Voice engine for call webhooks
# [x] Update lead status based on intent
# [x] Activity logging for all webhook events
# [x] Soft delete checks in lead queries (Rule 14)
# [x] Session passed as dependency (Rule 11)
# [x] Webhook-first architecture (Rule 20)
# [x] Error handling with graceful responses (200 to prevent retries)
# [x] All functions have type hints
# [x] All functions have docstrings
