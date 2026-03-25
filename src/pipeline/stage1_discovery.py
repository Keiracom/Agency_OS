# FILE: src/pipeline/stage1_discovery.py
# PURPOSE: Stage 1 — GMB discovery via DataForSEO Google Maps
# PIPELINE STAGE: 1 (discovered)
# DEPENDENCIES: DFSGMapsClient, SuburbCoordinateLoader, asyncpg
# DIRECTIVE: #249

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from src.clients.dfs_gmaps_client import (
    COST_PER_SEARCH_AUD,
    DFSGMapsClient,
    DFSInvalidLocationError,
)
from src.data.suburb_coordinates import SuburbCoordinateLoader

logger = logging.getLogger(__name__)


class Stage1Discovery:
    """
    Stage 1 Discovery — orchestrates GMB business discovery via DFSGMapsClient.

    For each suburb in the target state, calls DataForSEO Google Maps to discover
    GMB listings, deduplicates against business_universe, inserts new records with
    pipeline_stage=1, then runs ABR name+state match against abn_registry.

    Directive: #249
    """

    def __init__(
        self,
        dfs_client: DFSGMapsClient,
        suburb_loader: SuburbCoordinateLoader,
        db: Any,  # asyncpg connection or pool — match codebase pattern
    ) -> None:
        self.dfs_client = dfs_client
        self.suburb_loader = suburb_loader
        self.db = db

    async def run(self, campaign_config: dict) -> dict:
        """
        Execute Stage 1 discovery for a campaign.

        campaign_config keys:
          category: str        e.g. "digital marketing agency"
          state: str           e.g. "NSW"  (OR suburbs: list[dict] with lat/lng/suburb/state)
          campaign_id: uuid    (used for logging only — BU is a shared pool)
          client_id: uuid      (used for logging only)
          daily_spend_cap_aud: float  default 20.0

        Returns dict:
          discovered: int
          duplicates_skipped: int
          abr_matched: int
          cost_aud: float
          suburbs_searched: int
          errors: list[dict]
        """
        category: str = campaign_config["category"]
        state: str = campaign_config.get("state", "")
        campaign_id = campaign_config.get("campaign_id")
        client_id = campaign_config.get("client_id")
        daily_spend_cap_aud: float = campaign_config.get("daily_spend_cap_aud", 20.0)

        logger.info(
            f"Stage1Discovery.run: category={category!r} state={state!r} "
            f"campaign_id={campaign_id} client_id={client_id} "
            f"spend_cap={daily_spend_cap_aud}"
        )

        # ── 1. Get suburbs ──────────────────────────────────────────────────
        if "suburbs" in campaign_config:
            suburbs: list[dict] = campaign_config["suburbs"]
        else:
            self.suburb_loader.load()
            suburbs = self.suburb_loader.get_suburbs_by_state(state)

        logger.info(f"Stage1Discovery: {len(suburbs)} suburbs to search")

        # ── Counters ────────────────────────────────────────────────────────
        discovered: int = 0
        duplicates_skipped: int = 0
        abr_matched: int = 0
        suburbs_searched: int = 0
        inserted_ids: list = []
        errors: list[dict] = []

        # ── 2. Per-suburb loop ───────────────────────────────────────────────
        for suburb in suburbs:

            # Spend cap check before each API call
            if (
                self.dfs_client.estimated_cost_aud + COST_PER_SEARCH_AUD
                > Decimal(str(daily_spend_cap_aud))
            ):
                errors.append(
                    {
                        "reason": "spend_cap_reached",
                        "suburb": suburb.get("suburb"),
                        "cost_aud": float(self.dfs_client.estimated_cost_aud),
                    }
                )
                logger.warning(
                    f"Stage1Discovery: spend cap reached at "
                    f"AUD {float(self.dfs_client.estimated_cost_aud):.4f}, "
                    f"stopping after {suburbs_searched} suburbs"
                )
                break

            # DFS discovery call
            try:
                results = await self.dfs_client.discover_by_coordinates(
                    lat=suburb["lat"],
                    lng=suburb["lng"],
                    category=category,
                    zoom=14,
                    depth=100,
                )
            except DFSInvalidLocationError:
                logger.critical(
                    f"40501 on coordinates {suburb['lat']},{suburb['lng']} "
                    f"— should never happen"
                )
                errors.append({"suburb": suburb.get("suburb"), "reason": "invalid_location"})
                continue
            except Exception as e:
                logger.error(f"DFS failed for {suburb.get('suburb')}: {e}")
                errors.append({"suburb": suburb.get("suburb"), "reason": str(e)})
                continue

            suburbs_searched += 1

            # ── 3. Dedup + insert each result ──────────────────────────────
            for item in results:
                place_id = item.get("gmb_place_id")
                if not place_id:
                    continue

                # Dedup check
                existing = await self.db.fetchval(
                    "SELECT 1 FROM business_universe WHERE gmb_place_id = $1",
                    place_id,
                )
                if existing:
                    duplicates_skipped += 1
                    continue

                # Build insert dict — override pipeline_stage to 1
                row = {**item, "pipeline_stage": 1, "pipeline_status": "discovered"}

                # Build INSERT
                cols = list(row.keys())
                vals = list(row.values())
                placeholders = ", ".join(f"${i + 1}" for i in range(len(vals)))
                col_str = ", ".join(cols)

                inserted_id = await self.db.fetchval(
                    f"INSERT INTO business_universe ({col_str}) "
                    f"VALUES ({placeholders}) "
                    f"ON CONFLICT (gmb_place_id) DO NOTHING RETURNING id",
                    *vals,
                )
                if inserted_id:
                    inserted_ids.append(inserted_id)
                    discovered += 1

        # ── 4. ABR match against abn_registry for all newly inserted BUs ───
        if inserted_ids:
            abr_result = await self.db.execute(
                """
                UPDATE business_universe bu
                SET
                    abn = ar.abn,
                    entity_type = ar.entity_type,
                    entity_type_code = ar.entity_type_code,
                    gst_registered = CASE WHEN ar.gst_registered = true THEN true ELSE false END,
                    registration_date = ar.registration_date,
                    abn_status = ar.abn_status,
                    abr_matched_at = NOW()
                FROM abn_registry ar
                WHERE bu.id = ANY($1::uuid[])
                  AND bu.abn IS NULL
                  AND LOWER(bu.display_name) = LOWER(ar.display_name)
                  AND LOWER(bu.state) = LOWER(ar.state)
                  AND ar.abn_status = 'Active'
                """,
                inserted_ids,
            )
            # Parse "UPDATE N" string to get count
            abr_matched = int(abr_result.split()[-1]) if abr_result else 0
            logger.info(f"Stage1Discovery: ABR matched {abr_matched} records")

        summary = {
            "discovered": discovered,
            "duplicates_skipped": duplicates_skipped,
            "abr_matched": abr_matched,
            "cost_aud": float(self.dfs_client.estimated_cost_aud),
            "suburbs_searched": suburbs_searched,
            "errors": errors,
        }
        logger.info(f"Stage1Discovery complete: {summary}")
        return summary
