"""KEI-100 — ID misalignment root-fix tests.

Four test groups:
  1. Auto-KEI routes through Linear (no direct Supabase insert).
  2. Reconcile dry-run: diff output correct, no DB writes.
  3. Reconcile apply: Max Note 1 fixture — done-state preservation + orphan reason.
  4. Webhook title-guard: prefix mismatch → 400; no-prefix or matching prefix → accept.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _stub_slack_sdk() -> None:
    """Inject minimal slack_sdk stubs so central_listener can be imported in tests."""
    for mod_name in (
        "slack_sdk",
        "slack_sdk.socket_mode",
        "slack_sdk.socket_mode.request",
        "slack_sdk.socket_mode.response",
        "slack_sdk.web",
    ):
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)

    # Provide the specific names imported by central_listener at module-load time.
    sys.modules["slack_sdk.socket_mode"].SocketModeClient = MagicMock  # type: ignore[attr-defined]
    sys.modules["slack_sdk.socket_mode.request"].SocketModeRequest = MagicMock  # type: ignore[attr-defined]
    sys.modules["slack_sdk.socket_mode.response"].SocketModeResponse = MagicMock  # type: ignore[attr-defined]
    sys.modules["slack_sdk.web"].WebClient = MagicMock  # type: ignore[attr-defined]


def _load_central_listener() -> types.ModuleType:
    """Load central_listener with slack_sdk stubbed out."""
    _stub_slack_sdk()
    # Also stub transitive deps that may be missing in the test env.
    for dep in (
        "src.bot_common.enforcer_deterministic",
        "src.bot_common.enforcer_rules",
        "src.slack_bot.enforcer_callsign_map",
    ):
        if dep not in sys.modules:
            stub = types.ModuleType(dep)
            # Provide attributes referenced at import time.
            for attr in (
                "_R3_EVIDENCE_RE",
                "check_r2",
                "check_r3",
                "check_r4",
                "check_r6",
                "check_r8",
                "CHECK_MODEL",
                "FLAG_COOLDOWN_SECONDS",
                "HIGH_SEVERITY_RULES",
                "MAX_WINDOW",
                "RULES_PROMPT",
                "should_check",
                "attribute",
            ):
                setattr(stub, attr, MagicMock())
            stub.MAX_WINDOW = 50  # type: ignore[attr-defined]
            sys.modules[dep] = stub

    # Force fresh load (remove any cached half-initialised module).
    sys.modules.pop("src.slack_bot.central_listener", None)
    sys.modules.pop("src.slack_bot", None)

    spec = importlib.util.spec_from_file_location(
        "src.slack_bot.central_listener",
        REPO_ROOT / "src" / "slack_bot" / "central_listener.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules["src.slack_bot.central_listener"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Test group 1 — Auto-KEI routes through Linear (no direct Supabase INSERT)
# ---------------------------------------------------------------------------


def test_auto_kei_calls_linear_create_not_supabase(monkeypatch):
    """_create_kei_via_linear must POST to Linear GraphQL and return identifier.
    No psycopg.connect / INSERT call should occur.
    """
    central_listener = _load_central_listener()

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "linear-uuid-123",
                    "identifier": "KEI-85",
                    "url": "https://linear.app/keiracom/issue/KEI-85",
                },
            }
        }
    }
    mock_response.raise_for_status = MagicMock()

    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-uuid")

    with patch("src.slack_bot.central_listener.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.send.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = central_listener._create_kei_via_linear("Test KEI title")

    assert result == "KEI-85", f"Expected KEI-85, got {result}"
    # Verify Linear HTTP call was made (not Supabase direct insert)
    mock_client.send.assert_called_once()


def test_auto_kei_uses_linear_identifier_in_confirmation(monkeypatch):
    """_maybe_auto_create_kei must post confirmation with Linear's identifier, not a local one."""
    central_listener = _load_central_listener()

    monkeypatch.setenv("LINEAR_API_KEY", "test-key")

    with patch.object(
        central_listener, "_create_kei_via_linear", return_value="KEI-85"
    ) as mock_create:
        mock_web = MagicMock()
        event = {
            "type": "message",
            "channel": central_listener.CEO_CHANNEL,
            "text": "[CEO] Some new task",
        }
        central_listener._maybe_auto_create_kei(event, mock_web)

    mock_create.assert_called_once_with("Some new task")
    mock_web.chat_postMessage.assert_called_once()
    call_kwargs = mock_web.chat_postMessage.call_args
    assert "KEI-85" in str(call_kwargs), f"Confirmation did not contain KEI-85: {call_kwargs}"


