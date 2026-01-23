"""
Contract: src/services/meeting_service.py
Purpose: Service for managing meetings and show rate tracking
Layer: 3 - services
Imports: models, services, exceptions
Consumers: orchestration, API routes, CIS detectors, closer engine

FILE: src/services/meeting_service.py
PURPOSE: Service for managing meetings and show rate tracking
PHASE: 24E (Downstream Outcomes), Updated Phase 24E-CRM
TASK: OUTCOME-003, OUTCOME-007, CRM-008
DEPENDENCIES:
  - src/models/database.py
  - src/services/crm_push_service.py (Phase 24E-CRM)
LAYER: 3 (services)
CONSUMERS: orchestration, API routes, CIS detectors, closer engine

This service manages meetings through their lifecycle from booking
to outcome, tracking show rates and outcomes for CIS learning.
Also pushes meetings to client's CRM when booked (Phase 24E-CRM).
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


# Valid meeting types
MEETING_TYPES = [
    "discovery",
    "demo",
    "follow_up",
    "close",
    "onboarding",
    "other",
]

# Valid meeting outcomes
MEETING_OUTCOMES = [
    "good",
    "bad",
    "rescheduled",
    "no_show",
    "cancelled",
    "pending",
]


class MeetingService:
    """
    Service for managing meetings.

    Tracks meetings through their lifecycle and provides
    show rate analytics for CIS learning.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the Meeting service.

        Args:
            session: Async database session
        """
        self.session = session

    async def create(
        self,
        client_id: UUID,
        lead_id: UUID,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        meeting_type: str = "discovery",
        campaign_id: UUID | None = None,
        booked_by: str = "ai",
        booking_method: str = "calendly",
        meeting_link: str | None = None,
        calendar_event_id: str | None = None,
        converting_activity_id: UUID | None = None,
        converting_channel: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new meeting.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID
            scheduled_at: When the meeting is scheduled
            duration_minutes: Meeting duration
            meeting_type: Type of meeting
            campaign_id: Optional campaign UUID
            booked_by: Who booked (ai, human, lead)
            booking_method: How it was booked
            meeting_link: Video call link
            calendar_event_id: External calendar ID
            converting_activity_id: Activity that led to booking
            converting_channel: Channel that led to booking

        Returns:
            Created meeting record

        Raises:
            ValidationError: If inputs are invalid
        """
        if meeting_type not in MEETING_TYPES:
            raise ValidationError(message=f"Invalid meeting type. Must be one of: {MEETING_TYPES}")

        # Calculate touches and days to booking
        touches_query = text("""
            SELECT
                COUNT(*) as count,
                MIN(created_at) as first_touch
            FROM activities
            WHERE lead_id = :lead_id
        """)
        touches_result = await self.session.execute(touches_query, {"lead_id": lead_id})
        touches_row = touches_result.fetchone()
        touches_before = touches_row.count if touches_row else 0
        first_touch = touches_row.first_touch if touches_row else None
        days_to_booking = None
        if first_touch:
            days_to_booking = (datetime.utcnow() - first_touch).days

        query = text("""
            INSERT INTO meetings (
                client_id, lead_id, campaign_id,
                scheduled_at, duration_minutes, meeting_type,
                booked_by, booking_method, meeting_link, calendar_event_id,
                converting_activity_id, converting_channel,
                touches_before_booking, days_to_booking,
                original_scheduled_at,
                created_at, updated_at
            ) VALUES (
                :client_id, :lead_id, :campaign_id,
                :scheduled_at, :duration_minutes, :meeting_type,
                :booked_by, :booking_method, :meeting_link, :calendar_event_id,
                :converting_activity_id, :converting_channel,
                :touches_before_booking, :days_to_booking,
                :scheduled_at,
                NOW(), NOW()
            )
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "lead_id": lead_id,
            "campaign_id": campaign_id,
            "scheduled_at": scheduled_at,
            "duration_minutes": duration_minutes,
            "meeting_type": meeting_type,
            "booked_by": booked_by,
            "booking_method": booking_method,
            "meeting_link": meeting_link,
            "calendar_event_id": calendar_event_id,
            "converting_activity_id": converting_activity_id,
            "converting_channel": converting_channel,
            "touches_before_booking": touches_before,
            "days_to_booking": days_to_booking,
        })

        row = result.fetchone()
        await self.session.commit()

        # Update lead with meeting info
        await self.session.execute(
            text("""
                UPDATE leads SET
                    meeting_booked = TRUE,
                    meeting_booked_at = NOW(),
                    meeting_id = :meeting_id,
                    status = 'meeting_booked',
                    updated_at = NOW()
                WHERE id = :lead_id
            """),
            {"meeting_id": row.id, "lead_id": lead_id}
        )
        await self.session.commit()

        meeting_data = dict(row._mapping)

        # Phase 24E-CRM: Push meeting to client's CRM (non-blocking)
        try:
            crm_result = await self._push_to_crm(
                client_id=client_id,
                lead_id=lead_id,
                meeting_id=row.id,
                meeting_data=meeting_data,
            )
            if crm_result:
                meeting_data["crm_push_result"] = crm_result
        except Exception as e:
            # CRM push failure should not fail meeting creation
            logger.error(f"CRM push failed for meeting {row.id}: {e}")
            meeting_data["crm_push_error"] = str(e)

        return meeting_data

    async def create_blind_meeting(
        self,
        client_id: UUID,
        lead_id: UUID | None = None,
        deal_id: UUID | None = None,
        source: str = "crm_sync",
        notes: str | None = None,
        external_deal_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a blind meeting (captured from external CRM, not booked through Agency OS).

        This method is used for "blind conversions" - meetings/deals that were created
        directly in the client's CRM without going through Agency OS. We capture these
        to ensure complete conversion tracking.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID (optional - may be unknown for blind conversions)
            deal_id: Deal UUID if already linked
            source: Source of the blind meeting (e.g., "hubspot_sync", "pipedrive_sync")
            notes: Additional notes about the blind conversion
            external_deal_id: External CRM deal ID for deduplication

        Returns:
            Created meeting record with is_blind=True

        Note:
            - scheduled_at defaults to NOW() since actual meeting time may be unknown
            - meeting_type defaults to "other" since we don't know the type
            - booked_by is set to "external" to indicate CRM origin
        """
        # Check for existing blind meeting with same external deal ID to prevent duplicates
        if external_deal_id:
            existing_query = text("""
                SELECT id FROM meetings
                WHERE client_id = :client_id
                AND external_deal_id = :external_deal_id
            """)
            existing_result = await self.session.execute(existing_query, {
                "client_id": client_id,
                "external_deal_id": external_deal_id,
            })
            existing = existing_result.fetchone()
            if existing:
                logger.info(f"Blind meeting already exists for external deal {external_deal_id}")
                return await self.get_by_id(existing.id)  # type: ignore

        query = text("""
            INSERT INTO meetings (
                client_id, lead_id, deal_id,
                scheduled_at, duration_minutes, meeting_type,
                booked_by, booking_method,
                meeting_notes, external_deal_id, is_blind,
                created_at, updated_at
            ) VALUES (
                :client_id, :lead_id, :deal_id,
                NOW(), 30, 'other',
                'external', :source,
                :notes, :external_deal_id, TRUE,
                NOW(), NOW()
            )
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "lead_id": lead_id,
            "deal_id": deal_id,
            "source": source,
            "notes": notes,
            "external_deal_id": external_deal_id,
        })

        row = result.fetchone()
        await self.session.commit()

        logger.info(
            f"Created blind meeting {row.id} from {source} "
            f"(external_deal_id={external_deal_id}, lead_id={lead_id})"
        )

        # Update lead with meeting info if lead_id provided
        if lead_id:
            await self.session.execute(
                text("""
                    UPDATE leads SET
                        meeting_booked = TRUE,
                        meeting_booked_at = COALESCE(meeting_booked_at, NOW()),
                        meeting_id = COALESCE(meeting_id, :meeting_id),
                        status = CASE
                            WHEN status NOT IN ('meeting_booked', 'closed_won', 'closed_lost')
                            THEN 'meeting_booked'
                            ELSE status
                        END,
                        updated_at = NOW()
                    WHERE id = :lead_id
                """),
                {"meeting_id": row.id, "lead_id": lead_id}
            )
            await self.session.commit()

        return dict(row._mapping)

    async def get_by_id(self, meeting_id: UUID) -> dict[str, Any] | None:
        """
        Get a meeting by ID.

        Args:
            meeting_id: Meeting UUID

        Returns:
            Meeting record or None if not found
        """
        query = text("""
            SELECT m.*, l.email as lead_email, l.first_name as lead_first_name,
                   l.last_name as lead_last_name, l.company as lead_company
            FROM meetings m
            LEFT JOIN leads l ON l.id = m.lead_id
            WHERE m.id = :meeting_id
        """)

        result = await self.session.execute(query, {"meeting_id": meeting_id})
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def get_by_calendar_id(
        self,
        calendar_event_id: str,
    ) -> dict[str, Any] | None:
        """
        Get a meeting by external calendar event ID.

        Args:
            calendar_event_id: External calendar event ID

        Returns:
            Meeting record or None if not found
        """
        query = text("""
            SELECT * FROM meetings
            WHERE calendar_event_id = :calendar_event_id
        """)

        result = await self.session.execute(query, {
            "calendar_event_id": calendar_event_id,
        })
        row = result.fetchone()

        if not row:
            return None

        return dict(row._mapping)

    async def confirm(
        self,
        meeting_id: UUID,
    ) -> dict[str, Any]:
        """
        Confirm a meeting.

        Args:
            meeting_id: Meeting UUID

        Returns:
            Updated meeting record
        """
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            raise NotFoundError(resource="meeting", resource_id=str(meeting_id))

        query = text("""
            UPDATE meetings
            SET confirmed = TRUE,
                confirmed_at = NOW(),
                updated_at = NOW()
            WHERE id = :meeting_id
            RETURNING *
        """)

        result = await self.session.execute(query, {"meeting_id": meeting_id})
        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def send_reminder(
        self,
        meeting_id: UUID,
    ) -> dict[str, Any]:
        """
        Mark reminder as sent.

        Args:
            meeting_id: Meeting UUID

        Returns:
            Updated meeting record
        """
        query = text("""
            UPDATE meetings
            SET reminder_sent = TRUE,
                reminder_sent_at = NOW(),
                updated_at = NOW()
            WHERE id = :meeting_id
            RETURNING *
        """)

        result = await self.session.execute(query, {"meeting_id": meeting_id})
        row = result.fetchone()
        if not row:
            raise NotFoundError(resource="meeting", resource_id=str(meeting_id))
        await self.session.commit()

        return dict(row._mapping)

    async def record_show(
        self,
        meeting_id: UUID,
        showed_up: bool,
        confirmed_by: str = "manual",
        no_show_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Record whether the lead showed up.

        Args:
            meeting_id: Meeting UUID
            showed_up: Whether they showed up
            confirmed_by: How it was confirmed (webhook, manual, calendar)
            no_show_reason: Reason if they didn't show

        Returns:
            Updated meeting record
        """
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            raise NotFoundError(resource="meeting", resource_id=str(meeting_id))

        query = text("""
            UPDATE meetings
            SET showed_up = :showed_up,
                showed_up_confirmed_at = NOW(),
                showed_up_confirmed_by = :confirmed_by,
                no_show_reason = :no_show_reason,
                meeting_outcome = CASE WHEN :showed_up THEN 'pending' ELSE 'no_show' END,
                meeting_outcome_at = NOW(),
                updated_at = NOW()
            WHERE id = :meeting_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "meeting_id": meeting_id,
            "showed_up": showed_up,
            "confirmed_by": confirmed_by,
            "no_show_reason": no_show_reason,
        })

        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def record_outcome(
        self,
        meeting_id: UUID,
        outcome: str,
        meeting_notes: str | None = None,
        next_steps: str | None = None,
        create_deal: bool = False,
        deal_name: str | None = None,
        deal_value: float | None = None,
    ) -> dict[str, Any]:
        """
        Record meeting outcome.

        Args:
            meeting_id: Meeting UUID
            outcome: Meeting outcome (good, bad, rescheduled, no_show, cancelled)
            meeting_notes: Notes from the meeting
            next_steps: Agreed next steps
            create_deal: Whether to create a deal
            deal_name: Deal name if creating
            deal_value: Deal value if creating

        Returns:
            Updated meeting record

        Raises:
            ValidationError: If outcome is invalid
        """
        if outcome not in MEETING_OUTCOMES:
            raise ValidationError(message=f"Invalid outcome. Must be one of: {MEETING_OUTCOMES}")

        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            raise NotFoundError(resource="meeting", resource_id=str(meeting_id))

        # Auto-set showed_up based on outcome
        showed_up = None
        if outcome == "no_show":
            showed_up = False
        elif outcome in ("good", "bad"):
            showed_up = True

        query = text("""
            UPDATE meetings
            SET meeting_outcome = :outcome,
                meeting_outcome_at = NOW(),
                meeting_notes = :meeting_notes,
                next_steps = :next_steps,
                showed_up = COALESCE(:showed_up, showed_up),
                showed_up_confirmed_at = CASE WHEN :showed_up IS NOT NULL THEN COALESCE(showed_up_confirmed_at, NOW()) ELSE showed_up_confirmed_at END,
                updated_at = NOW()
            WHERE id = :meeting_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "meeting_id": meeting_id,
            "outcome": outcome,
            "meeting_notes": meeting_notes,
            "next_steps": next_steps,
            "showed_up": showed_up,
        })

        row = result.fetchone()
        await self.session.commit()

        meeting_result = dict(row._mapping)

        # Create deal if requested
        if create_deal and outcome == "good":
            from src.services.deal_service import DealService
            deal_service = DealService(self.session)
            deal = await deal_service.create(
                client_id=meeting["client_id"],
                lead_id=meeting["lead_id"],
                name=deal_name or f"Deal from meeting {meeting_id}",
                value=deal_value,
                meeting_id=meeting_id,
                converting_activity_id=meeting.get("converting_activity_id"),
                converting_channel=meeting.get("converting_channel"),
            )

            # Update meeting with deal reference
            await self.session.execute(
                text("""
                    UPDATE meetings
                    SET deal_created = TRUE, deal_id = :deal_id
                    WHERE id = :meeting_id
                """),
                {"deal_id": deal["id"], "meeting_id": meeting_id}
            )
            await self.session.commit()

            meeting_result["deal_id"] = deal["id"]
            meeting_result["deal_created"] = True

        return meeting_result

    async def _push_to_crm(
        self,
        client_id: UUID,
        lead_id: UUID,
        meeting_id: UUID,
        meeting_data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Push meeting to client's CRM (Phase 24E-CRM).

        This is a non-blocking operation - failures are logged but don't
        affect meeting creation.

        Args:
            client_id: Client UUID
            lead_id: Lead UUID
            meeting_id: Meeting UUID
            meeting_data: Meeting data dict

        Returns:
            CRM push result or None if no CRM configured
        """
        from src.services.crm_push_service import (
            CRMPushService,
            LeadData,
            MeetingData,
        )

        # Get lead data for CRM
        lead_query = text("""
            SELECT id, email, first_name, last_name, full_name, phone, title,
                   company as organization_name, organization_website,
                   organization_industry, linkedin_url
            FROM leads
            WHERE id = :lead_id
        """)
        lead_result = await self.session.execute(lead_query, {"lead_id": lead_id})
        lead_row = lead_result.fetchone()

        if not lead_row:
            logger.warning(f"Lead {lead_id} not found for CRM push")
            return None

        # Build lead data
        lead_data = LeadData(
            id=lead_row.id,
            email=lead_row.email,
            first_name=lead_row.first_name,
            last_name=lead_row.last_name,
            full_name=lead_row.full_name,
            phone=lead_row.phone,
            title=lead_row.title,
            organization_name=lead_row.organization_name,
            organization_website=lead_row.organization_website,
            organization_industry=lead_row.organization_industry,
            linkedin_url=lead_row.linkedin_url,
        )

        # Build meeting data
        meeting = MeetingData(
            id=meeting_id,
            scheduled_at=meeting_data.get("scheduled_at"),
            duration_minutes=meeting_data.get("duration_minutes", 30),
            meeting_link=meeting_data.get("meeting_link"),
            notes=meeting_data.get("meeting_notes"),
        )

        # Push to CRM
        crm_service = CRMPushService(self.session)
        try:
            result = await crm_service.push_meeting_booked(
                client_id=client_id,
                lead=lead_data,
                meeting=meeting,
            )

            if result.success:
                logger.info(
                    f"Pushed meeting {meeting_id} to CRM: "
                    f"contact={result.crm_contact_id}, deal={result.crm_deal_id}"
                )
            elif result.skipped:
                logger.debug(f"CRM push skipped for meeting {meeting_id}: {result.reason}")
            else:
                logger.warning(f"CRM push failed for meeting {meeting_id}: {result.error}")

            return {
                "success": result.success,
                "skipped": result.skipped,
                "reason": result.reason,
                "crm_contact_id": result.crm_contact_id,
                "crm_deal_id": result.crm_deal_id,
                "error": result.error,
            }
        finally:
            await crm_service.close()

    async def reschedule(
        self,
        meeting_id: UUID,
        new_scheduled_at: datetime,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Reschedule a meeting.

        Args:
            meeting_id: Meeting UUID
            new_scheduled_at: New scheduled time
            reason: Reason for rescheduling

        Returns:
            Updated meeting record
        """
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            raise NotFoundError(resource="meeting", resource_id=str(meeting_id))

        query = text("""
            UPDATE meetings
            SET scheduled_at = :new_scheduled_at,
                rescheduled_count = rescheduled_count + 1,
                meeting_outcome = 'rescheduled',
                meeting_outcome_at = NOW(),
                meeting_notes = COALESCE(meeting_notes || E'\n', '') || 'Rescheduled: ' || COALESCE(:reason, 'No reason given'),
                confirmed = FALSE,
                confirmed_at = NULL,
                reminder_sent = FALSE,
                reminder_sent_at = NULL,
                showed_up = NULL,
                updated_at = NOW()
            WHERE id = :meeting_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "meeting_id": meeting_id,
            "new_scheduled_at": new_scheduled_at,
            "reason": reason,
        })

        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def cancel(
        self,
        meeting_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Cancel a meeting.

        Args:
            meeting_id: Meeting UUID
            reason: Reason for cancellation

        Returns:
            Updated meeting record
        """
        meeting = await self.get_by_id(meeting_id)
        if not meeting:
            raise NotFoundError(resource="meeting", resource_id=str(meeting_id))

        query = text("""
            UPDATE meetings
            SET meeting_outcome = 'cancelled',
                meeting_outcome_at = NOW(),
                meeting_notes = COALESCE(meeting_notes || E'\n', '') || 'Cancelled: ' || COALESCE(:reason, 'No reason given'),
                updated_at = NOW()
            WHERE id = :meeting_id
            RETURNING *
        """)

        result = await self.session.execute(query, {
            "meeting_id": meeting_id,
            "reason": reason,
        })

        row = result.fetchone()
        await self.session.commit()

        return dict(row._mapping)

    async def list_upcoming(
        self,
        client_id: UUID,
        days: int = 7,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List upcoming meetings.

        Args:
            client_id: Client UUID
            days: Days ahead to look
            limit: Max results

        Returns:
            List of upcoming meetings
        """
        query = text("""
            SELECT m.*, l.email as lead_email, l.first_name as lead_first_name,
                   l.last_name as lead_last_name, l.company as lead_company
            FROM meetings m
            LEFT JOIN leads l ON l.id = m.lead_id
            WHERE m.client_id = :client_id
            AND m.scheduled_at >= NOW()
            AND m.scheduled_at <= NOW() + (:days || ' days')::INTERVAL
            AND m.meeting_outcome IS NULL OR m.meeting_outcome = 'pending'
            ORDER BY m.scheduled_at ASC
            LIMIT :limit
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
            "limit": limit,
        })
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def list_needing_reminder(
        self,
        client_id: UUID,
        hours_before: int = 24,
    ) -> list[dict[str, Any]]:
        """
        List meetings needing reminders.

        Args:
            client_id: Client UUID
            hours_before: Hours before meeting to send reminder

        Returns:
            List of meetings needing reminders
        """
        query = text("""
            SELECT m.*, l.email as lead_email, l.first_name as lead_first_name,
                   l.last_name as lead_last_name
            FROM meetings m
            LEFT JOIN leads l ON l.id = m.lead_id
            WHERE m.client_id = :client_id
            AND m.reminder_sent = FALSE
            AND m.scheduled_at > NOW()
            AND m.scheduled_at <= NOW() + (:hours_before || ' hours')::INTERVAL
            AND (m.meeting_outcome IS NULL OR m.meeting_outcome = 'pending')
            ORDER BY m.scheduled_at ASC
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "hours_before": hours_before,
        })
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]

    async def get_show_rate_analysis(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get show rate analysis.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Show rate analysis data
        """
        query = text("""
            SELECT * FROM get_show_rate_analysis(:client_id, :days)
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
        })
        rows = result.fetchall()

        return {row.metric: float(row.value) if row.value else 0 for row in rows}

    async def get_booking_analytics(
        self,
        client_id: UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get meeting booking analytics.

        Args:
            client_id: Client UUID
            days: Number of days to analyze

        Returns:
            Booking analytics data
        """
        query = text("""
            WITH meeting_stats AS (
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE meeting_type = 'discovery') as discovery,
                    COUNT(*) FILTER (WHERE meeting_type = 'demo') as demo,
                    COUNT(*) FILTER (WHERE meeting_type = 'follow_up') as follow_up,
                    COUNT(*) FILTER (WHERE booked_by = 'ai') as ai_booked,
                    COUNT(*) FILTER (WHERE booked_by = 'human') as human_booked,
                    COUNT(*) FILTER (WHERE booked_by = 'lead') as lead_booked,
                    AVG(touches_before_booking) as avg_touches,
                    AVG(days_to_booking) as avg_days_to_book,
                    COUNT(*) FILTER (WHERE meeting_outcome = 'good') as good_outcomes,
                    COUNT(*) FILTER (WHERE meeting_outcome IS NOT NULL AND meeting_outcome != 'pending') as completed
                FROM meetings
                WHERE client_id = :client_id
                AND booked_at >= NOW() - (:days || ' days')::INTERVAL
            )
            SELECT * FROM meeting_stats
        """)

        result = await self.session.execute(query, {
            "client_id": client_id,
            "days": days,
        })
        row = result.fetchone()

        if not row:
            return {
                "total_meetings": 0,
                "by_type": {},
                "by_booker": {},
                "avg_touches_before_booking": 0,
                "avg_days_to_booking": 0,
                "good_outcome_rate": 0,
            }

        return {
            "total_meetings": row.total,
            "by_type": {
                "discovery": row.discovery,
                "demo": row.demo,
                "follow_up": row.follow_up,
            },
            "by_booker": {
                "ai": row.ai_booked,
                "human": row.human_booked,
                "lead": row.lead_booked,
            },
            "avg_touches_before_booking": round(row.avg_touches, 1) if row.avg_touches else 0,
            "avg_days_to_booking": round(row.avg_days_to_book, 1) if row.avg_days_to_book else 0,
            "good_outcome_rate": round(row.good_outcomes / row.completed * 100, 1) if row.completed else 0,
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Session passed as argument
# [x] No imports from engines/integrations/orchestration
# [x] CRUD operations for meetings
# [x] Confirmation tracking
# [x] Reminder tracking
# [x] Show/no-show recording
# [x] Outcome recording with deal creation option
# [x] Reschedule support
# [x] Cancellation support
# [x] Upcoming meetings list
# [x] Reminder queue
# [x] Show rate analysis integration
# [x] Booking analytics
# [x] Lead updates when meeting created
# [x] All functions have type hints
# [x] All functions have docstrings
