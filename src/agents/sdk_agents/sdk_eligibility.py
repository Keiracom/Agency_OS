"""
Contract: src/agents/sdk_agents/sdk_eligibility.py
Purpose: Determine SDK eligibility based on ALS score and priority signals
Layer: 3 - agents (can import models, integrations)
Consumers: scout engine, content engine, voice engine

SDK Eligibility Rules:
- SDK Enrichment: Hot leads (ALS >= 85) WITH at least one priority signal (~20% of Hot)
- SDK Email: ALL Hot leads (ALS >= 85)
- SDK Voice KB: ALL Hot leads (ALS >= 85)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ALS threshold for Hot tier (per CLAUDE.md: Hot = 85-100, NOT 80-100)
HOT_THRESHOLD = 85


def should_use_sdk_enrichment(lead_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Check if lead qualifies for SDK ENRICHMENT (selective).

    Requirements:
    1. Must be Hot (ALS >= 85)
    2. Must have at least ONE priority signal

    Priority Signals:
    1. Recent funding (< 90 days)
    2. Actively hiring (3+ roles)
    3. Tech stack match > 80%
    4. LinkedIn engagement > 70
    5. Referral source
    6. Employee count sweet spot (50-500)

    Args:
        lead_data: Dict with lead info including als_score and company data

    Returns:
        Tuple of (eligible: bool, signals: list[str])
    """
    # Gate 1: Must be Hot
    als_score = lead_data.get("als_score") or 0
    if als_score < HOT_THRESHOLD:
        return False, []

    signals: list[str] = []

    # Signal 1: Recent funding (< 90 days)
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
            except TypeError:
                # Handle case where funding_date is date not datetime
                from datetime import date
                if isinstance(funding_date, date):
                    days_since = (datetime.utcnow().date() - funding_date).days
                    if 0 <= days_since <= 90:
                        signals.append(f"recent_funding_{days_since}d")

    # Signal 2: Actively hiring (3+ roles)
    hiring_count = lead_data.get("company_open_roles") or lead_data.get("company_is_hiring") or 0
    if isinstance(hiring_count, bool):
        # If it's a boolean, treat True as 3+ for backwards compatibility
        if hiring_count:
            signals.append("actively_hiring")
    elif isinstance(hiring_count, int) and hiring_count >= 3:
        signals.append(f"hiring_{hiring_count}_roles")

    # Signal 3: Tech stack match > 80%
    tech_match = lead_data.get("tech_stack_match_score") or 0
    if tech_match > 0.8:
        signals.append(f"tech_match_{int(tech_match * 100)}pct")

    # Signal 4: LinkedIn engagement > 70
    li_engagement = lead_data.get("linkedin_engagement_score") or 0
    if li_engagement > 70:
        signals.append(f"linkedin_engaged_{li_engagement}")

    # Signal 5: Referral source
    source = (lead_data.get("source") or "").lower()
    if source == "referral":
        signals.append("referral")

    # Signal 6: Employee count sweet spot (50-500)
    emp_count = lead_data.get("company_employee_count") or lead_data.get("organization_employee_count") or 0
    if 50 <= emp_count <= 500:
        signals.append(f"sweet_spot_{emp_count}_employees")

    # Must have at least one signal to qualify for SDK enrichment
    return len(signals) > 0, signals


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
