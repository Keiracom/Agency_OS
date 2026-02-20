"""
Calendar Booking Integration
Agency OS - Cal.com / Calendly webhook handling for demo bookings

Supports both Cal.com and Calendly with a unified interface.
Recommended: Cal.com (self-hostable, open source, better API)

Environment Variables:
- CAL_API_KEY: Cal.com API key
- CAL_WEBHOOK_SECRET: Cal.com webhook signing secret
- CALENDLY_API_KEY: Calendly API key (alternative)
- CALENDLY_WEBHOOK_SECRET: Calendly webhook signing secret
- CALENDLY_ORG_URI: Calendly organization URI for booking links
"""

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.supabase import get_supabase_client

if TYPE_CHECKING:
    from src.models.lead import Lead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bookings", tags=["bookings"])

# Configuration
CAL_API_KEY = os.getenv("CAL_API_KEY")
CAL_WEBHOOK_SECRET = os.getenv("CAL_WEBHOOK_SECRET")
CALENDLY_API_KEY = os.getenv("CALENDLY_API_KEY")
CALENDLY_WEBHOOK_SECRET = os.getenv("CALENDLY_WEBHOOK_SECRET")
CALENDLY_ORG_URI = os.getenv("CALENDLY_ORG_URI", "")
CALENDLY_EVENT_TYPE = os.getenv("CALENDLY_EVENT_TYPE", "demo")


# =============================================================================
# Booking Link Generation (Directive 048)
# =============================================================================


async def generate_booking_link(
    lead_email: str,
    lead_name: str,
    company_name: str | None = None,
    client_id: UUID | None = None,
) -> str:
    """
    Generate a personalized Calendly/Cal.com booking link.

    Creates a unique booking link with lead information pre-filled.

    Args:
        lead_email: Lead's email address
        lead_name: Lead's full name
        company_name: Lead's company name
        client_id: Agency client UUID for routing

    Returns:
        Personalized booking URL
    """
    # Try Calendly first (primary), fall back to Cal.com
    if CALENDLY_API_KEY and CALENDLY_ORG_URI:
        return await _generate_calendly_link(lead_email, lead_name, company_name, client_id)
    elif CAL_API_KEY:
        return await _generate_cal_link(lead_email, lead_name, company_name, client_id)
    else:
        # Fallback to static link with UTM parameters
        logger.warning("No calendar API configured, using fallback link")
        return _generate_fallback_link(lead_email, lead_name, company_name)


async def _generate_calendly_link(
    lead_email: str,
    lead_name: str,
    company_name: str | None,
    client_id: UUID | None,
) -> str:
    """Generate a Calendly booking link with pre-filled info."""
    from urllib.parse import urlencode

    # Build base URL
    base_url = f"https://calendly.com/{CALENDLY_ORG_URI}/{CALENDLY_EVENT_TYPE}"

    # Add pre-fill parameters
    params = {
        "email": lead_email,
        "name": lead_name,
    }

    if company_name:
        params["a1"] = company_name  # Custom question field for company

    if client_id:
        params["utm_source"] = str(client_id)  # Track which agency client

    return f"{base_url}?{urlencode(params)}"


async def _generate_cal_link(
    lead_email: str,
    lead_name: str,
    company_name: str | None,
    client_id: UUID | None,
) -> str:
    """Generate a Cal.com booking link with pre-filled info."""
    from urllib.parse import urlencode

    # Cal.com uses different parameter format
    base_url = os.getenv("CAL_BOOKING_URL", "https://cal.com/demo")

    params = {
        "email": lead_email,
        "name": lead_name,
    }

    if company_name:
        params["company"] = company_name

    if client_id:
        params["metadata[client_id]"] = str(client_id)

    return f"{base_url}?{urlencode(params)}"


def _generate_fallback_link(
    lead_email: str,
    lead_name: str,
    company_name: str | None,
) -> str:
    """Generate a fallback static booking link."""
    from urllib.parse import urlencode

    base_url = os.getenv("FALLBACK_BOOKING_URL", "https://calendly.com/agency-demo")

    params = {
        "email": lead_email,
        "name": lead_name,
    }

    if company_name:
        params["a1"] = company_name

    return f"{base_url}?{urlencode(params)}"


