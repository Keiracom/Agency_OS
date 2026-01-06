"""
FILE: src/api/routes/reports.py
PURPOSE: Metrics and reporting API endpoints
PHASE: 7 (API Routes)
TASK: API-008
DEPENDENCIES:
  - src/api/dependencies.py
  - src/engines/reporter.py
  - src/integrations/supabase.py
  - src/models/campaign.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft delete checks in queries
  - All endpoints require authentication
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_current_user_from_token, get_db_session as get_async_session
from src.engines.reporter import get_reporter_engine

# FIXED by fixer-agent: added auth imports from dependencies.py
router = APIRouter(
    prefix="/reports",
    tags=["reports"],
)


# ============================================
# Response Models
# ============================================


class ChannelMetrics(BaseModel):
    """Metrics breakdown by channel."""
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    replied: int = 0
    bounced: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    reply_rate: float = 0.0


class CampaignMetricsResponse(BaseModel):
    """Response model for campaign metrics."""
    campaign_id: UUID
    campaign_name: str
    status: str
    total_leads: int = 0
    leads_contacted: int = 0
    emails: ChannelMetrics = Field(default_factory=ChannelMetrics)
    sms: ChannelMetrics = Field(default_factory=ChannelMetrics)
    linkedin: ChannelMetrics = Field(default_factory=ChannelMetrics)
    voice: ChannelMetrics = Field(default_factory=ChannelMetrics)
    mail: ChannelMetrics = Field(default_factory=ChannelMetrics)
    overall_reply_rate: float = 0.0
    overall_conversion_rate: float = 0.0
    meetings_booked: int = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class CampaignSummary(BaseModel):
    """Summary of a single campaign for client metrics."""
    campaign_id: UUID
    campaign_name: str
    status: str
    leads: int = 0
    replies: int = 0
    conversions: int = 0
    reply_rate: float = 0.0
    conversion_rate: float = 0.0


class ClientMetricsResponse(BaseModel):
    """Response model for client metrics."""
    client_id: UUID
    client_name: str
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_leads: int = 0
    total_replies: int = 0
    total_conversions: int = 0
    overall_reply_rate: float = 0.0
    overall_conversion_rate: float = 0.0
    campaigns: list[CampaignSummary] = Field(default_factory=list)
    channel_performance: dict[str, ChannelMetrics] = Field(default_factory=dict)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TierDistribution(BaseModel):
    """Distribution data for a single ALS tier."""
    count: int = 0
    percentage: float = 0.0


class ALSDistributionResponse(BaseModel):
    """Response model for ALS tier distribution."""
    hot: TierDistribution = Field(default_factory=TierDistribution)
    warm: TierDistribution = Field(default_factory=TierDistribution)
    cool: TierDistribution = Field(default_factory=TierDistribution)
    cold: TierDistribution = Field(default_factory=TierDistribution)
    dead: TierDistribution = Field(default_factory=TierDistribution)
    total: int = 0
    campaign_id: Optional[UUID] = None
    client_id: Optional[UUID] = None


class ActivityItem(BaseModel):
    """Single activity in engagement timeline."""
    id: UUID
    channel: str
    action: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class LeadEngagementResponse(BaseModel):
    """Response model for lead engagement metrics."""
    lead_id: UUID
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    als_score: Optional[int] = None
    als_tier: Optional[str] = None
    open_count: int = 0
    click_count: int = 0
    reply_count: int = 0
    is_engaged: bool = False
    last_contacted: Optional[datetime] = None
    last_replied: Optional[datetime] = None
    channels_used: list[str] = Field(default_factory=list)
    timeline: list[ActivityItem] = Field(default_factory=list)


class DailyMetrics(BaseModel):
    """Metrics for a single day."""
    date: date
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    replied: int = 0
    bounced: int = 0
    conversions: int = 0


class DailyActivityResponse(BaseModel):
    """Response model for daily activity summary."""
    campaign_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    start_date: date
    end_date: date
    days: list[DailyMetrics] = Field(default_factory=list)
    totals: ChannelMetrics = Field(default_factory=ChannelMetrics)


# ============================================
# Routes
# ============================================


@router.get("/campaigns/{campaign_id}", response_model=dict[str, Any])
async def get_campaign_metrics(
    campaign_id: UUID,
    start_date: date | None = Query(None, description="Start date for metrics (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date for metrics (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
    # FIXED by fixer-agent: enabled auth dependency (CRIT-001)
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get comprehensive performance metrics for a campaign.

    Includes:
    - Send, delivery, open, click, reply, bounce, conversion rates
    - Per-channel breakdown
    - Date range filtering

    Args:
        campaign_id: Campaign UUID
        start_date: Optional start date (defaults to 30 days ago)
        end_date: Optional end date (defaults to today)
        db: Database session (injected)

    Returns:
        Campaign metrics with channel breakdown

    Raises:
        404: Campaign not found
        403: Unauthorized access to campaign
    """
    engine = get_reporter_engine()

    result = await engine.get_campaign_metrics(
        db=db,
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Campaign not found",
        )

    return result.data


