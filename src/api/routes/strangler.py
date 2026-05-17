"""
FILE: src/api/routes/strangler.py
PURPOSE: KEI-180 Strangler Fig routing layer — per-tenant Model A/B traffic split.
PHASE: 0.5 (P0 critical path)
LAYER: 4 - api/routes

Routes POST /api/strangler/outreach based on public.client_customers.use_model_b:
  use_model_b=false → _route_model_a  (existing internal outreach path)
  use_model_b=true  → _route_model_b  (Model B dispatcher, fail-open to A on 5xx)

Every routing decision is logged to public.tool_call_log with tenant_id,
route taken, and wall-clock latency. No request payload body is logged (PII guard).
"""

import logging
import time
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strangler", tags=["strangler"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class OutreachRequest(BaseModel):
    tenant_id: UUID
    payload: dict[str, Any] = {}


class OutreachResponse(BaseModel):
    route: str
    tenant_id: UUID
    latency_ms: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_use_model_b(tenant_id: UUID, db: AsyncSession) -> bool:
    """Return the use_model_b flag for a tenant; raise 404 if not found."""
    row = await db.execute(
        text(
            "SELECT use_model_b FROM public.client_customers "
            "WHERE id = :id AND deleted_at IS NULL LIMIT 1"
        ),
        {"id": str(tenant_id)},
    )
    result = row.fetchone()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found",
        )
    return bool(result[0])


async def _route_model_a(
    tenant_id: UUID,
) -> dict[str, Any]:
    """
    Model A path — existing internal outreach pipeline.

    Integration point: src/orchestration/flows/outreach_flow.py
    (hourly_outreach_flow / send_email_outreach_task).  Full wiring is a
    follow-up once the Strangler Fig routing is validated; this shim
    preserves the fork without modifying Model A code.
    """
    # Follow-up wiring tracked in KEI-180 dispatch — delegate to src/orchestration/flows/outreach_flow.py
    return {"model": "a", "tenant_id": str(tenant_id)}


async def _route_model_b(
    payload: dict[str, Any],
    tenant_id: UUID,
) -> dict[str, Any]:
    """
    Model B path — proxy to the dispatcher service (Scout KEI-111).

    Reads DISPATCHER_URL from settings; fail-open: any 5xx from the
    dispatcher falls back to Model A so no tenant is hard-blocked.
    """
    dispatcher_url = getattr(settings, "dispatcher_url", None) or ""
    if not dispatcher_url:
        raise httpx.HTTPStatusError(
            "DISPATCHER_URL not configured",
            request=None,  # type: ignore[arg-type]
            response=None,  # type: ignore[arg-type]
        )
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{dispatcher_url.rstrip('/')}/outreach",
            json={"tenant_id": str(tenant_id), **payload},
        )
        resp.raise_for_status()
    return {"model": "b", "tenant_id": str(tenant_id)}


async def _log_route_decision(
    tenant_id: UUID,
    route: str,
    latency_ms: float,
    db: AsyncSession,
) -> None:
    """Insert a row into public.tool_call_log — no request payload (PII guard)."""
    try:
        await db.execute(
            text(
                "INSERT INTO public.tool_call_log "
                "(callsign, tool_name, tool_input, started_at, duration_ms, created_at) "
                "VALUES ('strangler', :route, :input, NOW(), :latency_ms, NOW())"
            ),
            {
                "route": route,
                "input": f'{{"tenant_id":"{tenant_id}","route":"{route}"}}',
                "latency_ms": int(latency_ms),
            },
        )
        await db.commit()
    except Exception:  # noqa: BLE001
        logger.warning("Failed to log route decision for tenant %s", tenant_id, exc_info=True)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/outreach")
async def outreach(
    req: OutreachRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> OutreachResponse:
    """
    Route an outreach request per the Strangler Fig feature flag.

    Reads use_model_b from public.client_customers; proxies to Model B
    dispatcher when true, else executes Model A internal path.
    Fail-open: dispatcher 5xx falls back to Model A.
    """
    t0 = time.perf_counter()
    route = "model_a"

    use_b = await _get_use_model_b(req.tenant_id, db)

    if use_b:
        try:
            await _route_model_b(req.payload, req.tenant_id)
            route = "model_b"
        except Exception:  # noqa: BLE001
            logger.warning(
                "Model B dispatcher failed for tenant %s — failing open to Model A",
                req.tenant_id,
            )
            await _route_model_a(req.tenant_id)
            route = "model_b_failover"
    else:
        await _route_model_a(req.tenant_id)

    latency_ms = (time.perf_counter() - t0) * 1000
    await _log_route_decision(req.tenant_id, route, latency_ms, db)

    return OutreachResponse(
        route=route,
        tenant_id=req.tenant_id,
        latency_ms=latency_ms,
    )