async def send_booking_reply(
    db: AsyncSession,
    lead: "Lead",
    booking_link: str,
) -> bool:
    """
    Send automated reply with booking link to prospect.

    Uses the same channel the lead replied on to send the booking link.

    Args:
        db: Database session
        lead: Lead who requested the meeting
        booking_link: Personalized booking URL

    Returns:
        True if reply sent successfully
    """
    try:
        # Generate personalized message
        first_name = lead.first_name or "there"
        message = (
            f"Hi {first_name},\n\n"
            f"Thanks for your interest! I'd love to chat.\n\n"
            f"Here's my calendar link to book a time that works for you:\n"
            f"{booking_link}\n\n"
            f"Looking forward to connecting!\n"
        )

        # Determine reply channel from last activity
        last_channel = await _get_lead_last_channel(db, lead.id)

        if last_channel == "email":
            # Send via email engine
            from src.engines.email import get_email_engine

            email_engine = get_email_engine()

            result = await email_engine.send_email(
                db=db,
                lead_id=lead.id,
                subject="Re: Let's Schedule a Call",
                body=message,
                from_domain=lead.assigned_email_resource,
            )
            return result.success

        elif last_channel == "linkedin":
            # Send via LinkedIn engine
            from src.engines.linkedin import get_linkedin_engine

            linkedin_engine = get_linkedin_engine()

            result = await linkedin_engine.send_message(
                db=db,
                lead_id=lead.id,
                message=message,
                account_id=lead.assigned_linkedin_seat,
            )
            return result.success

        elif last_channel == "sms":
            # Send via SMS engine (shorter message)
            from src.engines.sms import get_sms_engine

            sms_engine = get_sms_engine()

            short_message = f"Hi {first_name}! Here's my calendar: {booking_link}"
            result = await sms_engine.send_sms(
                db=db,
                lead_id=lead.id,
                message=short_message,
                from_number=lead.assigned_phone_resource,
            )
            return result.success

        else:
            logger.warning(f"Unknown channel for lead {lead.id}, cannot send booking reply")
            return False

    except Exception as e:
        logger.error(f"Failed to send booking reply to lead {lead.id}: {e}")
        return False


