"""KEI-238 — Linear webhook ignores self-echo from orchestrator writes.

When the orchestrator pushes a state change to Linear via `issueUpdate`,
Linear echoes that change back through the webhook. The actor.id on the
echo equals our API key's viewer.id (LINEAR_VIEWER_ID env). Without the
echo skip, the webhook would write that state back to Postgres, risking
the loop pattern that downgraded 59 KEIs on 2026-05-19.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.api.webhooks import linear as linear_webhook  # noqa: E402

_VIEWER_ID = "f29152a3-3700-4217-a451-d6070f09de3c"
_OTHER_ACTOR = "0000aaaa-bbbb-cccc-dddd-eeeeffff0000"


def _payload(action: str, identifier: str, state_type: str, actor_id: str) -> dict:
    return {
        "action": action,
        "type": "Issue",
        "data": {
            "identifier": identifier,
            "title": "test",
            "priority": 2,
            "url": "https://linear.app/x",
            "state": {"type": state_type, "name": state_type},
            "actor": {"id": actor_id},
        },
    }


def test_update_from_own_viewer_id_is_ignored(monkeypatch) -> None:
    """KEI-238: actor.id == LINEAR_VIEWER_ID + action=update → return None."""
    monkeypatch.setenv("LINEAR_VIEWER_ID", _VIEWER_ID)
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "completed", _VIEWER_ID))
    assert out is None, "self-echo update must be skipped"


def test_update_from_other_actor_passes_through(monkeypatch) -> None:
    """Updates from other actors (Dave, integrations) still propagate."""
    monkeypatch.setenv("LINEAR_VIEWER_ID", _VIEWER_ID)
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "completed", _OTHER_ACTOR))
    assert out is not None
    assert out["op"] == "status"
    assert out["task_status"] == "done"


def test_create_from_own_viewer_id_still_propagates(monkeypatch) -> None:
    """KEI-238: only `update` is skipped — `create` from our API key is
    still a real intent (e.g. atlas creating a new KEI via MCP)."""
    monkeypatch.setenv("LINEAR_VIEWER_ID", _VIEWER_ID)
    out = linear_webhook._normalise_event(_payload("create", "KEI-101", "backlog", _VIEWER_ID))
    assert out is not None
    assert out["op"] == "create"


def test_update_when_viewer_id_unset_passes_through(monkeypatch) -> None:
    """If LINEAR_VIEWER_ID env not set, no skip — fail-open to existing
    behaviour (the env var is the lock, not a hard dependency)."""
    monkeypatch.delenv("LINEAR_VIEWER_ID", raising=False)
    out = linear_webhook._normalise_event(_payload("update", "KEI-100", "completed", _VIEWER_ID))
    assert out is not None
    assert out["op"] == "status"


def test_update_with_missing_actor_passes_through(monkeypatch) -> None:
    """Linear payloads sometimes omit actor (system events) — propagate."""
    monkeypatch.setenv("LINEAR_VIEWER_ID", _VIEWER_ID)
    payload = _payload("update", "KEI-100", "completed", _VIEWER_ID)
    payload["data"].pop("actor", None)
    out = linear_webhook._normalise_event(payload)
    assert out is not None  # missing actor != viewer match → don't skip
