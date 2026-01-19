"""
FILE: src/api/routes/campaigns.py
PURPOSE: Campaign CRUD + status management API endpoints with multi-tenancy
PHASE: 7 (API Routes)
TASK: API-004
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/campaign.py
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only (deleted_at)
  - Multi-tenancy via client_id enforcement
  - Channel allocation must sum to 100
"""

from datetime import date, datetime, time
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    ClientContext,
    get_current_client,
    get_db_session,
    require_admin,
    require_member,
)
from src.exceptions import (
    ResourceDeletedError,
    ResourceNotFoundError,
    ValidationError as AgencyValidationError,
)
from src.models.base import CampaignStatus, ChannelType, PermissionMode
from src.models.campaign import Campaign, CampaignResource, CampaignSequence

router = APIRouter(tags=["campaigns"])


# ============================================
# Pydantic Schemas
# ============================================


class CampaignCreate(BaseModel):
    """Schema for creating a campaign."""

    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    permission_mode: Optional[PermissionMode] = Field(
        None, description="Permission mode (overrides client default)"
    )

    # Target settings
    target_industries: Optional[List[str]] = Field(None, description="Target industries")
    target_titles: Optional[List[str]] = Field(None, description="Target job titles")
    target_company_sizes: Optional[List[str]] = Field(None, description="Target company sizes")
    target_locations: Optional[List[str]] = Field(None, description="Target locations")

    # Channel allocation (must sum to 100)
    allocation_email: int = Field(100, ge=0, le=100, description="Email allocation %")
    allocation_sms: int = Field(0, ge=0, le=100, description="SMS allocation %")
    allocation_linkedin: int = Field(0, ge=0, le=100, description="LinkedIn allocation %")
    allocation_voice: int = Field(0, ge=0, le=100, description="Voice allocation %")
    allocation_mail: int = Field(0, ge=0, le=100, description="Direct mail allocation %")

    # Scheduling
    start_date: Optional[date] = Field(None, description="Campaign start date")
    end_date: Optional[date] = Field(None, description="Campaign end date")
    daily_limit: int = Field(50, ge=1, le=500, description="Daily outreach limit")
    timezone: str = Field("Australia/Sydney", description="Campaign timezone")

    # Working hours
    work_hours_start: time = Field(time(9, 0), description="Work hours start (24h)")
    work_hours_end: time = Field(time(17, 0), description="Work hours end (24h)")
    work_days: List[int] = Field([1, 2, 3, 4, 5], description="Work days (1=Mon, 7=Sun)")

    # Sequence settings
    sequence_steps: int = Field(5, ge=1, le=20, description="Number of sequence steps")
    sequence_delay_days: int = Field(3, ge=1, le=30, description="Days between steps")

    @model_validator(mode="after")
    def validate_allocation_sum(self) -> "CampaignCreate":
        """Validate that channel allocations sum to 100."""
        total = (
            self.allocation_email
            + self.allocation_sms
            + self.allocation_linkedin
            + self.allocation_voice
            + self.allocation_mail
        )
        if total != 100:
            raise ValueError(f"Channel allocations must sum to 100, got {total}")
        return self

    @field_validator("work_days")
    @classmethod
    def validate_work_days(cls, v: List[int]) -> List[int]:
        """Validate work days are valid."""
        for day in v:
            if day < 1 or day > 7:
                raise ValueError(f"Invalid work day {day}, must be 1-7")
        return sorted(set(v))


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    permission_mode: Optional[PermissionMode] = None

    # Target settings
    target_industries: Optional[List[str]] = None
    target_titles: Optional[List[str]] = None
    target_company_sizes: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None

    # Channel allocation (must sum to 100 if any are set)
    allocation_email: Optional[int] = Field(None, ge=0, le=100)
    allocation_sms: Optional[int] = Field(None, ge=0, le=100)
    allocation_linkedin: Optional[int] = Field(None, ge=0, le=100)
    allocation_voice: Optional[int] = Field(None, ge=0, le=100)
    allocation_mail: Optional[int] = Field(None, ge=0, le=100)

    # Scheduling
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    daily_limit: Optional[int] = Field(None, ge=1, le=500)
    timezone: Optional[str] = None

    # Working hours
    work_hours_start: Optional[time] = None
    work_hours_end: Optional[time] = None
    work_days: Optional[List[int]] = None

    # Sequence settings
    sequence_steps: Optional[int] = Field(None, ge=1, le=20)
    sequence_delay_days: Optional[int] = Field(None, ge=1, le=30)


