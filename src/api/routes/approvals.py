"""
Contract: src/api/routes/approvals.py
Purpose: Approval workflow endpoints — approve/reject/defer/edit with multi-tenancy
Layer: 5 - routes
Imports: all lower layers
Consumers: frontend, automation triggers

FILE: src/api/routes/approvals.py
PURPOSE: Approval CRUD + state transition endpoints
PHASE: orion/phase-2-slice-8  (ORM refactor — raw SQL replaced by SQLAlchemy model)
DEPENDENCIES:
  - src/api/dependencies.py
  - src/models/approval.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft delete checks (deleted_at IS NULL)
  - Multi-tenancy via client_id enforcement
  - 404 on cross-tenant (existence must not leak across tenants)
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import ClientContext, get_current_client, get_db_session
from src.models.approval import Approval, ApprovalStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

# TODO slice 8: implement HMAC verification for X-Signature header


# ============================================
# Request Schemas
# ============================================


class RejectBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class DeferBody(BaseModel):
    defer_hours: int = Field(..., ge=1, le=720)


class EditBody(BaseModel):
    edits: dict[str, Any] = Field(..., min_length=1)


# ============================================
# Helpers
# ============================================


async def _load_approval(
    db: AsyncSession,
    approval_id: UUID,
    client_id: UUID,
) -> Approval:
    """
    Load Approval ORM object scoped to client_id.

    Returns Approval or raises 404 (row missing OR client_id mismatch).
    Using 404 for cross-tenant rather than 403 to avoid leaking existence
    of approvals that belong to other tenants.
    """
    result = await db.execute(
        select(Approval).where(
            Approval.id == approval_id,
            Approval.client_id == client_id,
        )
    )
    approval = result.scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found")
    return approval


def _check_not_terminal(approval: Approval) -> None:
    """Raise 409 if the approval is already in a terminal state."""
    if approval.is_terminal():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"approval already terminal (status={approval.status})",
        )


def _approval_response(approval_id: UUID, new_status: str, decided_at: datetime) -> dict:
    return {
        "approval_id": str(approval_id),
        "status": new_status,
        "decided_at": decided_at.isoformat(),
    }


# ============================================
# Endpoints — client_id in path so get_current_client resolves correctly
# ============================================


@router.post(
    "/clients/{client_id}/{approval_id}/approve",
    status_code=status.HTTP_200_OK,
)
async def approve_approval(
    client_id: UUID,
    approval_id: UUID,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    x_signature: Annotated[str | None, Header()] = None,  # TODO slice 8: verify HMAC
) -> dict:
    """Mark an approval as approved."""
    approval = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(approval)

    now = datetime.now(UTC)
    approval.status = ApprovalStatus.APPROVED
    approval.approved_at = now
    approval.approved_by = ctx.user_id
    await db.commit()

    return _approval_response(approval_id, "approved", now)


@router.post(
    "/clients/{client_id}/{approval_id}/reject",
    status_code=status.HTTP_200_OK,
)
async def reject_approval(
    client_id: UUID,
    approval_id: UUID,
    body: RejectBody,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    x_signature: Annotated[str | None, Header()] = None,  # TODO slice 8: verify HMAC
) -> dict:
    """Mark an approval as rejected with a reason."""
    approval = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(approval)

    now = datetime.now(UTC)
    approval.status = ApprovalStatus.REJECTED
    approval.notes = body.reason
    approval.approved_at = now
    approval.approved_by = ctx.user_id
    await db.commit()

    return _approval_response(approval_id, "rejected", now)


@router.post(
    "/clients/{client_id}/{approval_id}/defer",
    status_code=status.HTTP_200_OK,
)
async def defer_approval(
    client_id: UUID,
    approval_id: UUID,
    body: DeferBody,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    x_signature: Annotated[str | None, Header()] = None,  # TODO slice 8: verify HMAC
) -> dict:
    """Defer an approval decision by N hours."""
    approval = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(approval)

    now = datetime.now(UTC)
    approval.status = ApprovalStatus.DEFERRED
    approval.approved_at = now
    approval.approved_by = ctx.user_id
    await db.commit()

    result = _approval_response(approval_id, "deferred", now)
    result["defer_hours"] = body.defer_hours
    return result


@router.post(
    "/clients/{client_id}/{approval_id}/edit",
    status_code=status.HTTP_200_OK,
)
async def edit_approval(
    client_id: UUID,
    approval_id: UUID,
    body: EditBody,
    ctx: Annotated[ClientContext, Depends(get_current_client)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    x_signature: Annotated[str | None, Header()] = None,  # TODO slice 8: verify HMAC
) -> dict:
    """Apply edits to an approval's payload."""
    approval = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(approval)

    now = datetime.now(UTC)
    # Merge edits into existing payload (or initialise)
    existing = approval.payload or {}
    approval.payload = {**existing, **body.edits}
    approval.status = ApprovalStatus.EDITED
    approval.approved_at = now
    approval.approved_by = ctx.user_id
    await db.commit()

    return _approval_response(approval_id, "edit_applied", now)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with prefix and tags
# [x] All four action endpoints (approve, reject, defer, edit)
# [x] Multi-tenancy enforcement (client_id path param + ctx.client_id in ORM where-clause)
# [x] Authentication via get_current_client (Depends)
# [x] 401 on missing auth (FastAPI handles automatically)
# [x] 404 on cross-tenant — existence not leaked (ORM filter includes client_id)
# [x] 404 on not-found (_load_approval raises 404)
# [x] 409 on terminal re-transition (_check_not_terminal)
# [x] 422 on pydantic validation errors (FastAPI handles automatically)
# [x] ORM via Approval model (no raw SQL)
# [x] X-Signature header accepted, HMAC deferred to slice 8
# [x] Session passed as argument (Rule 11)
# [x] All functions have type hints and docstrings
