"""
Tests for src/outreach/cadence/nurture_drip.py

In-memory fakes (dict-backed stores). now_fn frozen to a fixed datetime.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.outreach.cadence.nurture_drip import (
    NURTURE_INTERVAL_DAYS,
    NURTURE_MAX_TOUCHES,
    NurtureDrip,
    NurtureState,
    NurtureStatus,
    next_channel_for,
)

FIXED_NOW = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# In-memory fakes
# ---------------------------------------------------------------------------


class FakeStore:
    def __init__(
        self, prospect_info: dict | None = None, initial_state: NurtureState | None = None
    ):
        self._prospects: dict[str, dict] = {}
        if prospect_info:
            self._prospects.update(prospect_info)
        self._states: dict[str, NurtureState] = {}
        if initial_state:
            self._states[initial_state.prospect_id] = initial_state
        self.upserted: list[NurtureState] = []
        self.scheduled: list[tuple] = []

    def get_prospect_status(self, prospect_id: str) -> dict:
        return self._prospects.get(prospect_id, {})

    def get_state(self, prospect_id: str) -> NurtureState | None:
        return self._states.get(prospect_id)

    def upsert_state(self, state: NurtureState) -> None:
        self._states[state.prospect_id] = state
        self.upserted.append(state)

    def insert_scheduled_touch(
        self, prospect_id, client_id, channel, scheduled_at, sequence_step=None
    ) -> None:
        self.scheduled.append((prospect_id, client_id, channel, scheduled_at, sequence_step))

    def build_drip(self) -> NurtureDrip:
        return NurtureDrip(
            get_prospect_status=self.get_prospect_status,
            get_state=self.get_state,
            upsert_state=self.upsert_state,
            insert_scheduled_touch=self.insert_scheduled_touch,
            now_fn=lambda: FIXED_NOW,
        )


def cold_prospect_info() -> dict:
    return {
        "outreach_status": "complete",
        "has_reply": False,
        "has_meeting": False,
    }


# ---------------------------------------------------------------------------
# 1. next_channel_for — alternating pattern
# ---------------------------------------------------------------------------


def test_next_channel_email_at_0():
    assert next_channel_for(0) == "email"


def test_next_channel_linkedin_at_1():
    assert next_channel_for(1) == "linkedin"


def test_next_channel_email_at_2():
    assert next_channel_for(2) == "email"


def test_next_channel_linkedin_at_3():
    assert next_channel_for(3) == "linkedin"


def test_next_channel_email_at_4():
    assert next_channel_for(4) == "email"


def test_next_channel_linkedin_at_5():
    assert next_channel_for(5) == "linkedin"


def test_next_channel_none_at_6():
    assert next_channel_for(6) is None


def test_next_channel_none_beyond_cap():
    assert next_channel_for(10) is None


# ---------------------------------------------------------------------------
# 2-6. is_eligible
# ---------------------------------------------------------------------------


def test_is_eligible_cold_prospect_true():
    store = FakeStore(prospect_info={"p1": cold_prospect_info()})
    drip = store.build_drip()
    eligible, reason = drip.is_eligible("p1")
    assert eligible is True
    assert reason == ""


def test_is_eligible_rejects_non_complete_status():
    store = FakeStore(
        prospect_info={
            "p1": {
                "outreach_status": "in_sequence",
                "has_reply": False,
                "has_meeting": False,
            }
        }
    )
    drip = store.build_drip()
    eligible, reason = drip.is_eligible("p1")
    assert eligible is False
    assert "not_cold" in reason
    assert "in_sequence" in reason


def test_is_eligible_rejects_has_reply():
    store = FakeStore(
        prospect_info={
            "p1": {
                "outreach_status": "complete",
                "has_reply": True,
                "has_meeting": False,
            }
        }
    )
    drip = store.build_drip()
    eligible, reason = drip.is_eligible("p1")
    assert eligible is False
    assert reason == "has_reply"


def test_is_eligible_rejects_has_meeting():
    store = FakeStore(
        prospect_info={
            "p1": {
                "outreach_status": "complete",
                "has_reply": False,
                "has_meeting": True,
            }
        }
    )
    drip = store.build_drip()
    eligible, reason = drip.is_eligible("p1")
    assert eligible is False
    assert reason == "has_meeting"


def test_is_eligible_rejects_suppressed():
    store = FakeStore(
        prospect_info={
            "p1": {
                "outreach_status": "suppressed",
                "has_reply": False,
                "has_meeting": False,
            }
        }
    )
    drip = store.build_drip()
    eligible, reason = drip.is_eligible("p1")
    assert eligible is False
    assert reason == "suppressed"


# ---------------------------------------------------------------------------
# 7. enqueue happy path
# ---------------------------------------------------------------------------


def test_enqueue_cold_prospect_creates_active_state_and_schedules_touch():
    store = FakeStore(prospect_info={"p1": cold_prospect_info()})
    drip = store.build_drip()
    result = drip.enqueue("p1", "cl1")

    assert result.action == "enqueued"
    assert result.status == NurtureStatus.ACTIVE
    assert result.state is not None
    assert result.state.touches_sent == 0
    assert result.state.next_channel == "email"
    expected_at = FIXED_NOW + timedelta(days=NURTURE_INTERVAL_DAYS)
    assert result.state.next_scheduled_at == expected_at

    # State was upserted
    assert len(store.upserted) == 1
    # Scheduled touch was inserted
    assert len(store.scheduled) == 1
    pid, cid, channel, sched_at, step = store.scheduled[0]
    assert pid == "p1"
    assert cid == "cl1"
    assert channel == "email"
    assert sched_at == expected_at
    assert step == 100


# ---------------------------------------------------------------------------
# 8. enqueue idempotent — already-active
# ---------------------------------------------------------------------------


def test_enqueue_already_active_returns_already_active_no_duplicate():
    existing = NurtureState(
        prospect_id="p1",
        client_id="cl1",
        next_channel="linkedin",
        next_scheduled_at=FIXED_NOW + timedelta(days=15),
        touches_sent=1,
        status=NurtureStatus.ACTIVE,
        started_at=FIXED_NOW,
    )
    store = FakeStore(prospect_info={"p1": cold_prospect_info()}, initial_state=existing)
    drip = store.build_drip()
    result = drip.enqueue("p1", "cl1")

    assert result.action == "already-active"
    assert result.status == NurtureStatus.ACTIVE
    assert result.state is existing
    # No new upserts or scheduled touches
    assert len(store.upserted) == 0
    assert len(store.scheduled) == 0


# ---------------------------------------------------------------------------
# 9. enqueue exhausted
# ---------------------------------------------------------------------------


def test_enqueue_exhausted_returns_exhausted_no_touch():
    existing = NurtureState(
        prospect_id="p1",
        client_id="cl1",
        next_channel=None,
        next_scheduled_at=None,
        touches_sent=6,
        status=NurtureStatus.EXHAUSTED,
        started_at=FIXED_NOW,
    )
    store = FakeStore(prospect_info={"p1": cold_prospect_info()}, initial_state=existing)
    drip = store.build_drip()
    result = drip.enqueue("p1", "cl1")

    assert result.action == "exhausted"
    assert result.status == NurtureStatus.EXHAUSTED
    assert len(store.scheduled) == 0


# ---------------------------------------------------------------------------
# 10. enqueue ineligible (suppressed)
# ---------------------------------------------------------------------------


def test_enqueue_suppressed_returns_skipped():
    store = FakeStore(
        prospect_info={
            "p1": {
                "outreach_status": "suppressed",
                "has_reply": False,
                "has_meeting": False,
            }
        }
    )
    drip = store.build_drip()
    result = drip.enqueue("p1", "cl1")

    assert result.action == "skipped"
    assert result.reason == "suppressed"
    assert len(store.scheduled) == 0


# ---------------------------------------------------------------------------
# 11. record_send advances 0->1 with next_channel='linkedin'
# ---------------------------------------------------------------------------


def test_record_send_advances_to_touch_1_linkedin():
    state = NurtureState(
        prospect_id="p1",
        client_id="cl1",
        next_channel="email",
        next_scheduled_at=FIXED_NOW,
        touches_sent=0,
        status=NurtureStatus.ACTIVE,
        started_at=FIXED_NOW,
    )
    store = FakeStore(initial_state=state)
    drip = store.build_drip()
    result = drip.record_send("p1")

    assert result.action == "enqueued"
    assert result.state.touches_sent == 1
    assert result.state.next_channel == "linkedin"
    assert result.state.next_scheduled_at == FIXED_NOW + timedelta(days=NURTURE_INTERVAL_DAYS)
    # A new scheduled touch was inserted
    assert len(store.scheduled) == 1
    _, _, ch, _, _ = store.scheduled[0]
    assert ch == "linkedin"


# ---------------------------------------------------------------------------
# 12. record_send alternates channels across 6 calls
# ---------------------------------------------------------------------------


def test_record_send_alternates_channels_across_6_calls():
    state = NurtureState(
        prospect_id="p1",
        client_id="cl1",
        next_channel="email",
        next_scheduled_at=FIXED_NOW,
        touches_sent=0,
        status=NurtureStatus.ACTIVE,
        started_at=FIXED_NOW,
    )
    store = FakeStore(initial_state=state)
    drip = store.build_drip()

    expected_sequence = ["linkedin", "email", "linkedin", "email", "linkedin"]
    for i, expected_ch in enumerate(expected_sequence):
        result = drip.record_send("p1")
        assert result.action == "enqueued", f"call {i + 1}: expected enqueued got {result.action}"
        assert result.state.next_channel == expected_ch, (
            f"call {i + 1}: expected {expected_ch} got {result.state.next_channel}"
        )


# ---------------------------------------------------------------------------
# 13. record_send at touch 5 -> touch 6 marks exhausted, no further insert
# ---------------------------------------------------------------------------


def test_record_send_at_touch_5_marks_exhausted():
    state = NurtureState(
        prospect_id="p1",
        client_id="cl1",
        next_channel="linkedin",
        next_scheduled_at=FIXED_NOW,
        touches_sent=5,
        status=NurtureStatus.ACTIVE,
        started_at=FIXED_NOW,
    )
    store = FakeStore(initial_state=state)
    drip = store.build_drip()
    result = drip.record_send("p1")

    assert result.action == "exhausted"
    assert result.status == NurtureStatus.EXHAUSTED
    assert result.state.touches_sent == NURTURE_MAX_TOUCHES
    assert result.state.next_channel is None
    assert result.state.next_scheduled_at is None
    # No scheduled touch inserted — drip is done
    assert len(store.scheduled) == 0


# ---------------------------------------------------------------------------
# 14. record_send on missing state -> skipped / no drip state
# ---------------------------------------------------------------------------


def test_record_send_missing_state_returns_skipped():
    store = FakeStore()  # no initial state
    drip = store.build_drip()
    result = drip.record_send("p1")

    assert result.action == "skipped"
    assert result.reason == "no drip state"
    assert len(store.scheduled) == 0
