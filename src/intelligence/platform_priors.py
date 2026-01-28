"""
FILE: src/intelligence/platform_priors.py
PURPOSE: Industry benchmark priors for ALS scoring and conversion patterns
PHASE: 20 (Platform Intelligence)
TASK: PLT-001
DEPENDENCIES: None

SOURCES:
  - Ruler Analytics: B2B conversion rates by industry (Aug 2025)
  - First Page Sage: B2B conversion rates report (Sep 2025)
  - Martal Group: Conversion rate statistics (Nov 2025)
  - SerpSculpt: B2B sales conversion rates (Aug 2025)
  - Kalungi: B2B SaaS funnel benchmarks (Sep 2025)
  - MarketJoy: B2B pipeline conversion data (Sep 2025)

These priors are used as fallback weights until the platform has
accumulated enough conversion data from clients to learn optimal weights.

HYBRID APPROACH:
  Phase 1 (Now): Seed with these industry benchmarks
  Phase 2 (Launch): Data co-op agreement in founding customer terms
  Phase 3 (Month 4+): Platform learning activates, aggregates real data

RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - No external dependencies required
"""

from typing import Any

# =============================================================================
# PLATFORM PRIORS - INDUSTRY BENCHMARK DERIVED
# =============================================================================

PLATFORM_PRIORS: dict[str, Any] = {
    # -------------------------------------------------------------------------
    # ALS (Agency Lead Score) Weight Priors
    # -------------------------------------------------------------------------
    # Derived from B2B conversion research showing:
    # - Title/authority highly predictive of B2B conversion
    # - Company fit (industry, size) correlates with deal success
    # - Timing signals (intent data) increasingly important
    # - Data quality less predictive than originally assumed
    # -------------------------------------------------------------------------
    "als_weights": {
        "data_quality": 0.15,   # Reduced from 0.20 - less predictive
        "authority": 0.30,      # Increased from 0.25 - decision-maker critical
        "company_fit": 0.25,    # Includes DataForSEO signals
        "timing": 0.20,         # Increased from 0.15 - intent matters
        "risk": 0.10,           # Reduced from 0.15 - fewer false negatives
    },

    # -------------------------------------------------------------------------
    # Timing Patterns
    # -------------------------------------------------------------------------
    # Research consensus: Mid-week, business hours outperform
    # B2B buyers more receptive Tue-Thu, 9-11am and 2-4pm
    # Monday morning = inbox overwhelm, Friday afternoon = checked out
    # -------------------------------------------------------------------------
    "timing_patterns": {
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": [9, 10, 14, 15],  # 9-10am, 2-3pm local time
        "good_hours": [8, 11, 13, 16],  # Acceptable alternatives
        "avoid_periods": [
            "Monday 8-10am",    # Inbox overwhelm
            "Friday 3-5pm",     # Checked out for weekend
            "Sunday",           # Non-business day
        ],
        "day_of_week_lift": {
            "Monday": 0.85,
            "Tuesday": 1.15,
            "Wednesday": 1.10,
            "Thursday": 1.05,
            "Friday": 0.90,
            "Saturday": 0.50,
            "Sunday": 0.40,
        },
    },

    # -------------------------------------------------------------------------
    # Content Patterns
    # -------------------------------------------------------------------------
    # Short subject lines (4-8 words) outperform
    # Body copy 50-125 words optimal for cold outreach
    # Personalization consistently shows 26% lift
    # Questions in subject lines improve open rates
    # -------------------------------------------------------------------------
    "content_patterns": {
        "optimal_subject_length": {"min": 4, "max": 8, "unit": "words"},
        "optimal_body_length": {"min": 50, "max": 125, "unit": "words"},
        "personalization_lift": 1.26,           # 26% improvement
        "question_in_subject_lift": 1.15,       # 15% improvement
        "company_mention_lift": 1.18,           # 18% improvement
        "first_name_usage_lift": 1.12,          # 12% improvement
        "recent_news_mention_lift": 1.22,       # 22% improvement
        "mutual_connection_lift": 1.35,         # 35% improvement
        "industry_specific_lift": 1.20,         # 20% improvement
    },

    # -------------------------------------------------------------------------
    # Channel Patterns
    # -------------------------------------------------------------------------
    # Multi-channel sequences outperform single channel
    # Email-first sequences most common in winning campaigns
    # LinkedIn addition provides 35% lift
    # Voice (costly) provides 85% lift for qualified leads
    # -------------------------------------------------------------------------
    "channel_patterns": {
        "email_first_sequence_rate": 0.67,      # 67% of wins start email
        "linkedin_touch_lift": 1.35,            # 35% lift when included
        "voice_touch_lift": 1.85,               # 85% lift (use selectively)
        "sms_touch_lift": 1.25,                 # 25% lift (permission required)
        "direct_mail_touch_lift": 1.40,         # 40% lift (expensive)
        "optimal_touches_before_convert": 4,    # Average touches to conversion
        "max_touches_recommended": 8,           # Diminishing returns after
        "days_between_touches": {
            "email_to_email": 3,
            "email_to_linkedin": 2,
            "linkedin_to_voice": 5,
            "any_to_followup": 4,
        },
    },

    # -------------------------------------------------------------------------
    # Funnel Conversion Benchmarks
    # -------------------------------------------------------------------------
    # From aggregated B2B research - marketing agency vertical
    # Outbound typically converts 1-3% lead-to-meeting
    # These are baseline expectations, not targets
    # -------------------------------------------------------------------------
    "funnel_benchmarks": {
        "visitor_to_lead": 0.023,               # 2.3% website visitors → leads
        "lead_to_mql": 0.31,                    # 31% leads → MQL
        "mql_to_sql": 0.13,                     # 13% MQL → SQL (biggest drop)
        "sql_to_opportunity": 0.45,             # 30-59% SQL → Opp
        "opportunity_to_close": 0.26,           # 22-30% Opp → Customer

        # Outbound-specific (cold email/LinkedIn)
        "cold_email_open_rate": 0.25,           # 25% open rate
        "cold_email_reply_rate": 0.02,          # 2% reply rate
        "cold_email_positive_reply": 0.30,      # 30% of replies positive
        "linkedin_connection_rate": 0.25,       # 25% accept rate
        "linkedin_message_reply_rate": 0.08,    # 8% reply to message
        "cold_call_connect_rate": 0.08,         # 8% answer rate
        "cold_call_meeting_rate": 0.15,         # 15% of connects → meeting
    },

    # -------------------------------------------------------------------------
    # Authority/Title Conversion Patterns
    # -------------------------------------------------------------------------
    # C-suite and founders convert at higher rates
    # Directors/VPs are key decision influencers
    # Managers typically require escalation
    # -------------------------------------------------------------------------
    "authority_patterns": {
        "title_conversion_lift": {
            "CEO": 1.45,
            "Founder": 1.40,
            "Owner": 1.35,
            "Managing Director": 1.30,
            "CMO": 1.25,
            "VP Marketing": 1.20,
            "Director": 1.10,
            "Head of": 1.15,
            "Manager": 0.85,
            "Coordinator": 0.65,
            "Specialist": 0.60,
        },
    },

    # -------------------------------------------------------------------------
    # Company Size Patterns
    # -------------------------------------------------------------------------
    # Sweet spot varies by offer price point
    # For Agency OS ($2,500-$7,500/mo): 5-50 employees optimal
    # Larger companies have longer sales cycles
    # -------------------------------------------------------------------------
    "company_size_patterns": {
        "optimal_employee_range": {"min": 5, "max": 50},
        "size_conversion_lift": {
            "1-4": 0.70,      # May not have budget
            "5-10": 1.20,     # Decision-maker accessible
            "11-25": 1.35,    # Sweet spot
            "26-50": 1.25,    # Good fit
            "51-100": 1.00,   # Longer cycle
            "101-250": 0.85,  # Committee decisions
            "251-500": 0.70,  # Enterprise complexity
            "500+": 0.50,     # Very long cycle
        },
    },

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    "metadata": {
        "sources": [
            "Ruler Analytics - Average Conversion Rate by Industry (Aug 2025)",
            "First Page Sage - B2B Conversion Rates Report (Sep 2025)",
            "Martal Group - Conversion Rate Statistics 2026 (Nov 2025)",
            "SerpSculpt - B2B Sales Conversion Rate by Industry (Aug 2025)",
            "Kalungi - B2B SaaS Funnel Benchmark Conversion Rates (Sep 2025)",
            "MarketJoy - B2B Sales Pipeline Conversion Rates (Sep 2025)",
            "EngageTech - Marketing Conversion Rate Benchmarks",
        ],
        "confidence": 0.5,  # Moderate confidence until validated with platform data
        "last_updated": "2026-01-04",
        "target_vertical": "Marketing Agencies (Australia, UK, Canada, USA)",
        "target_company_size": "5-50 employees",
        "target_price_point": "$2,500-$7,500 AUD/month",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_als_weights() -> dict[str, float]:
    """Get ALS weight priors for scoring."""
    return PLATFORM_PRIORS["als_weights"].copy()


def get_timing_patterns() -> dict[str, Any]:
    """Get timing pattern priors."""
    return PLATFORM_PRIORS["timing_patterns"].copy()


def get_content_patterns() -> dict[str, Any]:
    """Get content pattern priors."""
    return PLATFORM_PRIORS["content_patterns"].copy()


def get_channel_patterns() -> dict[str, Any]:
    """Get channel pattern priors."""
    return PLATFORM_PRIORS["channel_patterns"].copy()


def get_authority_lift(title: str) -> float:
    """
    Get conversion lift factor for a job title.

    Args:
        title: Job title to look up

    Returns:
        Lift factor (1.0 = baseline, >1 = better, <1 = worse)
    """
    title_patterns = PLATFORM_PRIORS["authority_patterns"]["title_conversion_lift"]
    title_lower = title.lower()

    for pattern, lift in title_patterns.items():
        if pattern.lower() in title_lower:
            return lift

    return 1.0  # Default baseline


def get_size_lift(employee_count: int) -> float:
    """
    Get conversion lift factor for company size.

    Args:
        employee_count: Number of employees

    Returns:
        Lift factor (1.0 = baseline, >1 = better, <1 = worse)
    """
    size_patterns = PLATFORM_PRIORS["company_size_patterns"]["size_conversion_lift"]

    if employee_count < 5:
        return size_patterns["1-4"]
    elif employee_count <= 10:
        return size_patterns["5-10"]
    elif employee_count <= 25:
        return size_patterns["11-25"]
    elif employee_count <= 50:
        return size_patterns["26-50"]
    elif employee_count <= 100:
        return size_patterns["51-100"]
    elif employee_count <= 250:
        return size_patterns["101-250"]
    elif employee_count <= 500:
        return size_patterns["251-500"]
    else:
        return size_patterns["500+"]


def get_day_lift(day_name: str) -> float:
    """
    Get conversion lift factor for day of week.

    Args:
        day_name: Day name (e.g., "Monday", "Tuesday")

    Returns:
        Lift factor (1.0 = baseline)
    """
    day_lifts = PLATFORM_PRIORS["timing_patterns"]["day_of_week_lift"]
    return day_lifts.get(day_name, 1.0)


def is_optimal_send_time(day_name: str, hour: int) -> bool:
    """
    Check if a day/hour combination is optimal for sending.

    Args:
        day_name: Day name (e.g., "Tuesday")
        hour: Hour in 24h format (0-23)

    Returns:
        True if optimal send time
    """
    timing = PLATFORM_PRIORS["timing_patterns"]

    is_best_day = day_name in timing["best_days"]
    is_best_hour = hour in timing["best_hours"]

    return is_best_day and is_best_hour


def get_confidence() -> float:
    """Get confidence level of platform priors."""
    return PLATFORM_PRIORS["metadata"]["confidence"]


# =============================================================================
# VERIFICATION CHECKLIST
# =============================================================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Sources documented
# [x] All patterns have metadata
# [x] Helper functions for common lookups
# [x] Type hints on all functions
# [x] Docstrings on all functions
# [x] Confidence level included
# [x] Last updated date tracked
