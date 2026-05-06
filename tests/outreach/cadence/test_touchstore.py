"""
Tests for TouchStore.apply() — all DB calls are AsyncMock, zero real DB hits.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.routes.outreach_webhooks import TouchStore
from src.outreach.cadence.decision_tree import TouchMutation

FAKE_ID = "00000000-0000-0000-0000-000000000001"
FAKE_LEAD = "00000000-0000-0000-0000-000000000002"
FUTURE = datetime.now(UTC) + timedelta(hours=24)


def _store() -> tuple[TouchStore, AsyncMock]:
    db = MagicMock()
    db.execute = AsyncMock(return_value=None)
    db.fetch = AsyncMock(return_value=[])
    return TouchStore(db_conn=db), db


# ---------------------------------------------------------------------------
# Single-action tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_updates_status():
    store, db = _store()
    m = TouchMutation(action="cancel", touch_id=FAKE_ID, reason="test")
    result = await store.apply([m])
    assert result == 1
    db.execute.assert_awaited_once()
    call_sql = db.execute.call_args[0][0]
    assert "cancelled" in call_sql
    assert db.execute.call_args[0][1] == FAKE_ID


@pytest.mark.asyncio
async def test_pause_updates_status():
    store, db = _store()
    m = TouchMutation(action="pause", touch_id=FAKE_ID, reason="test")
    result = await store.apply([m])
    assert result == 1
    call_sql = db.execute.call_args[0][0]
    assert "paused" in call_sql
    assert db.execute.call_args[0][1] == FAKE_ID


@pytest.mark.asyncio
async def test_reschedule_updates_scheduled_at():
    store, db = _store()
    m = TouchMutation(action="reschedule", touch_id=FAKE_ID, new_scheduled_at=FUTURE)
    result = await store.apply([m])
    assert result == 1
    call_sql = db.execute.call_args[0][0]
    assert "scheduled_at" in call_sql
    args = db.execute.call_args[0]
    assert args[1] == FUTURE
    assert args[2] == FAKE_ID


@pytest.mark.asyncio
async def test_insert_creates_row():
    store, db = _store()
    m = TouchMutation(
        action="insert",
        channel="email",
        sequence_step=1,
        new_scheduled_at=FUTURE,
        content={"template": "booking_offer"},
        extra={"lead_id": FAKE_LEAD, "prospect": {"email": "a@b.com"}},
    )
    result = await store.apply([m])
    assert result == 1
    call_sql = db.execute.call_args[0][0]
    assert "INSERT INTO scheduled_touches" in call_sql
    args = db.execute.call_args[0]
    assert args[1] == FAKE_LEAD  # lead_id
    assert args[2] == "email"  # channel
    assert args[3] == 1  # sequence_step
    assert args[4] == FUTURE  # scheduled_at
    content_arg = json.loads(args[5])
    assert content_arg["template"] == "booking_offer"


@pytest.mark.asyncio
async def test_suppress_cancels_all_pending():
    store, db = _store()
    m = TouchMutation(
        action="suppress",
        reason="not_interested",
        extra={"lead_id": FAKE_LEAD, "email": "x@y.com"},
    )
    result = await store.apply([m])
    assert result == 1
    call_sql = db.execute.call_args[0][0]
    assert "cancelled" in call_sql
    assert "lead_id" in call_sql
    assert db.execute.call_args[0][1] == FAKE_LEAD


@pytest.mark.asyncio
async def test_suppress_no_lead_id_skips_execute():
    """suppress mutation with no lead_id should still count as applied but skip DB."""
    store, db = _store()
    m = TouchMutation(action="suppress", reason="test", extra={})
    result = await store.apply([m])
    assert result == 1
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_noop_and_escalate_skip_db():
    store, db = _store()
    mutations = [
        TouchMutation(action="noop", reason="unclear"),
        TouchMutation(action="escalate", reason="human review"),
        TouchMutation(action="create_prospect", reason="referral"),
    ]
    result = await store.apply(mutations)
    assert result == 3
    db.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_db_returns_zero():
    store = TouchStore(db_conn=None)
    m = TouchMutation(action="cancel", touch_id=FAKE_ID)
    result = await store.apply([m])
    assert result == 0


@pytest.mark.asyncio
async def test_empty_list_returns_zero():
    store, db = _store()
    result = await store.apply([])
    assert result == 0
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_mixed_mutations():
    """Five different actions in one call — all should succeed."""
    store, db = _store()
    mutations = [
        TouchMutation(action="cancel", touch_id=FAKE_ID),
        TouchMutation(action="pause", touch_id=FAKE_ID),
        TouchMutation(action="reschedule", touch_id=FAKE_ID, new_scheduled_at=FUTURE),
        TouchMutation(
            action="insert",
            channel="linkedin",
            sequence_step=2,
            new_scheduled_at=FUTURE,
            extra={"lead_id": FAKE_LEAD},
        ),
        TouchMutation(action="noop", reason="referral logged"),
    ]
    result = await store.apply(mutations)
    assert result == 5
    # cancel + pause + reschedule + insert = 4 DB calls; noop = 0
    assert db.execute.await_count == 4


@pytest.mark.asyncio
async def test_db_error_logs_and_continues():
    """A DB error on one mutation should not abort subsequent mutations."""
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[Exception("db down"), None])
    store = TouchStore(db_conn=db)
    mutations = [
        TouchMutation(action="cancel", touch_id=FAKE_ID),
        TouchMutation(action="pause", touch_id=FAKE_ID),
    ]
    result = await store.apply(mutations)
    # First mutation raises → not counted; second succeeds → counted.
    # applied += 1 is inside the try block so errors prevent incrementing.
    assert result == 1
    assert db.execute.await_count == 2
