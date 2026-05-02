"""
Contract: src/orchestration/flows/daily_decider_flow.py
Purpose: Daily Prefect flow — evaluates every active prospect per client at 9am AEST.
Layer:   orchestration
Imports: prefect, daily_decider
Consumers: Prefect scheduler (daily deployment, cron '0 9 * * *' AEST)

Per client:
    1. DailyDecider.evaluate_all(db_conn, client_id)
    2. apply_actions(db_conn, client_id, actions) — writes scheduled_touches rows
    3. Aggregate summary counts

Errors in one client's evaluation do not block the rest — gathered with
return_exceptions=True. hourly_cadence_flow fires the scheduled rows later.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any

from prefect import flow

from src.outreach.cadence.daily_decider import DailyDecider, apply_actions

logger = logging.getLogger(__name__)


async def _list_active_clients(db_conn: Any) -> list[str]:
    if db_conn is None:
        return []
    rows = await db_conn.fetch("SELECT id FROM clients WHERE status = 'active'")
    return [str(r["id"]) for r in rows]


async def daily_decider_flow(
    db_conn: Any | None = None,
    decider: DailyDecider | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Pure async flow body. Called by the Prefect wrapper and directly by tests
    (to bypass Prefect's parameter-serialization recursion on AsyncMock).
    """
    if db_conn is None:
        logger.error("daily_decider_flow: db_conn required")
        return _empty_summary()

    clients = await _list_active_clients(db_conn)
    logger.info("daily_decider_flow: %d active clients", len(clients))
    if not clients:
        return _empty_summary()

    decider = decider or DailyDecider()

    async def evaluate_client(cid: str) -> dict[str, int]:
        actions = await decider.evaluate_all(db_conn, cid)
        if dry_run:
            counts = Counter(a.action for a in actions)
            return {
                "scheduled": counts.get("schedule_next", 0),
                "nurture": counts.get("nurture", 0),
                "skipped": counts.get("skip", 0),
                "suppressed": counts.get("suppress", 0),
                "escalated": counts.get("escalate", 0),
                "errors": 0,
                "evaluated": len(actions),
            }
        applied = await apply_actions(db_conn, cid, actions)
        applied["evaluated"] = len(actions)
        return applied

    per_client = await asyncio.gather(
        *[evaluate_client(c) for c in clients],
        return_exceptions=True,
    )

    totals = _empty_summary()
    totals["clients"] = len(clients)
    for r in per_client:
        if isinstance(r, dict):
            for k, v in r.items():
                totals[k] = totals.get(k, 0) + v
        else:
            totals["errors"] += 1
            logger.exception("daily_decider: per-client evaluate raised: %s", r)

    logger.info("daily_decider_flow complete: %s", totals)
    return totals


def _empty_summary() -> dict[str, int]:
    return {
        "clients": 0,
        "evaluated": 0,
        "scheduled": 0,
        "nurture": 0,
        "skipped": 0,
        "suppressed": 0,
        "escalated": 0,
        "errors": 0,
    }


@flow(name="daily_decider_flow", log_prints=True)
async def daily_decider_flow_prefect() -> dict[str, int]:
    """Scheduler entrypoint. Production wiring of db_conn happens here later."""
    return await daily_decider_flow(db_conn=None)


if __name__ == "__main__":
    asyncio.run(daily_decider_flow_prefect())
