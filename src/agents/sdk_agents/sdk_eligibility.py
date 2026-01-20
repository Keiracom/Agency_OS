"""
Contract: src/agents/sdk_agents/sdk_eligibility.py
Purpose: Determine SDK eligibility based on ALS score and priority signals
Layer: 3 - agents (can import models, integrations)
Consumers: scout engine, content engine, voice engine

SDK Eligibility Rules (Phase 4 Tiered Enrichment):
- SDK Enrichment: Tiered based on data completeness and lead characteristics
- SDK Email: ALL Hot leads (ALS >= 85)
- SDK Voice KB: ALL Hot leads (ALS >= 85)

Tiered SDK Enrichment Triggers:
1. Data completeness < 50% (sparse data from Apollo/Apify)
2. Enterprise company (500+ employees)
3. Executive title (CEO, Founder, VP, Director)
4. Recently funded (< 90 days)

Cost Comparison:
- Apify refresh: ~$0.02/lead
- SDK refresh: ~$0.40/lead
Only use SDK when Google search results likely exist (press, podcasts, conferences).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ALS threshold for Hot tier (per CLAUDE.md: Hot = 85-100, NOT 80-100)
HOT_THRESHOLD = 85

# Executive titles that warrant SDK enrichment
EXECUTIVE_TITLES = [
    "ceo", "chief executive", "founder", "co-founder", "cofounder",
    "vp", "vice president", "director", "head of", "svp", "evp",
    "cto", "cfo", "cmo", "coo", "cpo", "ciso", "chief",
    "president", "owner", "partner", "managing director",
]

# Minimum employee count for "enterprise" classification
ENTERPRISE_THRESHOLD = 500

# Data completeness threshold for SDK enrichment
COMPLETENESS_THRESHOLD = 0.50

# Fields used to calculate data completeness (weighted)
DATA_COMPLETENESS_FIELDS = {
    # Core person fields (weight: 2)
    "first_name": 2,
    "last_name": 2,
    "email": 2,
    "title": 2,
    "linkedin_url": 2,
    # Company fields (weight: 1.5)
    "company_name": 1.5,
    "company_domain": 1.5,
    "company_industry": 1.5,
    "company_employee_count": 1.5,
    # LinkedIn enrichment fields (weight: 1)
    "linkedin_headline": 1,
    "linkedin_about": 1,
    "linkedin_posts": 1,
    # Company signals (weight: 1)
    "company_is_hiring": 1,
    "company_latest_funding_stage": 1,
    "company_technologies": 1,
    # Enrichment metadata (weight: 0.5)
    "enrichment_data": 0.5,
    "pain_points": 0.5,
    "icebreaker_hooks": 0.5,
}


def calculate_data_completeness(lead_data: dict[str, Any]) -> float:
    """
    Calculate how complete a lead's enrichment data is.

    Uses weighted scoring where core fields (name, email, title, company)
    are worth more than optional enrichment fields.

    Args:
        lead_data: Dict with lead enrichment data

    Returns:
        Float between 0.0 and 1.0 representing completeness
    """
    total_weight = sum(DATA_COMPLETENESS_FIELDS.values())
    earned_weight = 0.0

    for field, weight in DATA_COMPLETENESS_FIELDS.items():
        value = lead_data.get(field)
        if value:
            # Check for non-empty values
            if isinstance(value, str) and value.strip():
                earned_weight += weight
            elif isinstance(value, (list, dict)) and len(value) > 0:
                earned_weight += weight
            elif isinstance(value, (int, float, bool)):
                earned_weight += weight

    completeness = earned_weight / total_weight if total_weight > 0 else 0.0
    return round(completeness, 2)


def is_executive_title(title: str | None) -> bool:
    """
    Check if a title indicates an executive position.

    Executives are more likely to have Google-searchable presence
    (press releases, podcast appearances, conference talks).

    Args:
        title: Job title string

    Returns:
        True if title indicates executive level
    """
    if not title:
        return False

    title_lower = title.lower()
    return any(exec_title in title_lower for exec_title in EXECUTIVE_TITLES)


def should_use_sdk_enrichment(lead_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Check if lead qualifies for SDK ENRICHMENT using tiered approach.

    Phase 4 Tiered Triggers (any ONE qualifies):
    1. Data completeness < 50% (sparse data from Apollo/Apify)
    2. Enterprise company (500+ employees)
    3. Executive title (CEO, Founder, VP, Director)
    4. Recently funded (< 90 days)

    IMPORTANT: SDK enrichment only valuable when Google results exist.
    Average mid-market contacts have no press/podcast coverage.

    Args:
        lead_data: Dict with lead info including als_score and company data

    Returns:
        Tuple of (eligible: bool, signals: list[str])
    """
    # Gate 1: Must be Hot (ALS >= 85)
    als_score = lead_data.get("als_score") or 0
    if als_score < HOT_THRESHOLD:
        return False, []

    signals: list[str] = []

    # Trigger 1: Sparse data (completeness < 50%)
    completeness = calculate_data_completeness(lead_data)
    if completeness < COMPLETENESS_THRESHOLD:
        signals.append(f"sparse_data_{int(completeness * 100)}pct")
        logger.debug(f"SDK trigger: sparse data ({completeness:.0%} complete)")

    # Trigger 2: Enterprise company (500+ employees)
    emp_count = lead_data.get("company_employee_count") or lead_data.get("organization_employee_count") or 0
    if emp_count >= ENTERPRISE_THRESHOLD:
        signals.append(f"enterprise_{emp_count}_employees")
        logger.debug(f"SDK trigger: enterprise ({emp_count} employees)")

    # Trigger 3: Executive title
    title = lead_data.get("title") or ""
    if is_executive_title(title):
        signals.append(f"executive_{title.lower().replace(' ', '_')[:20]}")
        logger.debug(f"SDK trigger: executive title ({title})")

    # Trigger 4: Recent funding (< 90 days)
    funding_date = lead_data.get("company_latest_funding_date")
    if funding_date:
        if isinstance(funding_date, str):
            try:
                funding_date = datetime.fromisoformat(funding_date[:10])
            except ValueError:
                funding_date = None
        if funding_date:
            try:
                days_since = (datetime.utcnow() - funding_date).days
                if 0 <= days_since <= 90:
                    signals.append(f"recent_funding_{days_since}d")
                    logger.debug(f"SDK trigger: recent funding ({days_since} days ago)")
            except TypeError:
                # Handle case where funding_date is date not datetime
                from datetime import date
                if isinstance(funding_date, date):
                    days_since = (datetime.utcnow().date() - funding_date).days
                    if 0 <= days_since <= 90:
                        signals.append(f"recent_funding_{days_since}d")
                        logger.debug(f"SDK trigger: recent funding ({days_since} days ago)")

    # Legacy signals (still valid but lower priority)
    # Signal: Actively hiring (3+ roles)
    hiring_count = lead_data.get("company_open_roles") or lead_data.get("company_is_hiring") or 0
    if isinstance(hiring_count, bool):
        if hiring_count:
            signals.append("actively_hiring")
    elif isinstance(hiring_count, int) and hiring_count >= 3:
        signals.append(f"hiring_{hiring_count}_roles")

    # Signal: Tech stack match > 80%
    tech_match = lead_data.get("tech_stack_match_score") or 0
    if tech_match > 0.8:
        signals.append(f"tech_match_{int(tech_match * 100)}pct")

    # Signal: LinkedIn engagement > 70
    li_engagement = lead_data.get("linkedin_engagement_score") or 0
    if li_engagement > 70:
        signals.append(f"linkedin_engaged_{li_engagement}")

    # Signal: Referral source
    source = (lead_data.get("source") or "").lower()
    if source == "referral":
        signals.append("referral")

    # Must have at least one signal to qualify for SDK enrichment
    eligible = len(signals) > 0
    if eligible:
        logger.info(f"Lead qualifies for SDK enrichment: {signals}")

    return eligible, signals


