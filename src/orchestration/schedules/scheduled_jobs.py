"""
FILE: src/orchestration/schedules/scheduled_jobs.py
PURPOSE: Prefect schedule configurations for automated flows
PHASE: 5 (Orchestration), modified Phase 16 for Conversion Intelligence, P0 for Credit Reset, Phase D for DNCR
TASK: ORC-010, 16F-004, P0-001, Item 13
DEPENDENCIES:
  - src/orchestration/flows/enrichment_flow.py
  - src/orchestration/flows/outreach_flow.py
  - src/orchestration/flows/reply_recovery_flow.py
  - src/orchestration/flows/pattern_learning_flow.py (Phase 16)
  - src/orchestration/flows/pattern_backfill_flow.py (Phase 16)
  - src/orchestration/flows/credit_reset_flow.py (P0)
  - src/orchestration/flows/dncr_rewash_flow.py (Phase D - DNCR compliance)
  - src/orchestration/flows/linkedin_health_flow.py (Phase D - LinkedIn warmup/health)
  - src/orchestration/flows/daily_pacing_flow.py (Item 15 - Daily pacing)
  - src/orchestration/flows/monthly_replenishment_flow.py (Item 17 - Monthly replenishment)
  - src/engines/reporter.py
RULES APPLIED:
  - Rule 20: Webhook-first architecture - cron jobs are safety nets only
  - Rule 1: Follow blueprint exactly
  - Prefect 3.x schedule patterns
  - DNCR quarterly re-wash for Australian SMS compliance
"""

from datetime import time
from typing import Dict, Any
from zoneinfo import ZoneInfo

from prefect.client.schemas.schedules import (
    CronSchedule,
    IntervalSchedule,
)


# Australia/Sydney timezone for all schedules
AEST = ZoneInfo("Australia/Sydney")


def get_enrichment_schedule() -> CronSchedule:
    """
    Daily enrichment at 2 AM AEST.

    This is a safety net - primary enrichment triggered by webhooks.
    Catches any leads that need re-enrichment or failed previously.

    Returns:
        CronSchedule: Daily at 2 AM AEST
    """
    return CronSchedule(
        cron="0 2 * * *",  # 2 AM daily
        timezone="Australia/Sydney",
    )


def get_outreach_schedule() -> CronSchedule:
    """
    Hourly outreach during business hours (8 AM - 6 PM AEST, Mon-Fri).

    This is a safety net - primary outreach triggered by webhooks.
    Processes any queued outreach during business hours.

    Returns:
        CronSchedule: Hourly 8 AM-6 PM weekdays AEST
    """
    # Run at the top of every hour from 8 AM to 6 PM, Monday-Friday
    return CronSchedule(
        cron="0 8-18 * * 1-5",  # Top of hour, 8am-6pm, Mon-Fri
        timezone="Australia/Sydney",
    )


def get_reply_recovery_schedule() -> IntervalSchedule:
    """
    Reply recovery every 6 hours.

    This is a safety net for missed reply webhooks.
    Checks for unprocessed replies from all channels.

    Returns:
        IntervalSchedule: Every 6 hours
    """
    return IntervalSchedule(
        interval=21600,  # 6 hours in seconds
        timezone="Australia/Sydney",
    )


def get_metrics_schedule() -> CronSchedule:
    """
    Daily metrics aggregation at midnight AEST.

    Generates daily reports and metrics snapshots.
    Uses Reporter engine for aggregation.

    Returns:
        CronSchedule: Daily at midnight AEST
    """
    return CronSchedule(
        cron="0 0 * * *",  # Midnight daily
        timezone="Australia/Sydney",
    )


# ============================================
# Phase 16: Conversion Intelligence Schedules
# ============================================


def get_pattern_learning_schedule() -> CronSchedule:
    """
    Weekly pattern learning at 3 AM Sunday AEST.

    Runs all 4 detectors (WHO, WHAT, WHEN, HOW) for eligible clients
    and optimizes ALS weights based on conversion history.

    Weekly frequency balances data freshness with compute cost.
    Runs on Sunday to minimize impact on weekday operations.

    Returns:
        CronSchedule: Sunday 3 AM AEST
    """
    return CronSchedule(
        cron="0 3 * * 0",  # 3 AM every Sunday
        timezone="Australia/Sydney",
    )


def get_pattern_backfill_schedule() -> CronSchedule:
    """
    Daily pattern backfill check at 4 AM AEST.

    Catches new clients or those missing patterns.
    Runs after pattern learning to handle any gaps.

    Returns:
        CronSchedule: Daily at 4 AM AEST
    """
    return CronSchedule(
        cron="0 4 * * *",  # 4 AM daily
        timezone="Australia/Sydney",
    )


# ============================================
# P0: Credit Reset Schedule
# ============================================


