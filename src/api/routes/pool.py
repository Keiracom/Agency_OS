"""
FILE: src/api/routes/pool.py
PURPOSE: Lead pool management endpoints - population and stats
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-013 (Gap fix - pool population API)
DEPENDENCIES:
  - src/api/dependencies.py
  - src/orchestration/flows/pool_population_flow.py
  - src/services/lead_pool_service.py
RULES APPLIED:
  - Rule 12: LAYER 5 - Top layer, can import from everything below
  - Rule 14: Soft deletes only
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.dependencies import CurrentUser, get_current_user_from_token
from src.integrations.supabase import get_db_session
from src.services.lead_pool_service import LeadPoolService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pool", tags=["pool"])


# ============================================
# SCHEMAS
# ============================================


class PoolPopulateRequest(BaseModel):
    """Request to populate the lead pool."""

    limit: int = Field(default=25, ge=1, le=100, description="Max leads to add")


class PoolPopulateResponse(BaseModel):
    """Response from pool population."""

    success: bool
    message: str
    job_status: str = "queued"
    client_id: str
    limit: int


class PoolStatsResponse(BaseModel):
    """Lead pool statistics."""

    total_leads: int
    available: int
    assigned: int
    converted: int
    tier_distribution: dict[str, int]


# ============================================
# BACKGROUND TASK
# ============================================


async def run_pool_population(client_id: UUID, limit: int):
    """
    Background task to run pool population flow.

    Args:
        client_id: Client UUID
        limit: Max leads to add
    """
    from src.orchestration.flows.pool_population_flow import pool_population_flow

    try:
        logger.info(f"Starting pool population for client {client_id}")
        result = await pool_population_flow(client_id=client_id, limit=limit)
        logger.info(
            f"Pool population completed for client {client_id}: "
            f"{result.get('leads_added', 0)} leads added"
        )
    except Exception as e:
        logger.error(f"Pool population failed for client {client_id}: {e}")


# ============================================
# ENDPOINTS
# ============================================


@router.post(
    "/populate",
    response_model=PoolPopulateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def populate_pool(
    request: PoolPopulateRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user_from_token),
) -> PoolPopulateResponse:
    """
    Trigger pool population from Apollo for the current user's client.

    This searches Apollo for leads matching the client's ICP and adds
    them to the lead pool. Runs asynchronously in background.

    - **limit**: Maximum number of leads to add (1-100, default 25)
    """
    from sqlalchemy import text

    # Get client_id for the user
    async with get_db_session() as db:
        # Get client_id from user's membership
        stmt = text("""
            SELECT client_id FROM memberships
            WHERE user_id = :user_id AND deleted_at IS NULL
            LIMIT 1
        """)
        result = await db.execute(stmt, {"user_id": user.id})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No client found for user",
            )

        client_id = row.client_id

    # Queue background task
    background_tasks.add_task(run_pool_population, client_id, request.limit)

    logger.info(f"Pool population queued for client {client_id}, limit={request.limit}")

    return PoolPopulateResponse(
        success=True,
        message=f"Pool population started with limit {request.limit}",
        job_status="queued",
        client_id=str(client_id),
        limit=request.limit,
    )


@router.post(
    "/clients/{client_id}/populate",
    response_model=PoolPopulateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def populate_pool_for_client(
    client_id: UUID,
    request: PoolPopulateRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user_from_token),
) -> PoolPopulateResponse:
    """
    Trigger pool population for a specific client (admin/agency use).

    This searches Apollo for leads matching the client's ICP and adds
    them to the lead pool. Runs asynchronously in background.

    - **client_id**: Target client UUID
    - **limit**: Maximum number of leads to add (1-100, default 25)
    """
    from sqlalchemy import text

    # Verify user has access to this client
    async with get_db_session() as db:
        stmt = text("""
            SELECT 1 FROM memberships
            WHERE user_id = :user_id
            AND client_id = :client_id
            AND deleted_at IS NULL
            LIMIT 1
        """)
        result = await db.execute(stmt, {"user_id": user.id, "client_id": client_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized for this client",
            )

    # Queue background task
    background_tasks.add_task(run_pool_population, client_id, request.limit)

    logger.info(f"Pool population queued for client {client_id}, limit={request.limit}")

    return PoolPopulateResponse(
        success=True,
        message=f"Pool population started with limit {request.limit}",
        job_status="queued",
        client_id=str(client_id),
        limit=request.limit,
    )


@router.get("/stats", response_model=PoolStatsResponse)
async def get_pool_stats(
    user: CurrentUser = Depends(get_current_user_from_token),
) -> PoolStatsResponse:
    """
    Get lead pool statistics.

    Returns counts of total leads, available, assigned, and converted,
    plus tier distribution.
    """
    async with get_db_session() as db:
        pool_service = LeadPoolService(db)
        stats = await pool_service.get_pool_stats()

        return PoolStatsResponse(
            total_leads=stats.get("total_leads", 0),
            available=stats.get("available", 0),
            assigned=stats.get("assigned", 0),
            converted=stats.get("converted", 0),
            tier_distribution=stats.get("tier_distribution", {}),
        )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] No hardcoded credentials
# [x] Uses get_current_user_id for auth
# [x] Uses BackgroundTasks for async processing
# [x] Proper error handling with HTTPException
# [x] Pydantic models for request/response
# [x] Logging throughout
# [x] All functions have type hints
# [x] All functions have docstrings
