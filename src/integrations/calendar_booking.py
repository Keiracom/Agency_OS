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
"""

import os
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel, EmailStr

from src.integrations.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bookings", tags=["bookings"])

# Configuration
CAL_API_KEY = os.getenv("CAL_API_KEY")
CAL_WEBHOOK_SECRET = os.getenv("CAL_WEBHOOK_SECRET")
CALENDLY_API_KEY = os.getenv("CALENDLY_API_KEY")
CALENDLY_WEBHOOK_SECRET = os.getenv("CALENDLY_WEBHOOK_SECRET")


class BookingProvider(str, Enum):
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
    attendee_name: Optional[str]
    scheduled_time: datetime
    duration_minutes: int
    meeting_url: Optional[str]
    location: Optional[str]
    notes: Optional[str]
    raw_payload: Dict[str, Any]


# =============================================================================
# Webhook Signature Verification
# =============================================================================

def verify_cal_signature(payload: bytes, signature: str) -> bool:
    """Verify Cal.com webhook signature."""
    if not CAL_WEBHOOK_SECRET:
        logger.warning("CAL_WEBHOOK_SECRET not set, skipping verification")
        return True
    
    expected = hmac.new(
        CAL_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
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
        CALENDLY_WEBHOOK_SECRET.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, sig)


# =============================================================================
# Payload Parsers
# =============================================================================

def parse_cal_webhook(payload: Dict[str, Any]) -> BookingEvent:
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
        raw_payload=payload
    )


def parse_calendly_webhook(payload: Dict[str, Any]) -> BookingEvent:
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
        scheduled_time=datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else datetime.utcnow(),
        duration_minutes=duration,
        meeting_url=scheduled.get("location", {}).get("join_url"),
        location=scheduled.get("location", {}).get("location"),
        notes=invitee.get("text_reminder_number"),
        raw_payload=payload
    )


# =============================================================================
# Business Logic
# =============================================================================

async def handle_booking_created(event: BookingEvent) -> None:
    """Handle new demo booking - update pipeline stage."""
    logger.info(f"Demo booked: {event.attendee_email} at {event.scheduled_time}")
    
    try:
        supabase = get_supabase_client()
        
        # Find lead by email
        lead_result = supabase.table("leads").select("id").eq(
            "email", event.attendee_email
        ).single().execute()
        
        if lead_result.data:
            lead_id = lead_result.data["id"]
            
            # Update pipeline to demo_booked
            supabase.table("sales_pipeline").update({
                "stage": "demo_booked",
                "next_action": f"Demo call: {event.event_name}",
                "next_action_date": event.scheduled_time.isoformat(),
                "notes": f"Meeting URL: {event.meeting_url or 'TBD'}"
            }).eq("lead_id", lead_id).execute()
            
            logger.info(f"Updated pipeline for lead {lead_id} to demo_booked")
        else:
            # Create lead if doesn't exist
            new_lead = supabase.table("leads").insert({
                "email": event.attendee_email,
                "full_name": event.attendee_name,
                "source": f"demo_booking_{event.provider.value}",
                "status": "demo_booked"
            }).execute()
            
            if new_lead.data:
                # Create pipeline entry
                supabase.table("sales_pipeline").insert({
                    "lead_id": new_lead.data[0]["id"],
                    "stage": "demo_booked",
                    "next_action": f"Demo call: {event.event_name}",
                    "next_action_date": event.scheduled_time.isoformat()
                }).execute()
                
                logger.info(f"Created new lead and pipeline for {event.attendee_email}")
        
        # Store booking record
        supabase.table("demo_bookings").upsert({
            "booking_id": event.booking_id,
            "provider": event.provider.value,
            "attendee_email": event.attendee_email,
            "attendee_name": event.attendee_name,
            "scheduled_time": event.scheduled_time.isoformat(),
            "duration_minutes": event.duration_minutes,
            "meeting_url": event.meeting_url,
            "status": "scheduled",
            "raw_payload": event.raw_payload
        }, on_conflict="booking_id").execute()
        
    except Exception as e:
        logger.error(f"Error handling booking created: {e}")
        raise


async def handle_booking_cancelled(event: BookingEvent) -> None:
    """Handle cancelled booking - revert pipeline stage."""
    logger.info(f"Demo cancelled: {event.attendee_email}")
    
    try:
        supabase = get_supabase_client()
        
        # Update booking status
        supabase.table("demo_bookings").update({
            "status": "cancelled"
        }).eq("booking_id", event.booking_id).execute()
        
        # Find lead and revert pipeline
        lead_result = supabase.table("leads").select("id").eq(
            "email", event.attendee_email
        ).single().execute()
        
        if lead_result.data:
            supabase.table("sales_pipeline").update({
                "stage": "contacted",  # Revert to contacted
                "next_action": "Follow up on cancelled demo",
                "notes": f"Demo cancelled at {datetime.utcnow().isoformat()}"
            }).eq("lead_id", lead_result.data["id"]).execute()
            
    except Exception as e:
        logger.error(f"Error handling booking cancelled: {e}")


async def handle_booking_rescheduled(event: BookingEvent) -> None:
    """Handle rescheduled booking - update scheduled time."""
    logger.info(f"Demo rescheduled: {event.attendee_email} to {event.scheduled_time}")
    
    try:
        supabase = get_supabase_client()
        
        # Update booking
        supabase.table("demo_bookings").update({
            "scheduled_time": event.scheduled_time.isoformat(),
            "status": "rescheduled"
        }).eq("booking_id", event.booking_id).execute()
        
        # Update pipeline next_action_date
        lead_result = supabase.table("leads").select("id").eq(
            "email", event.attendee_email
        ).single().execute()
        
        if lead_result.data:
            supabase.table("sales_pipeline").update({
                "next_action_date": event.scheduled_time.isoformat(),
                "notes": f"Rescheduled to {event.scheduled_time}"
            }).eq("lead_id", lead_result.data["id"]).execute()
            
    except Exception as e:
        logger.error(f"Error handling booking rescheduled: {e}")


# =============================================================================
# API Routes
# =============================================================================

@router.post("/webhook/cal")
async def cal_webhook(
    request: Request,
    x_cal_signature: str = Header(None, alias="X-Cal-Signature-256")
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
    calendly_webhook_signature: str = Header(None, alias="Calendly-Webhook-Signature")
):
    """Calendly webhook endpoint."""
    payload = await request.body()
    
    if calendly_webhook_signature and not verify_calendly_signature(payload, calendly_webhook_signature):
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
