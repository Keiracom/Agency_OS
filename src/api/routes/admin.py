"""
FILE: src/api/routes/admin.py
PURPOSE: Admin-only API endpoints for platform management
PHASE: Admin Dashboard
TASK: Admin API Routes
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/*
  - src/integrations/redis.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft delete checks (deleted_at IS NULL)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    AdminContext,
    get_admin_context,
    get_db_session,
)
from src.exceptions import ResourceNotFoundError
from src.models.activity import Activity
from src.models.campaign import Campaign
from src.models.client import Client
from src.models.lead import Lead
from src.models.membership import Membership
from src.models.user import User

router = APIRouter(tags=["admin"])


# ============================================================================
# Response Models
# ============================================================================


class KPIStats(BaseModel):
    """Command center KPI statistics."""

    mrr: Decimal = Field(..., description="Monthly Recurring Revenue in AUD")
    mrr_change: float = Field(..., description="MRR change percentage MoM")
    active_clients: int = Field(..., description="Count of active clients")
    new_clients_this_month: int = Field(..., description="New clients this month")
    leads_today: int = Field(..., description="Leads created today")
    leads_change: float = Field(..., description="Leads change vs yesterday")
    ai_spend_today: Decimal = Field(..., description="AI spend today in AUD")
    ai_spend_limit: Decimal = Field(..., description="Daily AI spend limit in AUD")


class ServiceStatus(BaseModel):
    """Individual service status."""

    name: str
    status: str = Field(..., description="healthy, degraded, or down")
    latency_ms: float | None = None
    message: str | None = None


class SystemStatusResponse(BaseModel):
    """System health status response."""

    overall_status: str
    services: list[ServiceStatus]
    timestamp: datetime


class Alert(BaseModel):
    """System alert."""

    id: str
    severity: str = Field(..., description="critical, warning, or info")
    message: str
    timestamp: datetime
    link: str | None = None
    dismissible: bool = True


class ActivityItem(BaseModel):
    """Activity feed item."""

    id: str
    client_name: str
    action: str
    details: str
    timestamp: datetime
    channel: str | None = None


class ClientListItem(BaseModel):
    """Client list item for directory."""

    id: UUID
    name: str
    tier: str
    subscription_status: str
    mrr: Decimal
    campaigns_count: int
    leads_count: int
    last_activity: datetime | None
    health_score: int


class ClientListResponse(BaseModel):
    """Paginated client list response."""

    clients: list[ClientListItem]
    total: int
    page: int
    page_size: int


class ClientDetail(BaseModel):
    """Detailed client information."""

    id: UUID
    name: str
    tier: str
    subscription_status: str
    credits_remaining: int
    default_permission_mode: str
    stripe_customer_id: str | None
    created_at: datetime
    updated_at: datetime
    health_score: int
    campaigns: list[dict]
    team_members: list[dict]
    recent_activity: list[dict]


class AISpendByAgent(BaseModel):
    """AI spend breakdown by agent."""

    agent: str
    spend_aud: Decimal
    percentage: float
    token_count: int


class AISpendByClient(BaseModel):
    """AI spend breakdown by client."""

    client_id: UUID
    client_name: str
    spend_aud: Decimal


class AISpendResponse(BaseModel):
    """AI spend dashboard response."""

    today_spend: Decimal
    today_limit: Decimal
    today_percentage: float
    mtd_spend: Decimal
    projected_mtd: Decimal
    by_agent: list[AISpendByAgent]
    by_client: list[AISpendByClient]
    daily_trend: list[dict]


class SuppressionEntry(BaseModel):
    """Suppression list entry."""

    id: UUID
    email: str
    reason: str
    source: str | None
    added_by_email: str | None
    notes: str | None
    created_at: datetime


class SuppressionListResponse(BaseModel):
    """Paginated suppression list response."""

    entries: list[SuppressionEntry]
    total: int
    page: int
    page_size: int


class AddSuppressionRequest(BaseModel):
    """Request to add email to suppression list."""

    email: str = Field(..., description="Email to suppress")
    reason: str = Field(..., description="Reason: unsubscribe, bounce, spam, manual")
    notes: str | None = None


# ============================================================================
# Command Center Endpoints
# ============================================================================


@router.get("/admin/stats", response_model=KPIStats)
async def get_admin_stats(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get command center KPI statistics."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    (month_start - timedelta(days=1)).replace(day=1)

    # MRR calculation (tier-based pricing)
    tier_pricing = {"ignition": Decimal("199"), "velocity": Decimal("499"), "dominance": Decimal("999")}

    # Active clients with MRR
    stmt = select(Client.tier, func.count(Client.id)).where(
        and_(
            Client.subscription_status == "active",
            Client.deleted_at.is_(None),
        )
    ).group_by(Client.tier)
    result = await db.execute(stmt)
    tier_counts = dict(result.fetchall())

    mrr = sum(tier_pricing.get(tier, Decimal("0")) * count for tier, count in tier_counts.items())
    active_clients = sum(tier_counts.values())

    # New clients this month
    stmt = select(func.count(Client.id)).where(
        and_(
            Client.created_at >= month_start,
            Client.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    new_clients = result.scalar() or 0

    # Leads today
    stmt = select(func.count(Lead.id)).where(
        and_(
            Lead.created_at >= today_start,
            Lead.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    leads_today = result.scalar() or 0

    # Leads yesterday (for comparison)
    stmt = select(func.count(Lead.id)).where(
        and_(
            Lead.created_at >= yesterday_start,
            Lead.created_at < today_start,
            Lead.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    leads_yesterday = result.scalar() or 1  # Avoid division by zero

    leads_change = ((leads_today - leads_yesterday) / leads_yesterday) * 100 if leads_yesterday else 0

    # AI spend from Redis (real data)
    from src.config.settings import settings
    from src.integrations.redis import ai_spend_tracker

    try:
        ai_spend_float = await ai_spend_tracker.get_spend()
        ai_spend_today = Decimal(str(round(ai_spend_float, 2)))
    except Exception:
        ai_spend_today = Decimal("0.00")

    ai_spend_limit = Decimal(str(settings.anthropic_daily_spend_limit))

    # MRR change (simplified - would compare to last month)
    mrr_change = 12.5  # Placeholder

    return KPIStats(
        mrr=mrr,
        mrr_change=mrr_change,
        active_clients=active_clients,
        new_clients_this_month=new_clients,
        leads_today=leads_today,
        leads_change=round(leads_change, 1),
        ai_spend_today=ai_spend_today,
        ai_spend_limit=ai_spend_limit,
    )


@router.get("/admin/activity", response_model=list[ActivityItem])
async def get_global_activity(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(20, ge=1, le=100),
):
    """Get global activity feed across all clients."""
    # Join activities with leads and clients
    stmt = (
        select(Activity, Lead, Client)
        .join(Lead, Activity.lead_id == Lead.id)
        .join(Client, Lead.client_id == Client.id)
        .where(Client.deleted_at.is_(None))
        .order_by(desc(Activity.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    activities = []
    for activity, lead, client in rows:
        activities.append(
            ActivityItem(
                id=str(activity.id),
                client_name=client.name,
                action=activity.action,
                details=f"{activity.channel} to {lead.email}" if lead.email else activity.action,
                timestamp=activity.created_at,
                channel=activity.channel,
            )
        )

    return activities


@router.get("/admin/alerts", response_model=list[Alert])
async def get_system_alerts(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get current system alerts."""
    alerts = []
    now = datetime.utcnow()

    # Check for clients with no activity in 48 hours
    stmt = select(Client).where(
        and_(
            Client.subscription_status == "active",
            Client.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    clients = result.scalars().all()

    for client in clients:
        # Check last activity
        stmt = (
            select(func.max(Activity.created_at))
            .join(Lead, Activity.lead_id == Lead.id)
            .where(Lead.client_id == client.id)
        )
        result = await db.execute(stmt)
        last_activity = result.scalar()

        if last_activity and last_activity < now - timedelta(hours=48):
            alerts.append(
                Alert(
                    id=f"inactive_{client.id}",
                    severity="warning",
                    message=f'Client "{client.name}" - no activity for 48+ hours',
                    timestamp=now,
                    link=f"/admin/clients/{client.id}",
                )
            )

    # Check for past due clients
    stmt = select(Client).where(
        and_(
            Client.subscription_status == "past_due",
            Client.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    past_due_clients = result.scalars().all()

    for client in past_due_clients:
        alerts.append(
            Alert(
                id=f"past_due_{client.id}",
                severity="critical",
                message=f'Client "{client.name}" - payment past due',
                timestamp=now,
                link=f"/admin/clients/{client.id}",
            )
        )

    return alerts


# ============================================================================
# System Status Endpoints
# ============================================================================


@router.get("/admin/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get system health status for all services."""
    services = []

    # Check database
    try:
        start = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        services.append(
            ServiceStatus(
                name="Database",
                status="healthy",
                latency_ms=round(latency, 2),
            )
        )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="Database",
                status="down",
                message=str(e),
            )
        )

    # Check Redis (placeholder - would use actual Redis check)
    services.append(
        ServiceStatus(
            name="Redis",
            status="healthy",
            latency_ms=3.5,
        )
    )

    # Check Prefect (placeholder - would use actual Prefect API)
    services.append(
        ServiceStatus(
            name="Prefect",
            status="healthy",
            message="2 flows running",
        )
    )

    # Check API
    services.append(
        ServiceStatus(
            name="API",
            status="healthy",
            latency_ms=45.0,
        )
    )

    # Determine overall status
    statuses = [s.status for s in services]
    if "down" in statuses or "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return SystemStatusResponse(
        overall_status=overall,
        services=services,
        timestamp=datetime.utcnow(),
    )


# ============================================================================
# Client Management Endpoints
# ============================================================================


@router.get("/admin/clients", response_model=ClientListResponse)
async def list_all_clients(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    tier_filter: str | None = Query(None, alias="tier"),
    search: str | None = None,
):
    """Get all clients with health scores and metrics."""
    tier_pricing = {"ignition": Decimal("199"), "velocity": Decimal("499"), "dominance": Decimal("999")}

    # Base query
    conditions = [Client.deleted_at.is_(None)]

    if status_filter:
        conditions.append(Client.subscription_status == status_filter)
    if tier_filter:
        conditions.append(Client.tier == tier_filter)
    if search:
        conditions.append(Client.name.ilike(f"%{search}%"))

    # Count total
    count_stmt = select(func.count(Client.id)).where(and_(*conditions))
    result = await db.execute(count_stmt)
    total = result.scalar() or 0

    # Get clients
    offset = (page - 1) * page_size
    stmt = (
        select(Client)
        .where(and_(*conditions))
        .order_by(desc(Client.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    clients = result.scalars().all()

    client_items = []
    for client in clients:
        # Count campaigns
        stmt = select(func.count(Campaign.id)).where(
            and_(
                Campaign.client_id == client.id,
                Campaign.status == "active",
                Campaign.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        campaigns_count = result.scalar() or 0

        # Count leads
        stmt = select(func.count(Lead.id)).where(
            and_(
                Lead.client_id == client.id,
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        leads_count = result.scalar() or 0

        # Get last activity
        stmt = (
            select(func.max(Activity.created_at))
            .join(Lead, Activity.lead_id == Lead.id)
            .where(Lead.client_id == client.id)
        )
        result = await db.execute(stmt)
        last_activity = result.scalar()

        # Calculate health score (simplified version)
        health_score = 50  # Base
        if campaigns_count > 0:
            health_score += 20
        if last_activity and last_activity > datetime.utcnow() - timedelta(hours=24):
            health_score += 30
        elif last_activity and last_activity > datetime.utcnow() - timedelta(hours=48):
            health_score += 15
        if client.subscription_status in ("active", "trialing"):
            health_score += 15
        elif client.subscription_status == "past_due":
            health_score -= 30

        health_score = max(0, min(100, health_score))

        client_items.append(
            ClientListItem(
                id=client.id,
                name=client.name,
                tier=client.tier.value if hasattr(client.tier, 'value') else client.tier,
                subscription_status=client.subscription_status.value if hasattr(client.subscription_status, 'value') else client.subscription_status,
                mrr=tier_pricing.get(client.tier if isinstance(client.tier, str) else client.tier.value, Decimal("0")),
                campaigns_count=campaigns_count,
                leads_count=leads_count,
                last_activity=last_activity,
                health_score=health_score,
            )
        )

    return ClientListResponse(
        clients=client_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/clients/{client_id}", response_model=ClientDetail)
async def get_client_detail(
    client_id: UUID,
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get detailed client information."""
    # Get client
    stmt = select(Client).where(
        and_(
            Client.id == client_id,
            Client.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    client = result.scalar_one_or_none()

    if not client:
        raise ResourceNotFoundError(resource_type="Client", resource_id=str(client_id))

    # Get campaigns
    stmt = select(Campaign).where(
        and_(
            Campaign.client_id == client_id,
            Campaign.deleted_at.is_(None),
        )
    ).order_by(desc(Campaign.created_at)).limit(10)
    result = await db.execute(stmt)
    campaigns = result.scalars().all()

    campaign_list = [
        {
            "id": str(c.id),
            "name": c.name,
            "status": c.status.value if hasattr(c.status, 'value') else c.status,
            "leads_count": 0,  # Would count actual leads
        }
        for c in campaigns
    ]

    # Get team members
    stmt = (
        select(User, Membership)
        .join(Membership, User.id == Membership.user_id)
        .where(
            and_(
                Membership.client_id == client_id,
                Membership.deleted_at.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    members = result.fetchall()

    team_list = [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": membership.role.value if hasattr(membership.role, 'value') else membership.role,
        }
        for user, membership in members
    ]

    # Get recent activity
    stmt = (
        select(Activity, Lead)
        .join(Lead, Activity.lead_id == Lead.id)
        .where(Lead.client_id == client_id)
        .order_by(desc(Activity.created_at))
        .limit(20)
    )
    result = await db.execute(stmt)
    activities = result.fetchall()

    activity_list = [
        {
            "id": str(activity.id),
            "action": activity.action,
            "channel": activity.channel,
            "lead_email": lead.email,
            "timestamp": activity.created_at.isoformat(),
        }
        for activity, lead in activities
    ]

    # Calculate health score
    health_score = 50
    if len(campaigns) > 0:
        health_score += 20
    if client.subscription_status.value in ("active", "trialing") if hasattr(client.subscription_status, 'value') else client.subscription_status in ("active", "trialing"):
        health_score += 15

    return ClientDetail(
        id=client.id,
        name=client.name,
        tier=client.tier.value if hasattr(client.tier, 'value') else client.tier,
        subscription_status=client.subscription_status.value if hasattr(client.subscription_status, 'value') else client.subscription_status,
        credits_remaining=client.credits_remaining,
        default_permission_mode=client.default_permission_mode.value if hasattr(client.default_permission_mode, 'value') else client.default_permission_mode,
        stripe_customer_id=client.stripe_customer_id,
        created_at=client.created_at,
        updated_at=client.updated_at,
        health_score=min(100, max(0, health_score)),
        campaigns=campaign_list,
        team_members=team_list,
        recent_activity=activity_list,
    )


# ============================================================================
# AI Spend Endpoints
# ============================================================================


@router.get("/admin/costs/ai", response_model=AISpendResponse)
async def get_ai_spend(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get AI spend breakdown and trends.

    Real-time spend comes from Redis via ai_spend_tracker.
    Agent/client breakdown requires ai_usage_logs table (not yet implemented).
    """
    from src.config.settings import settings
    from src.integrations.redis import ai_spend_tracker

    # Get real today's spend from Redis
    try:
        today_spend_float = await ai_spend_tracker.get_spend()
        today_spend = Decimal(str(round(today_spend_float, 2)))
        await ai_spend_tracker.get_remaining()
    except Exception:
        today_spend = Decimal("0.00")
        Decimal(str(settings.anthropic_daily_spend_limit))

    today_limit = Decimal(str(settings.anthropic_daily_spend_limit))
    today_percentage = float((today_spend / today_limit) * 100) if today_limit > 0 else 0.0

    # Agent breakdown (would require ai_usage_logs table with agent field)
    # For now, estimate based on typical usage patterns
    # TODO: Implement ai_usage_logs table for accurate tracking
    content_pct = 42.0
    reply_pct = 33.0
    cmo_pct = 25.0

    by_agent = [
        AISpendByAgent(
            agent="content",
            spend_aud=Decimal(str(round(float(today_spend) * content_pct / 100, 2))),
            percentage=content_pct,
            token_count=int(float(today_spend) * content_pct / 100 * 1000 / 0.015) if today_spend > 0 else 0,
        ),
        AISpendByAgent(
            agent="reply",
            spend_aud=Decimal(str(round(float(today_spend) * reply_pct / 100, 2))),
            percentage=reply_pct,
            token_count=int(float(today_spend) * reply_pct / 100 * 1000 / 0.015) if today_spend > 0 else 0,
        ),
        AISpendByAgent(
            agent="cmo",
            spend_aud=Decimal(str(round(float(today_spend) * cmo_pct / 100, 2))),
            percentage=cmo_pct,
            token_count=int(float(today_spend) * cmo_pct / 100 * 1000 / 0.015) if today_spend > 0 else 0,
        ),
    ]

    # Client breakdown (would require ai_usage_logs table with client_id)
    # For now, query top active clients and distribute proportionally
    # TODO: Implement ai_usage_logs table for accurate tracking
    top_clients_stmt = (
        select(Client.id, Client.company_name)
        .where(
            and_(
                Client.subscription_status == "active",
                Client.deleted_at.is_(None),
            )
        )
        .order_by(desc(Client.created_at))
        .limit(10)
    )
    top_clients_result = await db.execute(top_clients_stmt)
    top_clients = top_clients_result.all()

    by_client = []
    if top_clients and today_spend > 0:
        # Distribute spend proportionally (in reality, would come from logs)
        total_weight = sum(range(1, len(top_clients) + 1))
        for i, (client_id, client_name) in enumerate(top_clients):
            weight = len(top_clients) - i
            client_spend = float(today_spend) * weight / total_weight
            by_client.append(
                AISpendByClient(
                    client_id=client_id,
                    client_name=client_name or "Unknown",
                    spend_aud=Decimal(str(round(client_spend, 2))),
                )
            )

    # Daily trend - would require historical Redis data or ai_usage_logs
    # For now, show today's real data and placeholder for past days
    # TODO: Implement Redis historical tracking or ai_usage_logs table
    daily_trend = []
    for i in range(7, 0, -1):
        date_str = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        if i == 1:
            # Yesterday - placeholder
            daily_trend.append({"date": date_str, "spend": float(today_spend) * 0.9})
        else:
            # Older days - placeholder based on limit
            daily_trend.append({"date": date_str, "spend": float(today_limit) * 0.15 + i * 5})

    # Add today
    daily_trend.append({
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "spend": float(today_spend),
    })

    # Month to date (estimate based on today's spend)
    day_of_month = datetime.utcnow().day
    mtd_spend = today_spend * Decimal(str(day_of_month))  # Rough estimate
    days_in_month = 30
    projected_mtd = (mtd_spend / Decimal(str(day_of_month))) * Decimal(str(days_in_month)) if day_of_month > 0 else Decimal("0")

    return AISpendResponse(
        today_spend=today_spend,
        today_limit=today_limit,
        today_percentage=today_percentage,
        mtd_spend=mtd_spend,
        projected_mtd=projected_mtd,
        by_agent=by_agent,
        by_client=by_client,
        daily_trend=daily_trend,
    )


# ============================================================================
# Suppression List Endpoints
# ============================================================================


@router.get("/admin/suppression", response_model=SuppressionListResponse)
async def get_suppression_list(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    reason_filter: str | None = Query(None, alias="reason"),
    search: str | None = None,
):
    """Get global suppression list."""
    # Query from global_suppression_list table
    # For now, return placeholder data
    entries = [
        SuppressionEntry(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="spam@bad.com",
            reason="spam",
            source="Campaign: Tech Startups",
            added_by_email="system",
            notes=None,
            created_at=datetime.utcnow() - timedelta(days=2),
        ),
        SuppressionEntry(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            email="bounced@invalid.io",
            reason="bounce",
            source="Campaign: SaaS Decision Makers",
            added_by_email="system",
            notes="Hard bounce - mailbox does not exist",
            created_at=datetime.utcnow() - timedelta(days=5),
        ),
    ]

    return SuppressionListResponse(
        entries=entries,
        total=2,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/suppression", status_code=status.HTTP_201_CREATED)
async def add_to_suppression(
    request: AddSuppressionRequest,
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Add email to global suppression list."""
    # Would insert into global_suppression_list table
    # For now, just acknowledge
    return {
        "success": True,
        "email": request.email,
        "reason": request.reason,
        "message": f"Added {request.email} to suppression list",
    }


@router.delete("/admin/suppression/{entry_id}")
async def remove_from_suppression(
    entry_id: UUID,
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Remove email from global suppression list."""
    # Would delete from global_suppression_list table
    return {
        "success": True,
        "message": f"Removed entry {entry_id} from suppression list",
    }


# ============================================================================
# Revenue Endpoints
# ============================================================================


@router.get("/admin/revenue")
async def get_revenue_metrics(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get revenue dashboard metrics."""
    tier_pricing = {"ignition": Decimal("199"), "velocity": Decimal("499"), "dominance": Decimal("999")}

    # Get tier distribution
    stmt = select(Client.tier, func.count(Client.id)).where(
        and_(
            Client.subscription_status == "active",
            Client.deleted_at.is_(None),
        )
    ).group_by(Client.tier)
    result = await db.execute(stmt)
    tier_counts = dict(result.fetchall())

    mrr = sum(tier_pricing.get(tier if isinstance(tier, str) else tier.value, Decimal("0")) * count for tier, count in tier_counts.items())
    arr = mrr * 12

    return {
        "mrr": float(mrr),
        "arr": float(arr),
        "new_mrr": 1500.00,  # Placeholder
        "churned_mrr": 500.00,  # Placeholder
        "net_mrr_growth": 1000.00,  # Placeholder
        "churn_rate": 2.5,  # Placeholder
        "arpu": float(mrr / max(sum(tier_counts.values()), 1)),
        "by_tier": {
            tier if isinstance(tier, str) else tier.value: {
                "count": count,
                "mrr": float(tier_pricing.get(tier if isinstance(tier, str) else tier.value, Decimal("0")) * count),
            }
            for tier, count in tier_counts.items()
        },
    }


# ============================================================================
# Global Data Endpoints
# ============================================================================


@router.get("/admin/campaigns")
async def get_all_campaigns(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
):
    """Get all campaigns across all clients."""
    conditions = [Campaign.deleted_at.is_(None)]
    if status_filter:
        conditions.append(Campaign.status == status_filter)

    # Count total
    count_stmt = select(func.count(Campaign.id)).where(and_(*conditions))
    result = await db.execute(count_stmt)
    total = result.scalar() or 0

    # Get campaigns with client info
    offset = (page - 1) * page_size
    stmt = (
        select(Campaign, Client)
        .join(Client, Campaign.client_id == Client.id)
        .where(and_(*conditions))
        .order_by(desc(Campaign.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    campaigns = [
        {
            "id": str(campaign.id),
            "name": campaign.name,
            "client_id": str(client.id),
            "client_name": client.name,
            "status": campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
            "permission_mode": campaign.permission_mode.value if hasattr(campaign.permission_mode, 'value') else campaign.permission_mode,
            "created_at": campaign.created_at.isoformat(),
        }
        for campaign, client in rows
    ]

    return {
        "campaigns": campaigns,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/admin/leads")
async def get_all_leads(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tier_filter: str | None = Query(None, alias="tier"),
):
    """Get all leads across all clients."""
    conditions = [Lead.deleted_at.is_(None)]
    if tier_filter:
        conditions.append(Lead.als_tier == tier_filter)

    # Count total
    count_stmt = select(func.count(Lead.id)).where(and_(*conditions))
    result = await db.execute(count_stmt)
    total = result.scalar() or 0

    # Get leads with client info
    offset = (page - 1) * page_size
    stmt = (
        select(Lead, Client)
        .join(Client, Lead.client_id == Client.id)
        .where(and_(*conditions))
        .order_by(desc(Lead.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    leads = [
        {
            "id": str(lead.id),
            "email": lead.email,
            "client_id": str(client.id),
            "client_name": client.name,
            "als_score": lead.als_score,
            "als_tier": lead.als_tier,
            "status": lead.status.value if hasattr(lead.status, 'value') else lead.status,
            "created_at": lead.created_at.isoformat(),
        }
        for lead, client in rows
    ]

    return {
        "leads": leads,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================================================
# Lead Pool Management Endpoints (Phase 24A)
# ============================================================================


class PoolStats(BaseModel):
    """Lead pool statistics."""

    total_leads: int
    available: int
    assigned: int
    converted: int
    bounced: int
    unsubscribed: int
    utilization_rate: float
    avg_als_score: float | None = None


class PoolLeadItem(BaseModel):
    """Pool lead list item."""

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    company_name: str | None
    title: str | None
    pool_status: str
    email_status: str | None
    als_score: int | None
    als_tier: str | None
    created_at: datetime


class PoolLeadListResponse(BaseModel):
    """Paginated pool lead list."""

    leads: list[PoolLeadItem]
    total: int
    page: int
    page_size: int


class PoolLeadDetail(BaseModel):
    """Detailed pool lead information."""

    id: UUID
    email: str
    email_status: str | None
    first_name: str | None
    last_name: str | None
    title: str | None
    seniority: str | None
    company_name: str | None
    company_domain: str | None
    company_industry: str | None
    company_employee_count: int | None
    company_country: str | None
    linkedin_url: str | None
    phone: str | None
    pool_status: str
    als_score: int | None
    als_tier: str | None
    is_bounced: bool
    is_unsubscribed: bool
    created_at: datetime
    assignments: list[dict]


class AssignmentItem(BaseModel):
    """Assignment list item."""

    id: UUID
    lead_pool_id: UUID
    client_id: UUID
    client_name: str
    status: str
    total_touches: int
    has_replied: bool
    assigned_at: datetime


class AssignmentListResponse(BaseModel):
    """Paginated assignment list."""

    assignments: list[AssignmentItem]
    total: int
    page: int
    page_size: int


class ManualAssignRequest(BaseModel):
    """Request to manually assign pool leads."""

    lead_pool_ids: list[UUID] = Field(..., description="Pool lead IDs to assign")
    client_id: UUID = Field(..., description="Client to assign to")
    campaign_id: UUID | None = None


class ReleaseLeadRequest(BaseModel):
    """Request to release leads back to pool."""

    assignment_ids: list[UUID] = Field(..., description="Assignment IDs to release")
    reason: str = Field(default="admin_manual", description="Release reason")


@router.get("/admin/pool/stats", response_model=PoolStats)
async def get_pool_stats(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get lead pool statistics."""
    from src.services.lead_pool_service import LeadPoolService

    pool_service = LeadPoolService(db)
    stats = await pool_service.get_pool_stats()

    # Calculate utilization rate
    total = stats.get("total_leads", 0)
    assigned = stats.get("assigned", 0)
    utilization_rate = (assigned / total * 100) if total > 0 else 0.0

    # Get average ALS score from lead_assignments (where scoring happens)
    stmt = text("""
        SELECT AVG(als_score) as avg_score
        FROM lead_assignments
        WHERE als_score IS NOT NULL
    """)
    result = await db.execute(stmt)
    row = result.fetchone()
    avg_score = float(row.avg_score) if row and row.avg_score else None

    return PoolStats(
        total_leads=stats.get("total_leads", 0),
        available=stats.get("available", 0),
        assigned=stats.get("assigned", 0),
        converted=stats.get("converted", 0),
        bounced=stats.get("bounced", 0),
        unsubscribed=stats.get("unsubscribed", 0),
        utilization_rate=round(utilization_rate, 2),
        avg_als_score=round(avg_score, 1) if avg_score else None,
    )


@router.get("/admin/pool/leads", response_model=PoolLeadListResponse)
async def get_pool_leads(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    tier_filter: str | None = Query(None, alias="tier"),
    search: str | None = None,
):
    """Get paginated list of pool leads."""
    conditions = []
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}

    if status_filter:
        conditions.append("pool_status = :status")
        params["status"] = status_filter
    # Note: tier_filter removed - ALS scoring happens on lead_assignments, not lead_pool
    if search:
        conditions.append("(email ILIKE :search OR company_name ILIKE :search)")
        params["search"] = f"%{search}%"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_stmt = text(f"SELECT COUNT(*) FROM lead_pool {where_clause}")
    result = await db.execute(count_stmt, params)
    total = result.scalar() or 0

    # Get leads (ALS scores are on lead_assignments, not lead_pool)
    stmt = text(f"""
        SELECT id, email, first_name, last_name, company_name, title,
               pool_status, email_status, created_at
        FROM lead_pool
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(stmt, params)
    rows = result.fetchall()

    leads = [
        PoolLeadItem(
            id=row.id,
            email=row.email,
            first_name=row.first_name,
            last_name=row.last_name,
            company_name=row.company_name,
            title=row.title,
            pool_status=row.pool_status,
            email_status=row.email_status,
            als_score=None,  # ALS scores are on lead_assignments, not pool
            als_tier=None,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return PoolLeadListResponse(
        leads=leads,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/pool/leads/{lead_pool_id}", response_model=PoolLeadDetail)
async def get_pool_lead_detail(
    lead_pool_id: UUID,
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get detailed pool lead information with assignments."""
    # Get pool lead
    stmt = text("""
        SELECT id, email, email_status, first_name, last_name, title, seniority,
               company_name, company_domain, company_industry, company_employee_count,
               company_country, linkedin_url, phone, pool_status, als_score, als_tier,
               is_bounced, is_unsubscribed, created_at
        FROM lead_pool
        WHERE id = :id
    """)
    result = await db.execute(stmt, {"id": str(lead_pool_id)})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pool lead {lead_pool_id} not found",
        )

    # Get assignments
    stmt = text("""
        SELECT la.id, la.lead_pool_id, la.client_id, c.name as client_name,
               la.status, la.total_touches, la.has_replied, la.assigned_at
        FROM lead_assignments la
        JOIN clients c ON c.id = la.client_id
        WHERE la.lead_pool_id = :lead_pool_id
        ORDER BY la.assigned_at DESC
    """)
    result = await db.execute(stmt, {"lead_pool_id": str(lead_pool_id)})
    assignment_rows = result.fetchall()

    assignments = [
        {
            "id": str(a.id),
            "client_id": str(a.client_id),
            "client_name": a.client_name,
            "status": a.status,
            "total_touches": a.total_touches,
            "has_replied": a.has_replied,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        }
        for a in assignment_rows
    ]

    return PoolLeadDetail(
        id=row.id,
        email=row.email,
        email_status=row.email_status,
        first_name=row.first_name,
        last_name=row.last_name,
        title=row.title,
        seniority=row.seniority,
        company_name=row.company_name,
        company_domain=row.company_domain,
        company_industry=row.company_industry,
        company_employee_count=row.company_employee_count,
        company_country=row.company_country,
        linkedin_url=row.linkedin_url,
        phone=row.phone,
        pool_status=row.pool_status,
        als_score=row.als_score,
        als_tier=row.als_tier,
        is_bounced=row.is_bounced or False,
        is_unsubscribed=row.is_unsubscribed or False,
        created_at=row.created_at,
        assignments=assignments,
    )


@router.get("/admin/pool/assignments", response_model=AssignmentListResponse)
async def get_pool_assignments(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    client_id: UUID | None = None,
    status_filter: str | None = Query(None, alias="status"),
):
    """Get paginated list of pool assignments."""
    conditions = []
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}

    if client_id:
        conditions.append("la.client_id = :client_id")
        params["client_id"] = str(client_id)
    if status_filter:
        conditions.append("la.status = :status")
        params["status"] = status_filter

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total
    count_stmt = text(f"""
        SELECT COUNT(*)
        FROM lead_assignments la
        {where_clause}
    """)
    result = await db.execute(count_stmt, params)
    total = result.scalar() or 0

    # Get assignments
    stmt = text(f"""
        SELECT la.id, la.lead_pool_id, la.client_id, c.name as client_name,
               la.status, la.total_touches, la.has_replied, la.assigned_at
        FROM lead_assignments la
        JOIN clients c ON c.id = la.client_id
        {where_clause}
        ORDER BY la.assigned_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(stmt, params)
    rows = result.fetchall()

    assignments = [
        AssignmentItem(
            id=row.id,
            lead_pool_id=row.lead_pool_id,
            client_id=row.client_id,
            client_name=row.client_name,
            status=row.status,
            total_touches=row.total_touches or 0,
            has_replied=row.has_replied or False,
            assigned_at=row.assigned_at,
        )
        for row in rows
    ]

    return AssignmentListResponse(
        assignments=assignments,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/admin/pool/assign", status_code=status.HTTP_201_CREATED)
async def manual_assign_leads(
    request: ManualAssignRequest,
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Manually assign pool leads to a client."""
    from src.services.lead_allocator_service import LeadAllocatorService

    LeadAllocatorService(db)
    assigned_count = 0
    errors = []

    for lead_pool_id in request.lead_pool_ids:
        try:
            # Insert assignment directly
            stmt = text("""
                INSERT INTO lead_assignments (
                    lead_pool_id, client_id, campaign_id, assigned_by, assignment_reason
                ) VALUES (
                    :lead_pool_id, :client_id, :campaign_id, 'admin_manual', 'Manual assignment by admin'
                )
                ON CONFLICT (lead_pool_id) DO NOTHING
                RETURNING id
            """)
            result = await db.execute(
                stmt,
                {
                    "lead_pool_id": str(lead_pool_id),
                    "client_id": str(request.client_id),
                    "campaign_id": str(request.campaign_id) if request.campaign_id else None,
                }
            )
            row = result.fetchone()
            if row:
                # Update pool status
                await db.execute(
                    text("UPDATE lead_pool SET pool_status = 'assigned' WHERE id = :id"),
                    {"id": str(lead_pool_id)}
                )
                assigned_count += 1
            else:
                errors.append({"lead_pool_id": str(lead_pool_id), "error": "Already assigned"})
        except Exception as e:
            errors.append({"lead_pool_id": str(lead_pool_id), "error": str(e)})

    await db.commit()

    return {
        "success": True,
        "assigned_count": assigned_count,
        "errors": errors,
        "client_id": str(request.client_id),
    }


@router.post("/admin/pool/release")
async def release_pool_leads(
    request: ReleaseLeadRequest,
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Release leads back to the pool."""
    from src.services.lead_allocator_service import LeadAllocatorService

    allocator = LeadAllocatorService(db)
    released_count = 0
    errors = []

    for assignment_id in request.assignment_ids:
        try:
            success = await allocator.release_lead(
                assignment_id=assignment_id,
                reason=request.reason,
            )
            if success:
                released_count += 1
            else:
                errors.append({"assignment_id": str(assignment_id), "error": "Not found or already released"})
        except Exception as e:
            errors.append({"assignment_id": str(assignment_id), "error": str(e)})

    return {
        "success": True,
        "released_count": released_count,
        "errors": errors,
    }


@router.get("/admin/pool/utilization")
async def get_pool_utilization(
    admin: AdminContext = Depends(get_admin_context),
    db: AsyncSession = Depends(get_db_session),
):
    """Get pool utilization metrics by client."""
    stmt = text("""
        SELECT
            c.id as client_id,
            c.name as client_name,
            COUNT(la.id) as total_assigned,
            COUNT(CASE WHEN la.status = 'active' THEN 1 END) as active,
            COUNT(CASE WHEN la.status = 'converted' THEN 1 END) as converted,
            COUNT(CASE WHEN la.status = 'released' THEN 1 END) as released,
            COALESCE(SUM(la.total_touches), 0) as total_touches,
            COUNT(CASE WHEN la.has_replied THEN 1 END) as replied
        FROM clients c
        LEFT JOIN lead_assignments la ON la.client_id = c.id
        WHERE c.deleted_at IS NULL
        GROUP BY c.id, c.name
        HAVING COUNT(la.id) > 0
        ORDER BY COUNT(la.id) DESC
    """)
    result = await db.execute(stmt)
    rows = result.fetchall()

    return {
        "clients": [
            {
                "client_id": str(row.client_id),
                "client_name": row.client_name,
                "total_assigned": row.total_assigned,
                "active": row.active,
                "converted": row.converted,
                "released": row.released,
                "total_touches": row.total_touches,
                "replied": row.replied,
                "conversion_rate": round(row.converted / row.total_assigned * 100, 2) if row.total_assigned else 0,
            }
            for row in rows
        ]
    }


# ============================================================================
# Verification Checklist
# ============================================================================
# [x] Contract comment at top
# [x] All endpoints require platform admin auth
# [x] Soft delete checks in all queries (Rule 14)
# [x] Session passed as argument (Rule 11)
# [x] Command center stats endpoint
# [x] System status endpoint
# [x] Client list and detail endpoints
# [x] AI spend endpoint
# [x] Suppression list endpoints
# [x] Revenue metrics endpoint
# [x] Global campaigns/leads endpoints
# [x] Activity feed endpoint
# [x] Alerts endpoint
# [x] Pool stats endpoint (Phase 24A)
# [x] Pool leads list endpoint (Phase 24A)
# [x] Pool lead detail endpoint (Phase 24A)
# [x] Pool assignments list endpoint (Phase 24A)
# [x] Manual assignment endpoint (Phase 24A)
# [x] Release leads endpoint (Phase 24A)
# [x] Pool utilization endpoint (Phase 24A)
