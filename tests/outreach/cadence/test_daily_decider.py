"""
Tests for src/outreach/cadence/daily_decider.py — DailyDecider.

Covers the 9 decision paths in the brief:
  1/2 no-touch-yet -> schedule step 1
  3   gap exceeded -> schedule next step
  4   too soon -> skip
  5   positive reply -> skip (webhook owns)
  6   unsubscribe -> skip (suppressed)
  7   ooo with return_date -> skip until resume
  7b  ooo past resume -> re-schedules current step
  8   exhausted sequence -> nurture
  9   meeting booked -> skip permanently
Plus:
  - no usable channel -> escalate
  - nurture without email -> escalate
  - apply_actions executes inserts for schedule_next + nurture, swallows errors
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from src.outreach.cadence.daily_decider import (
    MAX_STEP,
    NURTURE_INTERVAL_DAYS,
    DailyDecider,
    DeciderAction,
    apply_actions,
)


def _p(**kw) -> dict:
    base = {
        "lead_id": "lead-1",
        "last_reply_intent": None,
        "last_reply_extracted": {},
        "last_touch_sent_at": None,
        "current_sequence_step": 0,
        "total_touches_sent": 0,
        "meeting_booked_at": None,
        "has_email": True, "has_phone": True, "has_linkedin": True,
        "timezone": "Australia/Sydney",
        "ooo_return_date": None,
    }
    base.update(kw)
    return base


def _decider() -> DailyDecider:
    return DailyDecider()


# ---------- positive paths ---------------------------------------------------

def test_no_touches_yet_schedules_step_1():
    a = _decider()._decide_one(_p())
    assert a.action == "schedule_next"
    assert a.sequence_step == 1
    assert a.channel == "email"
    assert a.scheduled_at is not None


def test_gap_exceeded_schedules_next_step():
    last = datetime.now(UTC) - timedelta(days=5)  # step 2 requires 3d gap
    a = _decider()._decide_one(_p(
        current_sequence_step=1, total_touches_sent=1, last_touch_sent_at=last,
    ))
    assert a.action == "schedule_next"
    assert a.sequence_step == 2


def test_too_soon_skips():
    last = datetime.now(UTC) - timedelta(days=1)  # needs 3d to advance to step 2
    a = _decider()._decide_one(_p(
        current_sequence_step=1, total_touches_sent=1, last_touch_sent_at=last,
    ))
    assert a.action == "skip"
    assert "too soon" in a.reason


def test_positive_reply_skips():
    a = _decider()._decide_one(_p(
        last_reply_intent="positive_interested",
        current_sequence_step=2, total_touches_sent=2,
    ))
    assert a.action == "skip"
    assert "replied" in a.reason


def test_unsubscribe_skips_as_suppressed():
    a = _decider()._decide_one(_p(
        last_reply_intent="unsubscribe", current_sequence_step=1, total_touches_sent=1,
    ))
    assert a.action == "skip"
    assert "suppressed" in a.reason


def test_ooo_with_future_return_skips():
    future = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    a = _decider()._decide_one(_p(
        last_reply_intent="out_of_office", ooo_return_date=future,
        current_sequence_step=1, total_touches_sent=1,
    ))
    assert a.action == "skip"
    assert "ooo" in a.reason


def test_ooo_past_resume_schedules_again():
    past = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    a = _decider()._decide_one(_p(
        last_reply_intent="out_of_office", ooo_return_date=past,
        current_sequence_step=2, total_touches_sent=2,
        last_touch_sent_at=datetime.now(UTC) - timedelta(days=30),
    ))
    assert a.action == "schedule_next"


def test_sequence_exhausted_becomes_nurture():
    last = datetime.now(UTC) - timedelta(days=30)
    a = _decider()._decide_one(_p(
        current_sequence_step=MAX_STEP, total_touches_sent=MAX_STEP,
        last_touch_sent_at=last,
    ))
    assert a.action == "nurture"
    assert a.channel == "email"
    expected_min = datetime.now(UTC) + timedelta(days=NURTURE_INTERVAL_DAYS - 1)
    assert a.scheduled_at >= expected_min


def test_meeting_booked_skips_permanently():
    a = _decider()._decide_one(_p(meeting_booked_at=datetime.now(UTC)))
    assert a.action == "skip"
    assert "meeting_booked" in a.reason


# ---------- escalation paths -------------------------------------------------

def test_no_usable_channel_escalates():
    a = _decider()._decide_one(_p(
        has_email=False, has_phone=False, has_linkedin=False,
    ))
    assert a.action == "escalate"
    assert "no usable channel" in a.reason


def test_exhausted_without_email_escalates():
    a = _decider()._decide_one(_p(
        current_sequence_step=MAX_STEP, total_touches_sent=MAX_STEP,
        has_email=False, has_phone=True, has_linkedin=True,
    ))
    assert a.action == "escalate"
    assert "nurture" in a.reason


# ---------- evaluate_all hits the DB path -----------------------------------

@pytest.mark.asyncio
async def test_evaluate_all_fetches_and_decides():
    db = AsyncMock()
    db.fetch = AsyncMock(return_value=[
        _p(lead_id="a"),
        _p(lead_id="b", meeting_booked_at=datetime.now(UTC)),
    ])
    actions = await DailyDecider().evaluate_all(db, client_id="c1")
    assert [a.action for a in actions] == ["schedule_next", "skip"]
    db.fetch.assert_awaited_once()


# ---------- apply_actions ---------------------------------------------------

@pytest.mark.asyncio
async def test_apply_actions_writes_scheduled_rows_and_counts():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    when = datetime.now(UTC) + timedelta(days=1)
    actions = [
        DeciderAction("l1", "schedule_next", "email", when, "", 1),
        DeciderAction("l2", "nurture",       "email", when, "", None),
        DeciderAction("l3", "skip",          None,    None, "too soon", None),
        DeciderAction("l4", "suppress",      None,    None, "unsub", None),
        DeciderAction("l5", "escalate",      None,    None, "no channel", None),
    ]
    counts = await apply_actions(db, "client-1", actions)
    assert counts["scheduled"] == 1
    assert counts["nurture"] == 1
    assert counts["skipped"] == 1
    assert counts["suppressed"] == 1
    assert counts["escalated"] == 1
    assert db.execute.await_count == 2  # only schedule_next + nurture insert


@pytest.mark.asyncio
async def test_apply_actions_swallows_db_errors():
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=RuntimeError("dead conn"))
    when = datetime.now(UTC) + timedelta(days=1)
    counts = await apply_actions(
        db, "c1",
        [DeciderAction("l1", "schedule_next", "email", when, "", 1)],
    )
    assert counts["errors"] == 1
    assert counts["scheduled"] == 0
