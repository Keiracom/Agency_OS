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
from datetime import datetime, timezone
from typing import Any

import asyncpg

from src.clients.bright_data_gmb_client import BrightDataGMBClient
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
            ORDER BY discovered_at ASC
            LIMIT $1
            """,
            batch_size,
        )

        already_enriched_rows = [r for r in rows if r["gmb_place_id"]]
        already_enriched = len(already_enriched_rows)
        to_process = [r for r in rows if not r["gmb_place_id"]]

        # BUG-265-1: advance already-enriched rows to stage=2 (they were stuck at stage=1)
        now = datetime.now(timezone.utc)
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

        for row in to_process:
            try:
                ok = await self._lookup_and_update(row["id"], row["domain"])
                if ok:
                    enriched += 1
                else:
                    no_gmb += 1
            except Exception as e:
                logger.error(f"Stage 2 error for {row['domain']}: {e}")
                errors += 1
            if self.delay > 0:
                await asyncio.sleep(self.delay)

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
        ok = await self._lookup_and_update(row["id"], row["domain"])
        return {"status": "enriched" if ok else "no_gmb_found"}

    async def _lookup_and_update(self, row_id: str, domain: str) -> bool:
        """
        Look up GMB for domain and update BU.
        Returns True if GMB found, False if not.
        """
        if not domain:
            logger.warning(f"S2: skipping row {row_id} — empty domain")
            return False
        now = datetime.now(timezone.utc)
        business_name = extract_business_name(domain)
        logger.info(f"Stage 2: {domain} → searching '{business_name}'")

        gmb_data = await self.gmb.search_by_name(business_name)

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
            return True
        else:
            # No GMB — still progress to S2
            await self.conn.execute(
                """
                UPDATE business_universe SET
                    pipeline_stage = $1,
                    pipeline_updated_at = $2
                WHERE id = $3
                """,
                PIPELINE_STAGE_S2,
                now,
                row_id,
            )
            return False