class CampaignStatusUpdate(BaseModel):
    """Schema for updating campaign status."""

    status: CampaignStatus = Field(..., description="New status")


class CampaignResponse(BaseModel):
    """Schema for campaign response."""

    id: UUID
    client_id: UUID
    created_by: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    status: CampaignStatus
    permission_mode: Optional[PermissionMode] = None

    # Target settings
    target_industries: Optional[List[str]] = None
    target_titles: Optional[List[str]] = None
    target_company_sizes: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None

    # Channel allocation
    allocation_email: int
    allocation_sms: int
    allocation_linkedin: int
    allocation_voice: int
    allocation_mail: int

    # Scheduling
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    daily_limit: int
    timezone: str
    work_hours_start: time
    work_hours_end: time
    work_days: List[int]

    # Sequence settings
    sequence_steps: int
    sequence_delay_days: int

    # Metrics
    total_leads: int = 0
    leads_contacted: int = 0
    leads_replied: int = 0
    leads_converted: int = 0

    # Computed metrics
    reply_rate: float = 0.0
    conversion_rate: float = 0.0

    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list."""

    campaigns: List[CampaignResponse] = Field(..., description="List of campaigns")
    total: int = Field(..., description="Total count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total pages")


class SequenceStepCreate(BaseModel):
    """Schema for creating a sequence step."""

    step_number: int = Field(..., ge=1, le=20, description="Step number")
    channel: ChannelType = Field(..., description="Channel for this step")
    delay_days: int = Field(3, ge=0, le=30, description="Days to wait before this step")
    subject_template: Optional[str] = Field(None, description="Subject template (email only)")
    body_template: str = Field(..., min_length=1, description="Body template")
    skip_if_replied: bool = Field(True, description="Skip if lead replied")
    skip_if_bounced: bool = Field(True, description="Skip if lead bounced")


class SequenceStepResponse(BaseModel):
    """Schema for sequence step response."""

    id: UUID
    campaign_id: UUID
    step_number: int
    channel: ChannelType
    delay_days: int
    subject_template: Optional[str] = None
    body_template: str
    skip_if_replied: bool
    skip_if_bounced: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResourceCreate(BaseModel):
    """Schema for creating a campaign resource."""

    channel: ChannelType = Field(..., description="Channel type")
    resource_id: str = Field(..., description="Resource ID (email domain, LinkedIn seat, etc)")
    resource_name: Optional[str] = Field(None, description="Friendly name")
    daily_limit: int = Field(..., ge=1, description="Daily send limit")
    is_warmed: bool = Field(False, description="Is resource warmed up")


class ResourceResponse(BaseModel):
    """Schema for campaign resource response."""

    id: UUID
    campaign_id: UUID
    channel: ChannelType
    resource_id: str
    resource_name: Optional[str] = None
    daily_limit: int
    daily_used: int
    remaining: int
    last_used_at: Optional[datetime] = None
    last_reset_at: datetime
    is_active: bool
    is_warmed: bool
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Helper Functions
# ============================================


async def get_campaign_or_404(
    campaign_id: UUID,
    client_id: UUID,
    db: AsyncSession,
) -> Campaign:
    """
    Get campaign by ID with soft delete check.

    Args:
        campaign_id: Campaign UUID
        client_id: Client UUID (for multi-tenancy)
        db: Database session

    Returns:
        Campaign object

    Raises:
        ResourceNotFoundError: If campaign not found
        ResourceDeletedError: If campaign was deleted
    """
    # Query with soft delete check (Rule 14)
    stmt = select(Campaign).where(
        and_(
            Campaign.id == campaign_id,
            Campaign.client_id == client_id,
            Campaign.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        # Check if it was deleted
        stmt_deleted = select(Campaign).where(
            and_(
                Campaign.id == campaign_id,
                Campaign.client_id == client_id,
            )
        )
        result_deleted = await db.execute(stmt_deleted)
        deleted_campaign = result_deleted.scalar_one_or_none()

        if deleted_campaign and deleted_campaign.deleted_at:
            raise ResourceDeletedError(
                resource_type="Campaign",
                resource_id=str(campaign_id),
            )

        raise ResourceNotFoundError(
            resource_type="Campaign",
            resource_id=str(campaign_id),
        )

    return campaign


# ============================================
# Campaign CRUD Routes
# ============================================


@router.get(
    "/clients/{client_id}/campaigns",
    response_model=CampaignListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_campaigns(
    client_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: Optional[CampaignStatus] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name"),
) -> CampaignListResponse:
    """
    List campaigns with pagination and filters.

    Args:
        client_id: Client UUID
        ctx: Client context (auth)
        db: Database session
        page: Page number
        page_size: Page size
        status_filter: Optional status filter
        search: Optional search query

    Returns:
        Paginated list of campaigns
    """
    # Build query with soft delete check (Rule 14)
    stmt = select(Campaign).where(
        and_(
            Campaign.client_id == client_id,
            Campaign.deleted_at.is_(None),
        )
    )

    # Apply filters
    if status_filter:
        stmt = stmt.where(Campaign.status == status_filter)

    if search:
        stmt = stmt.where(Campaign.name.ilike(f"%{search}%"))

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(Campaign.created_at)).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    # Calculate pages
    pages = (total + page_size - 1) // page_size

    # Build response with computed metrics
    campaign_responses = []
    for campaign in campaigns:
        response = CampaignResponse.model_validate(campaign)
        response.reply_rate = campaign.reply_rate
        response.conversion_rate = campaign.conversion_rate
        campaign_responses.append(response)

    return CampaignListResponse(
        campaigns=campaign_responses,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/clients/{client_id}/campaigns/{campaign_id}",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
)
async def get_campaign(
    client_id: UUID,
    campaign_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """
    Get a single campaign by ID.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        ctx: Client context (auth)
        db: Database session

    Returns:
        Campaign details
    """
    campaign = await get_campaign_or_404(campaign_id, client_id, db)
    response = CampaignResponse.model_validate(campaign)
    response.reply_rate = campaign.reply_rate
    response.conversion_rate = campaign.conversion_rate
    return response


@router.post(
    "/clients/{client_id}/campaigns",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    client_id: UUID,
    campaign_data: CampaignCreate,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """
    Create a new campaign.

    Args:
        client_id: Client UUID
        campaign_data: Campaign data
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Created campaign
    """
    # Create campaign
    campaign = Campaign(
        client_id=client_id,
        created_by=ctx.user_id,
        name=campaign_data.name,
        description=campaign_data.description,
        status=CampaignStatus.DRAFT,
        permission_mode=campaign_data.permission_mode,
        target_industries=campaign_data.target_industries,
        target_titles=campaign_data.target_titles,
        target_company_sizes=campaign_data.target_company_sizes,
        target_locations=campaign_data.target_locations,
        allocation_email=campaign_data.allocation_email,
        allocation_sms=campaign_data.allocation_sms,
        allocation_linkedin=campaign_data.allocation_linkedin,
        allocation_voice=campaign_data.allocation_voice,
        allocation_mail=campaign_data.allocation_mail,
        start_date=campaign_data.start_date,
        end_date=campaign_data.end_date,
        daily_limit=campaign_data.daily_limit,
        timezone=campaign_data.timezone,
        work_hours_start=campaign_data.work_hours_start,
        work_hours_end=campaign_data.work_hours_end,
        work_days=campaign_data.work_days,
        sequence_steps=campaign_data.sequence_steps,
        sequence_delay_days=campaign_data.sequence_delay_days,
    )

    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)

    return CampaignResponse.model_validate(campaign)


@router.put(
    "/clients/{client_id}/campaigns/{campaign_id}",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
)
async def update_campaign(
    client_id: UUID,
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """
    Update a campaign.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        campaign_data: Campaign update data
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Updated campaign
    """
    campaign = await get_campaign_or_404(campaign_id, client_id, db)

    # Check if updating allocations - need to validate sum
    update_data = campaign_data.model_dump(exclude_unset=True)

    allocation_fields = ["allocation_email", "allocation_sms", "allocation_linkedin",
                         "allocation_voice", "allocation_mail"]
    has_allocation_update = any(f in update_data for f in allocation_fields)

    if has_allocation_update:
        # Get current values for fields not being updated
        new_email = update_data.get("allocation_email", campaign.allocation_email)
        new_sms = update_data.get("allocation_sms", campaign.allocation_sms)
        new_linkedin = update_data.get("allocation_linkedin", campaign.allocation_linkedin)
        new_voice = update_data.get("allocation_voice", campaign.allocation_voice)
        new_mail = update_data.get("allocation_mail", campaign.allocation_mail)

        total = new_email + new_sms + new_linkedin + new_voice + new_mail
        if total != 100:
            raise AgencyValidationError(
                f"Channel allocations must sum to 100, got {total}",
                field="allocation",
            )

    # Update fields
    for field, value in update_data.items():
        setattr(campaign, field, value)

    await db.flush()
    await db.refresh(campaign)

    response = CampaignResponse.model_validate(campaign)
    response.reply_rate = campaign.reply_rate
    response.conversion_rate = campaign.conversion_rate
    return response


@router.delete(
    "/clients/{client_id}/campaigns/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_campaign(
    client_id: UUID,
    campaign_id: UUID,
    ctx: Annotated[ClientContext, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """
    Soft delete a campaign.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        ctx: Client context (requires admin role)
        db: Database session

    Returns:
        None (204 No Content)
    """
    campaign = await get_campaign_or_404(campaign_id, client_id, db)

    # Soft delete (Rule 14)
    campaign.deleted_at = datetime.utcnow()
    await db.flush()


# ============================================
# Campaign Status Routes
# ============================================


@router.patch(
    "/clients/{client_id}/campaigns/{campaign_id}/status",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
)
async def update_campaign_status(
    client_id: UUID,
    campaign_id: UUID,
    status_update: CampaignStatusUpdate,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """
    Update campaign status.

    Valid transitions:
    - draft -> active
    - active -> paused
    - active -> completed
    - paused -> active
    - paused -> completed

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        status_update: New status
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Updated campaign
    """
    campaign = await get_campaign_or_404(campaign_id, client_id, db)

    new_status = status_update.status
    current_status = campaign.status

    # Validate transitions
    valid_transitions = {
        CampaignStatus.DRAFT: [CampaignStatus.ACTIVE],
        CampaignStatus.ACTIVE: [CampaignStatus.PAUSED, CampaignStatus.COMPLETED],
        CampaignStatus.PAUSED: [CampaignStatus.ACTIVE, CampaignStatus.COMPLETED],
        CampaignStatus.COMPLETED: [],  # Terminal state
    }

    if new_status not in valid_transitions.get(current_status, []):
        raise AgencyValidationError(
            f"Invalid status transition from {current_status.value} to {new_status.value}",
            field="status",
        )

    campaign.status = new_status
    await db.flush()
    await db.refresh(campaign)

    response = CampaignResponse.model_validate(campaign)
    response.reply_rate = campaign.reply_rate
    response.conversion_rate = campaign.conversion_rate
    return response


@router.post(
    "/clients/{client_id}/campaigns/{campaign_id}/activate",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
)
async def activate_campaign(
    client_id: UUID,
    campaign_id: UUID,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """
    Activate a campaign (shortcut for status update).

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Activated campaign
    """
    campaign = await get_campaign_or_404(campaign_id, client_id, db)

    if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
        raise AgencyValidationError(
            f"Cannot activate campaign with status {campaign.status.value}",
            field="status",
        )

    campaign.status = CampaignStatus.ACTIVE
    await db.flush()
    await db.refresh(campaign)

    response = CampaignResponse.model_validate(campaign)
    response.reply_rate = campaign.reply_rate
    response.conversion_rate = campaign.conversion_rate
    return response


@router.post(
    "/clients/{client_id}/campaigns/{campaign_id}/pause",
    response_model=CampaignResponse,
    status_code=status.HTTP_200_OK,
)
async def pause_campaign(
    client_id: UUID,
    campaign_id: UUID,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignResponse:
    """
    Pause a campaign.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Paused campaign
    """
    campaign = await get_campaign_or_404(campaign_id, client_id, db)

    if campaign.status != CampaignStatus.ACTIVE:
        raise AgencyValidationError(
            f"Cannot pause campaign with status {campaign.status.value}",
            field="status",
        )

    campaign.status = CampaignStatus.PAUSED
    await db.flush()
    await db.refresh(campaign)

    response = CampaignResponse.model_validate(campaign)
    response.reply_rate = campaign.reply_rate
    response.conversion_rate = campaign.conversion_rate
    return response


# ============================================
# Sequence Routes
# ============================================


@router.get(
    "/clients/{client_id}/campaigns/{campaign_id}/sequences",
    response_model=List[SequenceStepResponse],
    status_code=status.HTTP_200_OK,
)
async def list_sequences(
    client_id: UUID,
    campaign_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> List[SequenceStepResponse]:
    """
    List campaign sequence steps.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        ctx: Client context (auth)
        db: Database session

    Returns:
        List of sequence steps ordered by step number
    """
    # Verify campaign exists
    await get_campaign_or_404(campaign_id, client_id, db)

    stmt = (
        select(CampaignSequence)
        .where(CampaignSequence.campaign_id == campaign_id)
        .order_by(CampaignSequence.step_number)
    )
    result = await db.execute(stmt)
    sequences = result.scalars().all()

    return [SequenceStepResponse.model_validate(seq) for seq in sequences]


@router.post(
    "/clients/{client_id}/campaigns/{campaign_id}/sequences",
    response_model=SequenceStepResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sequence(
    client_id: UUID,
    campaign_id: UUID,
    sequence_data: SequenceStepCreate,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SequenceStepResponse:
    """
    Create a sequence step.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        sequence_data: Sequence step data
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Created sequence step
    """
    # Verify campaign exists
    await get_campaign_or_404(campaign_id, client_id, db)

    # Check for duplicate step number
    stmt = select(CampaignSequence).where(
        and_(
            CampaignSequence.campaign_id == campaign_id,
            CampaignSequence.step_number == sequence_data.step_number,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise AgencyValidationError(
            f"Sequence step {sequence_data.step_number} already exists",
            field="step_number",
        )

    sequence = CampaignSequence(
        campaign_id=campaign_id,
        step_number=sequence_data.step_number,
        channel=sequence_data.channel,
        delay_days=sequence_data.delay_days,
        subject_template=sequence_data.subject_template,
        body_template=sequence_data.body_template,
        skip_if_replied=sequence_data.skip_if_replied,
        skip_if_bounced=sequence_data.skip_if_bounced,
    )

    db.add(sequence)
    await db.flush()
    await db.refresh(sequence)

    return SequenceStepResponse.model_validate(sequence)


@router.delete(
    "/clients/{client_id}/campaigns/{campaign_id}/sequences/{step_number}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_sequence(
    client_id: UUID,
    campaign_id: UUID,
    step_number: int,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """
    Delete a sequence step.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        step_number: Step number to delete
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        None (204 No Content)
    """
    # Verify campaign exists
    await get_campaign_or_404(campaign_id, client_id, db)

    stmt = select(CampaignSequence).where(
        and_(
            CampaignSequence.campaign_id == campaign_id,
            CampaignSequence.step_number == step_number,
        )
    )
    result = await db.execute(stmt)
    sequence = result.scalar_one_or_none()

    if not sequence:
        raise ResourceNotFoundError(
            resource_type="CampaignSequence",
            resource_id=f"{campaign_id}/step/{step_number}",
        )

    # FIXED by fixer-agent: converted to soft delete (Rule 14)
    sequence.deleted_at = datetime.utcnow()
    await db.flush()


# ============================================
# Resource Routes
# ============================================


@router.get(
    "/clients/{client_id}/campaigns/{campaign_id}/resources",
    response_model=List[ResourceResponse],
    status_code=status.HTTP_200_OK,
)
async def list_resources(
    client_id: UUID,
    campaign_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    channel: Optional[ChannelType] = Query(None, description="Filter by channel"),
) -> List[ResourceResponse]:
    """
    List campaign resources.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        ctx: Client context (auth)
        db: Database session
        channel: Optional channel filter

    Returns:
        List of campaign resources
    """
    # Verify campaign exists
    await get_campaign_or_404(campaign_id, client_id, db)

    stmt = select(CampaignResource).where(CampaignResource.campaign_id == campaign_id)

    if channel:
        stmt = stmt.where(CampaignResource.channel == channel)

    result = await db.execute(stmt)
    resources = result.scalars().all()

    responses = []
    for resource in resources:
        response = ResourceResponse.model_validate(resource)
        response.remaining = resource.remaining
        response.is_available = resource.is_available
        responses.append(response)

    return responses


@router.post(
    "/clients/{client_id}/campaigns/{campaign_id}/resources",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resource(
    client_id: UUID,
    campaign_id: UUID,
    resource_data: ResourceCreate,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ResourceResponse:
    """
    Add a resource to a campaign.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        resource_data: Resource data
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Created resource
    """
    # Verify campaign exists
    await get_campaign_or_404(campaign_id, client_id, db)

    # Check for duplicate resource
    stmt = select(CampaignResource).where(
        and_(
            CampaignResource.campaign_id == campaign_id,
            CampaignResource.channel == resource_data.channel,
            CampaignResource.resource_id == resource_data.resource_id,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise AgencyValidationError(
            f"Resource {resource_data.resource_id} already exists for channel {resource_data.channel.value}",
            field="resource_id",
        )

    resource = CampaignResource(
        campaign_id=campaign_id,
        channel=resource_data.channel,
        resource_id=resource_data.resource_id,
        resource_name=resource_data.resource_name,
        daily_limit=resource_data.daily_limit,
        is_warmed=resource_data.is_warmed,
    )

    db.add(resource)
    await db.flush()
    await db.refresh(resource)

    response = ResourceResponse.model_validate(resource)
    response.remaining = resource.remaining
    response.is_available = resource.is_available
    return response


@router.delete(
    "/clients/{client_id}/campaigns/{campaign_id}/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_resource(
    client_id: UUID,
    campaign_id: UUID,
    resource_id: UUID,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    """
    Remove a resource from a campaign.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        resource_id: Resource UUID
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        None (204 No Content)
    """
    # Verify campaign exists
    await get_campaign_or_404(campaign_id, client_id, db)

    stmt = select(CampaignResource).where(
        and_(
            CampaignResource.id == resource_id,
            CampaignResource.campaign_id == campaign_id,
        )
    )
    result = await db.execute(stmt)
    resource = result.scalar_one_or_none()

    if not resource:
        raise ResourceNotFoundError(
            resource_type="CampaignResource",
            resource_id=str(resource_id),
        )

    # FIXED by fixer-agent: converted to soft delete (Rule 14)
    resource.deleted_at = datetime.utcnow()
    await db.flush()


# ============================================
# Lead Enrichment Routes
# ============================================


class EnrichLeadsRequest(BaseModel):
    """Schema for enriching leads for a campaign."""

    count: int = Field(default=50, ge=1, le=200, description="Number of leads to enrich")


class EnrichLeadsResponse(BaseModel):
    """Response from lead enrichment trigger."""

    status: str
    message: str
    campaign_id: str
    client_id: str
    count: int


@router.post(
    "/clients/{client_id}/campaigns/{campaign_id}/enrich-leads",
    response_model=EnrichLeadsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enrich_campaign_leads(
    client_id: UUID,
    campaign_id: UUID,
    request: EnrichLeadsRequest,
    background_tasks: BackgroundTasks,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> EnrichLeadsResponse:
    """
    Trigger lead enrichment for a campaign.

    This runs asynchronously and:
    1. Populates the lead pool from Apollo based on client ICP
    2. Assigns leads from the pool to the campaign
    3. Scores assigned leads with ALS
    4. Triggers deep research for hot leads (ALS >= 85)

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID
        request: Enrichment parameters
        background_tasks: FastAPI background tasks
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Accepted response with processing status
    """
    # Verify campaign exists
    campaign = await get_campaign_or_404(campaign_id, client_id, db)

    # Trigger Prefect flow for enrichment
    import logging
    from prefect.deployments import run_deployment

    logger = logging.getLogger(__name__)

    await run_deployment(
        name="daily_enrichment/enrichment-flow",
        parameters={
            "client_id": str(client_id),
            "campaign_id": str(campaign_id),
            "batch_size": request.count,
        },
        timeout=0,  # Don't wait for completion
    )
    logger.info(f"Triggered Prefect enrichment flow for campaign {campaign_id}")

    return EnrichLeadsResponse(
        status="queued",
        message=f"Lead enrichment started via Prefect for {request.count} leads",
        campaign_id=str(campaign_id),
        client_id=str(client_id),
        count=request.count,
    )


async def _run_campaign_enrichment(client_id: UUID, campaign_id: UUID, count: int):
    """
    Execute full campaign enrichment pipeline.

    Runs in background:
    1. Populate pool from Apollo
    2. Assign leads to campaign
    3. Score assigned leads
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    try:
        # 1. Populate pool from Apollo
        logger.info(f"[BACKGROUND] Starting pool population for client {client_id}, count={count}")
        from src.orchestration.flows.pool_population_flow import pool_population_flow
        population_result = await pool_population_flow(
            client_id=client_id,
            limit=count,
        )
        leads_added = population_result.get('leads_added', 0)
        logger.info(
            f"[BACKGROUND] Pool population complete: {leads_added} leads added, "
            f"{population_result.get('leads_skipped', 0)} skipped"
        )

        # 2. Assign leads to campaign
        logger.info(f"[BACKGROUND] Assigning leads to campaign {campaign_id}")
        from src.orchestration.flows.pool_assignment_flow import pool_campaign_assignment_flow
        assignment_result = await pool_campaign_assignment_flow(
            campaign_id=campaign_id,
            lead_count=count,
        )
        leads_allocated = assignment_result.get('leads_allocated', 0)
        logger.info(
            f"[BACKGROUND] Lead assignment complete: {leads_allocated} leads assigned"
        )

        # Update campaign total_leads counter
        from src.integrations.supabase import get_db_session
        from sqlalchemy import text
        async with get_db_session() as db:
            await db.execute(
                text("""
                    UPDATE campaigns
                    SET total_leads = total_leads + :count,
                        updated_at = NOW()
                    WHERE id = :campaign_id
                """),
                {"count": leads_allocated, "campaign_id": str(campaign_id)},
            )
            await db.commit()

        logger.info(f"[BACKGROUND] Campaign enrichment complete for {campaign_id}: {leads_allocated} leads")
        return {
            "success": True,
            "leads_added_to_pool": leads_added,
            "leads_assigned": leads_allocated,
        }

    except Exception as e:
        logger.error(
            f"[BACKGROUND] Campaign enrichment failed for {campaign_id}: {e}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        raise


# ============================================
# Campaign Suggestion Routes (Phase 37)
# ============================================


class CampaignSuggestionItem(BaseModel):
    """Schema for a single campaign suggestion."""

    name: str = Field(..., description="Suggested campaign name")
    description: str = Field(..., description="Campaign description")
    target_industries: List[str] = Field(..., description="Target industries")
    target_titles: List[str] = Field(..., description="Target job titles")
    target_company_sizes: List[str] = Field(..., description="Target company sizes")
    target_locations: List[str] = Field(..., description="Target locations")
    lead_allocation_pct: int = Field(..., ge=0, le=100, description="Lead allocation percentage")
    ai_reasoning: str = Field(..., description="AI reasoning for this suggestion")
    priority: int = Field(..., ge=1, description="Priority (1 = highest)")


class CampaignSuggestionsResponse(BaseModel):
    """Schema for campaign suggestions response."""

    client_id: str = Field(..., description="Client UUID")
    tier: str = Field(..., description="Client tier name")
    ai_campaign_slots: int = Field(..., description="Max AI campaign slots for tier")
    custom_campaign_slots: int = Field(..., description="Max custom campaign slots for tier")
    suggestions: List[CampaignSuggestionItem] = Field(..., description="AI-suggested campaigns")
    generated_at: str = Field(..., description="ISO timestamp of generation")


class CreateCampaignsFromSuggestionsRequest(BaseModel):
    """Schema for creating campaigns from suggestions."""

    suggestion_indices: Optional[List[int]] = Field(
        None,
        description="Indices of suggestions to create (0-based). If None, creates all."
    )
    auto_activate: bool = Field(
        False,
        description="Activate campaigns immediately (otherwise created as draft)"
    )


class CreateCampaignsFromSuggestionsResponse(BaseModel):
    """Schema for create campaigns response."""

    client_id: str = Field(..., description="Client UUID")
    campaigns_created: int = Field(..., description="Number of campaigns created")
    total_allocation: int = Field(..., description="Total lead allocation percentage")
    campaigns: List[dict] = Field(..., description="Created campaign details")


@router.get(
    "/clients/{client_id}/campaigns/suggestions",
    response_model=CampaignSuggestionsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_campaign_suggestions(
    client_id: UUID,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignSuggestionsResponse:
    """
    Get AI-suggested campaigns based on client ICP.

    Analyzes the client's ICP (Ideal Customer Profile) and suggests
    optimal campaign segments using Claude AI. Each suggestion includes:
    - Campaign name and target segment
    - Recommended lead allocation percentage
    - AI reasoning for the segment

    Args:
        client_id: Client UUID
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        AI-generated campaign suggestions
    """
    from src.engines.campaign_suggester import get_campaign_suggester

    engine = get_campaign_suggester()
    result = await engine.suggest_campaigns(db, client_id)

    if not result.success:
        raise AgencyValidationError(
            message=result.error or "Failed to generate campaign suggestions",
            field="client_id",
        )

    data = result.data
    return CampaignSuggestionsResponse(
        client_id=data["client_id"],
        tier=data["tier"],
        ai_campaign_slots=data["ai_campaign_slots"],
        custom_campaign_slots=data["custom_campaign_slots"],
        suggestions=[
            CampaignSuggestionItem(**s) for s in data["suggestions"]
        ],
        generated_at=data["generated_at"],
    )


@router.post(
    "/clients/{client_id}/campaigns/suggestions/create",
    response_model=CreateCampaignsFromSuggestionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaigns_from_suggestions(
    client_id: UUID,
    request: CreateCampaignsFromSuggestionsRequest,
    ctx: Annotated[ClientContext, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CreateCampaignsFromSuggestionsResponse:
    """
    Create campaigns from AI suggestions.

    First call GET /suggestions to get AI suggestions, then call this
    endpoint with the indices of suggestions you want to create.

    Args:
        client_id: Client UUID
        request: Request with suggestion indices and options
        ctx: Client context (requires member role)
        db: Database session

    Returns:
        Created campaign details
    """
    from src.engines.campaign_suggester import get_campaign_suggester

    engine = get_campaign_suggester()

    # First get suggestions
    suggestions_result = await engine.suggest_campaigns(db, client_id)
    if not suggestions_result.success:
        raise AgencyValidationError(
            message=suggestions_result.error or "Failed to generate suggestions",
            field="client_id",
        )

    all_suggestions = suggestions_result.data["suggestions"]

    # Filter to selected indices if provided
    if request.suggestion_indices is not None:
        selected_suggestions = []
        for idx in request.suggestion_indices:
            if 0 <= idx < len(all_suggestions):
                selected_suggestions.append(all_suggestions[idx])
        suggestions_to_create = selected_suggestions
    else:
        suggestions_to_create = all_suggestions

    if not suggestions_to_create:
        raise AgencyValidationError(
            message="No valid suggestions selected",
            field="suggestion_indices",
        )

    # Create campaigns from suggestions
    create_result = await engine.create_suggested_campaigns(
        db=db,
        client_id=client_id,
        suggestions=suggestions_to_create,
        auto_activate=request.auto_activate,
    )

    if not create_result.success:
        raise AgencyValidationError(
            message=create_result.error or "Failed to create campaigns",
            field="suggestions",
        )

    data = create_result.data
    return CreateCampaignsFromSuggestionsResponse(
        client_id=data["client_id"],
        campaigns_created=data["campaigns_created"],
        total_allocation=data["total_allocation"],
        campaigns=data["campaigns"],
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with tags
# [x] All CRUD endpoints (list, get, create, update, delete)
# [x] Status management endpoints (activate, pause, status update)
# [x] Sequence step endpoints (list, create, delete)
# [x] Resource endpoints (list, create, delete)
# [x] Pagination on list endpoint
# [x] Filtering by status, search
# [x] Soft delete for campaigns (Rule 14)
# [x] Multi-tenancy enforcement (client_id)
# [x] Authentication via dependencies
# [x] Role-based access (require_member for write, require_admin for delete)
# [x] Channel allocation validation (sum to 100)
# [x] Status transition validation
# [x] Pydantic schemas with validation
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Campaign suggestion endpoints (Phase 37)
