"""
Contract: src/orchestration/flows/hourly_cadence_flow.py
Purpose: Hourly Prefect flow that fires all due scheduled_touches.
Layer:   orchestration
Imports: prefect, dispatcher, db connection helpers
Consumers: Prefect scheduler (hourly deployment)

Flow:
    1. Query scheduled_touches WHERE status='pending' AND scheduled_at <= now()
    2. For each touch: dispatcher.dispatch() — timing -> compliance -> rate -> send -> record
    3. UPDATE scheduled_touches.status to sent | failed | skipped
    4. Log summary (counts per status)

A single touch failure never blocks the rest — all results are gathered
with return_exceptions=True and unexpected raises are recorded as failures.
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from prefect import flow

from src.outreach.dispatcher import DispatchResult, OutreachDispatcher

logger = logging.getLogger(__name__)

BATCH_LIMIT = 500
CONCURRENCY = 10


async def get_pending_touches(db_conn: Any, limit: int = BATCH_LIMIT) -> list[dict]:
    """Return pending touches due for dispatch, ordered by scheduled_at."""
    now = datetime.now(UTC)
    rows = await db_conn.fetch(
        """
        SELECT id, channel, prospect, client_id, lead_id, activity_id,
               campaign_id, content, sequence_step, scheduled_at
        FROM scheduled_touches
        WHERE status = 'pending' AND scheduled_at <= $1
        ORDER BY scheduled_at
        LIMIT $2
        """,
        now, limit,
    )
    return [dict(r) for r in rows]


async def process_touch(
    dispatcher: OutreachDispatcher,
    db_conn: Any,
    touch: dict,
) -> DispatchResult:
    """Dispatch one touch and update its status row. Never raises."""
    try:
        result = await dispatcher.dispatch(touch)
    except Exception as exc:
        logger.exception("dispatcher.dispatch raised for touch %s", touch.get("id"))
        result = DispatchResult(
            status="failed",
            channel=str(touch.get("channel", "")),
            reason=f"unexpected:{type(exc).__name__}:{exc}",
        )

    await _update_touch_status(db_conn, touch.get("id"), result)
    return result


async def _update_touch_status(
    db_conn: Any, touch_id: Any, result: DispatchResult,
) -> None:
    """Record the outcome on scheduled_touches. Swallows DB errors."""
    if db_conn is None or touch_id is None:
        return
    try:
        await db_conn.execute(
            """
            UPDATE scheduled_touches
            SET status = $2,
                dispatched_at = CASE WHEN $2 = 'sent' THEN NOW() ELSE dispatched_at END,
                skipped_reason = CASE WHEN $2 = 'skipped' THEN $3 ELSE skipped_reason END,
                failure_reason = CASE WHEN $2 = 'failed'  THEN $3 ELSE failure_reason END,
                provider_message_id = COALESCE($4, provider_message_id),
                updated_at = NOW()
            WHERE id = $1
            """,
            touch_id, result.status, result.reason, result.provider_message_id,
        )
    except Exception as exc:
        logger.exception("failed to update scheduled_touches id=%s: %s", touch_id, exc)


async def hourly_cadence_flow(
    db_conn: Any | None = None,
    dispatcher: OutreachDispatcher | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Pure async flow body. Called by `hourly_cadence_flow_prefect` (the @flow
    wrapper, used by the scheduler) and directly by tests (to bypass Prefect's
    parameter serialization which can't handle AsyncMock injection).

    Args:
        db_conn:    asyncpg-compatible connection/pool (injected for tests).
        dispatcher: OutreachDispatcher (injected for tests).
        dry_run:    If True, fetch touches but do not dispatch or update.

    Returns a summary dict: {'total','sent','skipped','failed'}.
    """
    if db_conn is None:
        logger.error("hourly_cadence_flow: db_conn required")
        return {"total": 0, "sent": 0, "skipped": 0, "failed": 0}

    touches = await get_pending_touches(db_conn)
    logger.info("hourly_cadence_flow: %d touches due", len(touches))

    if dry_run or not touches:
        return {"total": len(touches), "sent": 0, "skipped": 0, "failed": 0}

    if dispatcher is None:
        dispatcher = OutreachDispatcher(db_conn=db_conn)

    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded(t: dict) -> DispatchResult:
        async with sem:
            return await process_touch(dispatcher, db_conn, t)

    results = await asyncio.gather(
        *[bounded(t) for t in touches], return_exceptions=True,
    )

    counts: Counter[str] = Counter()
    for r in results:
        if isinstance(r, DispatchResult):
            counts[r.status] += 1
        else:
            counts["failed"] += 1
            logger.exception("touch raised out of dispatcher: %s", r)

    summary = {
        "total":   len(touches),
        "sent":    counts.get("sent", 0),
        "skipped": counts.get("skipped", 0),
        "failed":  counts.get("failed", 0),
    }
    logger.info("hourly_cadence_flow complete: %s", summary)
    return summary


@flow(name="hourly_cadence_flow", log_prints=True)
async def hourly_cadence_flow_prefect() -> dict[str, int]:
    """Prefect entrypoint — takes no mock-able params; builds its own dispatcher.

    The scheduler calls this. Production wiring of db_conn happens here later.
    """
    return await hourly_cadence_flow(db_conn=None)


if __name__ == "__main__":
    asyncio.run(hourly_cadence_flow_prefect())