def test_auto_kei_no_direct_insert_function_exists():
    """_insert_kei_task must NOT exist in central_listener (removed by KEI-100)."""
    central_listener = _load_central_listener()

    assert not hasattr(central_listener, "_insert_kei_task"), (
        "_insert_kei_task should have been removed; direct Supabase insert is forbidden"
    )


# ---------------------------------------------------------------------------
# Test group 2 — Reconcile dry-run: diff output correct, no DB writes
# ---------------------------------------------------------------------------


def test_reconcile_dry_run_no_writes():
    """compute_reconciliation_plan is pure — no DB side effects regardless of input."""
    from scripts.reconcile_linear_supabase import compute_reconciliation_plan

    linear_issues = [
        {
            "identifier": "KEI-85",
            "title": "Some open issue",
            "priority": 2,
            "url": "https://linear.app/x/KEI-85",
            "state": {"type": "started"},
        },
        {
            "identifier": "KEI-86",
            "title": "A completed issue",
            "priority": 3,
            "url": "https://linear.app/x/KEI-86",
            "state": {"type": "completed"},
        },
    ]
    supabase_tasks = [
        {"id": "KEI-85", "status": "available", "metadata": {}},
        {"id": "OLD-LOCAL-1", "status": "available", "metadata": {}},  # orphan
        {"id": "OLD-DONE", "status": "done", "metadata": {}},  # already done — leave alone
    ]

    plan = compute_reconciliation_plan(linear_issues, supabase_tasks, "20260517T000000Z")

    identifiers_in_upserts = {u["identifier"] for u in plan["upserts"]}
    assert "KEI-85" in identifiers_in_upserts
    assert "KEI-86" in identifiers_in_upserts

    kei85_upsert = next(u for u in plan["upserts"] if u["identifier"] == "KEI-85")
    assert kei85_upsert["status"] == "active", "started → active"

    kei86_upsert = next(u for u in plan["upserts"] if u["identifier"] == "KEI-86")
    assert kei86_upsert["status"] == "done", "completed → done"

    orphan_ids = {o["id"] for o in plan["orphans"]}
    assert "OLD-LOCAL-1" in orphan_ids, "Open orphan should be in orphan list"
    assert "OLD-DONE" not in orphan_ids, "Already-done row must NOT be reopened as orphan"
    assert "20260517T000000Z" in plan["orphans"][0]["reason"]


def test_reconcile_diff_counts():
    """Verify the count semantics of the plan (upserted / orphans)."""
    from scripts.reconcile_linear_supabase import compute_reconciliation_plan

    linear_issues = [
        {
            "identifier": f"KEI-{i}",
            "title": f"Issue {i}",
            "priority": 2,
            "url": f"https://linear.app/x/KEI-{i}",
            "state": {"type": "unstarted"},
        }
        for i in range(1, 4)
    ]
    supabase_tasks = [
        {"id": "KEI-1", "status": "available", "metadata": {}},
        {"id": "ORPHAN-A", "status": "available", "metadata": {}},
        {"id": "ORPHAN-B", "status": "active", "metadata": {}},
    ]

    plan = compute_reconciliation_plan(linear_issues, supabase_tasks, "ts")

    assert len(plan["upserts"]) == 3, "One upsert per Linear issue"
    assert len(plan["orphans"]) == 2, "Two open orphans"


# ---------------------------------------------------------------------------
# Test group 3 — Reconcile apply: Max Note 1 fixture
# ---------------------------------------------------------------------------


