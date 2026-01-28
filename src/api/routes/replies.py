"""
FILE: src/api/routes/replies.py
PURPOSE: Reply inbox API endpoints
PHASE: 14 (Missing UI)
TASK: MUI-001
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/activity.py
  - src/models/lead.py
  - src/models/campaign.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only (deleted_at)
  - Multi-tenancy via client_id enforcement
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    ClientContext,
    get_current_client,
    get_db_session,
    require_member,
)
from src.exceptions import ResourceNotFoundError
from src.models.activity import Activity
from src.models.base import ChannelType, IntentType
from src.models.campaign import Campaign
from src.models.lead import Lead

router = APIRouter(tags=["replies"])


# ============================================
# Pydantic Schemas
# ============================================


class LeadSummary(BaseModel):
    """Summary lead info for reply list."""

    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    company: str | None = None

    class Config:
        from_attributes = True


class ReplyResponse(BaseModel):
    """Schema for a reply."""

    id: UUID
    lead_id: UUID
    lead: LeadSummary | None = None
    campaign_id: UUID
    campaign_name: str | None = None
    channel: ChannelType
    intent: IntentType | None = None
    intent_confidence: float | None = None
    content: str | None = None
    subject: str | None = None
    received_at: datetime
    handled: bool = False
    handled_at: datetime | None = None

    class Config:
        from_attributes = True


class ReplyListResponse(BaseModel):
    """Schema for paginated reply list."""

    items: list[ReplyResponse] = Field(..., description="List of replies")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total pages")


class ReplyHandledUpdate(BaseModel):
    """Schema for marking reply as handled."""

    handled: bool = Field(..., description="Whether the reply is handled")


# ============================================
# Routes
# ============================================


@router.get(
    "/clients/{client_id}/replies",
    response_model=ReplyListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_replies(
    client_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    intent: IntentType | None = Query(None, description="Filter by intent"),
    channel: ChannelType | None = Query(None, description="Filter by channel"),
    handled: bool | None = Query(None, description="Filter by handled status"),
    campaign_id: UUID | None = Query(None, description="Filter by campaign"),
) -> ReplyListResponse:
    """
    List replies with pagination and filters.

    Replies are activities with action='replied'.
    """
    # Build query for replies
    stmt = select(Activity).where(
        and_(
            Activity.client_id == client_id,
            Activity.action == "replied",
        )
    )

    # Apply filters
    if intent:
        stmt = stmt.where(Activity.intent == intent)

    if channel:
        stmt = stmt.where(Activity.channel == channel)

    if handled is not None:
        if handled:
            stmt = stmt.where(Activity.processed_at.isnot(None))
        else:
            stmt = stmt.where(Activity.processed_at.is_(None))

    if campaign_id:
        stmt = stmt.where(Activity.campaign_id == campaign_id)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply pagination and ordering (most recent first)
    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(Activity.created_at)).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(stmt)
    activities = result.scalars().all()

    # Get leads and campaigns for enrichment
    lead_ids = [a.lead_id for a in activities]
    campaign_ids = [a.campaign_id for a in activities]

    leads_map = {}
    campaigns_map = {}

    if lead_ids:
        leads_stmt = select(Lead).where(Lead.id.in_(lead_ids))
        leads_result = await db.execute(leads_stmt)
        leads_map = {l.id: l for l in leads_result.scalars().all()}

    if campaign_ids:
        campaigns_stmt = select(Campaign).where(Campaign.id.in_(campaign_ids))
        campaigns_result = await db.execute(campaigns_stmt)
        campaigns_map = {c.id: c for c in campaigns_result.scalars().all()}

    # Build response
    items = []
    for activity in activities:
        lead = leads_map.get(activity.lead_id)
        campaign = campaigns_map.get(activity.campaign_id)

        items.append(
            ReplyResponse(
                id=activity.id,
                lead_id=activity.lead_id,
                lead=LeadSummary.model_validate(lead) if lead else None,
                campaign_id=activity.campaign_id,
                campaign_name=campaign.name if campaign else None,
                channel=activity.channel,
                intent=activity.intent,
                intent_confidence=activity.intent_confidence,
                content=activity.content_preview or activity.extra_data.get("body"),
                subject=activity.subject,
                received_at=activity.created_at,
                handled=activity.processed_at is not None,
                handled_at=activity.processed_at,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return ReplyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/clients/{client_id}/replies/{reply_id}",
    response_model=ReplyResponse,
    status_code=status.HTTP_200_OK,
)
async def get_reply(
    client_id: UUID,
    reply_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReplyResponse:
    """Get a single reply by ID."""
    stmt = select(Activity).where(
        and_(
            Activity.id == reply_id,
            Activity.client_id == client_id,
            Activity.action == "replied",
        )
    )
    result = await db.execute(stmt)
    activity = result.scalar_one_or_none()

    if not activity:
        raise ResourceNotFoundError(resource_type="Reply", resource_id=str(reply_id))

    # Get lead and campaign
    lead = None
    campaign = None

    lead_stmt = select(Lead).where(Lead.id == activity.lead_id)
    lead_result = await db.execute(lead_stmt)
    lead = lead_result.scalar_one_or_none()

    campaign_stmt = select(Campaign).where(Campaign.id == activity.campaign_id)
    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()

    return ReplyResponse(
        id=activity.id,
        lead_id=activity.lead_id,
        lead=LeadSummary.model_validate(lead) if lead else None,
        campaign_id=activity.campaign_id,
        campaign_name=campaign.name if campaign else None,
        channel=activity.channel,
        intent=activity.intent,
        intent_confidence=activity.intent_confidence,
        content=activity.content_preview or activity.extra_data.get("body"),
        subject=activity.subject,
        received_at=activity.created_at,
        handled=activity.processed_at is not None,
        handled_at=activity.processed_at,
    )


@router.patch(
    "/clients/{client_id}/replies/{reply_id}/handled",
    response_model=ReplyResponse,
    status_code=status.HTTP_200_OK,
)
async def mark_reply_handled(
    client_id: UUID,
    reply_id: UUID,
    data: ReplyHandledUpdate,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReplyResponse:
    """Mark a reply as handled or unhandled."""
    stmt = select(Activity).where(
        and_(
            Activity.id == reply_id,
            Activity.client_id == client_id,
            Activity.action == "replied",
        )
    )
    result = await db.execute(stmt)
    activity = result.scalar_one_or_none()

    if not activity:
        raise ResourceNotFoundError(resource_type="Reply", resource_id=str(reply_id))

    # Update processed_at
    activity.processed_at = datetime.utcnow() if data.handled else None
    await db.flush()
    await db.refresh(activity)

    # Get lead and campaign
    lead = None
    campaign = None

    lead_stmt = select(Lead).where(Lead.id == activity.lead_id)
    lead_result = await db.execute(lead_stmt)
    lead = lead_result.scalar_one_or_none()

    campaign_stmt = select(Campaign).where(Campaign.id == activity.campaign_id)
    campaign_result = await db.execute(campaign_stmt)
    campaign = campaign_result.scalar_one_or_none()

    return ReplyResponse(
        id=activity.id,
        lead_id=activity.lead_id,
        lead=LeadSummary.model_validate(lead) if lead else None,
        campaign_id=activity.campaign_id,
        campaign_name=campaign.name if campaign else None,
        channel=activity.channel,
        intent=activity.intent,
        intent_confidence=activity.intent_confidence,
        content=activity.content_preview or activity.extra_data.get("body"),
        subject=activity.subject,
        received_at=activity.created_at,
        handled=activity.processed_at is not None,
        handled_at=activity.processed_at,
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with tags
# [x] List endpoint with pagination
# [x] Filter by intent, channel, handled, campaign
# [x] Get single reply endpoint
# [x] Mark as handled endpoint
# [x] Multi-tenancy enforcement (client_id)
# [x] Authentication via dependencies
# [x] Pydantic schemas with validation
# [x] All functions have type hints
# [x] All functions have docstrings
