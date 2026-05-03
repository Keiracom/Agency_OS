"""
FILE: src/pipeline/conversion_feedback.py
PURPOSE: Query CIS conversion data to generate category-level scoring boosts
PHASE: BU audit gap #7 — conversion feedback loop
"""

import logging

logger = logging.getLogger(__name__)

# Boost applied per conversion tier
CONVERSION_BOOST = {
    "high": 15,  # >=5 conversions in category in last 90 days
    "moderate": 10,  # 3-4 conversions
    "low": 5,  # 1-2 conversions
    "none": 0,  # 0 conversions
}


async def get_category_conversion_boost(conn, gmb_category: str | None) -> int:
    """Query CIS for recent conversions in this category and return score boost.

    Looks at cis_outreach_outcomes joined to business_universe to find how many
    conversions happened in domains with the same gmb_category in the last 90 days.

    Returns integer boost (0-15) to add to rescore combined score.
    """
    if not gmb_category:
        return 0

    try:
        # Join path: cis_outreach_outcomes.lead_id → leads.id → leads.domain → business_universe.domain
        # Verified against migrations: 061_cis_schema (lead_id UUID), 004_leads (domain TEXT)
        count = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM cis_outreach_outcomes o
            JOIN leads l ON l.id = o.lead_id
            JOIN business_universe bu ON bu.domain = l.domain
            WHERE bu.gmb_category = $1
              AND o.converted_at IS NOT NULL
              AND o.converted_at > NOW() - INTERVAL '90 days'
        """,
            gmb_category,
        )

        count = count or 0
        if count >= 5:
            return CONVERSION_BOOST["high"]
        elif count >= 3:
            return CONVERSION_BOOST["moderate"]
        elif count >= 1:
            return CONVERSION_BOOST["low"]
        return CONVERSION_BOOST["none"]
    except Exception as exc:
        logger.warning("conversion_feedback query failed for %s: %s", gmb_category, exc)
        return 0  # fail-open
