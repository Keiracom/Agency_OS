"""
FILE: src/api/routes/dashboard.py
PURPOSE: Phase-2.1 Dashboard endpoints — BU-direct hot leads, stats strip,
         funnel distribution, activity feed.
PHASE:   PHASE-2.1-DASHBOARD-WIRING

Reads directly from public.business_universe + public.cis_outreach_outcomes
via raw SQL, scoped to the calling client's id (RLS-friendly). Pure read-only.

Master Agency Desk v10 prototype was hard-coded; these endpoints replace
that mock layer with live counts.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    ClientContext,
    get_current_client,
    get_db_session,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ─────────────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────────────

class BUHotLead(BaseModel):
    id: str
    domain: str
    company: str
    dm_name: str | None = None
    dm_title: str | None = None
    propensity_score: int = Field(default=0)
    pipeline_stage: int = Field(default=0)
    has_email: bool = False
    has_mobile: bool = False


class BUHotLeadsResponse(BaseModel):
    items: list[BUHotLead]
    total: int


class BUStats(BaseModel):
    total_businesses: int
    businesses_with_email: int
    businesses_with_mobile: int
    total_bdms: int
    enriched_last_24h: int


class FunnelStage(BaseModel):
    stage: int
    label: str
    count: int


class FunnelResponse(BaseModel):
    stages: list[FunnelStage]
    total: int


class ActivityEvent(BaseModel):
    id: str
    timestamp: str
    kind: str  # 'enrichment' | 'outreach'
    domain: str | None = None
    detail: str
    cost_usd: float | None = None


class ActivityResponse(BaseModel):
    items: list[ActivityEvent]


# Stage label map — ordered for UI funnel rendering.
_STAGE_LABELS: dict[int, str] = {
    1: "Discovered",
    2: "SERP-verified",
    3: "Identity-confirmed",
    4: "Signal-bundled",
    5: "Composite-scored",
    6: "Historically-ranked",
    7: "F3B-analysed",
    8: "Contact-enriched",
    9: "LinkedIn-confirmed",
    10: "VR-scored",
    11: "Card-ready",
}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/bu-hot-leads", response_model=BUHotLeadsResponse)
async def bu_hot_leads(
    limit: int = Query(default=10, ge=1, le=50),
    min_score: int = Query(default=70, ge=0, le=100),
    min_stage: int = Query(default=6, ge=1, le=11),
    ctx: ClientContext = Depends(get_current_client),
    db: AsyncSession = Depends(get_db_session),
) -> BUHotLeadsResponse:
    """Hot leads from business_universe — pipeline_stage >= min_stage AND
    propensity_score > min_score, ordered by score desc."""
    rows = (await db.execute(
        text("""
            SELECT id, domain, display_name, dm_name, dm_title,
                   COALESCE(propensity_score, 0) AS propensity_score,
                   COALESCE(pipeline_stage, 0)   AS pipeline_stage,
                   (dm_email IS NOT NULL)        AS has_email,
                   ((dm_mobile IS NOT NULL) OR (dm_phone IS NOT NULL)) AS has_mobile
            FROM business_universe
            WHERE pipeline_stage >= :min_stage
              AND COALESCE(propensity_score, 0) > :min_score
            ORDER BY propensity_score DESC NULLS LAST
            LIMIT :limit
        """),
        {"min_stage": min_stage, "min_score": min_score, "limit": limit},
    )).mappings().all()

    items = [
        BUHotLead(
            id=str(r["id"]),
            domain=r["domain"] or "",
            company=r["display_name"] or r["domain"] or "Unknown",
            dm_name=r["dm_name"],
            dm_title=r["dm_title"],
            propensity_score=int(r["propensity_score"] or 0),
            pipeline_stage=int(r["pipeline_stage"] or 0),
            has_email=bool(r["has_email"]),
            has_mobile=bool(r["has_mobile"]),
        )
        for r in rows
    ]
    return BUHotLeadsResponse(items=items, total=len(items))


@router.get("/bu-stats", response_model=BUStats)
async def bu_stats(
    ctx: ClientContext = Depends(get_current_client),
    db: AsyncSession = Depends(get_db_session),
) -> BUStats:
    """Top-of-dashboard stats strip — total BU rows, with-email count,
    with-mobile count, total BDMs, enriched-in-last-24h count."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    row = (await db.execute(
        text("""
            SELECT
                COUNT(*)                                              AS total_businesses,
                COUNT(*) FILTER (WHERE dm_email IS NOT NULL)          AS with_email,
                COUNT(*) FILTER (WHERE dm_mobile IS NOT NULL
                                 OR dm_phone IS NOT NULL)             AS with_mobile,
                COUNT(*) FILTER (WHERE last_enriched_at >= :cutoff)   AS enriched_24h
            FROM business_universe
        """),
        {"cutoff": cutoff},
    )).mappings().first()

    bdm_total = (await db.execute(
        text("SELECT COUNT(*) AS n FROM business_decision_makers WHERE is_current = TRUE"),
    )).scalar_one_or_none() or 0

    return BUStats(
        total_businesses=int((row or {}).get("total_businesses", 0)),
        businesses_with_email=int((row or {}).get("with_email", 0)),
        businesses_with_mobile=int((row or {}).get("with_mobile", 0)),
        total_bdms=int(bdm_total),
        enriched_last_24h=int((row or {}).get("enriched_24h", 0)),
    )


