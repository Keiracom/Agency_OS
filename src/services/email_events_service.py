"""
Contract: src/services/email_events_service.py
Purpose: Email engagement events ingestion and processing
Layer: 3 - services
Imports: models
Consumers: webhooks, orchestration, CIS detectors

FILE: src/services/email_events_service.py
PURPOSE: Email engagement events ingestion and processing
PHASE: 24C (Email Engagement Tracking)
TASK: ENGAGE-003
DEPENDENCIES:
  - src/models/database.py
LAYER: 3 (services)
CONSUMERS: webhooks, orchestration, CIS detectors

This service ingests email engagement events (opens, clicks, bounces)
from Salesforge (primary email provider) and fallback providers.

Provider hierarchy:
1. Salesforge (primary - uses Warmforge-warmed mailboxes)
2. Smartlead (alternative)
3. Postmark (transactional)
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity


class EmailEventsService:
    """
    Service for processing email engagement events.

    Handles:
    - Open tracking (first open, repeat opens)
    - Click tracking (URL clicked, click counts)
    - Bounce processing (hard/soft bounces)
    - Unsubscribe/complaint handling
    - Activity summary updates via triggers
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Email Events service.

        Args:
            session: Async database session
        """
        self.session = session

    async def record_event(
        self,
        activity_id: UUID,
        event_type: str,
        event_at: datetime | None = None,
        clicked_url: str | None = None,
        device_type: str | None = None,
        email_client: str | None = None,
        os_type: str | None = None,
        open_ip: str | None = None,
        open_city: str | None = None,
        open_region: str | None = None,
        open_country: str | None = None,
        provider: str | None = None,
        provider_event_id: str | None = None,
        raw_payload: dict | None = None,
    ) -> dict[str, Any]:
        """
        Record an email engagement event.

        The database trigger will automatically update the activity's
        summary fields (email_opened, email_open_count, etc.).

        Args:
            activity_id: Activity UUID
            event_type: Event type (sent, delivered, opened, clicked, bounced, complained, unsubscribed)
            event_at: When the event occurred
            clicked_url: URL clicked (for click events)
            device_type: Device type (desktop, mobile, tablet)
            email_client: Email client detected
            os_type: Operating system
            open_ip: IP address of opener
            open_city: City from IP geolocation
            open_region: Region/state from IP
            open_country: Country from IP
            provider: Email provider (smartlead, salesforge, postmark, resend)
            provider_event_id: Provider's event ID for deduplication
            raw_payload: Full webhook payload for debugging

        Returns:
            Created event record
        """
        # Check for duplicate event
        if provider_event_id:
            existing = await self._check_duplicate(provider, provider_event_id)
            if existing:
                return {"status": "duplicate", "event_id": existing}

        # Get activity to get lead_id and client_id
        activity = await self._get_activity(activity_id)
        if not activity:
            return {"status": "error", "error": "activity_not_found"}

        # Insert email event
        query = text("""
            INSERT INTO email_events (
                activity_id, lead_id, client_id,
                event_type, event_at,
                clicked_url, open_count, click_count,
                first_opened_at, first_clicked_at,
                device_type, email_client, os_type,
                open_ip, open_city, open_region, open_country,
                provider, provider_event_id, raw_payload
            ) VALUES (
                :activity_id, :lead_id, :client_id,
                :event_type, :event_at,
                :clicked_url,
                CASE WHEN :event_type = 'opened' THEN 1 ELSE 0 END,
                CASE WHEN :event_type = 'clicked' THEN 1 ELSE 0 END,
                CASE WHEN :event_type = 'opened' THEN :event_at ELSE NULL END,
                CASE WHEN :event_type = 'clicked' THEN :event_at ELSE NULL END,
                :device_type, :email_client, :os_type,
                :open_ip, :open_city, :open_region, :open_country,
                :provider, :provider_event_id, :raw_payload::jsonb
            )
            RETURNING id
        """)

        result = await self.session.execute(query, {
            "activity_id": activity_id,
            "lead_id": activity.lead_id,
            "client_id": activity.client_id,
            "event_type": event_type,
            "event_at": event_at or datetime.utcnow(),
            "clicked_url": clicked_url,
            "device_type": device_type,
            "email_client": email_client,
            "os_type": os_type,
            "open_ip": open_ip,
            "open_city": open_city,
            "open_region": open_region,
            "open_country": open_country,
            "provider": provider,
            "provider_event_id": provider_event_id,
            "raw_payload": str(raw_payload) if raw_payload else None,
        })

        row = result.fetchone()
        await self.session.commit()

        event_id = str(row.id) if row else "unknown"
        return {
            "status": "created",
            "event_id": event_id,
            "event_type": event_type,
            "activity_id": str(activity_id),
        }

    async def record_open(
        self,
        activity_id: UUID,
        event_at: datetime | None = None,
        device_info: dict | None = None,
        geo_info: dict | None = None,
        provider: str | None = None,
        provider_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record an email open event.

        Args:
            activity_id: Activity UUID
            event_at: When the email was opened
            device_info: Device detection info (device_type, email_client, os_type)
            geo_info: Geolocation info (ip, city, region, country)
            provider: Email provider
            provider_event_id: Provider's event ID

        Returns:
            Event creation result
        """
        device = device_info or {}
        geo = geo_info or {}

        return await self.record_event(
            activity_id=activity_id,
            event_type="opened",
            event_at=event_at,
            device_type=device.get("device_type"),
            email_client=device.get("email_client"),
            os_type=device.get("os_type"),
            open_ip=geo.get("ip"),
            open_city=geo.get("city"),
            open_region=geo.get("region"),
            open_country=geo.get("country"),
            provider=provider,
            provider_event_id=provider_event_id,
        )

    async def record_click(
        self,
        activity_id: UUID,
        clicked_url: str,
        event_at: datetime | None = None,
        device_info: dict | None = None,
        geo_info: dict | None = None,
        provider: str | None = None,
        provider_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record an email click event.

        Args:
            activity_id: Activity UUID
            clicked_url: The URL that was clicked
            event_at: When the click occurred
            device_info: Device detection info
            geo_info: Geolocation info
            provider: Email provider
            provider_event_id: Provider's event ID

        Returns:
            Event creation result
        """
        device = device_info or {}
        geo = geo_info or {}

        return await self.record_event(
            activity_id=activity_id,
            event_type="clicked",
            event_at=event_at,
            clicked_url=clicked_url,
            device_type=device.get("device_type"),
            email_client=device.get("email_client"),
            os_type=device.get("os_type"),
            open_ip=geo.get("ip"),
            open_city=geo.get("city"),
            open_region=geo.get("region"),
            open_country=geo.get("country"),
            provider=provider,
            provider_event_id=provider_event_id,
        )

    async def record_bounce(
        self,
        activity_id: UUID,
        bounce_type: str = "hard",
        event_at: datetime | None = None,
        provider: str | None = None,
        provider_event_id: str | None = None,
        raw_payload: dict | None = None,
    ) -> dict[str, Any]:
        """
        Record an email bounce event.

        Args:
            activity_id: Activity UUID
            bounce_type: Type of bounce (hard, soft)
            event_at: When the bounce occurred
            provider: Email provider
            provider_event_id: Provider's event ID
            raw_payload: Full bounce payload

        Returns:
            Event creation result
        """
        return await self.record_event(
            activity_id=activity_id,
            event_type="bounced",
            event_at=event_at,
            provider=provider,
            provider_event_id=provider_event_id,
            raw_payload=raw_payload,
        )

    async def record_unsubscribe(
        self,
        activity_id: UUID,
        event_at: datetime | None = None,
        provider: str | None = None,
        provider_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record an unsubscribe event.

        Args:
            activity_id: Activity UUID
            event_at: When the unsubscribe occurred
            provider: Email provider
            provider_event_id: Provider's event ID

        Returns:
            Event creation result
        """
        return await self.record_event(
            activity_id=activity_id,
            event_type="unsubscribed",
            event_at=event_at,
            provider=provider,
            provider_event_id=provider_event_id,
        )

    async def record_complaint(
        self,
        activity_id: UUID,
        event_at: datetime | None = None,
        provider: str | None = None,
        provider_event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record a spam complaint event.

        Args:
            activity_id: Activity UUID
            event_at: When the complaint occurred
            provider: Email provider
            provider_event_id: Provider's event ID

        Returns:
            Event creation result
        """
        return await self.record_event(
            activity_id=activity_id,
            event_type="complained",
            event_at=event_at,
            provider=provider,
            provider_event_id=provider_event_id,
        )

    async def get_activity_events(
        self,
        activity_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        Get all events for an activity.

        Args:
            activity_id: Activity UUID

        Returns:
            List of event records
        """
        query = text("""
            SELECT * FROM email_events
            WHERE activity_id = :activity_id
            ORDER BY event_at ASC
        """)

        result = await self.session.execute(query, {"activity_id": activity_id})
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_engagement_summary(
        self,
        activity_id: UUID,
    ) -> dict[str, Any]:
        """
        Get engagement summary for an activity.

        Args:
            activity_id: Activity UUID

        Returns:
            Engagement summary
        """
        activity = await self._get_activity(activity_id)
        if not activity:
            return {}

        return {
            "email_opened": activity.email_opened,
            "email_opened_at": activity.email_opened_at,
            "email_open_count": activity.email_open_count,
            "email_clicked": activity.email_clicked,
            "email_clicked_at": activity.email_clicked_at,
            "email_click_count": activity.email_click_count,
            "time_to_open_minutes": activity.time_to_open_minutes,
            "time_to_click_minutes": activity.time_to_click_minutes,
        }

    async def find_activity_by_provider_id(
        self,
        provider_message_id: str,
    ) -> Activity | None:
        """
        Find activity by provider message ID.

        Args:
            provider_message_id: Provider's message ID

        Returns:
            Activity if found
        """
        stmt = select(Activity).where(
            Activity.provider_message_id == provider_message_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_activity(self, activity_id: UUID) -> Activity | None:
        """Get activity by ID."""
        stmt = select(Activity).where(Activity.id == activity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _check_duplicate(
        self,
        provider: str | None,
        provider_event_id: str,
    ) -> str | None:
        """Check if event already exists (for deduplication)."""
        query = text("""
            SELECT id FROM email_events
            WHERE provider = :provider AND provider_event_id = :provider_event_id
            LIMIT 1
        """)
        result = await self.session.execute(query, {
            "provider": provider,
            "provider_event_id": provider_event_id,
        })
        row = result.fetchone()
        return str(row.id) if row else None


# ============================================
# Provider-specific parsers
# ============================================


def parse_smartlead_webhook(payload: dict) -> dict[str, Any]:
    """
    Parse Smartlead webhook payload.

    Smartlead sends webhooks for email events including
    opens, clicks, replies, and bounces.

    Args:
        payload: Raw webhook payload

    Returns:
        Normalized event data
    """
    event_type_map = {
        "email_opened": "opened",
        "email_clicked": "clicked",
        "email_replied": "replied",
        "email_bounced": "bounced",
        "email_sent": "sent",
        "email_delivered": "delivered",
    }

    raw_type = payload.get("event_type", payload.get("type", ""))
    event_type = event_type_map.get(raw_type, raw_type)

    return {
        "event_type": event_type,
        "provider_message_id": payload.get("message_id") or payload.get("email_id"),
        "provider_event_id": payload.get("event_id") or payload.get("id"),
        "event_at": payload.get("timestamp") or payload.get("created_at"),
        "clicked_url": payload.get("link_url") or payload.get("clicked_url"),
        "lead_email": payload.get("lead_email") or payload.get("to_email"),
        "campaign_id": payload.get("campaign_id"),
        "device_info": {
            "device_type": payload.get("device_type"),
            "email_client": payload.get("email_client"),
            "os_type": payload.get("os"),
        },
        "geo_info": {
            "ip": payload.get("ip_address"),
            "city": payload.get("city"),
            "region": payload.get("region"),
            "country": payload.get("country"),
        },
        "raw": payload,
    }


def parse_salesforge_webhook(payload: dict) -> dict[str, Any]:
    """
    Parse Salesforge (InfraForge) webhook payload.

    Salesforge sends webhooks for email engagement events.

    Args:
        payload: Raw webhook payload

    Returns:
        Normalized event data
    """
    event_type_map = {
        "open": "opened",
        "click": "clicked",
        "reply": "replied",
        "bounce": "bounced",
        "send": "sent",
        "delivery": "delivered",
        "complaint": "complained",
        "unsubscribe": "unsubscribed",
    }

    raw_type = payload.get("event", payload.get("type", ""))
    event_type = event_type_map.get(raw_type.lower(), raw_type.lower())

    return {
        "event_type": event_type,
        "provider_message_id": payload.get("messageId") or payload.get("email_id"),
        "provider_event_id": payload.get("eventId") or payload.get("id"),
        "event_at": payload.get("timestamp") or payload.get("eventTime"),
        "clicked_url": payload.get("url") or payload.get("link"),
        "lead_email": payload.get("recipient") or payload.get("email"),
        "campaign_id": payload.get("campaignId"),
        "device_info": {
            "device_type": payload.get("deviceType"),
            "email_client": payload.get("client"),
            "os_type": payload.get("platform"),
        },
        "geo_info": {
            "ip": payload.get("ipAddress"),
            "city": payload.get("geoCity"),
            "region": payload.get("geoRegion"),
            "country": payload.get("geoCountry"),
        },
        "raw": payload,
    }


def parse_resend_webhook(payload: dict) -> dict[str, Any]:
    """
    Parse Resend webhook payload.

    Resend sends webhooks for email lifecycle events.

    Args:
        payload: Raw webhook payload

    Returns:
        Normalized event data
    """
    event_type_map = {
        "email.sent": "sent",
        "email.delivered": "delivered",
        "email.opened": "opened",
        "email.clicked": "clicked",
        "email.bounced": "bounced",
        "email.complained": "complained",
        "email.replied": "replied",
    }

    raw_type = payload.get("type", "")
    event_type = event_type_map.get(raw_type, raw_type.split(".")[-1])

    data = payload.get("data", {})

    return {
        "event_type": event_type,
        "provider_message_id": data.get("email_id"),
        "provider_event_id": payload.get("id"),
        "event_at": payload.get("created_at"),
        "clicked_url": data.get("click", {}).get("link"),
        "lead_email": data.get("to", [None])[0] if isinstance(data.get("to"), list) else data.get("to"),
        "device_info": {},
        "geo_info": {},
        "raw": payload,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] record_event() for generic event recording
# [x] record_open() for open events
# [x] record_click() for click events
# [x] record_bounce() for bounce events
# [x] record_unsubscribe() for unsubscribe events
# [x] record_complaint() for spam complaints
# [x] Duplicate event detection
# [x] Activity lookup by provider message ID
# [x] Provider-specific parsers (Smartlead, Salesforge, Resend)
# [x] All functions have type hints
# [x] All functions have docstrings
