"""
Contract: src/orchestration/flows/weekly_linkedin_reset_flow.py
Purpose: Monday 00:00 AEST flow that resets LinkedIn weekly counters so each
         new week starts with a fresh 100-connect + 350-message cap per
         account. Idempotent: re-running during the same ISO-week is a no-op.
Layer:   orchestration
Imports: prefect, db connection
Consumers: Prefect scheduler (weekly deployment — Monday)

Works by deleting stale outreach_rate_state rows (channel='linkedin') whose
window_start < this_week_monday_00_utc. The rate_limiter will re-initialise
fresh rows on the next send against any account.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from prefect import flow, task
from prefect.client.schemas.schedules import CronSchedule

logger = logging.getLogger(__name__)

AEST = ZoneInfo("Australia/Sydney")


@dataclass
class LinkedInResetSummary:
    fired_on_monday: bool
    rows_reset: int
    accounts_affected: int
    week_start: datetime


def _current_week_monday(now_aest: datetime) -> datetime:
    """Return Monday 00:00 AEST of the ISO-week containing now_aest."""
    # weekday(): Monday=0 .. Sunday=6
    monday = (now_aest - timedelta(days=now_aest.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return monday


def _is_monday(now_aest: datetime) -> bool:
    return now_aest.weekday() == 0


async def reset_linkedin_weekly(db_conn: Any, now_aest: datetime) -> dict:
    """Delete stale outreach_rate_state rows (linkedin channel) whose
    window_start < this week's Monday 00:00 AEST (converted to UTC for
    comparison).

    Returns {"rows_reset": N, "accounts_affected": M}.

    If now_aest is NOT a Monday, returns zeros and does NOT touch the table.
    """
    if not _is_monday(now_aest):
        return {"rows_reset": 0, "accounts_affected": 0}

    monday_aest = _current_week_monday(now_aest)
    monday_utc = monday_aest.astimezone(UTC)

    # Count affected rows first (for idempotent reporting), then DELETE.
    count_rows = await db_conn.fetch(
        """
        SELECT COUNT(*) AS rows_reset,
               COUNT(DISTINCT account_id) AS accounts_affected
        FROM outreach_rate_state
        WHERE channel = 'linkedin' AND window_start < $1
        """,
        monday_utc,
    )
    # Delete them. Rate limiter re-creates fresh rows on next send.
    await db_conn.execute(
        """
        DELETE FROM outreach_rate_state
        WHERE channel = 'linkedin' AND window_start < $1
        """,
        monday_utc,
    )
    r = count_rows[0] if count_rows else {"rows_reset": 0, "accounts_affected": 0}
    return {"rows_reset": r["rows_reset"], "accounts_affected": r["accounts_affected"]}


@task(name="reset-linkedin-weekly")
async def reset_linkedin_weekly_task(db_conn: Any, now_aest: datetime) -> dict:
    return await reset_linkedin_weekly(db_conn, now_aest)


@flow(name="weekly-linkedin-reset", log_prints=True)
async def weekly_linkedin_reset_flow(
    db_conn: Any,
    now_fn=lambda: datetime.now(AEST),
) -> LinkedInResetSummary:
    now_aest = now_fn()
    result = await reset_linkedin_weekly_task(db_conn, now_aest)
    summary = LinkedInResetSummary(
        fired_on_monday=_is_monday(now_aest),
        rows_reset=result["rows_reset"],
        accounts_affected=result["accounts_affected"],
        week_start=_current_week_monday(now_aest),
    )
    logger.info("weekly_linkedin_reset_flow complete: %s", summary)
    return summary


def get_weekly_linkedin_reset_schedule() -> CronSchedule:
    """Monday 00:00 AEST."""
    return CronSchedule(cron="0 0 * * 1", timezone="Australia/Sydney")
