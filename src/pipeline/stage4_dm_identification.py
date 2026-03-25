# FILE: src/pipeline/stage4_dm_identification.py
# PURPOSE: Stage 4 — DM identification via DFS SERP
# PIPELINE STAGE: 3 → 4
# DEPENDENCIES: DFSSerpClient, asyncpg
# DIRECTIVE: #250

import logging
from decimal import Decimal

from src.clients.dfs_serp_client import COST_PER_SERP_AUD, DFSSerpClient

logger = logging.getLogger(__name__)


class Stage4DMIdentification:
    def __init__(self, dfs_serp_client: DFSSerpClient, db) -> None:
        self.serp = dfs_serp_client
        self.db = db

    async def run(
        self,
        propensity_threshold: int = 40,
        batch_size: int = 50,
        daily_spend_cap_aud: float = 10.0,
    ) -> dict:
        attempted = dm_found = dm_not_found = skipped = 0
        errors = []

        # Fetch rows above threshold
        rows = await self.db.fetch("""
            SELECT id, display_name, suburb, state, propensity_score
            FROM business_universe
            WHERE pipeline_stage = 3 AND pipeline_status = 'scored'
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        """, batch_size)

        for row in rows:
            if row["propensity_score"] is None or row["propensity_score"] < propensity_threshold:
                # Below threshold — advance without DM search
                await self.db.execute("""
                    UPDATE business_universe SET
                        pipeline_stage = 4,
                        pipeline_status = 'dm_skipped_low_propensity'
                    WHERE id = $1
                """, row["id"])
                skipped += 1
                continue

            # Spend cap check
            if self.serp.estimated_cost_aud + COST_PER_SERP_AUD > Decimal(str(daily_spend_cap_aud)):
                errors.append({
                    "reason": "spend_cap_reached",
                    "id": str(row["id"]),
                    "cost_aud": float(self.serp.estimated_cost_aud),
                })
                # Still advance stage for remaining rows
                await self.db.execute("""
                    UPDATE business_universe SET pipeline_stage = 4, pipeline_status = 'dm_skipped_spend_cap'
                    WHERE id = $1
                """, row["id"])
                continue

            attempted += 1
            try:
                dm = await self.serp.find_decision_maker(
                    business_name=row["display_name"],
                    suburb=row["suburb"],
                    state=row["state"],
                )
                if dm:
                    await self.db.execute("""
                        UPDATE business_universe SET
                            dm_name = $1, dm_title = $2, dm_linkedin_url = $3,
                            dm_source = $4, dm_confidence = $5,
                            pipeline_stage = 4, pipeline_status = 'dm_found'
                        WHERE id = $6
                    """, dm.get("dm_name"), dm.get("dm_title"), dm.get("dm_linkedin_url"),
                        dm.get("dm_source"), dm.get("dm_confidence"), row["id"])
                    dm_found += 1
                else:
                    await self.db.execute("""
                        UPDATE business_universe SET
                            pipeline_stage = 4, pipeline_status = 'dm_searched'
                        WHERE id = $1
                    """, row["id"])
                    dm_not_found += 1
            except Exception as e:
                errors.append({"id": str(row["id"]), "error": str(e)})
                await self.db.execute("""
                    UPDATE business_universe SET pipeline_stage = 4, pipeline_status = 'dm_error'
                    WHERE id = $1
                """, row["id"])

        return {
            "attempted": attempted,
            "dm_found": dm_found,
            "dm_not_found": dm_not_found,
            "skipped_below_threshold": skipped,
            "cost_aud": float(self.serp.estimated_cost_aud),
            "errors": errors,
        }
