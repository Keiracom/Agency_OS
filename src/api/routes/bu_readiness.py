"""
FILE: src/api/routes/bu_readiness.py
PURPOSE: M10 — expose the BU readiness threshold report as a REST endpoint.
         Same query path as scripts/bu_readiness_check.py so the cron
         + dashboard widget agree.
PHASE:   M10 — BU readiness threshold instrumentation

Public-by-design endpoint: returns ONLY the four aggregate threshold
metrics (no PII, no per-row data). The frontend widget polls this on
mount and renders progress bars + pass/fail badges.
"""
from __future__ import annotations

import logging

import asyncpg
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from scripts.bu_readiness_check import gather_metrics  # type: ignore[import-not-found]
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bu", tags=["bu-readiness"])


class ReadinessMetric(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    value: float
    unit: str       # 'pct' | 'count'
    threshold: float
    # Serialized + accepted as 'pass' (Python keyword); attribute is pass_field.
    pass_field: bool = Field(..., alias="pass")
    detail: str


class ReadinessResponse(BaseModel):
    metrics: list[ReadinessMetric]
    overall_pass: bool


@router.get("/readiness", response_model=ReadinessResponse)
async def bu_readiness() -> ReadinessResponse:
    """Return the four BU sellable-threshold metrics (coverage / verified /
    outcomes / trajectory) plus an overall pass flag.

    Public by design — no PII surfaced, no client_id needed. Same query
    path as scripts/bu_readiness_check.py so cron + dashboard agree."""
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
    except Exception as exc:  # noqa: BLE001
        logger.error("bu_readiness DB connect failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DB unavailable",
        ) from exc

    try:
        report = await gather_metrics(conn)
    finally:
        await conn.close()

    return ReadinessResponse(
        metrics=[
            ReadinessMetric.model_validate({
                "name": m.name, "value": m.value, "unit": m.unit,
                "threshold": m.threshold, "pass": m.pass_, "detail": m.detail,
            })
            for m in report.metrics
        ],
        overall_pass=report.overall_pass,
    )
