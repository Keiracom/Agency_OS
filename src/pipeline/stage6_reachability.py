# FILE: src/pipeline/stage6_reachability.py
# PURPOSE: Stage 6 — Reachability scoring + mobile enrichment gate + pipeline completion
# PIPELINE STAGE: 5 → 6
# DEPENDENCIES: src.integrations.leadmagic, asyncpg
# DIRECTIVE: #251

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

# Channel access
SIGNAL_EMAIL_VERIFIED = 35
SIGNAL_EMAIL_UNVERIFIED = 12
SIGNAL_LINKEDIN_URL = 15
SIGNAL_MOBILE = 20
SIGNAL_WEBSITE = 5
SIGNAL_GMB_PHONE = 8

# Quality multipliers — applied as additive bonus
SIGNAL_HIGH_EMAIL_CONFIDENCE = 5
SIGNAL_HIGH_DM_CONFIDENCE = 5
SIGNAL_FULL_IDENTITY = 7

# Derived
MOBILE_LOOKUP_COST_AUD = Decimal("0.07700")
MOBILE_SCORE_THRESHOLD = 70


class Stage6Reachability:
    def __init__(self, leadmagic_client, db) -> None:
        self.client = leadmagic_client
        self.db = db
        self._mobile_cost = Decimal("0")

    async def run(
        self,
        mobile_threshold: int = 70,
        batch_size: int = 100,
        mobile_spend_cap_aud: float = 5.0,
    ) -> dict:
        """
        Two-pass reachability scoring + mobile gate for BU rows at pipeline_stage=5.
        Pass 1: score all rows without mobile.
        Pass 2: enrich mobile for high-score rows where dm_linkedin_url exists.
        Then mark pipeline_complete.
        """
        scored = mobile_attempted = mobile_found = completed = 0
        errors = []

        # Fetch all stage 5 rows
        rows = await self.db.fetch("""
            SELECT id, dm_email, dm_email_verified, dm_email_confidence,
                   dm_linkedin_url, dm_mobile, dm_name, dm_title, dm_confidence,
                   website, domain, phone
            FROM business_universe
            WHERE pipeline_stage = 5
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        """, batch_size)

        for row in rows:
            try:
                # PASS 1: Score without mobile
                score = self._score(row, include_mobile=False)

                await self.db.execute("""
                    UPDATE business_universe SET reachability_score = $1
                    WHERE id = $2
                """, score, row["id"])
                scored += 1

            except Exception as e:
                errors.append({"id": str(row["id"]), "error": f"pass1: {e}"})

        # PASS 2: Mobile enrichment for high-reachability rows
        if self._mobile_cost < Decimal(str(mobile_spend_cap_aud)):
            high_reach_rows = await self.db.fetch("""
                SELECT id, dm_linkedin_url, dm_mobile, dm_email, dm_email_verified,
                       dm_email_confidence, dm_confidence, website, domain, phone,
                       dm_name, dm_title
                FROM business_universe
                WHERE pipeline_stage = 5
                  AND reachability_score >= $1
                  AND dm_linkedin_url IS NOT NULL
                  AND dm_mobile IS NULL
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            """, mobile_threshold, batch_size)

            for row in high_reach_rows:
                if self._mobile_cost + MOBILE_LOOKUP_COST_AUD > Decimal(str(mobile_spend_cap_aud)):
                    break
                mobile_attempted += 1
                try:
                    mobile_result = await self.client.find_mobile(row["dm_linkedin_url"])
                    if mobile_result and getattr(mobile_result, "found", False):
                        phone = getattr(mobile_result, "mobile_number", None)
                        if phone:
                            # Recalculate score with mobile
                            updated_row = dict(row)
                            updated_row["dm_mobile"] = phone
                            new_score = self._score(updated_row, include_mobile=True)
                            await self.db.execute("""
                                UPDATE business_universe SET
                                    dm_mobile = $1,
                                    reachability_score = $2,
                                    enrichment_cost_aud = COALESCE(enrichment_cost_aud, 0) + $3,
                                    last_enriched_at = NOW()
                                WHERE id = $4
                            """, phone, new_score, MOBILE_LOOKUP_COST_AUD, row["id"])
                            self._mobile_cost += MOBILE_LOOKUP_COST_AUD
                            mobile_found += 1
                        else:
                            self._mobile_cost += MOBILE_LOOKUP_COST_AUD
                    else:
                        self._mobile_cost += MOBILE_LOOKUP_COST_AUD
                except Exception as e:
                    errors.append({"id": str(row["id"]), "error": f"mobile: {e}"})

        # Final pass: mark all stage 5 rows as pipeline_complete
        await self.db.execute("""
            UPDATE business_universe SET
                pipeline_stage = 6,
                pipeline_status = 'pipeline_complete',
                last_enriched_at = NOW()
            WHERE pipeline_stage = 5
        """)
        # Count completed
        completed_result = await self.db.fetchval("""
            SELECT COUNT(*) FROM business_universe WHERE pipeline_stage = 6
        """)
        completed = completed_result or 0

        return {
            "scored": scored,
            "mobile_attempted": mobile_attempted,
            "mobile_found": mobile_found,
            "completed": completed,
            "cost_aud": float(self._mobile_cost),
            "errors": errors,
        }

    def _score(self, row: dict, include_mobile: bool = False) -> int:
        pts = 0

        # Channel access
        if row.get("dm_email_verified"):
            pts += SIGNAL_EMAIL_VERIFIED
        elif row.get("dm_email"):
            pts += SIGNAL_EMAIL_UNVERIFIED

        if row.get("dm_linkedin_url"):
            pts += SIGNAL_LINKEDIN_URL

        if include_mobile and row.get("dm_mobile"):
            pts += SIGNAL_MOBILE

        if row.get("website") or row.get("domain"):
            pts += SIGNAL_WEBSITE

        if row.get("phone"):
            pts += SIGNAL_GMB_PHONE

        # Quality bonuses
        confidence = row.get("dm_email_confidence") or 0
        if confidence >= 80:
            pts += SIGNAL_HIGH_EMAIL_CONFIDENCE

        dm_conf = row.get("dm_confidence")
        if dm_conf is not None:
            try:
                if Decimal(str(dm_conf)) >= Decimal("0.80"):
                    pts += SIGNAL_HIGH_DM_CONFIDENCE
            except Exception:
                pass

        if row.get("dm_name") and row.get("dm_title"):
            pts += SIGNAL_FULL_IDENTITY

        return min(pts, 100)
