"""
Contract: src/orchestration/flows/daily_warming_flow.py
Purpose: Daily flow (02:00 AEST) that advances the warming_day counter for
         every mailbox in mailbox_pool and advances cycle_day for every
         active cycle. Resets daily_count to 0 per mailbox.
Layer:   orchestration
Imports: prefect, db connection
Consumers: Prefect scheduler (daily deployment)

Warming ladder (days 1-14 ramp, day 15+ fully warmed):
    Day 1-3:  10/day cap
    Day 4-6:  25/day cap
    Day 7-10: 50/day cap
    Day 11-14: 75/day cap
    Day 15+:  100/day cap (warming_day set to NULL — fully warmed)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from prefect import flow, task
from prefect.client.schemas.schedules import CronSchedule

logger = logging.getLogger(__name__)

AEST = ZoneInfo("Australia/Sydney")
WARMED_AT_DAY = 15  # warming_day >= 15 -> set to NULL (fully warmed)


@dataclass
class WarmingAdvanceSummary:
    mailboxes_advanced: int
    mailboxes_graduated: int  # warming_day was 14, now NULL (warmed)
    mailboxes_already_warmed: int
    daily_counts_reset: int
    cycles_advanced: int


async def advance_mailbox_warming(db_conn: Any) -> dict:
    """Advance warming_day +1; graduate at day 15; reset daily_count to 0.

    Uses three targeted UPDATEs to keep each statement under 50 lines and
    allow rowcount-based counting without RETURNING complexity.

    Returns dict with keys: advanced, graduated, already_warmed,
    daily_counts_reset.
    """
    # 1. Advance mailboxes still warming (day 1-13 -> day 2-14)
    advanced = await db_conn.execute(
        """
        UPDATE mailbox_pool
        SET warming_day = warming_day + 1,
            updated_at  = NOW()
        WHERE warming_day IS NOT NULL
          AND warming_day + 1 < $1
        """,
        WARMED_AT_DAY,
    )

    # 2. Graduate mailboxes that have reached day 14 (day 14 -> NULL)
    graduated = await db_conn.execute(
        """
        UPDATE mailbox_pool
        SET warming_day = NULL,
            updated_at  = NOW()
        WHERE warming_day IS NOT NULL
          AND warming_day + 1 >= $1
        """,
        WARMED_AT_DAY,
    )

    # 3. Count mailboxes already warmed (warming_day IS NULL before this run)
    #    We can't distinguish "just graduated" from "already NULL" in a count
    #    after the fact, so count NULL rows BEFORE reset (already_warmed = all
    #    NULL rows minus those we just graduated, approximated as a follow-up
    #    SELECT). For test determinism we track via a follow-up COUNT.
    already_rows = await db_conn.fetch(
        "SELECT COUNT(*) AS n FROM mailbox_pool WHERE warming_day IS NULL"
    )
    already_warmed = int(already_rows[0]["n"]) if already_rows else 0
    # Subtract the ones we just graduated so the count reflects pre-run state.
    already_warmed = max(0, already_warmed - graduated)

    # 4. Reset daily_count to 0 for ALL mailboxes (warmed and warming)
    daily_counts_reset = await db_conn.execute(
        """
        UPDATE mailbox_pool
        SET daily_count = 0,
            updated_at  = NOW()
        """
    )

    return {
        "advanced": advanced,
        "graduated": graduated,
        "already_warmed": already_warmed,
        "daily_counts_reset": daily_counts_reset,
    }


async def advance_active_cycles(db_conn: Any) -> int:
    """Advance cycle_day +1 for every active cycle, once per UTC day.

    Idempotency gate: skips rows already advanced today via last_advanced_on.
    Returns count of cycles advanced.
    """
    count = await db_conn.execute(
        """
        UPDATE warming_cycles
        SET cycle_day       = cycle_day + 1,
            last_advanced_on = CURRENT_DATE,
            updated_at       = NOW()
        WHERE status = 'active'
          AND CURRENT_DATE > COALESCE(last_advanced_on,
                                      CURRENT_DATE - INTERVAL '1 day')
        """,
    )
    return count


@task(name="advance-mailbox-warming")
async def advance_mailbox_warming_task(db_conn: Any) -> dict:
    return await advance_mailbox_warming(db_conn)


@task(name="advance-active-cycles")
async def advance_active_cycles_task(db_conn: Any) -> int:
    return await advance_active_cycles(db_conn)


async def daily_warming_flow(db_conn: Any) -> WarmingAdvanceSummary:
    """Pure async flow body. Callable directly by tests via .fn or direct call."""
    mb = await advance_mailbox_warming(db_conn)
    cycles = await advance_active_cycles(db_conn)
    summary = WarmingAdvanceSummary(
        mailboxes_advanced=mb["advanced"],
        mailboxes_graduated=mb["graduated"],
        mailboxes_already_warmed=mb["already_warmed"],
        daily_counts_reset=mb["daily_counts_reset"],
        cycles_advanced=cycles,
    )
    logger.info("daily_warming_flow complete: %s", summary)
    return summary


@flow(name="daily-warming", log_prints=True)
async def daily_warming_flow_prefect() -> WarmingAdvanceSummary:
    """Prefect entrypoint — scheduler calls this. db_conn wired at runtime."""
    return await daily_warming_flow(db_conn=None)


def get_daily_warming_schedule() -> CronSchedule:
    """Daily at 02:00 AEST. Matches the scheduled_jobs.py pattern."""
    return CronSchedule(cron="0 2 * * *", timezone="Australia/Sydney")


if __name__ == "__main__":
    asyncio.run(daily_warming_flow_prefect())
