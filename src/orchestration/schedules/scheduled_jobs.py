"""
FILE: src/orchestration/schedules/scheduled_jobs.py
PURPOSE: Prefect schedule configurations for automated flows
PHASE: 5 (Orchestration), modified Phase 16 for Conversion Intelligence
TASK: ORC-010, 16F-004
DEPENDENCIES:
  - src/orchestration/flows/enrichment_flow.py
  - src/orchestration/flows/outreach_flow.py
  - src/orchestration/flows/reply_recovery_flow.py
  - src/orchestration/flows/pattern_learning_flow.py (Phase 16)
  - src/orchestration/flows/pattern_backfill_flow.py (Phase 16)
  - src/engines/reporter.py
RULES APPLIED:
  - Rule 20: Webhook-first architecture - cron jobs are safety nets only
  - Rule 1: Follow blueprint exactly
  - Prefect 3.x schedule patterns
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