def get_credit_reset_schedule() -> CronSchedule:
    """
    Hourly credit reset check.

    Finds clients whose billing date has passed and resets their
    credits_remaining to their tier quota. Critical for billing integrity.

    Runs hourly to catch resets promptly without excessive load.
    Actual reset only happens when credits_reset_at <= now().

    Returns:
        CronSchedule: Every hour at minute 0
    """
    return CronSchedule(
        cron="0 * * * *",  # Top of every hour
        timezone="Australia/Sydney",
    )


# ============================================
# Phase D: LinkedIn Health Schedule
# ============================================


def get_linkedin_health_schedule() -> CronSchedule:
    """
    Daily LinkedIn health check at 6 AM AEST.

    Processes warmup completions, updates health metrics,
    marks stale connections, and detects restrictions.

    Runs early morning before business hours to ensure
    limits are correctly set for the day.

    Returns:
        CronSchedule: Daily at 6 AM AEST
    """
    return CronSchedule(
        cron="0 6 * * *",  # 6 AM daily
        timezone="Australia/Sydney",
    )


# ============================================
# Item 15: Daily Pacing Schedule
# ============================================


def get_daily_pacing_schedule() -> CronSchedule:
    """
    Daily pacing check at 7 AM AEST.

    Monitors lead consumption rate for all active clients.
    Flags clients burning >120% or <50% of expected pace.

    Runs daily to catch pacing issues early.

    Returns:
        CronSchedule: Daily at 7 AM AEST
    """
    return CronSchedule(
        cron="0 7 * * *",  # 7 AM daily
        timezone="Australia/Sydney",
    )


# ============================================
# Phase D: DNCR Compliance Schedule
# ============================================


def get_dncr_rewash_schedule() -> CronSchedule:
    """
    Quarterly DNCR re-wash on 1st of Jan, Apr, Jul, Oct at 5 AM AEST.

    Re-checks all Australian phone numbers against the Do Not Call Register
    to ensure compliance with ACMA regulations. Numbers can be added/removed
    from the register at any time, so quarterly re-checks are required.

    Runs at 5 AM to avoid business hours impact.

    Returns:
        CronSchedule: 1st of Jan, Apr, Jul, Oct at 5 AM AEST
    """
    return CronSchedule(
        # Day 1, months 1 (Jan), 4 (Apr), 7 (Jul), 10 (Oct), at 5 AM
        cron="0 5 1 1,4,7,10 *",
        timezone="Australia/Sydney",
    )


# Schedule registry for deployment configuration
SCHEDULE_REGISTRY: Dict[str, Any] = {
    "enrichment": {
        "schedule": get_enrichment_schedule(),
        "description": "Daily enrichment safety net at 2 AM AEST",
        "work_queue": "agency-os-queue",
        "tags": ["enrichment", "daily", "safety-net"],
        "parameters": {
            "batch_size": 100,
            "max_clay_percentage": 0.15,
        },
    },
    "outreach": {
        "schedule": get_outreach_schedule(),
        "description": "Hourly outreach during business hours (8 AM-6 PM AEST, Mon-Fri)",
        "work_queue": "agency-os-queue",
        "tags": ["outreach", "hourly", "business-hours"],
        "parameters": {
            "batch_size": 50,
            "respect_rate_limits": True,
        },
    },
    "reply_recovery": {
        "schedule": get_reply_recovery_schedule(),
        "description": "Reply recovery safety net every 6 hours",
        "work_queue": "agency-os-queue",
        "tags": ["replies", "recovery", "safety-net"],
        "parameters": {
            "lookback_hours": 6,
            "check_all_channels": True,
        },
    },
    "metrics": {
        "schedule": get_metrics_schedule(),
        "description": "Daily metrics aggregation at midnight AEST",
        "work_queue": "agency-os-queue",
        "tags": ["metrics", "reporting", "daily"],
        "parameters": {
            "include_als_distribution": True,
            "include_engagement": True,
        },
    },
    # Phase 16: Conversion Intelligence
    "pattern_learning": {
        "schedule": get_pattern_learning_schedule(),
        "description": "Weekly pattern learning at 3 AM Sunday AEST",
        "work_queue": "agency-os-queue",
        "tags": ["conversion-intelligence", "patterns", "weekly"],
        "parameters": {
            "min_conversions": 20,
        },
    },
    "pattern_backfill": {
        "schedule": get_pattern_backfill_schedule(),
        "description": "Daily pattern backfill check at 4 AM AEST",
        "work_queue": "agency-os-queue",
        "tags": ["conversion-intelligence", "backfill", "daily"],
        "parameters": {
            "min_activities": 50,
        },
    },
    # P0: Credit Reset
    "credit_reset": {
        "schedule": get_credit_reset_schedule(),
        "description": "Hourly credit reset check for billing integrity",
        "work_queue": "agency-os-queue",
        "tags": ["billing", "credits", "hourly", "critical"],
        "parameters": {},
    },
    # Phase D: LinkedIn Health
    "linkedin_health": {
        "schedule": get_linkedin_health_schedule(),
        "description": "Daily LinkedIn seat health and warmup management at 6 AM AEST",
        "work_queue": "agency-os-queue",
        "tags": ["linkedin", "health", "warmup", "daily"],
        "parameters": {
            "stale_days": 14,
        },
    },
    # Phase D: DNCR Compliance
    "dncr_rewash": {
        "schedule": get_dncr_rewash_schedule(),
        "description": "Quarterly DNCR re-wash for Australian SMS compliance (1st of Jan, Apr, Jul, Oct)",
        "work_queue": "agency-os-queue",
        "tags": ["compliance", "dncr", "sms", "quarterly"],
        "parameters": {
            "stale_days": 90,
            "max_leads": 10000,
            "batch_size": 500,
        },
    },
    # Item 15: Daily Pacing
    "daily_pacing": {
        "schedule": get_daily_pacing_schedule(),
        "description": "Daily pacing check at 7 AM AEST - monitors lead consumption rate",
        "work_queue": "agency-os-queue",
        "tags": ["pacing", "daily", "monitoring"],
        "parameters": {
            "fast_threshold": 1.2,  # 120%
            "slow_threshold": 0.5,  # 50%
        },
    },
    # Item 17: Monthly Replenishment (triggered by credit_reset, not scheduled)
    "monthly_replenishment": {
        "schedule": None,  # Triggered by credit_reset_flow, not scheduled
        "description": "Post-credit-reset lead replenishment (triggered, not scheduled)",
        "work_queue": "agency-os-queue",
        "tags": ["leads", "monthly", "replenishment"],
        "parameters": {
            "force_full": False,  # Default: smart replenishment (gap only)
        },
    },
    # Item 18: Campaign Evolution (triggered after pattern_learning, not scheduled)
    "campaign_evolution": {
        "schedule": None,  # Triggered after pattern_learning_flow, not scheduled
        "description": "CIS-driven campaign optimization suggestions (triggered, not scheduled)",
        "work_queue": "agency-os-queue",
        "tags": ["campaigns", "evolution", "cis", "suggestions"],
        "parameters": {
            "force": False,  # Default: check eligibility
        },
    },
}


