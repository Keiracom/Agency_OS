"""
opportunity_scorer.py
Opportunity scoring for business_universe.
Identifies businesses with real scale but
low digital presence — highest-value targets
for marketing agency representation.
Pure function — no DB calls, no side effects.
Ratified: March 18 2026 | Directive #217
See ARCHITECTURE.md Section 6.
"""
from typing import Any


OPPORTUNITY_PRIORITY_THRESHOLD = 60

STRUCTURAL_GAP_INDUSTRIES = [
    "construction", "trade", "plumbing",
    "electrical", "roofing", "concreting",
    "landscaping", "cleaning", "pest control",
    "healthcare", "dental", "medical",
    "physiotherapy", "chiropractic",
    "professional services", "accounting",
    "legal", "financial planning",
    "hospitality", "restaurant", "cafe",
    "hotel", "accommodation",
    "manufacturing", "wholesale",
    "automotive", "mechanic",
]


def score_business_opportunity(
    signals: dict[str, Any]
) -> int:
    """
    Score a business's opportunity level 0-100.
    High score = real business + low digital
    presence = untapped potential for agency.

    Scoring:
        gmb_review_count >= 20      +20
        gmb_review_count >= 40      +10 bonus
        abr_age_years >= 5          +20
        multiple_gmb_locations      +15
        hiring_signals_detected     +20
        industry_structural_gap     +15
        dfs_paid_traffic_cost == 0  +10
        dfs_organic_traffic < 500   +10
    Max 120, capped at 100.
    """
    score = 0

    reviews = signals.get("gmb_review_count", 0)
    if reviews and int(reviews) >= 20:
        score += 20
    if reviews and int(reviews) >= 40:
        score += 10

    abr_age = signals.get("abr_age_years", 0)
    if abr_age and float(abr_age) >= 5:
        score += 20

    if signals.get("multiple_gmb_locations"):
        score += 15

    if signals.get("hiring_signals_detected"):
        score += 20

    industry = (signals.get("gmb_category") or "").lower()
    if any(ind in industry for ind in STRUCTURAL_GAP_INDUSTRIES):
        score += 15

    paid = signals.get("dfs_paid_traffic_cost")
    if paid is None or float(paid or 0) == 0:
        score += 10

    organic = signals.get("dfs_organic_traffic")
    if organic is None or float(organic or 0) < 500:
        score += 10

    return min(score, 100)


def is_priority_opportunity(
    signals: dict[str, Any]
) -> bool:
    """
    Returns True if business is a priority
    opportunity — real scale, clear gap.
    Threshold: OPPORTUNITY_PRIORITY_THRESHOLD = 60
    """
    return score_business_opportunity(signals) >= OPPORTUNITY_PRIORITY_THRESHOLD


def get_opportunity_reason(
    signals: dict[str, Any]
) -> str:
    """
    Returns plain English reason for opportunity
    score. Feeds dashboard display.
    Never exposes raw score or weights.
    """
    reasons = []
    reviews = signals.get("gmb_review_count", 0)
    if reviews and int(reviews) >= 20:
        reasons.append(
            f"{reviews} customer reviews — established trading volume"
        )
    if signals.get("hiring_signals_detected"):
        reasons.append("actively hiring — growing business")
    if (signals.get("abr_age_years") or 0) >= 5:
        reasons.append("trading 5+ years — proven operation")
    paid = signals.get("dfs_paid_traffic_cost")
    if paid is None or float(paid or 0) == 0:
        reasons.append(
            "no digital ad spend detected — clear gap for agency value"
        )
    if not reasons:
        reasons.append(
            "established business with marketing opportunity identified"
        )
    return ". ".join(reasons[:2]).capitalize()
