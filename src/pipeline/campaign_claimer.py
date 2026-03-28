# FILE: src/pipeline/campaign_claimer.py
# PURPOSE: Claim pipeline_complete BU rows for a campaign
# DEPENDENCIES: asyncpg
# DIRECTIVE: #252

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class CampaignClaimer:
    def __init__(self, db) -> None:
        self.db = db

    async def claim_for_campaign(
        self,
        campaign_id: UUID,
        client_id: UUID,
        filters: dict[str, Any] | None = None,
        max_claims: int = 100,
    ) -> dict:
        """
        Claim pipeline_complete BU rows for a campaign.

        filters:
          min_propensity: int (default 40)
          min_reachability: int (default 30)
          gmb_category: str | None
          state: str | None

        Returns:
          claimed, skipped_already_claimed, skipped_suppressed, errors
        """
        f = filters or {}
        min_propensity = f.get("min_propensity", 40)
        min_reachability = f.get("min_reachability", 30)
        gmb_category = f.get("gmb_category")
        state = f.get("state")

        # Build WHERE clauses
        where_parts = [
            "bu.pipeline_stage = 6",
            "bu.pipeline_status = 'pipeline_complete'",
            "bu.propensity_score >= $1",
            "bu.reachability_score >= $2",
            # Exclude already claimed by this campaign
            """NOT EXISTS (
                SELECT 1 FROM campaign_leads cl2
                WHERE cl2.business_universe_id = bu.id
                  AND cl2.campaign_id = $3
            )""",
            # Exclude suppressed by this agency/client
            """NOT EXISTS (
                SELECT 1 FROM lead_agency_suppression las
                WHERE las.business_universe_id = bu.id
                  AND las.client_id = $4
                  AND (las.expires_at IS NULL OR las.expires_at > NOW())
            )""",
        ]
        params: list[Any] = [min_propensity, min_reachability, campaign_id, client_id]

        if gmb_category:
            params.append(gmb_category)
            where_parts.append(f"bu.gmb_category ILIKE ${len(params)}")
        if state:
            params.append(state)
            where_parts.append(f"bu.state = ${len(params)}")

        params.append(max_claims)
        limit_placeholder = f"${len(params)}"

        select_sql = f"""
            SELECT bu.id as bu_id
            FROM business_universe bu
            WHERE {' AND '.join(where_parts)}
            ORDER BY bu.propensity_score DESC, bu.reachability_score DESC
            LIMIT {limit_placeholder}
        """

        claimed = 0
        errors: list[dict] = []

        async with self.db.acquire() as conn, conn.transaction():
            rows = await conn.fetch(select_sql, *params)

            for row in rows:
                try:
                    await conn.execute("""
                        INSERT INTO campaign_leads
                            (campaign_id, business_universe_id, client_id, status, claimed_at)
                        VALUES ($1, $2, $3, 'never_touched', NOW())
                        ON CONFLICT (campaign_id, business_universe_id) DO NOTHING
                    """, campaign_id, row["bu_id"], client_id)
                    claimed += 1
                except Exception as e:
                    errors.append({"bu_id": str(row["bu_id"]), "error": str(e)})

        return {
            "claimed": claimed,
            "errors": errors,
        }