@router.get("/bu-funnel", response_model=FunnelResponse)
async def bu_funnel(
    ctx: ClientContext = Depends(get_current_client),
    db: AsyncSession = Depends(get_db_session),
) -> FunnelResponse:
    """Pipeline-stage distribution across business_universe.
    Returns one row per stage 1..11 with the stage label and live count."""
    rows = (await db.execute(
        text("""
            SELECT COALESCE(pipeline_stage, 0) AS stage, COUNT(*) AS n
            FROM business_universe
            GROUP BY pipeline_stage
        """),
    )).mappings().all()
    counts: dict[int, int] = {int(r["stage"]): int(r["n"]) for r in rows}

    stages = [
        FunnelStage(stage=s, label=_STAGE_LABELS[s], count=counts.get(s, 0))
        for s in sorted(_STAGE_LABELS.keys())
    ]
    return FunnelResponse(stages=stages, total=sum(c.count for c in stages))


@router.get("/bu-activity", response_model=ActivityResponse)
async def bu_activity(
    limit: int = Query(default=20, ge=1, le=100),
    ctx: ClientContext = Depends(get_current_client),
    db: AsyncSession = Depends(get_db_session),
) -> ActivityResponse:
    """Combined recent activity — most-recent enrichment events from BU
    plus most-recent outreach events from cis_outreach_outcomes, merged
    and ordered by timestamp desc."""
    enrich_rows = (await db.execute(
        text("""
            SELECT id, domain, display_name, last_enriched_at,
                   pipeline_stage, enrichment_cost_usd
            FROM business_universe
            WHERE last_enriched_at IS NOT NULL
            ORDER BY last_enriched_at DESC
            LIMIT :limit
        """),
        {"limit": limit},
    )).mappings().all()

    outreach_rows: list[Any] = []
    try:
        outreach_rows = (await db.execute(
            text("""
                SELECT id, channel, sent_at, final_outcome
                FROM cis_outreach_outcomes
                WHERE client_id = :cid
                ORDER BY sent_at DESC
                LIMIT :limit
            """),
            {"cid": ctx.client_id, "limit": limit},
        )).mappings().all()
    except Exception:  # noqa: BLE001 — outreach table may not exist in dev
        outreach_rows = []

    items: list[ActivityEvent] = []
    for r in enrich_rows:
        items.append(ActivityEvent(
            id=f"enr-{r['id']}",
            timestamp=(r["last_enriched_at"] or datetime.now(UTC)).isoformat(),
            kind="enrichment",
            domain=r["domain"],
            detail=f"{r['display_name'] or r['domain']} → stage {r['pipeline_stage'] or 0}",
            cost_usd=float(r["enrichment_cost_usd"]) if r["enrichment_cost_usd"] is not None else None,
        ))
    for r in outreach_rows:
        items.append(ActivityEvent(
            id=f"out-{r['id']}",
            timestamp=(r["sent_at"] or datetime.now(UTC)).isoformat(),
            kind="outreach",
            domain=None,
            detail=f"{r['channel']} sent — outcome={r['final_outcome'] or 'pending'}",
            cost_usd=None,
        ))

    items.sort(key=lambda e: e.timestamp, reverse=True)
    return ActivityResponse(items=items[:limit])
