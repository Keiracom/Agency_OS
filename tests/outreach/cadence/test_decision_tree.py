"""
Tests for src/outreach/cadence/decision_tree.py — CadenceDecisionTree.

Covers:
- each of the 8 intents produces the expected mutation shape
- low-confidence non-unclear input is forced to 'unclear' -> noop
- cancel-all emits one cancel per pending touch
- ooo reschedule uses return_date + OOO_RESUME_OFFSET_DAYS, and never shifts
  an already-later scheduled_at backwards
- suppress mutation carries the prospect email + correct reason
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.outreach.cadence.decision_tree import (
    CONFIDENCE_FLOOR,
    OOO_RESUME_OFFSET_DAYS,
    QUESTION_PAUSE_HOURS,
    CadenceDecisionTree,
)


def _state(n_pending: int = 2, email: str = "ceo@acme.com.au") -> dict:
    base = datetime.now(UTC) + timedelta(days=1)
    touches = [
        {
            "id": f"t{i}",
            "channel": "email",
            "sequence_step": i + 1,
            "scheduled_at": base + timedelta(days=i),
        }
        for i in range(n_pending)
    ]
    return {
        "lead_id": "lead-1",
        "client_id": "client-1",
        "prospect": {"email": email},
        "pending_touches": touches,
    }


# -- high-confidence happy paths --------------------------------------------


def test_positive_cancels_and_inserts_booking():
    muts = CadenceDecisionTree().decide("positive_interested", 0.95, _state(n_pending=3), {})
    actions = [m.action for m in muts]
    assert actions == ["cancel", "cancel", "cancel", "insert"]
    assert muts[-1].channel == "email"
    assert muts[-1].content.get("template") == "booking_offer"


def test_booking_cancels_and_inserts_confirmation():
    muts = CadenceDecisionTree().decide("booking_request", 0.9, _state(2), {"time": "Tue 3pm"})
    assert [m.action for m in muts] == ["cancel", "cancel", "insert"]
    assert muts[-1].content.get("template") == "meeting_confirmation"
    assert muts[-1].content["extracted"]["time"] == "Tue 3pm"


def test_not_interested_cancels_and_suppresses():
    muts = CadenceDecisionTree().decide("not_interested", 0.85, _state(2), {})
    assert [m.action for m in muts] == ["cancel", "cancel", "suppress"]
    assert muts[-1].extra["email"] == "ceo@acme.com.au"
    assert muts[-1].extra["suppression_reason"] == "not_interested"


def test_unsubscribe_cancels_and_permanently_suppresses():
    muts = CadenceDecisionTree().decide("unsubscribe", 1.0, _state(2), {})
    assert muts[-1].action == "suppress"
    assert muts[-1].extra["suppression_reason"] == "unsubscribe"


def test_ooo_reschedules_all_pending_to_return_plus_offset():
    return_date = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    muts = CadenceDecisionTree().decide(
        "out_of_office", 0.9, _state(2), {"return_date": return_date}
    )
    assert all(m.action == "reschedule" for m in muts)
    expected_min = datetime.fromisoformat(return_date) + timedelta(days=OOO_RESUME_OFFSET_DAYS)
    for m in muts:
        assert m.new_scheduled_at >= expected_min


def test_ooo_keeps_later_scheduled_at_untouched():
    # A touch already further in the future than the resume date should not move.
    resume_input = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    state = _state(1)
    state["pending_touches"][0]["scheduled_at"] = datetime.now(UTC) + timedelta(days=30)
    muts = CadenceDecisionTree().decide(
        "out_of_office",
        0.9,
        state,
        {"return_date": resume_input},
    )
    # Kept the later scheduled_at (>2d+offset)
    assert muts[0].new_scheduled_at > datetime.now(UTC) + timedelta(days=7)


def test_question_pauses_and_escalates():
    muts = CadenceDecisionTree().decide("question", 0.85, _state(2), {})
    actions = [m.action for m in muts]
    assert actions == ["pause", "pause", "escalate"]
    # pause target is now + QUESTION_PAUSE_HOURS ± a few seconds
    expected = datetime.now(UTC) + timedelta(hours=QUESTION_PAUSE_HOURS)
    assert abs((muts[0].new_scheduled_at - expected).total_seconds()) < 30


def test_referral_logs_and_continues_sequence():
    # With referral_email present, _handle_referral now emits a
    # create_prospect mutation alongside the noop log. The noop-log and its
    # extras remain the first mutation — original sequence still untouched.
    # (See tests/outreach/cadence/test_referral_create_prospect.py for the
    # create_prospect branch coverage.)
    muts = CadenceDecisionTree().decide(
        "referral",
        0.85,
        _state(3),
        {"referral_name": "Jane", "referral_email": "jane@acme.com.au"},
    )
    assert muts[0].action == "noop"
    assert muts[0].extra["referral_email"] == "jane@acme.com.au"


def test_unclear_returns_single_noop():
    muts = CadenceDecisionTree().decide("unclear", 1.0, _state(2), {})
    assert [m.action for m in muts] == ["noop"]


# -- confidence-floor downgrade ---------------------------------------------


def test_low_confidence_non_unclear_is_forced_to_unclear():
    muts = CadenceDecisionTree().decide(
        "positive_interested", CONFIDENCE_FLOOR - 0.01, _state(2), {}
    )
    assert [m.action for m in muts] == ["noop"]


def test_exact_floor_confidence_is_not_downgraded():
    muts = CadenceDecisionTree().decide("positive_interested", CONFIDENCE_FLOOR, _state(2), {})
    assert any(m.action == "insert" for m in muts)


# -- edge cases -------------------------------------------------------------


def test_ooo_falls_back_to_plus_7d_when_return_date_missing():
    muts = CadenceDecisionTree().decide("out_of_office", 0.9, _state(1), {})
    # Fallback is now + 7d + OOO_RESUME_OFFSET_DAYS
    expected = datetime.now(UTC) + timedelta(days=7 + OOO_RESUME_OFFSET_DAYS)
    assert abs((muts[0].new_scheduled_at - expected).total_seconds()) < 60


def test_no_pending_touches_is_safe():
    state = _state(0)
    muts = CadenceDecisionTree().decide("not_interested", 0.9, state, {})
    # Only the suppress mutation — no cancels possible
    assert [m.action for m in muts] == ["suppress"]


@pytest.mark.parametrize(
    "intent",
    [
        "positive_interested",
        "booking_request",
        "not_interested",
        "unsubscribe",
        "out_of_office",
        "question",
        "referral",
        "unclear",
    ],
)
def test_all_eight_intents_return_at_least_one_mutation(intent):
    muts = CadenceDecisionTree().decide(intent, 0.9, _state(1), {})
    assert len(muts) >= 1
