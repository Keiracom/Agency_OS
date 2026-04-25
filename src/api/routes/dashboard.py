"""
FILE: src/api/routes/dashboard.py
PURPOSE: Phase-2.1 Dashboard endpoints — BU-direct hot leads, stats strip,
         funnel distribution, activity feed.
PHASE:   PHASE-2.1-DASHBOARD-WIRING

Reads directly from public.business_universe + public.cis_outreach_outcomes
via raw SQL, scoped to the calling client's id (RLS-friendly). Pure read-only.

Multi-tenant filtering: business_universe is shared inventory — every
BU-touching endpoint joins through campaign_leads (which carries
client_id) so a client only ever sees BU rows they have claimed.
"""
from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

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
    0:  "Queued",
    1:  "Discovered",
    2:  "SERP-verified",
    3:  "Identity-confirmed",
    4:  "Signal-bundled",
    5:  "Composite-scored",
    6:  "Historically-ranked",
    7:  "F3B-analysed",
    8:  "Contact-enriched",
    9:  "LinkedIn-confirmed",
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
    propensity_score >= min_score, ordered by score desc.
    Multi-tenant via JOIN on campaign_leads.client_id."""
    page = (await db.execute(
        text("""
            SELECT bu.id, bu.domain, bu.display_name, bu.dm_name, bu.dm_title,
                   COALESCE(bu.propensity_score, 0) AS propensity_score,
                   COALESCE(bu.pipeline_stage, 0)   AS pipeline_stage,
                   (bu.dm_email IS NOT NULL)        AS has_email,
                   ((bu.dm_mobile IS NOT NULL) OR (bu.dm_phone IS NOT NULL)) AS has_mobile
            FROM business_universe bu
            JOIN campaign_leads cl ON cl.business_universe_id = bu.id
            WHERE cl.client_id = :client_id
              AND bu.pipeline_stage >= :min_stage
              AND COALESCE(bu.propensity_score, 0) >= :min_score
            GROUP BY bu.id
            ORDER BY MAX(COALESCE(bu.propensity_score, 0)) DESC
            LIMIT :limit
        """),
        {
            "client_id": ctx.client_id,
            "min_stage": min_stage,
            "min_score": min_score,
            "limit":     limit,
        },
    )).mappings().all()

    # Distinct count of qualifying BU rows for this client (not page size).
    total = (await db.execute(
        text("""
            SELECT COUNT(DISTINCT bu.id) AS n
            FROM business_universe bu
            JOIN campaign_leads cl ON cl.business_universe_id = bu.id
            WHERE cl.client_id = :client_id
              AND bu.pipeline_stage >= :min_stage
              AND COALESCE(bu.propensity_score, 0) >= :min_score
        """),
        {
            "client_id": ctx.client_id,
            "min_stage": min_stage,
            "min_score": min_score,
        },
    )).scalar_one_or_none() or 0

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
        for r in page
    ]
    return BUHotLeadsResponse(items=items, total=int(total))


@router.get("/bu-stats", response_model=BUStats)
async def bu_stats(
    ctx: ClientContext = Depends(get_current_client),
    db: AsyncSession = Depends(get_db_session),
) -> BUStats:
    """Top-of-dashboard stats strip — total BU rows, with-email count,
    with-mobile count, total BDMs, enriched-in-last-24h count.
    All BU counts JOIN campaign_leads.client_id; BDM count joins via
    business_universe_id → campaign_leads."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    row = (await db.execute(
        text("""
            SELECT
              COUNT(DISTINCT bu.id) AS total_businesses,
              COUNT(DISTINCT bu.id) FILTER (WHERE bu.dm_email IS NOT NULL)
                                             AS with_email,
              COUNT(DISTINCT bu.id) FILTER (WHERE bu.dm_mobile IS NOT NULL
                                             OR bu.dm_phone IS NOT NULL)
                                             AS with_mobile,
              COUNT(DISTINCT bu.id) FILTER (WHERE bu.last_enriched_at >= :cutoff)
                                             AS enriched_24h
            FROM business_universe bu
            JOIN campaign_leads cl ON cl.business_universe_id = bu.id
            WHERE cl.client_id = :client_id
        """),
        {"client_id": ctx.client_id, "cutoff": cutoff},
    )).mappings().first()

    bdm_total = (await db.execute(
        text("""
            SELECT COUNT(DISTINCT bdm.id) AS n
            FROM business_decision_makers bdm
            JOIN campaign_leads cl
              ON cl.business_universe_id = bdm.business_universe_id
            WHERE cl.client_id = :client_id
              AND bdm.is_current = TRUE
        """),
        {"client_id": ctx.client_id},
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
    Returns one row per stage 0..11 with the stage label and live count.
    Multi-tenant via JOIN on campaign_leads.client_id."""
    rows = (await db.execute(
        text("""
            SELECT COALESCE(bu.pipeline_stage, 0) AS stage,
                   COUNT(DISTINCT bu.id)          AS n
            FROM business_universe bu
            JOIN campaign_leads cl ON cl.business_universe_id = bu.id
            WHERE cl.client_id = :client_id
            GROUP BY bu.pipeline_stage
        """),
        {"client_id": ctx.client_id},
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
    and ordered by timestamp desc.
    Both sources scoped to ctx.client_id."""
    enrich_rows = (await db.execute(
        text("""
            SELECT bu.id, bu.domain, bu.display_name, bu.last_enriched_at,
                   bu.pipeline_stage, bu.enrichment_cost_usd
            FROM business_universe bu
            JOIN campaign_leads cl ON cl.business_universe_id = bu.id
            WHERE cl.client_id = :client_id
              AND bu.last_enriched_at IS NOT NULL
            GROUP BY bu.id
            ORDER BY MAX(bu.last_enriched_at) DESC
            LIMIT :limit
        """),
        {"client_id": ctx.client_id, "limit": limit},
    )).mappings().all()

    outreach_rows: list[Any] = []
    try:
        outreach_rows = (await db.execute(
            text("""
                SELECT o.id, o.channel, o.sent_at, o.final_outcome,
                       bu.domain
                FROM cis_outreach_outcomes o
                LEFT JOIN leads l    ON l.id  = o.lead_id
                LEFT JOIN business_universe bu
                       ON bu.id = l.business_universe_id
                WHERE o.client_id = :client_id
                ORDER BY o.sent_at DESC
                LIMIT :limit
            """),
            {"client_id": ctx.client_id, "limit": limit},
        )).mappings().all()
    except Exception as exc:  # noqa: BLE001 — table may not exist in dev
        logger.error(
            "bu_activity: outreach query failed (table missing in dev?): %s", exc,
        )
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
            domain=r.get("domain"),
            detail=f"{r['channel']} sent — outcome={r['final_outcome'] or 'pending'}",
            cost_usd=None,
        ))

    items.sort(key=lambda e: e.timestamp, reverse=True)
    return ActivityResponse(items=items[:limit])
