"""
Stage 2 GMB Reverse Lookup — Architecture v5
Directive #260

Takes S1-discovered domains (pipeline_stage=1), finds their GMB listing
via Bright Data GMB client, and writes physical identity to BU.

Enriches ONLY. No scoring, no DM discovery, no outreach.
Pipeline progresses to stage 2 whether or not GMB is found.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import asyncpg

from src.integrations.bright_data_gmb_client import BrightDataGMBClient
from src.utils.domain_parser import extract_business_name

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S2 = 2
DEFAULT_BATCH_SIZE = 50
DEFAULT_DELAY_BETWEEN_LOOKUPS = 0.2  # seconds


class Stage2GMBLookup:
    """
    GMB reverse lookup for S1-discovered domains.

    Usage:
        stage = Stage2GMBLookup(bd_gmb_client, conn)
        result = await stage.run(batch_size=50)
    """

    def __init__(
        self,
        gmb_client: BrightDataGMBClient,
        conn: asyncpg.Connection,
        delay: float = DEFAULT_DELAY_BETWEEN_LOOKUPS,
    ) -> None:
        self.gmb = gmb_client
        self.conn = conn
        self.delay = delay

    async def run(self, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
        """
        Process all S1 rows (pipeline_stage=1) in batches.
        Returns {enriched, no_gmb_found, already_enriched, errors, cost_usd}
        """
        rows = await self.conn.fetch(
            """
            SELECT id, domain, gmb_place_id
            FROM business_universe
            WHERE pipeline_stage = 1
            AND domain IS NOT NULL AND domain <> ''
            AND domain LIKE '%.au'
            ORDER BY discovered_at ASC
            LIMIT $1
            """,
            batch_size,
        )

        already_enriched_rows = [r for r in rows if r["gmb_place_id"]]
        already_enriched = len(already_enriched_rows)
        to_process = [r for r in rows if not r["gmb_place_id"]]

        # BUG-265-1: advance already-enriched rows to stage=2 (they were stuck at stage=1)
        now = datetime.now(UTC)
        for row in already_enriched_rows:
            await self.conn.execute(
                """
                UPDATE business_universe SET
                    pipeline_stage = $1,
                    pipeline_updated_at = $2
                WHERE id = $3
                """,
                PIPELINE_STAGE_S2,
                now,
                row["id"],
            )

        enriched = 0
        no_gmb = 0
        errors = 0

        # ── Phase 1: fetch all GMB data concurrently ─────────────────────────
        # Submit all BD jobs at once. BD processes in parallel on their side.
        # Pure httpx — no DB operations. Safe to run fully concurrent.
        # Directive #268: O(n×35s) → O(35s) for the expensive part.
        async def _fetch_gmb(row: asyncpg.Record) -> tuple[str, str, dict | None]:
            """Returns (row_id, domain, gmb_data_or_None). No DB writes."""
            try:
                business_name = extract_business_name(row["domain"])
                logger.info(f"Stage 2: {row['domain']} → searching '{business_name}'")
                data = await self.gmb.search_by_name(business_name)
                return row["id"], row["domain"], data
            except Exception as e:
                logger.error(f"Stage 2 fetch error for {row['domain']}: {e}")
                return row["id"], row["domain"], None

        fetch_results = await asyncio.gather(*[_fetch_gmb(row) for row in to_process])

        # ── Phase 2: write results to DB sequentially ────────────────────────
        # asyncpg requires one active operation per connection. Sequential writes
        # are fast (<1ms each) so total DB write time is negligible.
        now = datetime.now(UTC)
        for row_id, domain, gmb_data in fetch_results:
            try:
                if gmb_data:
                    await self.conn.execute(
                        """
                        UPDATE business_universe SET
                            gmb_place_id = $1,
                            gmb_category = $2,
                            gmb_rating = $3,
                            gmb_review_count = $4,
                            gmb_work_hours = $5,
                            gmb_claimed = $6,
                            gmb_maps_url = $7,
                            gmb_cid = $8,
                            address = COALESCE($9, address),
                            phone = COALESCE($10, phone),
                            lat = COALESCE($11, lat),
                            lng = COALESCE($12, lng),
                            state = COALESCE(
                                (SELECT regexp_match($9, ',\\s*([A-Z]{2,3})\\s+\\d{4}'))[1],
                                state
                            ),
                            suburb = COALESCE(
                                (SELECT (regexp_match($9, '^([^,]+),'))[1]),
                                suburb
                            ),
                            address_source = 'gmb',
                            pipeline_stage = $13,
                            pipeline_updated_at = $14
                        WHERE id = $15
                        """,
                        gmb_data.get("gmb_place_id"),
                        gmb_data.get("gmb_category"),
                        gmb_data.get("gmb_rating"),
                        gmb_data.get("gmb_review_count"),
                        gmb_data.get("gmb_work_hours"),
                        gmb_data.get("gmb_claimed"),
                        gmb_data.get("gmb_maps_url"),
                        gmb_data.get("gmb_cid"),
                        gmb_data.get("address"),
                        gmb_data.get("phone"),
                        gmb_data.get("lat"),
                        gmb_data.get("lng"),
                        PIPELINE_STAGE_S2,
                        now,
                        row_id,
                    )
                    enriched += 1
                else:
                    await self.conn.execute(
                        "UPDATE business_universe SET pipeline_stage=$1, pipeline_updated_at=$2 WHERE id=$3",
                        PIPELINE_STAGE_S2,
                        now,
                        row_id,
                    )
                    no_gmb += 1
            except Exception as e:
                logger.error(f"Stage 2 DB write error for {domain}: {e}")
                errors += 1

        result = {
            "enriched": enriched,
            "no_gmb_found": no_gmb,
            "already_enriched": already_enriched,
            "errors": errors,
            "cost_usd": float(self.gmb.total_cost_usd),
        }
        logger.info(f"Stage 2 complete: {result}")
        return result

    async def run_single(self, domain: str) -> dict[str, Any]:
        """For testing individual lookups."""
        row = await self.conn.fetchrow(
            "SELECT id, domain, gmb_place_id FROM business_universe WHERE domain = $1",
            domain,
        )
        if not row:
            return {"status": "not_found"}
        business_name = extract_business_name(domain)
        gmb_data = await self.gmb.search_by_name(business_name)
        now = datetime.now(UTC)
        if gmb_data:
            await self.conn.execute(
                "UPDATE business_universe SET gmb_place_id=$1, gmb_category=$2, pipeline_stage=$3, pipeline_updated_at=$4 WHERE id=$5",
                gmb_data.get("gmb_place_id"),
                gmb_data.get("gmb_category"),
                PIPELINE_STAGE_S2,
                now,
                row["id"],
            )
            return {"status": "enriched"}
        else:
            await self.conn.execute(
                "UPDATE business_universe SET pipeline_stage=$1, pipeline_updated_at=$2 WHERE id=$3",
                PIPELINE_STAGE_S2,
                now,
                row["id"],
            )
            return {"status": "no_gmb_found"}
