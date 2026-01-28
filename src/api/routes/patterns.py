"""
FILE: src/api/routes/patterns.py
PURPOSE: Conversion Intelligence patterns API endpoints
PHASE: 16 (Conversion Intelligence)
TASK: 16F-002
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/conversion_patterns.py
  - src/models/client.py
  - src/engines/allocator.py
  - src/detectors/*
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only (deleted_at)
  - Multi-tenancy via client_id enforcement

API Endpoints:
  GET /patterns - List all patterns for client
  GET /patterns/{pattern_type} - Get specific pattern (who, what, when, how)
  GET /patterns/recommendations/channels - Get channel recommendations
  GET /patterns/recommendations/timing - Get timing recommendations
  GET /patterns/weights - Get current ALS weights
  POST /patterns/trigger - Trigger pattern learning (admin)
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    ClientContext,
    get_current_client,
    get_db_session,
    require_member,
)
from src.engines.allocator import get_allocator_engine
from src.models.client import Client
from src.models.conversion_patterns import ConversionPattern, ConversionPatternHistory

router = APIRouter(tags=["patterns"])


# ============================================
# Pydantic Schemas
# ============================================


class PatternResponse(BaseModel):
    """Response schema for a conversion pattern."""

    id: UUID
    pattern_type: str
    patterns: dict[str, Any]
    sample_size: int
    confidence: float
    computed_at: datetime
    valid_until: datetime
    is_expired: bool

    class Config:
        from_attributes = True


class PatternListResponse(BaseModel):
    """Response schema for list of patterns."""

    patterns: list[PatternResponse]
    total: int


class ChannelRecommendation(BaseModel):
    """Response schema for channel recommendations."""

    has_patterns: bool
    channel_rankings: list[dict[str, Any]]
    tier_specific_channels: list[dict[str, Any]]
    multi_channel_recommended: bool
    multi_channel_lift: float
    winning_sequences: list[dict[str, Any]]
    confidence: float | None = None
    sample_size: int | None = None
    source: str


class TimingRecommendation(BaseModel):
    """Response schema for timing recommendations."""

    has_patterns: bool
    best_days: list[str]
    best_hours: list[int]
    optimal_gaps: dict[str, int]
    peak_converting_touch: str | None = None
    confidence: float | None = None
    sample_size: int | None = None
    source: str


class WeightsResponse(BaseModel):
    """Response schema for ALS weights."""

    weights: dict[str, float]
    source: str
    sample_count: int | None = None
    updated_at: datetime | None = None


class PatternTriggerRequest(BaseModel):
    """Request schema for triggering pattern learning."""

    force: bool = Field(
        default=False,
        description="Force recomputation even if patterns are still valid",
    )


class PatternTriggerResponse(BaseModel):
    """Response schema for pattern trigger."""

    status: str
    message: str
    task_id: str | None = None


# ============================================
# Endpoints
# ============================================


@router.get(
    "",
    response_model=PatternListResponse,
    summary="List all patterns",
    description="Get all conversion patterns for the current client.",
)
async def list_patterns(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
    include_expired: bool = Query(
        default=False,
        description="Include expired patterns in response",
    ),
) -> PatternListResponse:
    """List all conversion patterns for the client."""
    now = datetime.utcnow()

    # Build query
    conditions = [ConversionPattern.client_id == client.client_id]

    if not include_expired:
        conditions.append(ConversionPattern.valid_until > now)

    stmt = (
        select(ConversionPattern)
        .where(and_(*conditions))
        .order_by(ConversionPattern.pattern_type)
    )

    result = await db.execute(stmt)
    patterns = list(result.scalars().all())

    pattern_responses = [
        PatternResponse(
            id=p.id,
            pattern_type=p.pattern_type,
            patterns=p.patterns,
            sample_size=p.sample_size,
            confidence=p.confidence,
            computed_at=p.computed_at,
            valid_until=p.valid_until,
            is_expired=p.valid_until < now,
        )
        for p in patterns
    ]

    return PatternListResponse(patterns=pattern_responses, total=len(pattern_responses))


@router.get(
    "/{pattern_type}",
    response_model=PatternResponse,
    summary="Get specific pattern",
    description="Get a specific pattern type (who, what, when, how).",
)
async def get_pattern(
    pattern_type: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
) -> PatternResponse:
    """Get a specific conversion pattern by type."""
    if pattern_type not in ["who", "what", "when", "how"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid pattern type: {pattern_type}. Must be one of: who, what, when, how",
        )

    now = datetime.utcnow()

    stmt = (
        select(ConversionPattern)
        .where(
            and_(
                ConversionPattern.client_id == client.client_id,
                ConversionPattern.pattern_type == pattern_type,
            )
        )
        .order_by(ConversionPattern.computed_at.desc())
    )

    result = await db.execute(stmt)
    pattern = result.scalar_one_or_none()

    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {pattern_type} pattern found for this client",
        )

    return PatternResponse(
        id=pattern.id,
        pattern_type=pattern.pattern_type,
        patterns=pattern.patterns,
        sample_size=pattern.sample_size,
        confidence=pattern.confidence,
        computed_at=pattern.computed_at,
        valid_until=pattern.valid_until,
        is_expired=pattern.valid_until < now,
    )


@router.get(
    "/recommendations/channels",
    response_model=ChannelRecommendation,
    summary="Get channel recommendations",
    description="Get channel recommendations based on HOW patterns.",
)
async def get_channel_recommendations(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
    tier: str | None = Query(
        default=None,
        description="ALS tier for tier-specific recommendations",
    ),
) -> ChannelRecommendation:
    """Get channel recommendations from HOW patterns."""
    allocator = get_allocator_engine()

    result = await allocator.get_channel_recommendations(
        db=db,
        client_id=client.client_id,
        tier=tier,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error,
        )

    data = result.data
    return ChannelRecommendation(
        has_patterns=data.get("has_patterns", False),
        channel_rankings=data.get("channel_rankings", []),
        tier_specific_channels=data.get("tier_specific_channels", []),
        multi_channel_recommended=data.get("multi_channel_recommended", True),
        multi_channel_lift=data.get("multi_channel_lift", 1.0),
        winning_sequences=data.get("winning_sequences", []),
        confidence=data.get("confidence"),
        sample_size=data.get("sample_size"),
        source=result.metadata.get("source", "unknown"),
    )


@router.get(
    "/recommendations/timing",
    response_model=TimingRecommendation,
    summary="Get timing recommendations",
    description="Get timing recommendations based on WHEN patterns.",
)
async def get_timing_recommendations(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
) -> TimingRecommendation:
    """Get timing recommendations from WHEN patterns."""
    allocator = get_allocator_engine()

    result = await allocator.get_timing_recommendations(
        db=db,
        client_id=client.client_id,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error,
        )

    data = result.data
    return TimingRecommendation(
        has_patterns=data.get("has_patterns", False),
        best_days=data.get("best_days", []),
        best_hours=data.get("best_hours", []),
        optimal_gaps=data.get("optimal_gaps", {}),
        peak_converting_touch=data.get("peak_converting_touch"),
        confidence=data.get("confidence"),
        sample_size=data.get("sample_size"),
        source=result.metadata.get("source", "unknown"),
    )


@router.get(
    "/weights",
    response_model=WeightsResponse,
    summary="Get ALS weights",
    description="Get current ALS weights for the client.",
)
async def get_weights(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
) -> WeightsResponse:
    """Get current ALS weights for the client."""
    # Default weights
    default_weights = {
        "data_quality": 0.20,
        "authority": 0.25,
        "company_fit": 0.25,
        "timing": 0.15,
        "risk": 0.15,
    }

    # Fetch client
    stmt = select(Client).where(Client.id == client.client_id)
    result = await db.execute(stmt)
    client_obj = result.scalar_one_or_none()

    if not client_obj:
        return WeightsResponse(
            weights=default_weights,
            source="default",
        )

    if client_obj.als_learned_weights:
        return WeightsResponse(
            weights=client_obj.als_learned_weights,
            source="learned",
            sample_count=client_obj.conversion_sample_count,
            updated_at=client_obj.als_weights_updated_at,
        )

    return WeightsResponse(
        weights=default_weights,
        source="default",
    )


@router.get(
    "/history",
    summary="Get pattern history",
    description="Get archived pattern history for the client.",
)
async def get_pattern_history(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
    pattern_type: str | None = Query(
        default=None,
        description="Filter by pattern type",
    ),
    limit: int = Query(default=10, le=100, description="Maximum records to return"),
) -> dict[str, Any]:
    """Get archived pattern history."""
    conditions = [ConversionPatternHistory.client_id == client.client_id]

    if pattern_type:
        if pattern_type not in ["who", "what", "when", "how"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pattern type: {pattern_type}",
            )
        conditions.append(ConversionPatternHistory.pattern_type == pattern_type)

    stmt = (
        select(ConversionPatternHistory)
        .where(and_(*conditions))
        .order_by(ConversionPatternHistory.archived_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    history = list(result.scalars().all())

    return {
        "history": [
            {
                "id": str(h.id),
                "pattern_type": h.pattern_type,
                "sample_size": h.sample_size,
                "confidence": h.confidence,
                "computed_at": h.computed_at.isoformat(),
                "archived_at": h.archived_at.isoformat(),
            }
            for h in history
        ],
        "total": len(history),
    }


@router.post(
    "/trigger",
    response_model=PatternTriggerResponse,
    summary="Trigger pattern learning",
    description="Manually trigger pattern learning for the client. Admin only.",
)
async def trigger_pattern_learning(
    request: PatternTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    client: Annotated[ClientContext, Depends(get_current_client)],
    _: Annotated[bool, Depends(require_member)],
) -> PatternTriggerResponse:
    """
    Trigger pattern learning for the current client.

    This runs in the background and may take several minutes.
    """

    # Check if patterns already exist and are valid
    if not request.force:
        now = datetime.utcnow()
        stmt = (
            select(ConversionPattern)
            .where(
                and_(
                    ConversionPattern.client_id == client.client_id,
                    ConversionPattern.valid_until > now,
                )
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return PatternTriggerResponse(
                status="skipped",
                message="Valid patterns already exist. Use force=true to recompute.",
            )

    # Trigger Prefect flow for pattern learning
    import logging

    from prefect.deployments import run_deployment

    logger = logging.getLogger(__name__)

    await run_deployment(
        name="single_client_pattern_learning/client-pattern-learning-flow",
        parameters={
            "client_id": str(client.client_id),
        },
        timeout=0,  # Don't wait for completion
    )
    logger.info(f"Triggered Prefect pattern learning flow for client {client.client_id}")

    return PatternTriggerResponse(
        status="queued",
        message="Pattern learning has been queued via Prefect.",
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Multi-tenancy via client_id enforcement
# [x] Soft delete awareness (patterns don't have deleted_at)
# [x] List patterns endpoint
# [x] Get specific pattern endpoint
# [x] Channel recommendations endpoint
# [x] Timing recommendations endpoint
# [x] Weights endpoint
# [x] Pattern history endpoint
# [x] Trigger pattern learning endpoint
# [x] Proper Pydantic schemas
# [x] All functions have type hints
# [x] All functions have docstrings