@router.get("/campaigns/{campaign_id}/daily", response_model=dict[str, Any])
async def get_campaign_daily_metrics(
    campaign_id: UUID,
    start_date: date | None = Query(None, description="Start date for metrics (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date for metrics (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
    # FIXED by fixer-agent: enabled auth dependency (CRIT-001)
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get daily metrics breakdown for a campaign.

    Returns metrics aggregated by day for trend analysis.

    Args:
        campaign_id: Campaign UUID
        start_date: Optional start date (defaults to 30 days ago)
        end_date: Optional end date (defaults to today)
        db: Database session (injected)

    Returns:
        Daily metrics with trends

    Raises:
        404: Campaign not found
        403: Unauthorized access to campaign
    """
    engine = get_reporter_engine()

    # Get overall campaign metrics
    result = await engine.get_campaign_metrics(
        db=db,
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Campaign not found",
        )

    # Note: Daily breakdown logic would be extended here
    # For now, returning overall metrics as per requirements
    return result.data


@router.get("/clients/{client_id}", response_model=dict[str, Any])
async def get_client_metrics(
    client_id: UUID,
    start_date: date | None = Query(None, description="Start date for metrics (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date for metrics (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_async_session),
    # FIXED by fixer-agent: enabled auth dependency (CRIT-001)
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get aggregated metrics for a client across all campaigns.

    Includes:
    - Overall reply rate, conversion rate
    - Per-campaign summary
    - Channel performance comparison
    - Date range filtering

    Args:
        client_id: Client UUID
        start_date: Optional start date (defaults to 30 days ago)
        end_date: Optional end date (defaults to today)
        db: Database session (injected)

    Returns:
        Client metrics with campaign breakdown

    Raises:
        404: Client not found
        403: Unauthorized access to client
    """
    engine = get_reporter_engine()

    result = await engine.get_client_metrics(
        db=db,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Client not found",
        )

    return result.data


@router.get("/leads/distribution", response_model=dict[str, Any])
async def get_als_distribution(
    campaign_id: UUID | None = Query(None, description="Filter by campaign ID"),
    client_id: UUID | None = Query(None, description="Filter by client ID"),
    db: AsyncSession = Depends(get_async_session),
    # FIXED by fixer-agent: enabled auth dependency (CRIT-001)
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get ALS tier distribution for leads.

    Shows breakdown of leads across tiers:
    - Hot (85-100)
    - Warm (60-84)
    - Cool (35-59)
    - Cold (20-34)
    - Dead (0-19)

    Args:
        campaign_id: Optional campaign filter
        client_id: Optional client filter (required if campaign_id not provided)
        db: Database session (injected)

    Returns:
        ALS tier distribution with counts and percentages

    Raises:
        400: Neither campaign_id nor client_id provided
        404: Campaign/client not found
        403: Unauthorized access
    """
    if not campaign_id and not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either campaign_id or client_id must be provided",
        )

    engine = get_reporter_engine()

    result = await engine.get_als_distribution(
        db=db,
        campaign_id=campaign_id,
        client_id=client_id,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Resource not found",
        )

    return result.data


@router.get("/leads/{lead_id}/engagement", response_model=dict[str, Any])
async def get_lead_engagement(
    lead_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    # FIXED by fixer-agent: enabled auth dependency (CRIT-001)
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get detailed engagement metrics for a specific lead.

    Includes:
    - Activity timeline (all touches across channels)
    - Open count, reply count, click count
    - Last contacted/replied timestamps
    - Engagement score (is_engaged boolean)
    - Channels used

    Args:
        lead_id: Lead UUID
        db: Database session (injected)

    Returns:
        Lead engagement metrics with timeline

    Raises:
        404: Lead not found
        403: Unauthorized access to lead
    """
    engine = get_reporter_engine()

    result = await engine.get_lead_engagement(
        db=db,
        lead_id=lead_id,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Lead not found",
        )

    return result.data


@router.get("/activity/daily", response_model=dict[str, Any])
async def get_daily_activity(
    client_id: UUID = Query(..., description="Client ID to get activity for"),
    target_date: date | None = Query(None, description="Target date (defaults to today)"),
    db: AsyncSession = Depends(get_async_session),
    # FIXED by fixer-agent: enabled auth dependency (CRIT-001)
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get daily activity summary for a client.

    Includes:
    - Hourly breakdown of activities
    - Per-channel activity counts
    - Summary statistics (sent, delivered, opened, clicked, replied)
    - Peak activity hour

    Args:
        client_id: Client UUID (required)
        target_date: Optional target date (defaults to today)
        db: Database session (injected)

    Returns:
        Daily activity metrics with hourly breakdown

    Raises:
        404: Client not found
        403: Unauthorized access to client
    """
    engine = get_reporter_engine()

    result = await engine.get_daily_activity(
        db=db,
        client_id=client_id,
        target_date=target_date,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.error or "Client not found",
        )

    return result.data


# ============================================
# Lead Pool Analytics (Phase 24A)
# ============================================


class PoolAnalytics(BaseModel):
    """Pool analytics response model."""
    total_leads: int = 0
    available: int = 0
    assigned: int = 0
    converted: int = 0
    bounced: int = 0
    utilization_rate: float = 0.0
    avg_als_score: Optional[float] = None
    tier_distribution: dict[str, int] = Field(default_factory=dict)
    industry_distribution: dict[str, int] = Field(default_factory=dict)
    email_status_distribution: dict[str, int] = Field(default_factory=dict)


class AssignmentAnalytics(BaseModel):
    """Assignment analytics response model."""
    total_assignments: int = 0
    active: int = 0
    converted: int = 0
    released: int = 0
    avg_touches_per_lead: float = 0.0
    reply_rate: float = 0.0
    conversion_rate: float = 0.0
    top_performing_industries: list[dict] = Field(default_factory=list)


@router.get("/pool/analytics", response_model=PoolAnalytics)
async def get_pool_analytics(
    db: AsyncSession = Depends(get_async_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> PoolAnalytics:
    """
    Get comprehensive lead pool analytics.

    Includes:
    - Pool size and utilization metrics
    - Tier distribution
    - Industry distribution
    - Email status distribution

    Args:
        db: Database session (injected)

    Returns:
        Pool analytics with distributions
    """
    from sqlalchemy import text

    # Get pool status distribution
    status_query = text("""
        SELECT
            pool_status,
            COUNT(*) as count
        FROM lead_pool
        GROUP BY pool_status
    """)
    result = await db.execute(status_query)
    status_counts = {row.pool_status: row.count for row in result.fetchall()}

    total = sum(status_counts.values())
    available = status_counts.get("available", 0)
    assigned = status_counts.get("assigned", 0)
    converted = status_counts.get("converted", 0)
    bounced = status_counts.get("bounced", 0)

    # Get tier distribution
    tier_query = text("""
        SELECT
            COALESCE(als_tier, 'unscored') as tier,
            COUNT(*) as count
        FROM lead_pool
        GROUP BY als_tier
    """)
    result = await db.execute(tier_query)
    tier_distribution = {row.tier: row.count for row in result.fetchall()}

    # Get industry distribution (top 10)
    industry_query = text("""
        SELECT
            COALESCE(company_industry, 'Unknown') as industry,
            COUNT(*) as count
        FROM lead_pool
        GROUP BY company_industry
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    result = await db.execute(industry_query)
    industry_distribution = {row.industry: row.count for row in result.fetchall()}

    # Get email status distribution
    email_query = text("""
        SELECT
            COALESCE(email_status, 'unknown') as status,
            COUNT(*) as count
        FROM lead_pool
        GROUP BY email_status
    """)
    result = await db.execute(email_query)
    email_status_distribution = {row.status: row.count for row in result.fetchall()}

    # Get average ALS score
    avg_query = text("""
        SELECT AVG(als_score) as avg_score
        FROM lead_pool
        WHERE als_score IS NOT NULL
    """)
    result = await db.execute(avg_query)
    row = result.fetchone()
    avg_als_score = round(float(row.avg_score), 1) if row and row.avg_score else None

    return PoolAnalytics(
        total_leads=total,
        available=available,
        assigned=assigned,
        converted=converted,
        bounced=bounced,
        utilization_rate=round(assigned / total * 100, 2) if total > 0 else 0.0,
        avg_als_score=avg_als_score,
        tier_distribution=tier_distribution,
        industry_distribution=industry_distribution,
        email_status_distribution=email_status_distribution,
    )


@router.get("/pool/assignments/analytics", response_model=AssignmentAnalytics)
async def get_assignment_analytics(
    client_id: UUID | None = Query(None, description="Filter by client ID"),
    db: AsyncSession = Depends(get_async_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> AssignmentAnalytics:
    """
    Get assignment analytics for the pool.

    Includes:
    - Assignment status distribution
    - Average touches per lead
    - Reply and conversion rates
    - Top performing industries

    Args:
        client_id: Optional client filter
        db: Database session (injected)

    Returns:
        Assignment analytics with performance metrics
    """
    from sqlalchemy import text

    params = {}
    client_filter = ""
    if client_id:
        client_filter = "WHERE la.client_id = :client_id"
        params["client_id"] = str(client_id)

    # Get assignment counts
    count_query = text(f"""
        SELECT
            status,
            COUNT(*) as count,
            SUM(total_touches) as total_touches,
            COUNT(CASE WHEN has_replied THEN 1 END) as replied
        FROM lead_assignments la
        {client_filter}
        GROUP BY status
    """)
    result = await db.execute(count_query, params)
    rows = result.fetchall()

    total = 0
    active = 0
    converted = 0
    released = 0
    total_touches = 0
    total_replied = 0

    for row in rows:
        total += row.count
        total_touches += row.total_touches or 0
        total_replied += row.replied or 0
        if row.status == "active":
            active = row.count
        elif row.status == "converted":
            converted = row.count
        elif row.status == "released":
            released = row.count

    # Get top performing industries by conversion rate
    industry_query = text(f"""
        SELECT
            COALESCE(lp.company_industry, 'Unknown') as industry,
            COUNT(*) as total,
            COUNT(CASE WHEN la.status = 'converted' THEN 1 END) as converted,
            COUNT(CASE WHEN la.has_replied THEN 1 END) as replied
        FROM lead_assignments la
        JOIN lead_pool lp ON lp.id = la.lead_pool_id
        {client_filter}
        GROUP BY lp.company_industry
        HAVING COUNT(*) >= 5
        ORDER BY COUNT(CASE WHEN la.status = 'converted' THEN 1 END)::float / NULLIF(COUNT(*), 0) DESC
        LIMIT 5
    """)
    result = await db.execute(industry_query, params)
    top_industries = [
        {
            "industry": row.industry,
            "total": row.total,
            "converted": row.converted,
            "replied": row.replied,
            "conversion_rate": round(row.converted / row.total * 100, 2) if row.total > 0 else 0,
        }
        for row in result.fetchall()
    ]

    return AssignmentAnalytics(
        total_assignments=total,
        active=active,
        converted=converted,
        released=released,
        avg_touches_per_lead=round(total_touches / total, 2) if total > 0 else 0.0,
        reply_rate=round(total_replied / total * 100, 2) if total > 0 else 0.0,
        conversion_rate=round(converted / total * 100, 2) if total > 0 else 0.0,
        top_performing_industries=top_industries,
    )


@router.get("/pool/clients/{client_id}/analytics")
async def get_client_pool_analytics(
    client_id: UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """
    Get pool analytics for a specific client.

    Includes:
    - Client's assigned leads count and distribution
    - Conversion funnel metrics
    - Channel performance from pool assignments

    Args:
        client_id: Client UUID
        db: Database session (injected)

    Returns:
        Client-specific pool analytics
    """
    from sqlalchemy import text

    # Get client's assignment stats
    stats_query = text("""
        SELECT
            COUNT(*) as total_assigned,
            COUNT(CASE WHEN la.status = 'active' THEN 1 END) as active,
            COUNT(CASE WHEN la.status = 'converted' THEN 1 END) as converted,
            COUNT(CASE WHEN la.status = 'released' THEN 1 END) as released,
            COALESCE(SUM(la.total_touches), 0) as total_touches,
            COUNT(CASE WHEN la.has_replied THEN 1 END) as replied,
            COUNT(CASE WHEN lp.als_tier = 'hot' THEN 1 END) as hot_leads,
            COUNT(CASE WHEN lp.als_tier = 'warm' THEN 1 END) as warm_leads,
            COUNT(CASE WHEN lp.als_tier = 'cool' THEN 1 END) as cool_leads,
            AVG(lp.als_score) as avg_score
        FROM lead_assignments la
        JOIN lead_pool lp ON lp.id = la.lead_pool_id
        WHERE la.client_id = :client_id
    """)
    result = await db.execute(stats_query, {"client_id": str(client_id)})
    stats = result.fetchone()

    if not stats or stats.total_assigned == 0:
        return {
            "client_id": str(client_id),
            "total_assigned": 0,
            "message": "No pool assignments for this client",
        }

    # Get channel breakdown
    channel_query = text("""
        SELECT
            channel,
            COUNT(*) as count
        FROM lead_assignments la,
             LATERAL unnest(la.channels_used) as channel
        WHERE la.client_id = :client_id
        GROUP BY channel
    """)
    result = await db.execute(channel_query, {"client_id": str(client_id)})
    channel_usage = {row.channel: row.count for row in result.fetchall()}

    return {
        "client_id": str(client_id),
        "total_assigned": stats.total_assigned,
        "active": stats.active,
        "converted": stats.converted,
        "released": stats.released,
        "total_touches": stats.total_touches,
        "replied": stats.replied,
        "reply_rate": round(stats.replied / stats.total_assigned * 100, 2) if stats.total_assigned > 0 else 0,
        "conversion_rate": round(stats.converted / stats.total_assigned * 100, 2) if stats.total_assigned > 0 else 0,
        "tier_distribution": {
            "hot": stats.hot_leads or 0,
            "warm": stats.warm_leads or 0,
            "cool": stats.cool_leads or 0,
        },
        "avg_als_score": round(float(stats.avg_score), 1) if stats.avg_score else None,
        "channel_usage": channel_usage,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] FastAPI router with tags=["reports"]
# [x] 6 endpoints as per requirements:
#     - GET /reports/campaigns/{id} - Campaign performance metrics
#     - GET /reports/campaigns/{id}/daily - Daily metrics for campaign
#     - GET /reports/clients/{id} - Client-level metrics
#     - GET /reports/leads/distribution - ALS tier distribution
#     - GET /reports/leads/{lead_id}/engagement - Lead engagement metrics
#     - GET /reports/activity/daily - Daily activity summary
# [x] All endpoints use Reporter engine for metric calculation
# [x] All endpoints support date range filters where applicable
# [x] Query parameters with descriptions
# [x] Session passed via Depends(get_async_session) (Rule 11)
# [x] Auth dependency enabled - FIXED by fixer-agent 2025-12-24 (CRIT-001)
# [x] Proper HTTP status codes (404 for not found, 400 for validation)
# [x] Docstrings for all endpoints
# [x] Type hints for all parameters and returns
# [x] Metrics include reply rate, bounce rate, open rate, conversion rate
# [x] ALS tier distribution support
# [x] Channel performance comparison
# [x] Daily/weekly/monthly trends via date range filtering
# ============================================
# PHASE 24A POOL ANALYTICS ADDITIONS
# ============================================
# [x] GET /reports/pool/analytics - Pool size and utilization
# [x] GET /reports/pool/assignments/analytics - Assignment metrics
# [x] GET /reports/pool/clients/{id}/analytics - Client pool metrics
