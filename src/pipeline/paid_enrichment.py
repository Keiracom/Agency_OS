"""
Contract: src/pipeline/paid_enrichment.py
Purpose: Paid enrichment pass — affordability gate + DFS bulk metrics + DFS Maps GMB
Layer: 4 - orchestration (uses asyncpg connection directly)
Imports: asyncpg, clients (dfs_labs_client, dfs_gmaps_client)
Consumers: orchestration flows
Directive: #283
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg

from src.clients.dfs_gmaps_client import DFSGMapsClient
from src.clients.dfs_labs_client import DFSLabsClient
from src.pipeline.pipeline_orchestrator import GLOBAL_SEM_DFS
from src.utils.domain_parser import extract_business_name

BATCH_SIZE = 50
DFS_BULK_BATCH_SIZE = 100  # max domains per bulk_domain_metrics call

# State-level coordinates for GMB search (capital city defaults)
_STATE_COORDS: dict[str, tuple[float, float]] = {
    "NSW": (-33.87, 151.21),
    "VIC": (-37.81, 144.96),
    "QLD": (-27.47, 153.02),
    "WA": (-31.95, 115.86),
    "SA": (-34.93, 138.60),
    "TAS": (-42.88, 147.33),
    "ACT": (-35.28, 149.13),
    "NT": (-12.46, 130.84),
}
_DEFAULT_COORDS = (-33.87, 151.21)  # Sydney fallback


def _state_coords(state: str | None) -> tuple[float, float]:
    if state:
        return _STATE_COORDS.get(state.upper(), _DEFAULT_COORDS)
    return _DEFAULT_COORDS


async def _suppression_cross_check(
    conn: asyncpg.Connection,
    bu_ids: list[str],
) -> set[str]:
    """Return the subset of BU ids whose website_contact_emails intersect the
    public.suppression_list (any email match on channel ∈ {'all','email'}).

    Pre-paid-spend SQL guard. Pure SQL — no live API calls. DNCR phone checks
    live in Redis cache (src/integrations/dncr.py) and have no SQL surface, so
    they are not joined here; that path is exercised at the live-call site.
    """
    if not bu_ids:
        return set()
    rows = await conn.fetch(
        """SELECT DISTINCT bu.id
             FROM business_universe bu,
                  jsonb_array_elements_text(
                      COALESCE(bu.website_contact_emails, '[]'::jsonb)
                  ) AS contact_email
             JOIN public.suppression_list s
               ON LOWER(s.email) = LOWER(contact_email)
            WHERE bu.id = ANY($1::uuid[])
              AND s.channel IN ('all', 'email')""",
        bu_ids,
    )
    return {str(r["id"]) for r in rows}


async def affordability_gate(
    conn: asyncpg.Connection,
    limit: int = 1000,
) -> tuple[list[asyncpg.Record], list[asyncpg.Record]]:
    """
    Query BU for domains ready for paid enrichment. Apply 4-gate filter +
    suppression cross-check.
    Returns (passing_rows, failing_rows).
    Failing rows have paid_enrichment_skipped_reason written to DB before returning.
    """
    rows = await conn.fetch(
        """SELECT id, domain, state, website_cms, website_tech_stack,
                  website_contact_emails, abn_matched, gst_registered, entity_type
           FROM business_universe
           WHERE pipeline_stage >= 1
             AND free_enrichment_completed_at IS NOT NULL
             AND paid_enrichment_completed_at IS NULL
             AND domain IS NOT NULL
           LIMIT $1""",
        limit,
    )

    # Suppression cross-check BEFORE any paid-spend SQL. Skip-marker rows
    # whose contact emails match the suppression list — they never enter the
    # _check_gates loop and never reach DFS / GMB calls downstream.
    suppressed_ids = await _suppression_cross_check(
        conn, [str(r["id"]) for r in rows]
    )

    passing: list[asyncpg.Record] = []
    failing: list[tuple[asyncpg.Record, str]] = []

    for row in rows:
        if str(row["id"]) in suppressed_ids:
            failing.append((row, "suppression_match"))
            continue
        reason = _check_gates(row)
        if reason is None:
            passing.append(row)
        else:
            failing.append((row, reason))

    # Write skip reasons for failing rows
    for row, reason in failing:
        await conn.execute(
            """UPDATE business_universe
               SET paid_enrichment_skipped_reason = $2,
                   paid_enrichment_completed_at = NOW()
               WHERE id = $1""",
            row["id"],
            reason,
        )

    return passing, [r for r, _ in failing]


def _check_gates(row: asyncpg.Record) -> str | None:
    """Return skip reason string if row fails any gate, else None."""
    # GATE 1 — Domain is reachable (at least one free enrichment signal)
    has_signal = (
        row["website_cms"] is not None
        or row["website_tech_stack"] is not None
        or row["website_contact_emails"] is not None
    )
    if not has_signal:
        return "gate1_dead_site"

    # GATE 2 — ABN matched
    if not row["abn_matched"]:
        return "gate2_no_abn"

    # GATE 3 — GST registered
    if row["gst_registered"] is False:
        return "gate3_no_gst"

    # GATE 4 — Not sole trader (None passes)
    sole_trader_types = {"Individual/Sole Trader", "Sole Trader"}
    if row["entity_type"] in sole_trader_types:
        return "gate4_sole_trader"

    return None


class PaidEnrichment:
    """
    Paid enrichment: runs DFS bulk domain metrics + DFS Maps GMB for gate-passing domains.

    Usage:
        engine = PaidEnrichment(conn, dfs_client, gmaps_client)
        stats = await engine.run()
    """

    def __init__(
        self,
        conn: asyncpg.Connection,
        dfs: DFSLabsClient,
        gmaps: DFSGMapsClient,
    ) -> None:
        self._conn = conn
        self._dfs = dfs
        self._gmaps = gmaps
        self._logger = logging.getLogger(__name__)

    async def run(self, limit: int = 500) -> dict[str, Any]:
        passing_rows, failing_rows = await affordability_gate(self._conn, limit)
        stats: dict[str, Any] = {
            "total_evaluated": len(passing_rows) + len(failing_rows),
            "gate_passed": len(passing_rows),
            "gate_failed": len(failing_rows),
            "dfs_enriched": 0,
            "gmb_enriched": 0,
            "intelligence_enriched": 0,
            "completed": 0,
            "errors": [],
        }

        # STEP 1 — DFS Bulk Domain Metrics (batch up to DFS_BULK_BATCH_SIZE)
        domains = [row["domain"] for row in passing_rows]
        domain_to_id = {row["domain"]: row["id"] for row in passing_rows}
        domain_to_state = {row["domain"]: row.get("state") for row in passing_rows}

        for i in range(0, len(domains), DFS_BULK_BATCH_SIZE):
            batch = domains[i : i + DFS_BULK_BATCH_SIZE]
            try:
                metrics_list = await self._dfs.bulk_domain_metrics(batch)
                for m in metrics_list:
                    domain = m.get("domain", "")
                    bu_id = domain_to_id.get(domain)
                    if not bu_id:
                        continue
                    await self._conn.execute(
                        """UPDATE business_universe SET
                               dfs_organic_traffic    = $2,
                               dfs_domain_rank        = $3,
                               dfs_backlinks          = $4,
                               dfs_referring_domains  = $5,
                               dfs_enriched_at        = NOW()
                           WHERE id = $1""",
                        bu_id,
                        m.get("organic_etv", 0.0),
                        m.get("domain_rank", 0),
                        m.get("backlinks_count", 0),
                        m.get("referring_domains") or 0,
                    )
                    stats["dfs_enriched"] += 1
            except Exception as exc:
                self._logger.error("DFS bulk metrics error batch %d: %s", i, exc)
                stats["errors"].append({"step": "dfs_bulk", "batch": i, "error": str(exc)})

        # STEP 2 — DFS Maps GMB (sequential per domain, discover_by_coordinates)
        for i, row in enumerate(passing_rows):
            domain = row["domain"]
            bu_id = row["id"]
            state = domain_to_state.get(domain)
            try:
                business_name = extract_business_name(domain)
                lat, lng = _state_coords(state)
                results = await self._gmaps.discover_by_coordinates(
                    lat=lat,
                    lng=lng,
                    category=business_name,
                    zoom=12,
                    depth=20,
                )
                if results:
                    maps_result = results[0]
                    await self._conn.execute(
                        """UPDATE business_universe SET
                               gmb_rating       = $2,
                               gmb_review_count = $3,
                               gmb_phone        = COALESCE($4, gmb_phone),
                               gmb_address      = COALESCE($5, gmb_address),
                               gmb_enriched_at  = NOW()
                           WHERE id = $1""",
                        bu_id,
                        maps_result.get("gmb_rating"),
                        maps_result.get("gmb_review_count"),
                        maps_result.get("phone"),
                        maps_result.get("address"),
                    )
                    stats["gmb_enriched"] += 1
            except Exception as exc:
                self._logger.error("GMB error for %s: %s", domain, exc)
                stats["errors"].append({"step": "gmb", "domain": domain, "error": str(exc)})

            if (i + 1) % 10 == 0:
                self._logger.info("PaidEnrichment GMB: %d/%d", i + 1, len(passing_rows))

        # STEP 3 — Intelligence endpoints (Directive #303)
        # Runs competitors, backlinks, brand SERP, and indexed pages for each domain.
        intel_results: dict[str, Any] = {}

        async def _sem_call(coro):  # type: ignore[type-arg]
            async with GLOBAL_SEM_DFS:
                return await coro

        for row in passing_rows:
            domain = row["domain"]
            bu_id = row["id"]
            business_name = row.get("display_name") or row.get("gmb_name") or extract_business_name(domain)
            try:
                (
                    comp_result,
                    bl_result,
                    serp_result,
                    idx_result,
                ) = await asyncio.gather(
                    _sem_call(self._dfs.competitors_domain(domain)),
                    _sem_call(self._dfs.backlinks_summary(domain)),
                    _sem_call(self._dfs.brand_serp(business_name, location_code=2036)),
                    _sem_call(self._dfs.indexed_pages(domain)),
                    return_exceptions=True,
                )

                # Parse competitors
                comp_items = []
                competitor_count = 0
                if isinstance(comp_result, dict):
                    comp_items = [
                        item.get("domain")
                        for item in (comp_result.get("items") or [])
                        if item.get("domain")
                    ][:3]
                    competitor_count = len(comp_result.get("items") or [])

                # Parse backlinks
                referring_domains = 0
                domain_rank = 0
                backlink_trend = "unknown"
                if isinstance(bl_result, dict):
                    referring_domains = bl_result.get("referring_domains") or 0
                    domain_rank = bl_result.get("domain_rank") or 0
                    backlink_trend = bl_result.get("backlink_trend") or "unknown"

                # Parse brand SERP
                brand_position = None
                brand_gmb_showing = False
                brand_competitors_bidding = False
                if isinstance(serp_result, dict):
                    brand_position = serp_result.get("brand_position")
                    brand_gmb_showing = bool(serp_result.get("gmb_showing"))
                    brand_competitors_bidding = bool(serp_result.get("competitors_bidding"))

                # Parse indexed pages
                indexed_pages = int(idx_result) if isinstance(idx_result, int) else 0

                intel_results[domain] = {
                    "competitors_top3": comp_items,
                    "competitor_count": competitor_count,
                    "referring_domains": referring_domains,
                    "domain_rank": domain_rank,
                    "backlink_trend": backlink_trend,
                    "brand_position": brand_position,
                    "brand_gmb_showing": brand_gmb_showing,
                    "brand_competitors_bidding": brand_competitors_bidding,
                    "indexed_pages": indexed_pages,
                }

                try:
                    await self._conn.execute(
                        """UPDATE business_universe SET
                               competitors_top3                = $2,
                               competitor_count                = $3,
                               backlinks_referring_domains     = $4,
                               backlinks_domain_rank           = $5,
                               backlinks_trend                 = $6,
                               brand_serp_position             = $7,
                               brand_serp_gmb_showing          = $8,
                               brand_serp_competitors_bidding  = $9,
                               indexed_pages_count             = $10,
                               intelligence_enriched_at        = NOW()
                           WHERE id = $1""",
                        bu_id,
                        comp_items,
                        competitor_count,
                        referring_domains,
                        domain_rank,
                        backlink_trend,
                        brand_position,
                        brand_gmb_showing,
                        brand_competitors_bidding,
                        indexed_pages,
                    )
                except Exception as db_exc:
                    self._logger.warning(
                        "Intelligence DB write error for %s (columns may not exist yet): %s",
                        domain,
                        db_exc,
                    )

            except Exception as exc:
                self._logger.error("Intelligence enrichment error for %s: %s", domain, exc)
                stats["errors"].append({"step": "intelligence", "domain": domain, "error": str(exc)})

        stats["intelligence_enriched"] = len(intel_results)

        # STEP 4 — Mark completion for all passing rows
        for row in passing_rows:
            try:
                await self._conn.execute(
                    "UPDATE business_universe SET paid_enrichment_completed_at = NOW() WHERE id = $1",
                    row["id"],
                )
                stats["completed"] += 1
            except Exception as exc:
                self._logger.error("Completion mark error %s: %s", row["domain"], exc)

        return stats
