"""
Tests for src/orchestration/flows/monthly_cycle_close_flow.py.

Covers: cycle-discovery filter, 3-tier state transition priority (meeting >
replied > complete), idempotent close, event emission, next-cycle trigger
fire, schedule cron/timezone. Uses an in-memory FakeConn to record all
executed/fetched SQL without needing a real DB.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.orchestration.flows.monthly_cycle_close_flow import (
    CYCLE_LENGTH_DAYS,
    CycleCloseSummary,
    close_cycles_task,
    emit_cycle_close_event,
    find_cycles_to_close,
    get_monthly_cycle_close_schedule,
    mark_cycle_closed,
    monthly_cycle_close_flow,
    transition_cycle_prospects,
    trigger_next_cycle_release,
)


class FakeConn:
    """Records every .execute / .fetch call. Returns programmable rowcounts
    and fetch results in order."""

    def __init__(
        self,
        fetch_returns: list[list[dict]] | None = None,
        execute_rowcounts: list[int] | None = None,
    ):
        self.executed: list[tuple[str, tuple]] = []
        self.fetched: list[tuple[str, tuple]] = []
        self._fetch_returns = list(fetch_returns or [])
        self._exec_rc = list(execute_rowcounts or [])

    async def execute(self, sql: str, *args) -> int:
        self.executed.append((sql, args))
        return self._exec_rc.pop(0) if self._exec_rc else 0

    async def fetch(self, sql: str, *args) -> list[dict]:
        self.fetched.append((sql, args))
        return self._fetch_returns.pop(0) if self._fetch_returns else []


# -- find_cycles_to_close ---------------------------------------------------

@pytest.mark.asyncio
async def test_find_cycles_filters_by_age_and_status():
    rows = [
        {"id": "c1", "client_id": "cl1", "cycle_day_1_date": date(2026, 3, 20), "cycle_number": 1},
    ]
    conn = FakeConn(fetch_returns=[rows])
    out = await find_cycles_to_close(conn)
    assert out == rows
    sql, args = conn.fetched[0]
    assert "status = 'active'" in sql
    assert "CURRENT_DATE - cycle_day_1_date" in sql
    assert args == (CYCLE_LENGTH_DAYS,)


@pytest.mark.asyncio
async def test_find_cycles_returns_empty_when_no_matches():
    conn = FakeConn(fetch_returns=[[]])
    assert await find_cycles_to_close(conn) == []


# -- transition_cycle_prospects — priority + counts --------------------------

@pytest.mark.asyncio
async def test_transition_priority_meeting_beats_reply_beats_complete():
    # meeting=2, replied=3, complete=5 — all three UPDATEs fire in order.
    conn = FakeConn(execute_rowcounts=[2, 3, 5])
    counts = await transition_cycle_prospects(conn, "cycle-1")
    assert counts == {"meeting_booked": 2, "replied": 3, "complete": 5}
    sqls = [s for (s, _) in conn.executed]
    assert "meeting_booked" in sqls[0]
    assert "replied" in sqls[1]
    assert "complete" in sqls[2]


@pytest.mark.asyncio
async def test_transition_idempotent_when_all_already_terminal():
    conn = FakeConn(execute_rowcounts=[0, 0, 0])
    counts = await transition_cycle_prospects(conn, "cycle-1")
    assert counts == {"meeting_booked": 0, "replied": 0, "complete": 0}


# -- mark_cycle_closed ------------------------------------------------------

@pytest.mark.asyncio
async def test_mark_cycle_closed_gates_on_active():
    conn = FakeConn()
    await mark_cycle_closed(conn, "cycle-1")
    sql, args = conn.executed[0]
    assert "status = 'complete'" in sql
    assert "status = 'active'" in sql
    assert args == ("cycle-1",)


# -- emit_cycle_close_event -------------------------------------------------

@pytest.mark.asyncio
async def test_emit_cycle_close_event_inserts_outreach_event():
    conn = FakeConn()
    cycle = {"id": "c1", "client_id": "cl1", "cycle_number": 7}
    transitions = {"meeting_booked": 2, "replied": 3, "complete": 5}
    await emit_cycle_close_event(conn, cycle, transitions)
    sql, args = conn.executed[0]
    assert "INSERT INTO outreach_events" in sql
    assert "'cycle_close'" in sql
    payload = args[1]
    assert payload["cycle_id"] == "c1"
    assert payload["cycle_number"] == 7
    assert payload["transitions"] == transitions


# -- trigger_next_cycle_release ---------------------------------------------

@pytest.mark.asyncio
async def test_trigger_next_cycle_release_calls_injected_fn():
    calls = []

    async def trigger(db, client_id):
        calls.append((db, client_id))

    conn = FakeConn()
    ok = await trigger_next_cycle_release(conn, "cl1", trigger)
    assert ok is True
    assert calls == [(conn, "cl1")]


@pytest.mark.asyncio
async def test_trigger_next_cycle_release_swallows_error():
    async def bad_trigger(db, client_id):
        raise RuntimeError("boom")

    conn = FakeConn()
    ok = await trigger_next_cycle_release(conn, "cl1", bad_trigger)
    assert ok is False


# -- close_cycles_task composition ------------------------------------------

@pytest.mark.asyncio
async def test_close_cycles_task_end_to_end_two_cycles():
    cycles = [
        {"id": "c1", "client_id": "cl1", "cycle_day_1_date": date(2026, 3, 20), "cycle_number": 1},
        {"id": "c2", "client_id": "cl2", "cycle_day_1_date": date(2026, 3, 22), "cycle_number": 2},
    ]
    # per cycle: 3 transition UPDATEs + 1 mark_cycle_closed + 1 event emit = 5 execs
    # order of rowcounts: (meeting, replied, complete, mark, event) × 2
    conn = FakeConn(
        fetch_returns=[cycles],
        execute_rowcounts=[2, 3, 5, 1, 1,  1, 2, 4, 1, 1],
    )
    calls = []

    async def trigger(db, client_id):
        calls.append(client_id)

    summary = await close_cycles_task(conn, trigger)
    assert summary.cycles_closed == 2
    assert summary.transitions == {
        "meeting_booked": 3, "replied": 5, "complete": 9,
    }
    assert summary.events_emitted == 2
    assert summary.next_cycles_released == 2
    assert calls == ["cl1", "cl2"]


@pytest.mark.asyncio
async def test_close_cycles_task_no_cycles_returns_zero_summary():
    conn = FakeConn(fetch_returns=[[]])

    async def trigger(db, client_id):
        pass

    summary = await close_cycles_task(conn, trigger)
    assert summary.cycles_closed == 0
    assert summary.events_emitted == 0
    assert summary.next_cycles_released == 0


# -- monthly_cycle_close_flow (via .fn) -------------------------------------

@pytest.mark.asyncio
async def test_flow_fn_composes_summary():
    conn = FakeConn(fetch_returns=[[]])

    async def trigger(db, client_id):
        pass

    summary = await monthly_cycle_close_flow.fn(conn, new_cycle_trigger=trigger)
    assert isinstance(summary, CycleCloseSummary)
    assert summary.cycles_closed == 0


# -- schedule ---------------------------------------------------------------

def test_get_schedule_cron_and_tz():
    s = get_monthly_cycle_close_schedule()
    assert s.cron == "30 0 1 * *"
    assert str(s.timezone) == "Australia/Sydney"


def test_cycle_length_constant_is_30():
    assert CYCLE_LENGTH_DAYS == 30