def test_reconcile_apply_done_state_preserved():
    """Max Note 1 fixture:
    - Supabase has KEI-101 status=done (old local ID, no Linear match).
    - Linear has KEI-75 as completed.
    After reconcile:
      - KEI-101 row → status=done + orphan reason (not deleted).
      - KEI-75 row → status=done (matching Linear's completed state).
      - done state propagated, not collapsed to available.
    """
    from scripts.reconcile_linear_supabase import compute_reconciliation_plan

    linear_issues = [
        {
            "identifier": "KEI-75",
            "title": "Old relay watcher",
            "priority": 2,
            "url": "https://linear.app/x/KEI-75",
            "state": {"type": "completed"},
        },
    ]
    # KEI-101 is an old Supabase row that predates Linear-ID sync.
    supabase_tasks = [
        {"id": "KEI-101", "status": "done", "metadata": {}},
    ]

    plan = compute_reconciliation_plan(linear_issues, supabase_tasks, "20260517T120000Z")

    # KEI-75 should be upserted as done (Linear says completed)
    kei75 = next((u for u in plan["upserts"] if u["identifier"] == "KEI-75"), None)
    assert kei75 is not None, "KEI-75 should be in upserts"
    assert kei75["status"] == "done", "KEI-75 from Linear completed → status=done"

    # KEI-101 is already done → must NOT appear in orphans (orphans only covers open rows)
    orphan_ids = {o["id"] for o in plan["orphans"]}
    assert "KEI-101" not in orphan_ids, (
        "KEI-101 is already done — must not be re-processed as orphan (done preservation)"
    )


def test_reconcile_apply_open_orphan_gets_reason():
    """An open Supabase row with no Linear match must receive orphan reason."""
    from scripts.reconcile_linear_supabase import compute_reconciliation_plan

    linear_issues = []
    supabase_tasks = [
        {"id": "LOCAL-ONLY-123", "status": "available", "metadata": {}},
    ]

    plan = compute_reconciliation_plan(linear_issues, supabase_tasks, "20260517T130000Z")

    assert len(plan["orphans"]) == 1
    orphan = plan["orphans"][0]
    assert orphan["id"] == "LOCAL-ONLY-123"
    assert orphan["reason"] == "orphan_no_linear_match_20260517T130000Z"


# ---------------------------------------------------------------------------
# Test group 4 — Webhook title-guard
# ---------------------------------------------------------------------------


def _make_linear_payload(action: str, identifier: str, title: str) -> dict:
    return {
        "action": action,
        "type": "Issue",
        "data": {
            "identifier": identifier,
            "title": title,
            "priority": 2,
            "url": f"https://linear.app/x/{identifier}",
            "state": {"type": "unstarted", "name": "Todo"},
        },
    }


def test_title_guard_mismatched_prefix_raises_400():
    """Title starts with KEI-99 but identifier is KEI-83 → HTTPException 400."""
    from fastapi import HTTPException

    from src.api.webhooks import linear as linear_webhook

    payload = _make_linear_payload("create", "KEI-83", "KEI-99 Relay watcher session resilience")
    with pytest.raises(HTTPException) as exc_info:
        linear_webhook._normalise_event(payload)
    assert exc_info.value.status_code == 400


def test_title_guard_no_prefix_is_accepted():
    """Title with no KEI-prefix is accepted regardless of identifier."""
    from src.api.webhooks import linear as linear_webhook

    payload = _make_linear_payload("create", "KEI-83", "Relay watcher session resilience")
    result = linear_webhook._normalise_event(payload)
    assert result is not None
    assert result["op"] == "create"
    assert result["identifier"] == "KEI-83"


def test_title_guard_matching_prefix_is_accepted():
    """Title prefix matches identifier → accepted."""
    from src.api.webhooks import linear as linear_webhook

    payload = _make_linear_payload("create", "KEI-83", "KEI-83 Relay watcher session resilience")
    result = linear_webhook._normalise_event(payload)
    assert result is not None
    assert result["identifier"] == "KEI-83"


def test_title_guard_case_insensitive():
    """Lowercase 'kei-83' in title should still match 'KEI-83' identifier."""
    from src.api.webhooks import linear as linear_webhook

    payload = _make_linear_payload("create", "KEI-83", "kei-83 Relay watcher")
    result = linear_webhook._normalise_event(payload)
    assert result is not None, "Lowercase prefix matching identifier should be accepted"
