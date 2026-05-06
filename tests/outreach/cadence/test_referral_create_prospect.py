"""
Tests for referral-to-new-prospect flow.

Covers:
- decision_tree._handle_referral emits create_prospect mutation when referral_email present
- decision_tree._handle_referral still emits noop-logging mutation (backwards-compatible)
- cadence_orchestrator.create_prospect_from_referral: happy path, existing, malformed,
  missing client_id, name-optional.
"""

from __future__ import annotations

from src.outreach.cadence.decision_tree import (
    VALID_ACTIONS,
    CadenceDecisionTree,
)
from src.pipeline.cadence_orchestrator import create_prospect_from_referral


# ---------------------------------------------------------------------------
# Decision tree — referral now emits create_prospect + noop
# ---------------------------------------------------------------------------


def _state() -> dict:
    return {
        "lead_id": "lead-1",
        "client_id": "client-1",
        "prospect": {"email": "ceo@acme.com.au"},
        "pending_touches": [],
    }


def test_valid_action_create_prospect_registered():
    assert "create_prospect" in VALID_ACTIONS


def test_referral_with_email_emits_noop_plus_create_prospect():
    muts = CadenceDecisionTree().decide(
        "referral",
        0.9,
        _state(),
        {"referral_name": "Jane", "referral_email": "jane@acme.com.au"},
    )
    actions = [m.action for m in muts]
    assert actions == ["noop", "create_prospect"]
    cp = muts[1]
    assert cp.extra["referral_email"] == "jane@acme.com.au"
    assert cp.extra["referral_name"] == "Jane"
    assert cp.extra["source"] == "referral"
    assert cp.extra["referred_by_lead_id"] == "lead-1"
    assert cp.extra["client_id"] == "client-1"


def test_referral_without_email_only_logs():
    # Existing behaviour preserved when no referral_email extracted.
    muts = CadenceDecisionTree().decide(
        "referral",
        0.9,
        _state(),
        {"referral_name": "Jane"},
    )
    assert [m.action for m in muts] == ["noop"]


# ---------------------------------------------------------------------------
# create_prospect_from_referral — injected DB callables
# ---------------------------------------------------------------------------


def _noop_lookup(*_a, **_kw):
    return None


def _reject_insert(*_a, **_kw):
    raise AssertionError("should not insert")


def test_create_prospect_happy_path():
    inserted = []
    touch_counts = []

    def bu_insert(row):
        inserted.append(row)
        return "prospect-xyz"

    def touches_insert(pid, cid, seq):
        touch_counts.append((pid, cid, len(seq)))
        return len(seq)

    out = create_prospect_from_referral(
        {
            "client_id": "c1",
            "referral_email": "new@acme.com",
            "referral_name": "New Person",
            "referred_by_lead_id": "lead-A",
        },
        bu_lookup_by_email=_noop_lookup,
        bu_insert=bu_insert,
        scheduled_touches_insert=touches_insert,
    )
    assert out["status"] == "created"
    assert out["prospect_id"] == "prospect-xyz"
    assert out["touches_scheduled"] == 5
    assert inserted[0]["email"] == "new@acme.com"
    assert inserted[0]["display_name"] == "New Person"
    assert inserted[0]["source"] == "referral"
    assert inserted[0]["outreach_status"] == "pending"
    assert touch_counts == [("prospect-xyz", "c1", 5)]


def test_create_prospect_existing_rejects_insert():
    def lookup(_cid, _email):
        return {"id": "existing-123"}

    out = create_prospect_from_referral(
        {"client_id": "c1", "referral_email": "dup@acme.com"},
        bu_lookup_by_email=lookup,
        bu_insert=_reject_insert,
        scheduled_touches_insert=_reject_insert,
    )
    assert out["status"] == "exists"
    assert out["prospect_id"] == "existing-123"
    assert out["touches_scheduled"] == 0


def test_create_prospect_malformed_email_rejected():
    out = create_prospect_from_referral(
        {"client_id": "c1", "referral_email": "not-an-email"},
        bu_lookup_by_email=_noop_lookup,
        bu_insert=_reject_insert,
        scheduled_touches_insert=_reject_insert,
    )
    assert out["status"] == "rejected"
    assert "invalid email" in out["reason"]
    assert out["prospect_id"] is None


def test_create_prospect_missing_email_rejected():
    out = create_prospect_from_referral(
        {"client_id": "c1"},
        bu_lookup_by_email=_noop_lookup,
        bu_insert=_reject_insert,
        scheduled_touches_insert=_reject_insert,
    )
    assert out["status"] == "rejected"


def test_create_prospect_missing_client_id_rejected():
    out = create_prospect_from_referral(
        {"referral_email": "x@y.com"},
        bu_lookup_by_email=_noop_lookup,
        bu_insert=_reject_insert,
        scheduled_touches_insert=_reject_insert,
    )
    assert out["status"] == "rejected"
    assert "client_id" in out["reason"]


def test_create_prospect_name_optional():
    def bu_insert(_row):
        return "pid-1"

    def touches_insert(_a, _b, _c):
        return 5

    out = create_prospect_from_referral(
        {"client_id": "c1", "referral_email": "a@b.com"},
        bu_lookup_by_email=_noop_lookup,
        bu_insert=bu_insert,
        scheduled_touches_insert=touches_insert,
    )
    assert out["status"] == "created"
    assert out["touches_scheduled"] == 5
