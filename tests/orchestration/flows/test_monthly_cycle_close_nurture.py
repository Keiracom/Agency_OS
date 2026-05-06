"""
Tests for nurture_enqueue_fn integration in close_cycles_task.

Verifies the post-close hook is called correctly for prospects
transitioning to 'complete', and is safely skipped when absent
or when no 'complete' transitions occurred.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from src.orchestration.flows.monthly_cycle_close_flow import close_cycles_task


class FakeConn:
    """Minimal FakeConn — records executed/fetched SQL; returns programmable results."""

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


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def one_cycle(cycle_id="c1", client_id="cl1") -> dict:
    return {
        "id": cycle_id,
        "client_id": client_id,
        "cycle_day_1_date": date(2026, 3, 1),
        "cycle_number": 1,
    }


async def noop_trigger(db: Any, client_id: str) -> None:
    pass


# ---------------------------------------------------------------------------
# Test 1: nurture_enqueue_fn called for each complete prospect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nurture_enqueue_called_for_complete_prospects():
    """One cycle with 3 prospects that transition to 'complete' — hook called 3 times."""
    cycle = one_cycle()
    # FakeConn fetch_returns order:
    #   1st fetch = find_cycles_to_close -> [cycle]
    #   2nd fetch = _enqueue_cold_prospects_for_nurture -> 3 prospect rows
    prospect_rows = [
        {"prospect_id": "p1"},
        {"prospect_id": "p2"},
        {"prospect_id": "p3"},
    ]
    conn = FakeConn(
        fetch_returns=[[cycle], prospect_rows],
        # transitions: meeting=0, replied=0, complete=3
        # Then mark_cycle_closed + event emit = 2 more executes
        execute_rowcounts=[0, 0, 3, 1, 1],
    )

    enqueue_calls: list[tuple[str, str]] = []

    def nurture_fn(prospect_id: str, client_id: str) -> None:
        enqueue_calls.append((prospect_id, client_id))

    summary = await close_cycles_task(conn, noop_trigger, nurture_enqueue_fn=nurture_fn)

    assert summary.cycles_closed == 1
    assert summary.transitions["complete"] == 3
    assert len(enqueue_calls) == 3
    assert set(enqueue_calls) == {("p1", "cl1"), ("p2", "cl1"), ("p3", "cl1")}


# ---------------------------------------------------------------------------
# Test 2: nurture_enqueue_fn=None — no crash
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nurture_enqueue_fn_none_no_crash():
    """nurture_enqueue_fn=None is the default — must not raise."""
    cycle = one_cycle()
    conn = FakeConn(
        fetch_returns=[[cycle]],
        execute_rowcounts=[0, 0, 3, 1, 1],
    )

    # Should complete cleanly without raising even though complete=3
    summary = await close_cycles_task(conn, noop_trigger, nurture_enqueue_fn=None)
    assert summary.cycles_closed == 1
    # No fetch for prospect IDs was attempted (early return because fn is None)
    # The only fetch is the initial find_cycles_to_close
    assert len(conn.fetched) == 1


# ---------------------------------------------------------------------------
# Test 3: no 'complete' transitions — nurture_enqueue_fn NOT called
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nurture_enqueue_not_called_when_no_complete_transitions():
    """All prospects replied or meeting_booked — complete=0, hook skipped."""
    cycle = one_cycle()
    conn = FakeConn(
        fetch_returns=[[cycle]],
        # meeting=2, replied=1, complete=0
        execute_rowcounts=[2, 1, 0, 1, 1],
    )

    enqueue_calls: list[tuple] = []

    def nurture_fn(prospect_id: str, client_id: str) -> None:
        enqueue_calls.append((prospect_id, client_id))

    summary = await close_cycles_task(conn, noop_trigger, nurture_enqueue_fn=nurture_fn)

    assert summary.transitions["complete"] == 0
    assert enqueue_calls == []
    # No second fetch for prospect IDs was made
    assert len(conn.fetched) == 1