def should_use_sdk_email(lead_data: dict[str, Any]) -> bool:
    """
    Check if lead qualifies for SDK EMAIL (all Hot).

    Simple check: ALS >= 85

    Args:
        lead_data: Dict with lead info including als_score

    Returns:
        True if lead is Hot tier
    """
    als_score = lead_data.get("als_score") or 0
    return als_score >= HOT_THRESHOLD


def should_use_sdk_voice_kb(lead_data: dict[str, Any]) -> bool:
    """
    Check if lead qualifies for SDK VOICE KB (all Hot).

    Simple check: ALS >= 85

    Args:
        lead_data: Dict with lead info including als_score

    Returns:
        True if lead is Hot tier
    """
    als_score = lead_data.get("als_score") or 0
    return als_score >= HOT_THRESHOLD


def get_sdk_coverage_estimate(total_leads: int, hot_percentage: float = 0.10) -> dict[str, Any]:
    """
    Estimate SDK usage based on lead volume.

    Assumes:
    - 10% of leads are Hot (ALS 85+)
    - 20% of Hot leads have signals (SDK enrichment)
    - 100% of Hot leads get SDK email
    - 100% of Hot leads get SDK voice KB

    Args:
        total_leads: Total number of leads
        hot_percentage: Percentage expected to be Hot (default 10%)

    Returns:
        Dict with coverage estimates and cost projections
    """
    hot_count = int(total_leads * hot_percentage)
    sdk_enrichment_count = int(hot_count * 0.20)  # 20% of Hot have signals
    sdk_email_count = hot_count
    sdk_voice_kb_count = hot_count

    # Cost estimates (per lead, AUD)
    enrichment_cost = 1.21  # ~$1.00-1.21 per enrichment
    email_cost = 0.25       # ~$0.20-0.25 per email
    voice_kb_cost = 1.79    # ~$1.50-1.79 per voice KB

    return {
        "total_leads": total_leads,
        "hot_leads": hot_count,
        "hot_percentage": hot_percentage,
        "sdk_enrichment": {
            "count": sdk_enrichment_count,
            "estimated_cost_aud": round(sdk_enrichment_count * enrichment_cost, 2),
        },
        "sdk_email": {
            "count": sdk_email_count,
            "estimated_cost_aud": round(sdk_email_count * email_cost, 2),
        },
        "sdk_voice_kb": {
            "count": sdk_voice_kb_count,
            "estimated_cost_aud": round(sdk_voice_kb_count * voice_kb_cost, 2),
        },
        "total_estimated_cost_aud": round(
            sdk_enrichment_count * enrichment_cost
            + sdk_email_count * email_cost
            + sdk_voice_kb_count * voice_kb_cost,
            2
        ),
    }
