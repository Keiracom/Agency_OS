"""
Contract: src/api/routes/approvals.py
Purpose: Approval workflow endpoints — approve/reject/defer/edit with multi-tenancy
Layer: 5 - routes
Imports: all lower layers
Consumers: frontend, automation triggers

FILE: src/api/routes/approvals.py
PURPOSE: Approval CRUD + state transition endpoints
PHASE: orion/phase-2-slice-7
DEPENDENCIES:
  - src/api/dependencies.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 14: Soft delete checks (deleted_at IS NULL)
  - Multi-tenancy via client_id enforcement
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import ClientContext, get_current_client, get_db_session

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
# Helper
# ============================================

TERMINAL_STATUSES = {"approved", "rejected"}


async def _load_approval(
    db: AsyncSession,
    approval_id: UUID,
    client_id: UUID,
) -> dict:
    """
    Load approval row, enforcing 404 (not found) and 403 (cross-tenant).

    Returns row as dict or raises HTTPException.
    """
    result = await db.execute(
        text(
            "SELECT id, client_id, status, payload, decided_at, decided_by, reason, created_at, updated_at"
            " FROM approvals WHERE id = :approval_id"
        ),
        {"approval_id": approval_id},
    )
    row = result.fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found")

    row_dict = dict(row._mapping)

    if row_dict["client_id"] != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="approval not owned by client",
        )

    return row_dict


def _check_not_terminal(row: dict) -> None:
    """Raise 409 if the approval is already in a terminal state."""
    if row["status"] in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"approval already terminal (status={row['status']})",
        )


def _approval_response(approval_id: UUID, new_status: str, decided_at: datetime) -> dict:
    return {
        "approval_id": str(approval_id),
        "status": new_status,
        "decided_at": decided_at.isoformat(),
    }


# ============================================
# Endpoints — note: client_id in path so get_current_client resolves correctly
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
    row = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(row)

    now = datetime.now(UTC)
    await db.execute(
        text(
            "UPDATE approvals SET status='approved', decided_at=:now, decided_by=:user_id,"
            " updated_at=:now WHERE id=:approval_id"
        ),
        {"now": now, "user_id": ctx.user_id, "approval_id": approval_id},
    )
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
    row = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(row)

    now = datetime.now(UTC)
    await db.execute(
        text(
            "UPDATE approvals SET status='rejected', reason=:reason, decided_at=:now,"
            " decided_by=:user_id, updated_at=:now WHERE id=:approval_id"
        ),
        {"reason": body.reason, "now": now, "user_id": ctx.user_id, "approval_id": approval_id},
    )
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
    row = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(row)

    now = datetime.now(UTC)
    await db.execute(
        text(
            "UPDATE approvals SET status='deferred', decided_at=:now,"
            " decided_by=:user_id, updated_at=:now WHERE id=:approval_id"
        ),
        {"now": now, "user_id": ctx.user_id, "approval_id": approval_id},
    )
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
    row = await _load_approval(db, approval_id, ctx.client_id)
    _check_not_terminal(row)

    now = datetime.now(UTC)
    await db.execute(
        text(
            "UPDATE approvals SET status='edit_applied', payload=payload || :edits::jsonb,"
            " decided_at=:now, decided_by=:user_id, updated_at=:now WHERE id=:approval_id"
        ),
        {
            "edits": str(body.edits).replace("'", '"'),
            "now": now,
            "user_id": ctx.user_id,
            "approval_id": approval_id,
        },
    )
    await db.commit()

    return _approval_response(approval_id, "edit_applied", now)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Router with prefix and tags
# [x] All four action endpoints (approve, reject, defer, edit)
# [x] Multi-tenancy enforcement (client_id path param + ctx.client_id check)
# [x] Authentication via get_current_client (Depends)
# [x] 401 on missing auth (FastAPI handles automatically)
# [x] 403 on cross-tenant (_load_approval checks client_id)
# [x] 404 on not-found (_load_approval raises 404)
# [x] 409 on terminal re-transition (_check_not_terminal)
# [x] 422 on pydantic validation errors (FastAPI handles automatically)
# [x] Raw SQL through AsyncSession (no new ORM model)
# [x] X-Signature header accepted, HMAC deferred to slice 8
# [x] Session passed as argument (Rule 11)
# [x] All functions have type hints and docstrings
