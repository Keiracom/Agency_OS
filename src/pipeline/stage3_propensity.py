# FILE: src/pipeline/stage3_propensity.py
# PURPOSE: Stage 3 — Propensity scoring for business_universe rows
# PIPELINE STAGE: 2 → 3
# DEPENDENCIES: asyncpg
# DIRECTIVE: #250

from __future__ import annotations

import datetime
import json
from datetime import timezone

# Category A — max 35
SIGNAL_TIMING_ADS = 15
SIGNAL_TIMING_LOW_RATING = 10
SIGNAL_TIMING_STALE_SITE = 5
SIGNAL_TIMING_NEW_BUSINESS = 5

# Category B — max 25
SIGNAL_DIGITAL_GA = 8
SIGNAL_DIGITAL_FB_PIXEL = 5
SIGNAL_DIGITAL_CONVERSION = 5
SIGNAL_DIGITAL_MOBILE = 4
SIGNAL_DIGITAL_BOOKING = 2
SIGNAL_DIGITAL_WEBSITE = 1

# Category C — max 25
SIGNAL_BUSINESS_REVIEWS_LOW = 5
SIGNAL_BUSINESS_REVIEWS_MID = 8
SIGNAL_BUSINESS_REVIEWS_HIGH = 5
SIGNAL_BUSINESS_GST = 4
SIGNAL_BUSINESS_YP_LISTED = 2
SIGNAL_BUSINESS_YP_ADVERTISER = 8
SIGNAL_BUSINESS_YP_LONGEVITY = 3  # per bracket, applied once

# Category D — max 15
SIGNAL_FIT_CATEGORY = 8
SIGNAL_FIT_GEOGRAPHY = 5
SIGNAL_FIT_ENTITY = 2

# Derived
PROPENSITY_STAGE_THRESHOLD = 40  # min score to attempt DM identification
STALE_SITE_YEARS = 2
NEW_BUSINESS_MONTHS = 18
LOW_GMB_RATING = 3.5


class Stage3Propensity:
    def __init__(self, db) -> None:
        self.db = db

    async def run(self, batch_size: int = 100) -> dict:
        """
        Score all BU rows at pipeline_stage=2, pipeline_status='signals_collected'.
        Returns: scored, above_threshold, below_threshold, errors
        """
        scored = above_threshold = below_threshold = 0
        errors = []

        rows = await self.db.fetch("""
            SELECT id, display_name, state, suburb, gmb_category,
                   gmb_rating, gmb_review_count, gmb_claimed,
                   has_google_ads, has_google_analytics, has_facebook_pixel,
                   has_conversion_tracking, is_mobile_responsive, has_booking_system,
                   website, domain, gst_registered, entity_type,
                   listed_on_yp, yp_advertiser, yp_years_in_business,
                   registration_date, site_copyright_year, abn_status
            FROM business_universe
            WHERE pipeline_stage = 2 AND pipeline_status = 'signals_collected'
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        """, batch_size)

        for row in rows:
            try:
                signals = dict(row)
                score, reasons = self._score(signals)
                above = score >= PROPENSITY_STAGE_THRESHOLD
                if above:
                    above_threshold += 1
                else:
                    below_threshold += 1

                reasons_serialized = [json.dumps(r) for r in reasons]
                await self.db.execute("""
                    UPDATE business_universe SET
                        propensity_score = $1,
                        propensity_reasons = $2,
                        scored_at = NOW(),
                        category_baselines = NULL,
                        pipeline_stage = 3,
                        pipeline_status = 'scored'
                    WHERE id = $3
                """, score, reasons_serialized, row["id"])
                scored += 1
            except Exception as e:
                errors.append({"id": str(row["id"]), "error": str(e)})

        return {
            "scored": scored,
            "above_threshold": above_threshold,
            "below_threshold": below_threshold,
            "errors": errors,
        }

    def _score(self, s: dict) -> tuple[int, list[dict]]:
        """Returns (score 0-100, reasons list)."""
        pts = 0
        reasons = []

        # Category A
        if s.get("has_google_ads"):
            pts += SIGNAL_TIMING_ADS
            reasons.append({"signal": "has_google_ads", "category": "timing"})
        if s.get("gmb_rating") and float(s["gmb_rating"]) < LOW_GMB_RATING:
            pts += SIGNAL_TIMING_LOW_RATING
            reasons.append({"signal": "low_gmb_rating", "category": "timing"})
        if s.get("site_copyright_year"):
            age = datetime.date.today().year - s["site_copyright_year"]
            if age >= STALE_SITE_YEARS:
                pts += SIGNAL_TIMING_STALE_SITE
                reasons.append({"signal": "stale_site", "category": "timing"})
        if s.get("registration_date"):
            months = (datetime.date.today() - s["registration_date"]).days / 30
            if months <= NEW_BUSINESS_MONTHS:
                pts += SIGNAL_TIMING_NEW_BUSINESS
                reasons.append({"signal": "new_business", "category": "timing"})

        # Category B
        if s.get("has_google_analytics"):
            pts += SIGNAL_DIGITAL_GA
            reasons.append({"signal": "has_google_analytics", "category": "digital"})
        if s.get("has_facebook_pixel"):
            pts += SIGNAL_DIGITAL_FB_PIXEL
            reasons.append({"signal": "has_facebook_pixel", "category": "digital"})
        if s.get("has_conversion_tracking"):
            pts += SIGNAL_DIGITAL_CONVERSION
            reasons.append({"signal": "has_conversion_tracking", "category": "digital"})
        if s.get("is_mobile_responsive"):
            pts += SIGNAL_DIGITAL_MOBILE
            reasons.append({"signal": "is_mobile_responsive", "category": "digital"})
        if s.get("has_booking_system"):
            pts += SIGNAL_DIGITAL_BOOKING
            reasons.append({"signal": "has_booking_system", "category": "digital"})
        if s.get("website") or s.get("domain"):
            pts += SIGNAL_DIGITAL_WEBSITE
            reasons.append({"signal": "has_website", "category": "digital"})

        # Category C
        count = s.get("gmb_review_count") or 0
        if count >= 5:
            pts += SIGNAL_BUSINESS_REVIEWS_LOW
            reasons.append({"signal": "gmb_reviews_5plus", "category": "business"})
        if count >= 20:
            pts += SIGNAL_BUSINESS_REVIEWS_MID
            reasons.append({"signal": "gmb_reviews_20plus", "category": "business"})
        if count >= 50:
            pts += SIGNAL_BUSINESS_REVIEWS_HIGH
            reasons.append({"signal": "gmb_reviews_50plus", "category": "business"})
        if s.get("gst_registered"):
            pts += SIGNAL_BUSINESS_GST
            reasons.append({"signal": "gst_registered", "category": "business"})
        if s.get("listed_on_yp"):
            pts += SIGNAL_BUSINESS_YP_LISTED
            reasons.append({"signal": "listed_on_yp", "category": "business"})
        if s.get("yp_advertiser"):
            pts += SIGNAL_BUSINESS_YP_ADVERTISER
            reasons.append({"signal": "yp_advertiser", "category": "business"})
        yp_years = s.get("yp_years_in_business") or 0
        if yp_years >= 3:
            pts += SIGNAL_BUSINESS_YP_LONGEVITY
            reasons.append({"signal": "yp_longevity_3plus", "category": "business"})

        # Category D: fit signals applied by orchestrator when campaign context is available

        return (min(pts, 100), reasons)
