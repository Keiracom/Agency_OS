"""Tests for daily_warming_flow — all run without a real DB or Prefect runtime."""
from __future__ import annotations

import logging
import pytest

from src.orchestration.flows.daily_warming_flow import (
    WarmingAdvanceSummary,
    advance_active_cycles,
    advance_mailbox_warming,
    daily_warming_flow,
    get_daily_warming_schedule,
)


# ---------------------------------------------------------------------------
# Fake DB connection
# ---------------------------------------------------------------------------

class FakeConn:
    """Records all SQL calls; pops from rowcounts for execute(); returns
    rows from fetch_rows for fetch()."""

    def __init__(self, rowcounts: list[int], fetch_rows: list[list[dict]] | None = None):
        self.calls: list[tuple] = []
        self._rowcounts = list(rowcounts)
        self._fetch_rows: list[list[dict]] = list(fetch_rows or [])

    async def execute(self, sql: str, *args) -> int:
        self.calls.append(("execute", sql, args))
        return self._rowcounts.pop(0) if self._rowcounts else 0

    async def fetch(self, sql: str, *args) -> list[dict]:
        self.calls.append(("fetch", sql, args))
        return self._fetch_rows.pop(0) if self._fetch_rows else []


# ---------------------------------------------------------------------------
# Case 1: advance_mailbox_warming returns correct counts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_mailbox_warming_counts():
    """5 advanced, 1 graduated, fetch returns 4 NULL rows -> already_warmed=3,
    9 daily_counts_reset."""
    conn = FakeConn(
        rowcounts=[5, 1, 9],
        fetch_rows=[[{"n": 4}]],  # 4 NULL rows after graduation; minus 1 graduated = 3
    )
    result = await advance_mailbox_warming(conn)
    assert result["advanced"] == 5
    assert result["graduated"] == 1
    assert result["already_warmed"] == 3
    assert result["daily_counts_reset"] == 9


# ---------------------------------------------------------------------------
# Case 2: advance_active_cycles returns correct count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_active_cycles_count():
    """Fake returns 3 -> function returns 3."""
    conn = FakeConn(rowcounts=[3])
    result = await advance_active_cycles(conn)
    assert result == 3


# ---------------------------------------------------------------------------
# Case 3: daily_warming_flow composes WarmingAdvanceSummary correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_warming_flow_summary():
    """End-to-end: flow calls both sub-functions and composes summary."""
    conn = FakeConn(
        rowcounts=[5, 1, 9, 3],
        fetch_rows=[[{"n": 4}]],
    )
    summary = await daily_warming_flow(conn)
    assert isinstance(summary, WarmingAdvanceSummary)
    assert summary.mailboxes_advanced == 5
    assert summary.mailboxes_graduated == 1
    assert summary.mailboxes_already_warmed == 3
    assert summary.daily_counts_reset == 9
    assert summary.cycles_advanced == 3


# ---------------------------------------------------------------------------
# Case 4: Mailbox SQL contains warming_day ladder references
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mailbox_sql_contains_warming_ladder_keywords():
    """The recorded SQL must reference warming_day and daily_count; the
    WARMED_AT_DAY value (15) must appear either in SQL text or as a bind arg."""
    conn = FakeConn(rowcounts=[0, 0, 0], fetch_rows=[[{"n": 0}]])
    await advance_mailbox_warming(conn)

    all_sql = " ".join(call[1] for call in conn.calls)
    # Flatten all args tuples for arg presence check
    all_args = [str(a) for call in conn.calls for a in call[2]]

    assert "warming_day" in all_sql
    assert "daily_count" in all_sql
    # 15 may appear as literal in SQL or as a bind parameter
    assert "15" in all_sql or "15" in all_args


# ---------------------------------------------------------------------------
# Case 5: Cycle advancement SQL is idempotent (contains CURRENT_DATE gate)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cycle_sql_is_idempotent():
    """SQL must contain CURRENT_DATE or last_advanced_on guard."""
    conn = FakeConn(rowcounts=[0])
    await advance_active_cycles(conn)

    assert conn.calls, "No SQL calls recorded"
    sql = conn.calls[0][1]
    assert "CURRENT_DATE" in sql or "last_advanced_on" in sql


# ---------------------------------------------------------------------------
# Case 6: get_daily_warming_schedule returns correct cron + timezone
# ---------------------------------------------------------------------------

def test_get_daily_warming_schedule():
    from prefect.client.schemas.schedules import CronSchedule
    sched = get_daily_warming_schedule()
    assert isinstance(sched, CronSchedule)
    assert sched.cron == "0 2 * * *"
    assert "Sydney" in sched.timezone


# ---------------------------------------------------------------------------
# Case 7: Logging side-effect — INFO message emitted after successful run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_warming_flow_logs_info(caplog):
    conn = FakeConn(rowcounts=[2, 0, 4, 1], fetch_rows=[[{"n": 0}]])
    with caplog.at_level(logging.INFO, logger="src.orchestration.flows.daily_warming_flow"):
        await daily_warming_flow(conn)
    assert any("daily_warming_flow complete" in r.message for r in caplog.records)
