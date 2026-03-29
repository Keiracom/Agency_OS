"""
Contract: src/pipeline/paid_enrichment.py
Purpose: Paid enrichment pass — affordability gate + DFS bulk metrics + DFS Maps GMB
Layer: 4 - orchestration (uses asyncpg connection directly)
Imports: asyncpg, clients (dfs_labs_client, dfs_gmaps_client)
Consumers: orchestration flows
Directive: #283
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg

from src.clients.dfs_gmaps_client import DFSGMapsClient
from src.clients.dfs_labs_client import DFSLabsClient
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


async def affordability_gate(
    conn: asyncpg.Connection,
    limit: int = 1000,
) -> tuple[list[asyncpg.Record], list[asyncpg.Record]]:
    """
    Query BU for domains ready for paid enrichment. Apply 4-gate filter.
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

    passing: list[asyncpg.Record] = []
    failing: list[tuple[asyncpg.Record, str]] = []

    for row in rows:
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

        # STEP 3 — Mark completion for all passing rows
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
