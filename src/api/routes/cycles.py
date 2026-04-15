"""
Contract: src/api/routes/cycles.py
Purpose: Cycle pause/resume endpoints for customer-facing Pause Cycle button
Layer: 4 - api
Imports: models, dependencies
Consumers: frontend dashboard (PauseCycleButton)
Directive: #314 — Task F
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_client, get_db_session, ClientContext
from src.models.cycle import Cycle, CycleEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cycles"])


class CycleStatusResponse(BaseModel):
    id: str
    status: str
    client_id: str


async def get_cycle_or_404(
    cycle_id: UUID,
    client_id: UUID,
    db: AsyncSession,
) -> Cycle:
    result = await db.execute(
        select(Cycle).where(
            Cycle.id == cycle_id,
            Cycle.client_id == client_id,
        )
    )
    cycle = result.scalar_one_or_none()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cycle {cycle_id} not found for client {client_id}",
        )
    return cycle


@router.patch(
    "/clients/{client_id}/cycles/{cycle_id}/pause",
    response_model=CycleStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def pause_cycle(
    client_id: UUID,
    cycle_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CycleStatusResponse:
    """
    Pause an active cycle. Customer-facing endpoint.

    Sets cycle.status = 'paused' and logs a cycle_events row.
    """
    cycle = await get_cycle_or_404(cycle_id, client_id, db)

    if cycle.status == "paused":
        return CycleStatusResponse(
            id=str(cycle.id),
            status="paused",
            client_id=str(cycle.client_id),
        )

    cycle.status = "paused"
    db.add(
        CycleEvent(
            cycle_id=cycle.id,
            event_type="paused",
            triggered_by="customer",
            event_metadata={"user_id": str(ctx.user_id)},
        )
    )
    await db.flush()

    logger.info(f"[Cycles] Cycle {cycle_id} paused by user {ctx.user_id}")

    return CycleStatusResponse(
        id=str(cycle.id),
        status="paused",
        client_id=str(cycle.client_id),
    )


@router.patch(
    "/clients/{client_id}/cycles/{cycle_id}/resume",
    response_model=CycleStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def resume_cycle(
    client_id: UUID,
    cycle_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CycleStatusResponse:
    """
    Resume a paused cycle. Customer-facing endpoint.

    Sets cycle.status = 'active' and logs a cycle_events row.
    """
    cycle = await get_cycle_or_404(cycle_id, client_id, db)

    if cycle.status == "active":
        return CycleStatusResponse(
            id=str(cycle.id),
            status="active",
            client_id=str(cycle.client_id),
        )

    cycle.status = "active"
    db.add(
        CycleEvent(
            cycle_id=cycle.id,
            event_type="resumed",
            triggered_by="customer",
            event_metadata={"user_id": str(ctx.user_id)},
        )
    )
    await db.flush()

    logger.info(f"[Cycles] Cycle {cycle_id} resumed by user {ctx.user_id}")

    return CycleStatusResponse(
        id=str(cycle.id),
        status="active",
        client_id=str(cycle.client_id),
    )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] pause endpoint: sets status='paused', logs CycleEvent triggered_by='customer'
# [x] resume endpoint: sets status='active', logs CycleEvent triggered_by='customer'
# [x] get_cycle_or_404 enforces client_id scoping
# [x] Idempotent: already paused/active returns current status without error