async def _get_lead_last_channel(db: AsyncSession, lead_id: UUID) -> str | None:
    """Get the last channel a lead used to communicate."""
    try:
        result = await db.execute(
            text("""
                SELECT channel FROM activities
                WHERE lead_id = :lead_id
                AND action = 'replied'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"lead_id": str(lead_id)},
        )
        row = result.fetchone()
        return row.channel if row else "email"  # Default to email
    except Exception:
        return "email"


# =============================================================================
# Calendly Webhook Handler (Directive 048)
# =============================================================================


async def handle_calendly_booking_confirmed(
    db: AsyncSession,
    event: "BookingEvent",
) -> None:
    """
    Handle Calendly booking confirmation webhook.

    Updates lead status to CONVERTED and triggers agency owner notification.

    Args:
        db: Database session
        event: Parsed booking event
    """
    try:
        # Find lead by email
        from sqlalchemy import text

        result = await db.execute(
            text("""
                SELECT id, client_id, campaign_id, full_name, company
                FROM leads
                WHERE email = :email
                AND deleted_at IS NULL
            """),
            {"email": event.attendee_email.lower()},
        )
        row = result.fetchone()

        if not row:
            logger.warning(f"No lead found for booking email: {event.attendee_email}")
            return

        lead_id = row.id
        client_id = row.client_id

        # Update lead status to CONVERTED
        await db.execute(
            text("""
                UPDATE leads
                SET status = 'converted',
                    metadata = COALESCE(metadata, '{}'::jsonb) || :booking_info,
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {
                "lead_id": str(lead_id),
                "booking_info": {
                    "booking_confirmed_at": datetime.utcnow().isoformat(),
                    "booking_id": event.booking_id,
                    "scheduled_time": event.scheduled_time.isoformat(),
                    "meeting_url": event.meeting_url,
                },
            },
        )

        # Trigger agency owner notification
        await db.execute(
            text("""
                SELECT create_admin_notification(
                    'booking_confirmed',
                    :client_id,
                    :title,
                    :message,
                    'medium',
                    :lead_id,
                    NULL,
                    :metadata
                )
            """),
            {
                "client_id": str(client_id),
                "title": "New Demo Booked! 🎉",
                "message": f"{row.full_name} from {row.company} has booked a demo "
                f"for {event.scheduled_time.strftime('%B %d at %I:%M %p')}.",
                "lead_id": str(lead_id),
                "metadata": {
                    "booking_id": event.booking_id,
                    "scheduled_time": event.scheduled_time.isoformat(),
                    "lead_email": event.attendee_email,
                },
            },
        )

        await db.commit()
        logger.info(f"Lead {lead_id} marked as CONVERTED after booking confirmation")

    except Exception as e:
        logger.error(f"Error handling booking confirmation: {e}")
        raise


class BookingProvider(StrEnum):
    CAL = "cal.com"
    CALENDLY = "calendly"


@dataclass
class BookingEvent:
    """Unified booking event from either provider."""

    provider: BookingProvider
    event_type: Literal["created", "cancelled", "rescheduled"]
    booking_id: str
    event_name: str
    attendee_email: str
    attendee_name: str | None
    scheduled_time: datetime
    duration_minutes: int
    meeting_url: str | None
    location: str | None
    notes: str | None
    raw_payload: dict[str, Any]


# =============================================================================
# Webhook Signature Verification
# =============================================================================


def verify_cal_signature(payload: bytes, signature: str) -> bool:
    """Verify Cal.com webhook signature."""
    if not CAL_WEBHOOK_SECRET:
        logger.warning("CAL_WEBHOOK_SECRET not set, skipping verification")
        return True

    expected = hmac.new(CAL_WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, signature)


def verify_calendly_signature(payload: bytes, signature: str) -> bool:
    """Verify Calendly webhook signature."""
    if not CALENDLY_WEBHOOK_SECRET:
        logger.warning("CALENDLY_WEBHOOK_SECRET not set, skipping verification")
        return True

    # Calendly uses: t=timestamp,v1=signature format
    parts = dict(p.split("=") for p in signature.split(",") if "=" in p)
    sig = parts.get("v1", "")
    timestamp = parts.get("t", "")

    signed_payload = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(
        CALENDLY_WEBHOOK_SECRET.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, sig)


# =============================================================================
# Payload Parsers
# =============================================================================


def parse_cal_webhook(payload: dict[str, Any]) -> BookingEvent:
    """Parse Cal.com webhook payload into unified BookingEvent."""
    trigger = payload.get("triggerEvent", "")
    data = payload.get("payload", {})

    # Map Cal.com triggers to our event types
    event_type_map = {
        "BOOKING_CREATED": "created",
        "BOOKING_CANCELLED": "cancelled",
        "BOOKING_RESCHEDULED": "rescheduled",
    }

    attendees = data.get("attendees", [{}])
    attendee = attendees[0] if attendees else {}

    return BookingEvent(
        provider=BookingProvider.CAL,
        event_type=event_type_map.get(trigger, "created"),
        booking_id=str(data.get("id", "")),
        event_name=data.get("title", "Demo Call"),
        attendee_email=attendee.get("email", ""),
        attendee_name=attendee.get("name"),
        scheduled_time=datetime.fromisoformat(data.get("startTime", "").replace("Z", "+00:00")),
        duration_minutes=data.get("length", 30),
        meeting_url=data.get("metadata", {}).get("videoCallUrl"),
        location=data.get("location"),
        notes=attendee.get("notes"),
        raw_payload=payload,
    )


def parse_calendly_webhook(payload: dict[str, Any]) -> BookingEvent:
    """Parse Calendly webhook payload into unified BookingEvent."""
    event = payload.get("event", "")
    data = payload.get("payload", {})

    # Map Calendly events
    event_type_map = {
        "invitee.created": "created",
        "invitee.canceled": "cancelled",
    }

    invitee = data.get("invitee", {})
    scheduled = data.get("scheduled_event", {})

    start_time = scheduled.get("start_time", "")
    end_time = scheduled.get("end_time", "")

    # Calculate duration
    duration = 30
    if start_time and end_time:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = int((end - start).total_seconds() / 60)

    return BookingEvent(
        provider=BookingProvider.CALENDLY,
        event_type=event_type_map.get(event, "created"),
        booking_id=data.get("uri", "").split("/")[-1],
        event_name=scheduled.get("name", "Demo Call"),
        attendee_email=invitee.get("email", ""),
        attendee_name=invitee.get("name"),
        scheduled_time=datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if start_time
        else datetime.utcnow(),
        duration_minutes=duration,
        meeting_url=scheduled.get("location", {}).get("join_url"),
        location=scheduled.get("location", {}).get("location"),
        notes=invitee.get("text_reminder_number"),
        raw_payload=payload,
    )


# =============================================================================
# Business Logic
# =============================================================================


async def handle_booking_created(event: BookingEvent) -> None:
    """Handle new demo booking - update pipeline stage and convert lead."""
    logger.info(f"Demo booked: {event.attendee_email} at {event.scheduled_time}")

    try:
        supabase = get_supabase_client()

        # Find lead by email
        lead_result = (
            supabase.table("leads")
            .select("id, client_id")
            .eq("email", event.attendee_email)
            .single()
            .execute()
        )

        if lead_result.data:
            lead_id = lead_result.data["id"]
            client_id = lead_result.data.get("client_id")

            # Directive 048: Update lead status to CONVERTED
            supabase.table("leads").update(
                {
                    "status": "converted",
                    "metadata": {
                        "booking_confirmed_at": datetime.utcnow().isoformat(),
                        "booking_id": event.booking_id,
                        "scheduled_time": event.scheduled_time.isoformat(),
                        "meeting_url": event.meeting_url,
                    },
                }
            ).eq("id", lead_id).execute()

            # Update pipeline to demo_booked
            supabase.table("sales_pipeline").update(
                {
                    "stage": "demo_booked",
                    "next_action": f"Demo call: {event.event_name}",
                    "next_action_date": event.scheduled_time.isoformat(),
                    "notes": f"Meeting URL: {event.meeting_url or 'TBD'}",
                }
            ).eq("lead_id", lead_id).execute()

            # Directive 048: Trigger agency owner notification
            if client_id:
                supabase.rpc(
                    "create_admin_notification",
                    {
                        "p_notification_type": "booking_confirmed",
                        "p_client_id": str(client_id),
                        "p_title": "New Demo Booked! 🎉",
                        "p_message": f"{event.attendee_name} has booked a demo for {event.scheduled_time.strftime('%B %d at %I:%M %p')}.",
                        "p_severity": "medium",
                        "p_lead_id": str(lead_id),
                        "p_metadata": {
                            "booking_id": event.booking_id,
                            "scheduled_time": event.scheduled_time.isoformat(),
                        },
                    },
                ).execute()

            logger.info(f"Lead {lead_id} converted and pipeline updated")
        else:
            # Create lead if doesn't exist
            new_lead = (
                supabase.table("leads")
                .insert(
                    {
                        "email": event.attendee_email,
                        "full_name": event.attendee_name,
                        "source": f"demo_booking_{event.provider.value}",
                        "status": "converted",  # Direct to converted since they booked
                    }
                )
                .execute()
            )

            if new_lead.data:
                # Create pipeline entry
                supabase.table("sales_pipeline").insert(
                    {
                        "lead_id": new_lead.data[0]["id"],
                        "stage": "demo_booked",
                        "next_action": f"Demo call: {event.event_name}",
                        "next_action_date": event.scheduled_time.isoformat(),
                    }
                ).execute()

                logger.info(f"Created new lead and pipeline for {event.attendee_email}")

        # Store booking record
        supabase.table("demo_bookings").upsert(
            {
                "booking_id": event.booking_id,
                "provider": event.provider.value,
                "attendee_email": event.attendee_email,
                "attendee_name": event.attendee_name,
                "scheduled_time": event.scheduled_time.isoformat(),
                "duration_minutes": event.duration_minutes,
                "meeting_url": event.meeting_url,
                "status": "scheduled",
                "raw_payload": event.raw_payload,
            },
            on_conflict="booking_id",
        ).execute()

    except Exception as e:
        logger.error(f"Error handling booking created: {e}")
        raise


async def handle_booking_cancelled(event: BookingEvent) -> None:
    """Handle cancelled booking - revert pipeline stage."""
    logger.info(f"Demo cancelled: {event.attendee_email}")

    try:
        supabase = get_supabase_client()

        # Update booking status
        supabase.table("demo_bookings").update({"status": "cancelled"}).eq(
            "booking_id", event.booking_id
        ).execute()

        # Find lead and revert pipeline
        lead_result = (
            supabase.table("leads")
            .select("id")
            .eq("email", event.attendee_email)
            .single()
            .execute()
        )

        if lead_result.data:
            supabase.table("sales_pipeline").update(
                {
                    "stage": "contacted",  # Revert to contacted
                    "next_action": "Follow up on cancelled demo",
                    "notes": f"Demo cancelled at {datetime.utcnow().isoformat()}",
                }
            ).eq("lead_id", lead_result.data["id"]).execute()

    except Exception as e:
        logger.error(f"Error handling booking cancelled: {e}")


async def handle_booking_rescheduled(event: BookingEvent) -> None:
    """Handle rescheduled booking - update scheduled time."""
    logger.info(f"Demo rescheduled: {event.attendee_email} to {event.scheduled_time}")

    try:
        supabase = get_supabase_client()

        # Update booking
        supabase.table("demo_bookings").update(
            {"scheduled_time": event.scheduled_time.isoformat(), "status": "rescheduled"}
        ).eq("booking_id", event.booking_id).execute()

        # Update pipeline next_action_date
        lead_result = (
            supabase.table("leads")
            .select("id")
            .eq("email", event.attendee_email)
            .single()
            .execute()
        )

        if lead_result.data:
            supabase.table("sales_pipeline").update(
                {
                    "next_action_date": event.scheduled_time.isoformat(),
                    "notes": f"Rescheduled to {event.scheduled_time}",
                }
            ).eq("lead_id", lead_result.data["id"]).execute()

    except Exception as e:
        logger.error(f"Error handling booking rescheduled: {e}")


# =============================================================================
# API Routes
# =============================================================================


@router.post("/webhook/cal")
async def cal_webhook(
    request: Request, x_cal_signature: str = Header(None, alias="X-Cal-Signature-256")
):
    """Cal.com webhook endpoint."""
    payload = await request.body()

    if x_cal_signature and not verify_cal_signature(payload, x_cal_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event = parse_cal_webhook(data)

    handlers = {
        "created": handle_booking_created,
        "cancelled": handle_booking_cancelled,
        "rescheduled": handle_booking_rescheduled,
    }

    handler = handlers.get(event.event_type)
    if handler:
        await handler(event)

    return {"status": "ok"}


@router.post("/webhook/calendly")
async def calendly_webhook(
    request: Request,
    calendly_webhook_signature: str = Header(None, alias="Calendly-Webhook-Signature"),
):
    """Calendly webhook endpoint."""
    payload = await request.body()

    if calendly_webhook_signature and not verify_calendly_signature(
        payload, calendly_webhook_signature
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    event = parse_calendly_webhook(data)

    handlers = {
        "created": handle_booking_created,
        "cancelled": handle_booking_cancelled,
    }

    handler = handlers.get(event.event_type)
    if handler:
        await handler(event)

    return {"status": "ok"}


# =============================================================================
# Integration Spec Documentation
# =============================================================================
"""
# Demo Booking Integration Specification

## Overview
Unified calendar booking integration supporting Cal.com (recommended) and Calendly.

## Recommended Provider: Cal.com
- Open source, self-hostable
- Better API and webhook support
- Lower cost for enterprise features
- Native Stripe integration for paid bookings

## Setup Steps

### 1. Cal.com Setup
1. Create account at cal.com or self-host
2. Create event type for "Agency OS Demo" (30 min)
3. Configure video conferencing (Zoom/Google Meet)
4. Generate API key: Settings → Developer → API Keys
5. Create webhook: Settings → Developer → Webhooks
   - URL: https://api.keiracom.com/bookings/webhook/cal
   - Events: BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_RESCHEDULED
   - Copy webhook secret

### 2. Environment Variables
```
CAL_API_KEY=cal_live_xxx
CAL_WEBHOOK_SECRET=whsec_xxx
```

### 3. Database Table
Create demo_bookings table:
```sql
CREATE TABLE demo_bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    booking_id TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL,
    attendee_email TEXT NOT NULL,
    attendee_name TEXT,
    scheduled_time TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    meeting_url TEXT,
    status TEXT DEFAULT 'scheduled',
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Pipeline Integration
- New booking → stage: demo_booked
- Cancelled → stage: contacted (with follow-up task)
- After demo → manually update to: demo_done

## Webhook Flow
1. Prospect books demo via Cal.com embed/link
2. Cal.com sends webhook to our endpoint
3. We parse event and update:
   - Create/update lead if needed
   - Update sales_pipeline stage
   - Store booking record
4. Notification sent (future: Slack/email)

## Embedding on Landing Page
```html
<!-- Cal.com embed -->
<script>
  (function (C, A, L) {
    let p = function (a, ar) { a.q.push(ar); };
    let d = C.document;
    C.Cal = C.Cal || function () {
      let cal = C.Cal;
      let ar = arguments;
      if (!cal.loaded) {
        cal.ns = {}; cal.q = cal.q || [];
        d.head.appendChild(d.createElement("script")).src = A;
        cal.loaded = true;
      }
      if (ar[0] === L) {
        const api = function () { p(api, arguments); };
        const namespace = ar[1];
        api.q = api.q || [];
        typeof namespace === "string" ? (cal.ns[namespace] = api) && p(api, ar) : p(cal, ar);
        return;
      }
      p(cal, ar);
    };
  })(window, "https://app.cal.com/embed/embed.js", "init");
  Cal("init", {origin:"https://app.cal.com"});
  Cal("ui", {"theme":"light","styles":{"branding":{"brandColor":"#5046e5"}}});
</script>

<button data-cal-link="keiracom/demo">Book a Demo</button>
```

## API Endpoints
- POST /bookings/webhook/cal - Cal.com webhooks
- POST /bookings/webhook/calendly - Calendly webhooks (backup)
"""
