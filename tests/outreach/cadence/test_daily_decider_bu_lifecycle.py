"""
Tests for BU lifecycle column population in daily_decider.apply_actions.

Covers the state transitions fired on scheduled_touches inserts + suppressions:
  - schedule_next / nurture -> UPDATE business_universe SET outreach_status='active'
    (from pending only) + last_outreach_at[channel] = scheduled_at +
    signal_snapshot_at = NOW()
  - suppress -> UPDATE business_universe SET outreach_status='suppressed'
    (unless currently 'converted')
  - BU UPDATE failures are swallowed (logged, not raised; errors counter
    unaffected by BU-only failures).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.outreach.cadence.daily_decider import (
    DeciderAction,
    _bu_mark_active,
    _bu_mark_suppressed,
    apply_actions,
)


def _when() -> datetime:
    return datetime.now(UTC) + timedelta(days=1)


# -- _bu_mark_active --------------------------------------------------------


@pytest.mark.asyncio
async def test_bu_mark_active_fires_update_with_channel_timestamp():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    when = _when()
    await _bu_mark_active(db, "lead-1", "email", when)
    assert db.execute.await_count == 1
    call_args = db.execute.await_args.args
    sql = call_args[0]
    rest = call_args[1:]
    assert "business_universe" in sql
    assert "outreach_status" in sql
    assert "CASE" in sql  # idempotent pending->active gate
    assert "last_outreach_at" in sql
    assert "signal_snapshot_at" in sql
    assert rest == ("lead-1", "email", when)


@pytest.mark.asyncio
async def test_bu_mark_active_swallows_db_errors():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("dead conn"))
    # Should not raise
    await _bu_mark_active(db, "lead-1", "email", _when())


# -- _bu_mark_suppressed ----------------------------------------------------


@pytest.mark.asyncio
async def test_bu_mark_suppressed_fires_update_gated_on_not_converted():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    await _bu_mark_suppressed(db, "lead-1")
    assert db.execute.await_count == 1
    call_args = db.execute.await_args.args
    sql = call_args[0]
    rest = call_args[1:]
    assert "suppressed" in sql
    assert "converted" in sql  # gate prevents regression from converted
    assert rest == ("lead-1",)


@pytest.mark.asyncio
async def test_bu_mark_suppressed_swallows_db_errors():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("dead conn"))
    await _bu_mark_suppressed(db, "lead-1")  # no raise


# -- apply_actions composition --------------------------------------------


@pytest.mark.asyncio
async def test_schedule_next_fires_insert_and_bu_active():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    when = _when()
    actions = [DeciderAction("lead-1", "schedule_next", "email", when, "", 1)]
    counts = await apply_actions(db, "client-1", actions)
    assert counts["scheduled"] == 1
    assert counts["errors"] == 0
    # 1 insert + 1 bu_mark_active = 2 executes
    assert db.execute.await_count == 2
    # Second call is the BU UPDATE
    second_sql = db.execute.await_args_list[1].args[0]
    assert "UPDATE business_universe" in second_sql


@pytest.mark.asyncio
async def test_nurture_fires_insert_and_bu_active():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    when = _when()
    actions = [DeciderAction("lead-2", "nurture", "linkedin", when, "", None)]
    counts = await apply_actions(db, "client-1", actions)
    assert counts["nurture"] == 1
    assert db.execute.await_count == 2
    second_args = db.execute.await_args_list[1].args
    assert "linkedin" in second_args  # channel passed to BU UPDATE


@pytest.mark.asyncio
async def test_suppress_fires_bu_suppressed():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    actions = [DeciderAction("lead-3", "suppress", None, None, "unsub", None)]
    counts = await apply_actions(db, "client-1", actions)
    assert counts["suppressed"] == 1
    assert db.execute.await_count == 1  # only bu_mark_suppressed, no touch insert
    sql = db.execute.await_args.args[0]
    assert "suppressed" in sql


@pytest.mark.asyncio
async def test_skip_and_escalate_fire_no_bu_update():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    actions = [
        DeciderAction("lead-4", "skip", None, None, "too soon", None),
        DeciderAction("lead-5", "escalate", None, None, "no chan", None),
    ]
    counts = await apply_actions(db, "client-1", actions)
    assert counts["skipped"] == 1
    assert counts["escalated"] == 1
    assert db.execute.await_count == 0  # no DB writes for pure-logging actions


@pytest.mark.asyncio
async def test_bu_update_failure_does_not_regress_success_counts():
    # Insert succeeds; BU UPDATE fails. The scheduled counter still increments;
    # errors counter remains 0 (BU is best-effort).
    db = AsyncMock()
    call_count = {"n": 0}

    async def flaky_execute(*_args, **_kw):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None  # scheduled_touches insert succeeds
        raise RuntimeError("bu boom")

    db.execute = AsyncMock(side_effect=flaky_execute)
    actions = [DeciderAction("lead-1", "schedule_next", "email", _when(), "", 1)]
    counts = await apply_actions(db, "client-1", actions)
    assert counts["scheduled"] == 1
    assert counts["errors"] == 0  # BU failure does not bump errors
