"""
Contract: src/orchestration/flows/monthly_cycle_close_flow.py
Purpose: 1st-of-month 00:30 AEST flow that closes cycles reaching Day 30,
         transitions each cycle_prospects.outreach_status based on observed
         activity, emits cycle_close events, and triggers a fresh cycle
         release for active customers via cadence_orchestrator.
Layer:   orchestration
Imports: prefect, db connection, cadence_orchestrator (stateless helpers)
Consumers: Prefect scheduler (monthly deployment)

State transition rules (per dispatch):
  in_sequence -> replied         (any reply recorded against prospect)
  in_sequence -> meeting_booked  (meeting booked — "converted" in dispatch vocab)
  in_sequence -> complete        (no reply, no meeting — "closed_no_reply" in dispatch vocab)

Schema note: cycle_prospects.outreach_status uses the canonical enum
{pending, in_sequence, replied, meeting_booked, suppressed, complete}. The
dispatch used looser labels ("active", "converted", "closed_no_reply") —
the mapping above is the authoritative translation for this flow.

Idempotency: only cycles that have (a) status='active' and (b) reached
day 30 are closed. Re-running the flow within the same day is safe — the
second run finds no cycles still 'active' at day 30.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from prefect import flow, task
from prefect.client.schemas.schedules import CronSchedule

logger = logging.getLogger(__name__)

AEST = ZoneInfo("Australia/Sydney")
CYCLE_LENGTH_DAYS = 30


@dataclass
class CycleCloseSummary:
    cycles_closed: int
    transitions: dict[str, int] = field(default_factory=dict)   # outreach_status -> count
    events_emitted: int = 0
    next_cycles_released: int = 0


async def find_cycles_to_close(db_conn: Any) -> list[dict]:
    """Return active cycles that have reached day 30 (cycle_day_1_date + 30)."""
    rows = await db_conn.fetch(
        """
        SELECT id, client_id, cycle_day_1_date, cycle_number
        FROM cycles
        WHERE status = 'active'
          AND (CURRENT_DATE - cycle_day_1_date) >= $1
        ORDER BY cycle_day_1_date
        """,
        CYCLE_LENGTH_DAYS,
    )
    return [dict(r) for r in rows]


async def transition_cycle_prospects(db_conn: Any, cycle_id: str) -> dict[str, int]:
    """Advance every cycle_prospects row for this cycle to its terminal state.

    Priority when multiple signals exist:
      meeting_booked > replied > complete
    Rows already in suppressed | meeting_booked | replied | complete are left
    untouched (idempotent).
    """
    counts = {"meeting_booked": 0, "replied": 0, "complete": 0}

    # meeting_booked — highest priority
    r = await db_conn.execute(
        """
        UPDATE cycle_prospects cp
        SET outreach_status = 'meeting_booked', updated_at = NOW()
        WHERE cp.cycle_id = $1
          AND cp.outreach_status = 'in_sequence'
          AND EXISTS (
              SELECT 1 FROM dm_meetings m WHERE m.prospect_id = cp.prospect_id
          )
        """,
        cycle_id,
    )
    counts["meeting_booked"] = _rowcount(r)

    # replied — any reply row for prospect
    r = await db_conn.execute(
        """
        UPDATE cycle_prospects cp
        SET outreach_status = 'replied', updated_at = NOW()
        WHERE cp.cycle_id = $1
          AND cp.outreach_status = 'in_sequence'
          AND EXISTS (
              SELECT 1 FROM replies rp WHERE rp.prospect_id = cp.prospect_id
          )
        """,
        cycle_id,
    )
    counts["replied"] = _rowcount(r)

    # complete — everyone left still in_sequence
    r = await db_conn.execute(
        """
        UPDATE cycle_prospects
        SET outreach_status = 'complete', updated_at = NOW()
        WHERE cycle_id = $1 AND outreach_status = 'in_sequence'
        """,
        cycle_id,
    )
    counts["complete"] = _rowcount(r)

    return counts


async def mark_cycle_closed(db_conn: Any, cycle_id: str) -> None:
    await db_conn.execute(
        """
        UPDATE cycles
        SET status = 'complete', completed_at = NOW(), updated_at = NOW()
        WHERE id = $1 AND status = 'active'
        """,
        cycle_id,
    )


async def emit_cycle_close_event(db_conn: Any, cycle: dict, transitions: dict) -> None:
    """Insert a cycle_close row into outreach_events (best-effort; swallow errors)."""
    try:
        await db_conn.execute(
            """
            INSERT INTO outreach_events (event_type, client_id, payload, created_at)
            VALUES ('cycle_close', $1, $2::jsonb, NOW())
            """,
            cycle["client_id"],
            {
                "cycle_id": str(cycle["id"]),
                "cycle_number": cycle["cycle_number"],
                "transitions": transitions,
            },
        )
    except Exception as exc:  # pragma: no cover — logged, not raised
        logger.warning("cycle_close event emit failed for cycle=%s: %s", cycle["id"], exc)


async def trigger_next_cycle_release(
    db_conn: Any, client_id: str, new_cycle_trigger,
) -> bool:
    """Call the injected new_cycle_trigger(db_conn, client_id) to release a new
    30-day cycle for active customers. Returns True on success."""
    try:
        await new_cycle_trigger(db_conn, client_id)
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("next-cycle trigger failed for client=%s: %s", client_id, exc)
        return False


def _rowcount(result: Any) -> int:
    if isinstance(result, int):
        return result
    if hasattr(result, "rowcount"):
        return result.rowcount or 0
    if isinstance(result, str) and " " in result:
        parts = result.split()
        if parts[-1].isdigit():
            return int(parts[-1])
    return 0


@task(name="close-cycles")
async def close_cycles_task(
    db_conn: Any, new_cycle_trigger,
) -> CycleCloseSummary:
    summary = CycleCloseSummary(cycles_closed=0, transitions={
        "meeting_booked": 0, "replied": 0, "complete": 0,
    })
    cycles = await find_cycles_to_close(db_conn)
    for cycle in cycles:
        transitions = await transition_cycle_prospects(db_conn, cycle["id"])
        for k, v in transitions.items():
            summary.transitions[k] = summary.transitions.get(k, 0) + v
        await mark_cycle_closed(db_conn, cycle["id"])
        await emit_cycle_close_event(db_conn, cycle, transitions)
        summary.events_emitted += 1
        if await trigger_next_cycle_release(db_conn, cycle["client_id"], new_cycle_trigger):
            summary.next_cycles_released += 1
        summary.cycles_closed += 1
    return summary


async def _default_new_cycle_trigger(db_conn: Any, client_id: str) -> None:
    """Default next-cycle trigger — stubbed as a no-op INSERT into cycles.
    In production this is overridden by the deployment to call
    cadence_orchestrator's cycle-release helper with real sequence defaults."""
    await db_conn.execute(
        """
        INSERT INTO cycles (client_id, cycle_number, target_prospects, cycle_day_1_date, status)
        SELECT $1, COALESCE(MAX(cycle_number), 0) + 1, 0, CURRENT_DATE, 'active'
        FROM cycles WHERE client_id = $1
        """,
        client_id,
    )


@flow(name="monthly-cycle-close", log_prints=True)
async def monthly_cycle_close_flow(
    db_conn: Any,
    new_cycle_trigger=_default_new_cycle_trigger,
) -> CycleCloseSummary:
    summary = await close_cycles_task(db_conn, new_cycle_trigger)
    logger.info("monthly_cycle_close_flow complete: %s", summary)
    return summary


def get_monthly_cycle_close_schedule() -> CronSchedule:
    """1st of month 00:30 AEST."""
    return CronSchedule(cron="30 0 1 * *", timezone="Australia/Sydney")
