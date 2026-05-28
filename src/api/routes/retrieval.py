"""Contract: src/api/routes/retrieval.py
Purpose: Customer memory override interface (Wave 5).
Layer: API routes

POST /retrieval/overrides records a customer's intent to ``ignore`` (suppress)
or ``prefer`` (boost) a specific memory in recall, optionally scoped to a
``task_type`` and/or with an ``expires_at``. The retrieval read-path
(src/retrieval/agent_query.query) consults these rows behind the
RETRIEVAL_OVERRIDES_ENABLED feature flag.

The endpoint is itself gated by the same flag: with the feature off (default)
it returns 404, so the surface stays inert in production until deliberately
enabled. The route function is sync so the blocking psycopg write runs in
FastAPI's threadpool rather than the event loop.

Security follow-up: overrides are not yet auth- or tenant-scoped (the data
model has no tenant_id — it follows the Wave 5 dispatch spec verbatim). Add
authentication + tenant binding before exposing this to real customers.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.retrieval import overrides

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


def require_overrides_enabled() -> bool:
    """Gate the endpoint on RETRIEVAL_OVERRIDES_ENABLED — 404 when off."""
    if not overrides.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory overrides feature is not enabled (RETRIEVAL_OVERRIDES_ENABLED).",
        )
    return True


class MemoryOverrideRequest(BaseModel):
    memory_id: str = Field(min_length=1, description="Citation source_id to override.")
    override_type: overrides.OverrideType = Field(
        description="'ignore' suppresses the memory from recall; 'prefer' boosts it."
    )
    task_type: str | None = Field(
        default=None, description="Scope to one task type; None applies to all queries."
    )
    expires_at: datetime | None = Field(
        default=None, description="Override is inert after this time; None never expires."
    )


class MemoryOverrideResponse(BaseModel):
    id: str
    memory_id: str
    override_type: str
    task_type: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


@router.post(
    "/overrides",
    response_model=MemoryOverrideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer memory override",
    description="Records an ignore/prefer override for a memory. Gated by RETRIEVAL_OVERRIDES_ENABLED.",
)
def create_memory_override(
    request: MemoryOverrideRequest,
    _enabled: bool = Depends(require_overrides_enabled),
) -> MemoryOverrideResponse:
    try:
        row = overrides.insert_override(
            request.memory_id,
            request.override_type,
            task_type=request.task_type,
            expires_at=request.expires_at,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return MemoryOverrideResponse(**row)
