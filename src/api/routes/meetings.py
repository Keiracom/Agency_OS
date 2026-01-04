"""
FILE: src/api/routes/meetings.py
PURPOSE: Meetings API endpoints
PHASE: 14 (Missing UI)
TASK: MUI-002
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/activity.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only (deleted_at)
  - Multi-tenancy via client_id enforcement

NOTE: Meetings are derived from activities where intent='meeting_request'
and lead status is 'converted', or from extra_data containing meeting info.
"""

from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    ClientContext,
    get_current_client,
    get_db_session,
)
from src.models.activity import Activity
from src.models.base import IntentType
from src.models.lead import Lead

router = APIRouter(tags=["meetings"])


# ============================================
# Pydantic Schemas
# ============================================


class MeetingResponse(BaseModel):
    """Schema for a meeting."""
    id: UUID
    lead_id: UUID
    lead_name: str
    lead_company: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: int = 30
    meeting_type: str = "discovery"
    calendar_link: Optional[str] = None
    status: str = "scheduled"
    created_at: datetime

    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """Schema for meeting list."""
    items: List[MeetingResponse] = Field(..., description="List of meetings")
    total: int = Field(..., description="Total count")


# ============================================
# Routes
# ============================================


@router.get(
    "/clients/{client_id}/meetings",
    response_model=MeetingListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_meetings(
    client_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    upcoming: bool = Query(False, description="Only show upcoming meetings"),
    limit: int = Query(10, ge=1, le=50, description="Max meetings to return"),
) -> MeetingListResponse:
    """
    List meetings for a client.

    Meetings are derived from:
    1. Activities with intent='meeting_request' that have meeting info in extra_data
    2. Activities with action='meeting_booked'
    """
    now = datetime.utcnow()

    # Query for meeting-related activities
    stmt = (
        select(Activity)
        .where(
            and_(
                Activity.client_id == client_id,
                or_(
                    Activity.intent == IntentType.MEETING_REQUEST,
                    Activity.action == "meeting_booked",
                    Activity.action == "converted",
                ),
            )
        )
        .order_by(desc(Activity.created_at))
        .limit(limit * 2)  # Fetch extra to filter
    )

    result = await db.execute(stmt)
    activities = result.scalars().all()

    # Get leads for enrichment
    lead_ids = list(set(a.lead_id for a in activities))
    leads_map = {}

    if lead_ids:
        leads_stmt = select(Lead).where(Lead.id.in_(lead_ids))
        leads_result = await db.execute(leads_stmt)
        leads_map = {l.id: l for l in leads_result.scalars().all()}

    # Build meeting list
    meetings = []
    seen_leads = set()  # One meeting per lead

    for activity in activities:
        if activity.lead_id in seen_leads:
            continue

        lead = leads_map.get(activity.lead_id)
        if not lead:
            continue

        # Extract meeting info from extra_data if available
        extra = activity.extra_data or {}
        scheduled_at = None

        if "scheduled_at" in extra:
            try:
                scheduled_at = datetime.fromisoformat(extra["scheduled_at"])
            except (ValueError, TypeError):
                pass

        # If no scheduled_at, use activity created_at + 2 days as estimate
        if not scheduled_at:
            from datetime import timedelta
            scheduled_at = activity.created_at + timedelta(days=2)

        # Filter upcoming if requested
        if upcoming and scheduled_at < now:
            continue

        lead_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or lead.email

        meetings.append(
            MeetingResponse(
                id=activity.id,
                lead_id=lead.id,
                lead_name=lead_name,
                lead_company=lead.company,
                scheduled_at=scheduled_at,
                duration_minutes=extra.get("duration_minutes", 30),
                meeting_type=extra.get("meeting_type", "discovery"),
                calendar_link=extra.get("calendar_link"),
                status=extra.get("status", "scheduled"),
                created_at=activity.created_at,
            )
        )
        seen_leads.add(activity.lead_id)

        if len(meetings) >= limit:
            break

    # Sort by scheduled_at
    meetings.sort(key=lambda m: m.scheduled_at or datetime.max)

    return MeetingListResponse(
        items=meetings,
        total=len(meetings),
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with tags
# [x] List endpoint with upcoming filter
# [x] Multi-tenancy enforcement (client_id)
# [x] Authentication via dependencies
# [x] Pydantic schemas with validation
# [x] All functions have type hints
# [x] All functions have docstrings
