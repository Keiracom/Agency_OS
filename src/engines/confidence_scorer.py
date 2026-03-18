"""
confidence_scorer.py
Revenue confidence scoring for business_universe.
Pure function — no DB calls, no side effects.
Ratified: March 17 2026 | Directive #215
See ARCHITECTURE.md Section 5 for signal definitions.
"""
from typing import Any


CONFIDENCE_FLOOR_TO_ENRICH = 50


def score_business_confidence(signals: dict[str, Any]) -> int:
    """
    Score a business's revenue confidence 0-100.
    Uses signals already present in business_universe.
    Returns integer. Caller decides what to do with it.

    Scoring:
      gst_registered = True            +25
      dfs_paid_traffic_cost > 0        +25
      dfs_organic_traffic >= 1000      +15
      job_listings_active > 0          +15
      gmb_review_count >= 10           +10
      gmb_review_count >= 20           +5 (bonus)
      linkedin_employee_count >= 5     +10
      domain_age_years >= 2            +10
      Max: 115 — capped at 100.
    """
    score = 0

    if signals.get("gst_registered"):
        score += 25

    paid_cost = signals.get("dfs_paid_traffic_cost")
    if paid_cost and float(paid_cost) > 0:
        score += 25

    organic = signals.get("dfs_organic_traffic")
    if organic and float(organic) >= 1000:
        score += 15

    jobs = signals.get("job_listings_active", 0)
    if jobs and int(jobs) > 0:
        score += 15

    reviews = signals.get("gmb_review_count", 0)
    if reviews and int(reviews) >= 10:
        score += 10
    if reviews and int(reviews) >= 20:
        score += 5

    employees = signals.get("linkedin_employee_count")
    if employees and int(employees) >= 5:
        score += 10

    domain_age = signals.get("domain_age_years", 0)
    if domain_age and float(domain_age) >= 2:
        score += 10

    return min(score, 100)


def meets_enrichment_threshold(signals: dict[str, Any]) -> bool:
    """
    Returns True if business should proceed to
    Leadmagic email/mobile enrichment.
    Threshold: CONFIDENCE_FLOOR_TO_ENRICH = 50
    """
    return score_business_confidence(signals) >= CONFIDENCE_FLOOR_TO_ENRICH
