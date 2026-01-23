"""
FILE: src/api/routes/digest.py
PURPOSE: API routes for daily digest settings and preview
PHASE: H (Client Transparency)
TASK: Item 44 - Daily Digest Email
DEPENDENCIES:
  - src/services/digest_service.py
  - src/models/client.py
  - src/models/digest_log.py
"""

from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_db,
    get_current_user_client_id,
)
from src.models.client import Client
from src.models.digest_log import DigestLog
from src.services.digest_service import DigestService

router = APIRouter(prefix="/digest", tags=["digest"])


# ============================================
# Request/Response Models
# ============================================


class DigestSettingsResponse(BaseModel):
    """Response model for digest settings."""

    digest_enabled: bool
    digest_frequency: str = Field(description="daily, weekly, or none")
    digest_send_hour: int = Field(ge=0, le=23, description="Hour of day (0-23)")
    digest_timezone: str
    digest_recipients: List[str] = Field(default_factory=list)
    last_digest_sent_at: Optional[str] = None


class DigestSettingsUpdate(BaseModel):
    """Request model for updating digest settings."""

    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = Field(
        None, description="daily, weekly, or none"
    )
    digest_send_hour: Optional[int] = Field(
        None, ge=0, le=23, description="Hour of day (0-23)"
    )
    digest_timezone: Optional[str] = None
    digest_recipients: Optional[List[str]] = None


class DigestPreviewResponse(BaseModel):
    """Response model for digest preview."""

    client_name: str
    digest_date: str
    metrics: dict
    top_campaigns: List[dict]
    content_samples: List[dict]
    html_preview: str


class DigestLogResponse(BaseModel):
    """Response model for digest log entry."""

    id: str
    digest_date: str
    digest_type: str
    recipients: List[str]
    status: str
    sent_at: Optional[str]
    metrics_snapshot: dict
    opened_at: Optional[str]
    clicked_at: Optional[str]


class DigestHistoryResponse(BaseModel):
    """Response model for digest history."""

    digests: List[DigestLogResponse]
    total: int


# ============================================
# Routes
# ============================================


@router.get("/settings", response_model=DigestSettingsResponse)
async def get_digest_settings(
    db: AsyncSession = Depends(get_db),
    client_id: UUID = Depends(get_current_user_client_id),
) -> DigestSettingsResponse:
    """
    Get current digest settings for the client.

    Phase H, Item 44: Daily Digest Email settings.
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return DigestSettingsResponse(
        digest_enabled=client.digest_enabled,
        digest_frequency=client.digest_frequency,
        digest_send_hour=client.digest_send_hour,
        digest_timezone=client.digest_timezone,
        digest_recipients=client.digest_recipients or [],
        last_digest_sent_at=(
            client.last_digest_sent_at.isoformat()
            if client.last_digest_sent_at
            else None
        ),
    )


@router.patch("/settings", response_model=DigestSettingsResponse)
async def update_digest_settings(
    settings_update: DigestSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    client_id: UUID = Depends(get_current_user_client_id),
) -> DigestSettingsResponse:
    """
    Update digest settings for the client.

    Phase H, Item 44: Daily Digest Email settings.
    """
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Validate frequency
    if settings_update.digest_frequency is not None:
        valid_frequencies = ["daily", "weekly", "none"]
        if settings_update.digest_frequency not in valid_frequencies:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid frequency. Must be one of: {valid_frequencies}",
            )

    # Update fields
    if settings_update.digest_enabled is not None:
        client.digest_enabled = settings_update.digest_enabled

    if settings_update.digest_frequency is not None:
        client.digest_frequency = settings_update.digest_frequency

    if settings_update.digest_send_hour is not None:
        client.digest_send_hour = settings_update.digest_send_hour

    if settings_update.digest_timezone is not None:
        client.digest_timezone = settings_update.digest_timezone

    if settings_update.digest_recipients is not None:
        client.digest_recipients = settings_update.digest_recipients

    await db.commit()
    await db.refresh(client)

    return DigestSettingsResponse(
        digest_enabled=client.digest_enabled,
        digest_frequency=client.digest_frequency,
        digest_send_hour=client.digest_send_hour,
        digest_timezone=client.digest_timezone,
        digest_recipients=client.digest_recipients or [],
        last_digest_sent_at=(
            client.last_digest_sent_at.isoformat()
            if client.last_digest_sent_at
            else None
        ),
    )


@router.get("/preview", response_model=DigestPreviewResponse)
async def preview_digest(
    digest_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    client_id: UUID = Depends(get_current_user_client_id),
) -> DigestPreviewResponse:
    """
    Preview what the digest would look like for a given date.

    Phase H, Item 44: Allows clients to preview digest before enabling.

    Args:
        digest_date: Date to generate preview for (defaults to yesterday)
    """
    # Default to yesterday
    if digest_date is None:
        digest_date = date.today() - timedelta(days=1)

    service = DigestService(db)

    try:
        digest_data = await service.get_digest_data(client_id, digest_date)
        html_preview = service.render_digest_html(digest_data)

        return DigestPreviewResponse(
            client_name=digest_data["client_name"],
            digest_date=digest_data["digest_date"],
            metrics=digest_data["metrics"],
            top_campaigns=digest_data["top_campaigns"],
            content_samples=digest_data["content_samples"],
            html_preview=html_preview,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history", response_model=DigestHistoryResponse)
async def get_digest_history(
    limit: int = 30,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    client_id: UUID = Depends(get_current_user_client_id),
) -> DigestHistoryResponse:
    """
    Get history of sent digests for the client.

    Phase H, Item 44: Allows clients to review past digests.
    """
    # Query digest logs
    query = (
        select(DigestLog)
        .where(DigestLog.client_id == client_id)
        .order_by(DigestLog.digest_date.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    # Get total count
    from sqlalchemy import func

    count_query = select(func.count(DigestLog.id)).where(
        DigestLog.client_id == client_id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return DigestHistoryResponse(
        digests=[
            DigestLogResponse(
                id=str(log.id),
                digest_date=log.digest_date.isoformat(),
                digest_type=log.digest_type,
                recipients=log.recipients or [],
                status=log.status,
                sent_at=log.sent_at.isoformat() if log.sent_at else None,
                metrics_snapshot=log.metrics_snapshot or {},
                opened_at=log.opened_at.isoformat() if log.opened_at else None,
                clicked_at=log.clicked_at.isoformat() if log.clicked_at else None,
            )
            for log in logs
        ],
        total=total,
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] All routes have type hints
# [x] All routes have docstrings
# [x] Request/Response models defined
# [x] Authorization via get_current_user_client_id
# [x] GET /settings - get digest preferences
# [x] PATCH /settings - update digest preferences
# [x] GET /preview - preview digest for a date
# [x] GET /history - get sent digest history
# [x] Validation for frequency values
# [x] Pagination for history endpoint
