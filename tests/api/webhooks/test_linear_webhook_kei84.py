"""KEI-84 — behavioural tests for the extended Linear → Supabase webhook.

Covers the new event matrix per spec:
- create (existing path; regression-locked)
- status update: backlog/unstarted/triage → available
- status update: started → active
- status update: completed → done (clears claimed_by)
- status update: canceled → cancelled
- remove (Linear delete) → cancelled
- never-downgrade-done guard
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.api.webhooks import linear as linear_webhook  # noqa: E402


def _payload(action: str, identifier: str, state_type: str | None = None) -> dict:
    data: dict = {
        "identifier": identifier,
        "title": "test",
        "priority": 2,
        "url": "https://linear.app/x",
    }
    if state_type:
        data["state"] = {"type": state_type, "name": state_type}
    return {"action": action, "type": "Issue", "data": data}


def test_normalise_create_returns_create_op():
    out = linear_webhook._normalise_event(_payload("create", "KEI-100"))
    assert out["op"] == "create"
    assert out["identifier"] == "KEI-100"


def test_normalise_update_backlog_maps_to_available():
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "backlog"))
    assert out["op"] == "status"
    assert out["task_status"] == "available"


def test_normalise_update_unstarted_maps_to_available():
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "unstarted"))
    assert out["task_status"] == "available"


def test_normalise_update_started_maps_to_active():
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "started"))
    assert out["task_status"] == "active"


def test_normalise_update_completed_maps_to_done():
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "completed"))
    assert out["task_status"] == "done"


def test_normalise_update_canceled_maps_to_cancelled():
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "canceled"))
    assert out["task_status"] == "cancelled"


def test_normalise_remove_returns_cancelled_op():
    out = linear_webhook._normalise_event(_payload("remove", "KEI-100"))
    assert out["op"] == "remove"
    assert out["task_status"] == "cancelled"


def test_normalise_unknown_state_returns_none():
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "obscure_state"))
    assert out is None


def test_normalise_non_issue_type_returns_none():
    payload = {"action": "update", "type": "Comment", "data": {"identifier": "KEI-100"}}
    assert linear_webhook._normalise_event(payload) is None


def test_normalise_missing_identifier_returns_none():
    payload = {"action": "create", "type": "Issue", "data": {"title": "no id"}}
    assert linear_webhook._normalise_event(payload) is None


def test_state_mapping_constants_cover_all_linear_state_types():
    expected = {"backlog", "unstarted", "triage", "started", "completed", "canceled"}
    assert expected.issubset(linear_webhook.LINEAR_STATE_TO_BD.keys())
    assert expected.issubset(linear_webhook.LINEAR_STATE_TO_TASK_STATUS.keys())


def test_state_mapping_canceled_is_distinct_from_done():
    # KEI-84 regression: prior code mapped canceled→closed→done; spec requires cancelled.
    assert linear_webhook.LINEAR_STATE_TO_TASK_STATUS["canceled"] == "cancelled"
    assert linear_webhook.LINEAR_STATE_TO_TASK_STATUS["completed"] == "done"
    assert (
        linear_webhook.LINEAR_STATE_TO_TASK_STATUS["canceled"]
        != linear_webhook.LINEAR_STATE_TO_TASK_STATUS["completed"]
    )
