"""
Contract: src/pipeline/booking_handler.py
Purpose: Process calendar booking webhooks — pause outreach cadence and create deal record.
         Handles Calendly and Cal.com payload shapes. Supabase writes are best-effort.
Layer: 3 - pipeline
Directive: booking-webhook-handler
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — keep module importable in test environments
# ---------------------------------------------------------------------------

try:
    from src.integrations.supabase import get_db_session  # type: ignore

    _HAS_SUPABASE = True
except ImportError:
    _HAS_SUPABASE = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def handle_booking_webhook(payload: dict) -> dict:
    """Process a booking webhook from a calendar provider (Calendly, Cal.com, etc).

    Args:
        payload: webhook payload with at minimum:
            - email: str (booker's email)
            - name: str (booker's name)
            - event_type: str (meeting type)
            - scheduled_time: str (ISO datetime)
            - calendar_link: str (the booking URL)

    Returns:
        {
            "action": "cadence_paused",
            "prospect_email": str,
            "meeting_time": str,
            "deal_created": bool,
            "deal_data": dict,
        }
    """
    prospect = extract_prospect_from_booking(payload)

    email = prospect.get("email", "")
    if not email:
        return {
            "action": "error",
            "error": "missing_email",
            "detail": "No email found in booking payload",
        }

    name = prospect.get("name", "")
    event_type = prospect.get("event_type", "discovery_call")
    scheduled_time = prospect.get("scheduled_time", "")

    pause_result = pause_prospect_cadence(email)
    deal_data = create_deal_from_booking(email, name, event_type, scheduled_time)

    return {
        "action": "cadence_paused",
        "prospect_email": email,
        "meeting_time": scheduled_time,
        "deal_created": deal_data.get("persisted", False),
        "deal_data": deal_data,
        "pause_result": pause_result,
    }


# ---------------------------------------------------------------------------
# Extraction — normalise across provider payload shapes
# ---------------------------------------------------------------------------


def extract_prospect_from_booking(payload: dict) -> dict:
    """Normalise email/name from Calendly and Cal.com webhook shapes.

    Calendly shape:
        payload.event.invitees[0].email / .name
        payload.event.event_type.name
        payload.event.start_time

    Cal.com shape:
        payload.email / payload.name
        payload.type
        payload.startTime

    Flat shape (generic / testing):
        payload.email, payload.name, payload.event_type, payload.scheduled_time
    """
    # --- Calendly ---
    if "event" in payload and isinstance(payload.get("event"), dict):
        event = payload["event"]
        invitees = event.get("invitees") or []
        invitee = invitees[0] if invitees else {}
        return {
            "email": invitee.get("email", ""),
            "name": invitee.get("name", ""),
            "event_type": (event.get("event_type") or {}).get("name", ""),
            "scheduled_time": event.get("start_time", ""),
        }

    # --- Cal.com ---
    if "startTime" in payload or "type" in payload:
        return {
            "email": payload.get("email", ""),
            "name": payload.get("name", ""),
            "event_type": payload.get("type", ""),
            "scheduled_time": payload.get("startTime", ""),
        }

    # --- Flat / generic ---
    return {
        "email": payload.get("email", ""),
        "name": payload.get("name", ""),
        "event_type": payload.get("event_type", ""),
        "scheduled_time": payload.get("scheduled_time", ""),
    }


# ---------------------------------------------------------------------------
# Deal creation — Supabase best-effort
# ---------------------------------------------------------------------------


def create_deal_from_booking(
    email: str,
    name: str,
    event_type: str,
    scheduled_time: str,
) -> dict:
    """Build and persist a deal record. Returns the deal dict.

    Supabase write is best-effort — failures are logged but do not raise.
    The returned dict always contains the deal payload regardless of persistence.
    """
    deal = {
        "id": str(uuid.uuid4()),
        "prospect_email": email,
        "prospect_name": name,
        "event_type": event_type,
        "meeting_time": scheduled_time,
        "stage": "meeting_booked",
        "source": "calendar_webhook",
        "created_at": datetime.now(UTC).isoformat(),
        "persisted": False,
    }

    if not _HAS_SUPABASE:
        logger.warning("Supabase unavailable — deal not persisted for %s", email)
        return deal

    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(_persist_deal(deal))
        deal["persisted"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Deal persist failed (best-effort) for %s: %s", email, exc)

    return deal


async def _persist_deal(deal: dict) -> None:
    """Write deal row via SQLAlchemy session (best-effort inner coroutine)."""
    async with get_db_session() as db:
        from sqlalchemy import text  # lazy import

        await db.execute(
            text(
                "INSERT INTO public.deals "
                "(id, prospect_email, prospect_name, event_type, meeting_time, "
                " stage, source, created_at) "
                "VALUES (:id, :prospect_email, :prospect_name, :event_type, "
                " :meeting_time, :stage, :source, :created_at) "
                "ON CONFLICT DO NOTHING"
            ),
            {k: v for k, v in deal.items() if k != "persisted"},
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Cadence pause — marks prospect as booked in Supabase (best-effort)
# ---------------------------------------------------------------------------


def pause_prospect_cadence(email: str) -> dict:
    """Mark prospect as 'booked' to halt all outreach channels.

    Updates the prospect's cadence_status to 'booked' and stops further
    steps from firing. Supabase write is best-effort.

    Returns:
        {"paused": bool, "email": str, "status": str}
    """
    result: dict[str, Any] = {"paused": False, "email": email, "status": "booked"}

    if not _HAS_SUPABASE:
        logger.warning("Supabase unavailable — cadence not paused for %s", email)
        return result

    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(_pause_in_db(email))
        result["paused"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cadence pause failed (best-effort) for %s: %s", email, exc)

    return result


async def _pause_in_db(email: str) -> None:
    """Update prospect cadence_status via SQLAlchemy session."""
    async with get_db_session() as db:
        from sqlalchemy import text  # lazy import

        await db.execute(
            text(
                "UPDATE public.prospects "
                "SET cadence_status = 'booked', updated_at = NOW() "
                "WHERE email = :email AND deleted_at IS NULL"
            ),
            {"email": email},
        )
        await db.commit()
