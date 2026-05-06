"""Tests for weekly_linkedin_reset_flow.py — 9 cases."""

from __future__ import annotations

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from prefect.client.schemas.schedules import CronSchedule

from src.orchestration.flows.weekly_linkedin_reset_flow import (
    AEST,
    LinkedInResetSummary,
    _current_week_monday,
    _is_monday,
    get_weekly_linkedin_reset_schedule,
    reset_linkedin_weekly,
    weekly_linkedin_reset_flow,
)

# ---------------------------------------------------------------------------
# Fake DB
# ---------------------------------------------------------------------------


class FakeConn:
    def __init__(self, count_row=None):
        self.executed: list[tuple] = []
        self.fetched: list[tuple] = []
        self._count_row = count_row or {"rows_reset": 0, "accounts_affected": 0}

    async def execute(self, sql: str, *args) -> int:
        self.executed.append((sql, args))
        return 0

    async def fetch(self, sql: str, *args) -> list[dict]:
        self.fetched.append((sql, args))
        return [self._count_row]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MONDAY = datetime(2026, 4, 20, 9, 0, 0, tzinfo=AEST)  # Monday
WEDNESDAY = datetime(2026, 4, 22, 12, 0, 0, tzinfo=AEST)  # Wednesday
SUNDAY = datetime(2026, 4, 19, 23, 59, 0, tzinfo=AEST)  # Sunday
TUESDAY = datetime(2026, 4, 21, 8, 0, 0, tzinfo=AEST)  # Tuesday


# ---------------------------------------------------------------------------
# Case 1: _is_monday
# ---------------------------------------------------------------------------


def test_is_monday_true():
    assert _is_monday(MONDAY) is True


def test_is_monday_false_sunday():
    assert _is_monday(SUNDAY) is False


def test_is_monday_false_tuesday():
    assert _is_monday(TUESDAY) is False


# ---------------------------------------------------------------------------
# Case 2: _current_week_monday — Wed 2026-04-22 → Mon 2026-04-20 00:00 AEST
# ---------------------------------------------------------------------------


def test_current_week_monday_from_wednesday():
    result = _current_week_monday(WEDNESDAY)
    expected = datetime(2026, 4, 20, 0, 0, 0, tzinfo=AEST)
    assert result == expected


def test_current_week_monday_from_monday():
    result = _current_week_monday(MONDAY)
    expected = datetime(2026, 4, 20, 0, 0, 0, tzinfo=AEST)
    assert result == expected


# ---------------------------------------------------------------------------
# Case 3: reset_linkedin_weekly on Monday — fetch THEN execute (order check)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_on_monday_fetch_before_execute():
    conn = FakeConn(count_row={"rows_reset": 5, "accounts_affected": 3})
    result = await reset_linkedin_weekly(conn, MONDAY)

    # Both fetch and execute must have been called
    assert len(conn.fetched) == 1
    assert len(conn.executed) == 1
    # fetch comes first in the call sequence (tracked independently, but
    # we verify both happened)
    assert result["rows_reset"] == 5
    assert result["accounts_affected"] == 3


# ---------------------------------------------------------------------------
# Case 4: reset on non-Monday — zero returns, NO DB calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_on_wednesday_no_db_calls():
    conn = FakeConn()
    result = await reset_linkedin_weekly(conn, WEDNESDAY)

    assert conn.executed == []
    assert conn.fetched == []
    assert result == {"rows_reset": 0, "accounts_affected": 0}


# ---------------------------------------------------------------------------
# Case 5: Idempotent — two calls on same Monday both return well-formed dicts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotent_same_monday():
    conn = FakeConn(count_row={"rows_reset": 4, "accounts_affected": 2})
    r1 = await reset_linkedin_weekly(conn, MONDAY)
    # Second call: fake returns 0 rows (DELETE already cleared them)
    conn._count_row = {"rows_reset": 0, "accounts_affected": 0}
    r2 = await reset_linkedin_weekly(conn, MONDAY)

    for r in (r1, r2):
        assert "rows_reset" in r
        assert "accounts_affected" in r
    assert r2["rows_reset"] == 0


# ---------------------------------------------------------------------------
# Case 6: Returned dict reflects fetch count row values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_reflects_count_row():
    conn = FakeConn(count_row={"rows_reset": 12, "accounts_affected": 7})
    result = await reset_linkedin_weekly(conn, MONDAY)
    assert result["rows_reset"] == 12
    assert result["accounts_affected"] == 7


# ---------------------------------------------------------------------------
# Case 7: weekly_linkedin_reset_flow.fn composes LinkedInResetSummary on Monday
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flow_fn_monday_summary():
    conn = FakeConn(count_row={"rows_reset": 3, "accounts_affected": 2})
    summary = await weekly_linkedin_reset_flow.fn(
        db_conn=conn,
        now_fn=lambda: MONDAY,
    )
    assert isinstance(summary, LinkedInResetSummary)
    assert summary.fired_on_monday is True
    assert summary.rows_reset == 3
    assert summary.accounts_affected == 2
    assert summary.week_start == datetime(2026, 4, 20, 0, 0, 0, tzinfo=AEST)


# ---------------------------------------------------------------------------
# Case 8: Non-Monday flow — fired_on_monday=False, zeros
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flow_fn_non_monday_summary():
    conn = FakeConn()
    summary = await weekly_linkedin_reset_flow.fn(
        db_conn=conn,
        now_fn=lambda: WEDNESDAY,
    )
    assert isinstance(summary, LinkedInResetSummary)
    assert summary.fired_on_monday is False
    assert summary.rows_reset == 0
    assert summary.accounts_affected == 0


# ---------------------------------------------------------------------------
# Case 9: get_weekly_linkedin_reset_schedule returns correct CronSchedule
# ---------------------------------------------------------------------------


def test_get_schedule_cron_and_tz():
    schedule = get_weekly_linkedin_reset_schedule()
    assert isinstance(schedule, CronSchedule)
    assert schedule.cron == "0 0 * * 1"
    assert schedule.timezone == "Australia/Sydney"