def get_schedule_config(schedule_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific schedule.

    Args:
        schedule_name: Name of the schedule (enrichment, outreach, reply_recovery, metrics)

    Returns:
        Schedule configuration dictionary

    Raises:
        KeyError: If schedule name not found
    """
    if schedule_name not in SCHEDULE_REGISTRY:
        raise KeyError(
            f"Schedule '{schedule_name}' not found. "
            f"Available schedules: {list(SCHEDULE_REGISTRY.keys())}"
        )

    return SCHEDULE_REGISTRY[schedule_name]


def list_all_schedules() -> Dict[str, str]:
    """
    List all available schedules with descriptions.

    Returns:
        Dictionary mapping schedule names to descriptions
    """
    return {
        name: config["description"]
        for name, config in SCHEDULE_REGISTRY.items()
    }


# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Uses Prefect 3.x schedule patterns
# [x] Timezone handling for Australia (AEST/AEDT auto-handled by ZoneInfo)
# [x] Work queue assignments defined
# [x] Webhook-first architecture noted (schedules are safety nets)
# [x] Business hours schedule (8 AM-6 PM AEST, Mon-Fri) for outreach
# [x] Daily enrichment at 2 AM AEST
# [x] 6-hourly reply recovery
# [x] Midnight metrics aggregation
# [x] Schedule registry for deployment automation
# --- Phase 16 Additions ---
# [x] Weekly pattern learning at 3 AM Sunday AEST
# [x] Daily pattern backfill at 4 AM AEST
# [x] Conversion Intelligence schedules in registry
# --- P0: Credit Reset ---
# [x] Hourly credit reset check
# [x] Credit reset in schedule registry with "critical" tag
# --- Phase D: LinkedIn Health ---
# [x] Daily LinkedIn health check at 6 AM AEST
# [x] LinkedIn warmup processing
# [x] LinkedIn health metrics and limit reductions
# --- Phase D: DNCR Compliance ---
# [x] Quarterly DNCR re-wash (1st of Jan, Apr, Jul, Oct at 5 AM AEST)
# [x] DNCR re-wash in schedule registry with compliance tags
# --- Item 15: Daily Pacing ---
# [x] Daily pacing check at 7 AM AEST
# [x] Daily pacing in schedule registry with pacing/monitoring tags
# [x] Parameters for fast_threshold (1.2) and slow_threshold (0.5)
# --- Item 17: Monthly Replenishment ---
# [x] Monthly replenishment in schedule registry (on-demand, not scheduled)
# [x] Triggered by credit_reset_flow, not cron scheduled
# [x] Parameters for force_full mode
