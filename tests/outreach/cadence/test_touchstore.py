"""
Tests for src/outreach/cadence/decision_tree.py — TouchStore executor.

Zero paid API calls. Pure mocked asyncpg + stubbed SuppressionManager.

Covers:
- cancel                  → UPDATE status='cancelled'
- pause                   → UPDATE status='paused'
- reschedule              → UPDATE scheduled_at
- insert                  → INSERT scheduled_touches
- insert missing fields   → returns False, no INSERT fires
- suppress                → add_to_suppression + cascade cancel all pending
- escalate                → logged only, no DB write
- noop                    → skipped
- mixed list              → count matches successful applies
- no-db fallback          → apply() returns 0 when db_conn=None (legacy stub)
- per-mutation exception  → contained; successful ones still counted
- load_pending            → SELECT with correct filter
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.outreach.cadence.decision_tree import TouchMutation, TouchStore


def _db():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    db.fetch = AsyncMock(return_value=[])
    return db


# ---------- per-action coverage --------------------------------------------

@pytest.mark.asyncio
async def test_cancel_updates_status_cancelled():
    db = _db()
    store = TouchStore(db_conn=db)
    mutation = TouchMutation(action="cancel", touch_id="t1", reason="user rejected")
    applied = await store.apply([mutation])
    assert applied == 1
    db.execute.assert_awaited_once()
    sql, *args = db.execute.await_args.args
    assert "UPDATE scheduled_touches" in sql
    assert args[0] == "t1"
    assert args[1] == "cancelled"
    assert args[2] == "user rejected"


@pytest.mark.asyncio
async def test_pause_updates_status_paused():
    db = _db()
    store = TouchStore(db_conn=db)
    applied = await store.apply(
        [TouchMutation(action="pause", touch_id="t1", reason="question — 48h pause")],
    )
    assert applied == 1
    sql, *args = db.execute.await_args.args
    assert "UPDATE scheduled_touches" in sql
    assert args[1] == "paused"


@pytest.mark.asyncio
async def test_reschedule_updates_scheduled_at():
    db = _db()
    store = TouchStore(db_conn=db)
    when = datetime.now(UTC) + timedelta(days=5)
    applied = await store.apply(
        [TouchMutation(action="reschedule", touch_id="t1", new_scheduled_at=when)],
    )
    assert applied == 1
    sql, *args = db.execute.await_args.args
    assert "scheduled_at = $2" in sql
    assert args[0] == "t1"
    assert args[1] == when


@pytest.mark.asyncio
async def test_insert_writes_scheduled_touches_row():
    db = _db()
    store = TouchStore(db_conn=db)
    mutation = TouchMutation(
        action="insert",
        channel="email",
        sequence_step=2,
        content={"subject": "Hi", "html_body": "<p>hey</p>"},
        extra={
            "client_id": "c1",
            "lead_id": "l1",
            "prospect": {"email": "amy@acme.com.au"},
        },
    )
    applied = await store.apply([mutation])
    assert applied == 1
    sql, *args = db.execute.await_args.args
    assert "INSERT INTO scheduled_touches" in sql
    # client_id, lead_id, channel, sequence_step, scheduled_at, content, prospect
    assert args[0] == "c1"
    assert args[1] == "l1"
    assert args[2] == "email"
    assert args[3] == 2


@pytest.mark.asyncio
async def test_insert_skipped_when_client_or_lead_missing():
    db = _db()
    store = TouchStore(db_conn=db)
    mutation = TouchMutation(
        action="insert", channel="email",
        extra={"lead_id": "l1"},  # no client_id
    )
    applied = await store.apply([mutation])
    assert applied == 0
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_suppress_writes_suppression_and_cancels_pending():
    db = _db()
    store = TouchStore(db_conn=db)
    mutation = TouchMutation(
        action="suppress",
        extra={
            "lead_id": "l1",
            "email": "amy@acme.com.au",
            "suppression_reason": "unsubscribe",
            "channel": "all",
            "source": "decision_tree",
        },
    )
    with patch(
        "src.outreach.cadence.decision_tree.SuppressionManager.add_to_suppression",
        return_value={"success": True, "email": "amy@acme.com.au"},
    ) as mock_add:
        applied = await store.apply([mutation])

    assert applied == 1
    mock_add.assert_called_once()
    # Cascade UPDATE fires with lead_id filter
    db.execute.assert_awaited_once()
    sql, *args = db.execute.await_args.args
    assert "status = 'cancelled'" in sql
    assert "lead_id = $1" in sql
    assert args[0] == "l1"


@pytest.mark.asyncio
async def test_escalate_logs_only_no_db_write():
    db = _db()
    store = TouchStore(db_conn=db)
    applied = await store.apply(
        [TouchMutation(action="escalate", reason="question", extra={"lead_id": "l1"})],
    )
    assert applied == 1
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_noop_is_skipped():
    db = _db()
    store = TouchStore(db_conn=db)
    applied = await store.apply([TouchMutation(action="noop", reason="unclear")])
    assert applied == 0
    db.execute.assert_not_awaited()


# ---------- aggregate behaviour --------------------------------------------

@pytest.mark.asyncio
async def test_mixed_mutations_count_matches_applied():
    db = _db()
    store = TouchStore(db_conn=db)
    when = datetime.now(UTC) + timedelta(days=3)
    muts = [
        TouchMutation(action="cancel", touch_id="t1"),
        TouchMutation(action="pause", touch_id="t2"),
        TouchMutation(action="reschedule", touch_id="t3", new_scheduled_at=when),
        TouchMutation(action="escalate", extra={"lead_id": "l1"}),
        TouchMutation(action="noop"),  # skipped
    ]
    applied = await store.apply(muts)
    assert applied == 4
    # 3 UPDATEs (cancel, pause, reschedule); escalate has no DB call; noop has no DB call
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_no_db_fallback_returns_zero_applied():
    store = TouchStore(db_conn=None)
    applied = await store.apply(
        [TouchMutation(action="cancel", touch_id="t1")],
    )
    assert applied == 0


@pytest.mark.asyncio
async def test_exception_in_one_mutation_does_not_block_others():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[RuntimeError("boom"), None])
    store = TouchStore(db_conn=db)
    muts = [
        TouchMutation(action="cancel", touch_id="t1"),
        TouchMutation(action="cancel", touch_id="t2"),
    ]
    applied = await store.apply(muts)
    assert applied == 1  # only the second succeeded
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_load_pending_queries_only_pending_and_paused():
    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[
        {"id": "t1", "channel": "email", "sequence_step": 2,
         "scheduled_at": datetime.now(UTC), "status": "pending"},
    ])
    store = TouchStore(db_conn=db)
    rows = await store.load_pending("lead-1")
    assert len(rows) == 1
    sql, *args = db.fetch.await_args.args
    assert "lead_id = $1" in sql
    assert "status IN ('pending', 'paused')" in sql
    assert args[0] == "lead-1"


@pytest.mark.asyncio
async def test_load_pending_empty_when_no_db():
    store = TouchStore(db_conn=None)
    rows = await store.load_pending("lead-1")
    assert rows == []
