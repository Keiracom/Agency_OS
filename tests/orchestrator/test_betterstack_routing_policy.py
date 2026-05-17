"""Tests for scripts/orchestrator/betterstack_routing_policy.py — PR-C-v3 (KEI-20).

Severity-routing architecture:
  - Critical policy → #ceo integration (slack_integration step_member by id)
  - Routine policy → #execution integration (gated on OAuth)
  - Monitors: policy_id (critical) + expiration_policy_id (routine)
  - Heartbeats: policy_id (critical) only — BS API limitation

Idempotency contract:
  - ensure_urgency: match by name; create if missing.
  - ensure_policy: match by name; PATCH if step drift; POST if missing.
  - _step_drift: detect mismatch on len/type/urgency_id/member-shape (incl. integration id).
  - apply_policy_field: PATCH only if resource[field] missing/different.

Routine policy create is gated: when no #execution integration exists, main()
returns 0 after critical wiring and logs the OAuth gate. When the integration
exists, both policies are created and attached.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "betterstack_routing_policy.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bs_routing", SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bs_routing"] = m
    spec.loader.exec_module(m)
    return m


# ─── _step_drift ─────────────────────────────────────────────────────────────


def test_step_drift_correct_step_returns_false(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "slack_integration", "id": 102756}],
        }
    ]
    assert mod._step_drift(steps, 42, 102756) is False


def test_step_drift_wrong_urgency_returns_true(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "slack_integration", "id": 102756}],
        }
    ]
    assert mod._step_drift(steps, 999, 102756) is True


def test_step_drift_wrong_integration_id_returns_true(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "slack_integration", "id": 102756}],
        }
    ]
    assert mod._step_drift(steps, 42, 999999) is True


def test_step_drift_stale_all_slack_integrations_returns_true(mod):
    """PR-C-v2 phase-1 used type=all_slack_integrations. PR-C-v3 must rewrite."""
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "all_slack_integrations"}],
        }
    ]
    assert mod._step_drift(steps, 42, 102756) is True


def test_step_drift_no_steps_returns_true(mod):
    assert mod._step_drift([], 42, 102756) is True


def test_step_drift_wrong_type_returns_true(mod):
    steps = [{"type": "time_branching", "urgency_id": 42, "step_members": []}]
    assert mod._step_drift(steps, 42, 102756) is True


def test_step_drift_wrong_member_type_returns_true(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "current_on_call"}],
        }
    ]
    assert mod._step_drift(steps, 42, 102756) is True


def test_step_drift_too_many_step_members_returns_true(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [
                {"type": "slack_integration", "id": 102756},
                {"type": "slack_integration", "id": 102757},
            ],
        }
    ]
    assert mod._step_drift(steps, 42, 102756) is True


def test_step_drift_too_many_steps_returns_true(mod):
    member = [{"type": "slack_integration", "id": 102756}]
    steps = [
        {"type": "escalation", "urgency_id": 42, "step_members": member},
        {"type": "escalation", "urgency_id": 42, "step_members": member},
    ]
    assert mod._step_drift(steps, 42, 102756) is True


# ─── find_integration_by_channel ─────────────────────────────────────────────


def test_find_integration_by_channel_matches(mod):
    ints = [
        {"id": "100", "attributes": {"slack_channel_id": "C_AAA"}},
        {"id": "200", "attributes": {"slack_channel_id": "C_BBB"}},
    ]
    assert mod.find_integration_by_channel(ints, "C_BBB")["id"] == "200"


def test_find_integration_by_channel_returns_none_on_miss(mod):
    ints = [{"id": "100", "attributes": {"slack_channel_id": "C_AAA"}}]
    assert mod.find_integration_by_channel(ints, "C_OTHER") is None


# ─── ensure_urgency ──────────────────────────────────────────────────────────


def test_ensure_urgency_reuses_existing(mod, monkeypatch):
    calls: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        calls.append((method, path))
        if path.startswith("/urgencies?per_page"):
            return {"data": [{"id": "100", "attributes": {"name": "Critical"}}]}
        raise AssertionError("should not POST when urgency exists")

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_urgency("k", "Critical")
    assert result is not None
    assert result["id"] == "100"
    assert all(c[0] == "GET" for c in calls)


def test_ensure_urgency_creates_when_missing(mod, monkeypatch):
    captured_body: dict | None = None

    def _fake_request(method, path, api_key, body=None):
        nonlocal captured_body
        if path == "/urgencies?per_page=100":
            return {"data": []}
        if method == "POST" and path == "/urgencies":
            captured_body = body
            return {"data": {"id": "200", "attributes": body}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_urgency("k", "Critical")
    assert result is not None
    assert result["id"] == "200"
    # S5727 false positive on both asserts: captured_body is mutated via
    # nonlocal inside the monkeypatched _fake_request closure invoked by
    # mod.ensure_urgency above. Sonar's flow analyzer can't trace
    # closure-mutation-via-monkeypatch and treats captured_body as still
    # None at this point. The assertions are correct and the closure
    # firing is verified by the test passing.
    assert captured_body is not None  # NOSONAR S5727 — see above
    assert captured_body == {  # NOSONAR S5727 — see above
        "name": "Critical",
        "email": True,
        "push": False,
        "sms": False,
        "call": False,
    }


# ─── ensure_policy ───────────────────────────────────────────────────────────


def test_ensure_policy_reuses_when_correct(mod, monkeypatch):
    existing_step = {
        "type": "escalation",
        "urgency_id": 42,
        "step_members": [{"type": "slack_integration", "id": 102756}],
    }

    def _fake_request(method, path, api_key, body=None):
        if path == "/policies?per_page=100":
            return {
                "data": [
                    {
                        "id": "300",
                        "attributes": {"name": "Critical", "steps": [existing_step]},
                    },
                ]
            }
        raise AssertionError(f"no further calls expected: {method} {path}")

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_policy("k", "Critical", 42, 102756)
    assert result is not None
    assert result["id"] == "300"


def test_ensure_policy_patches_on_drift(mod, monkeypatch):
    """Stale phase-1 all_slack_integrations step must be PATCHed."""
    stale = {
        "type": "escalation",
        "urgency_id": 42,
        "step_members": [{"type": "all_slack_integrations"}],
    }
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        if path == "/policies?per_page=100":
            return {"data": [{"id": "301", "attributes": {"name": "Critical", "steps": [stale]}}]}
        if method == "PATCH":
            return {"data": {"id": "301", "attributes": {"steps": body["steps"]}}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_policy("k", "Critical", 42, 102756)
    assert result is not None
    patches = [c for c in captured if c[0] == "PATCH"]
    assert len(patches) == 1
    assert patches[0][1] == "/policies/301"
    patched_step = patches[0][2]["steps"][0]
    assert patched_step["step_members"] == [{"type": "slack_integration", "id": 102756}]


def test_ensure_policy_creates_when_missing(mod, monkeypatch):
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        if path == "/policies?per_page=100":
            return {"data": []}
        if method == "POST" and path == "/policies":
            return {"data": {"id": "302", "attributes": body}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_policy("k", "Critical", 42, 102756)
    assert result is not None
    posts = [c for c in captured if c[0] == "POST"]
    assert len(posts) == 1
    assert posts[0][2]["name"] == "Critical"
    step = posts[0][2]["steps"][0]
    assert step["type"] == "escalation"
    assert step["urgency_id"] == 42
    assert step["step_members"] == [{"type": "slack_integration", "id": 102756}]


# ─── apply_policy_field ──────────────────────────────────────────────────────


def test_apply_policy_field_skips_when_match(mod, monkeypatch):
    def _fake_request(method, path, api_key, body=None):
        if method == "GET":
            return {"data": {"attributes": {"policy_id": 42}}}
        raise AssertionError("must not PATCH when field already matches")

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.apply_policy_field("k", "monitors", "4400037", "policy_id", 42) is False


def test_apply_policy_field_patches_when_unset(mod, monkeypatch):
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        if method == "GET":
            return {"data": {"attributes": {"policy_id": None}}}
        if method == "PATCH":
            return {"data": {"attributes": {"policy_id": 42}}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.apply_policy_field("k", "monitors", "4400037", "policy_id", 42) is True
    patches = [c for c in captured if c[0] == "PATCH"]
    assert len(patches) == 1
    assert patches[0][2] == {"policy_id": 42}


def test_apply_policy_field_handles_expiration_policy_id(mod, monkeypatch):
    """Routine policy attaches to monitors.expiration_policy_id, not policy_id."""
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        if method == "GET":
            return {"data": {"attributes": {"expiration_policy_id": None}}}
        if method == "PATCH":
            return {"data": {"attributes": {"expiration_policy_id": 999}}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.apply_policy_field("k", "monitors", "4400037", "expiration_policy_id", 999) is True
    patch_bodies = [c[2] for c in captured if c[0] == "PATCH"]
    assert patch_bodies == [{"expiration_policy_id": 999}]


# ─── main / gating ───────────────────────────────────────────────────────────


def test_main_missing_api_key_returns_2(mod, monkeypatch):
    monkeypatch.delenv("BETTERSTACK_API_KEY", raising=False)
    assert mod.main() == 2


def test_main_ceo_integration_missing_returns_1(mod, monkeypatch):
    """No #ceo integration → critical wiring impossible → exit 1."""
    monkeypatch.setenv("BETTERSTACK_API_KEY", "k")

    def _fake_request(method, path, api_key, body=None):
        if path.startswith("/slack-integrations"):
            return {"data": []}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.main() == 1


def test_main_execution_integration_missing_returns_0_with_gate(  # NOSONAR S3776 — REST-mock nested branches mirror BetterStack API surface; reducing cognitive complexity here would obscure the route-table shape under test
    mod, monkeypatch, capsys
):
    """#ceo present, #execution missing → critical wired, routine gated, exit 0."""
    monkeypatch.setenv("BETTERSTACK_API_KEY", "k")

    state = {"created_policies": []}

    def _fake_request(method, path, api_key, body=None):
        if path.startswith("/slack-integrations"):
            return {
                "data": [
                    {
                        "id": "102756",
                        "attributes": {"slack_channel_id": "C0B2PM3TV0B"},
                    }
                ]
            }
        if path.startswith("/urgencies"):
            if method == "GET":
                return {"data": []}
            if method == "POST":
                return {"data": {"id": "1", "attributes": body}}
        if path.startswith("/policies"):
            if method == "GET" and "?" in path:
                return {"data": []}
            if method == "POST":
                state["created_policies"].append(body["name"])
                return {"data": {"id": "10", "attributes": body}}
        if path.startswith("/monitors") and "?" in path:
            return {"data": []}
        if path.startswith("/heartbeats") and "?" in path:
            return {"data": []}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    rc = mod.main()
    assert rc == 0
    # Only the critical policy was created — routine was gated.
    assert state["created_policies"] == [mod.DEFAULT_CRITICAL_POLICY_NAME]
    captured = capsys.readouterr()
    assert "GATE" in captured.err
    assert "#execution" in captured.err


def test_main_both_integrations_present_creates_both_policies(  # NOSONAR S3776 — REST-mock nested branches mirror BetterStack API surface; reducing cognitive complexity here would obscure the route-table shape under test
    mod, monkeypatch
):
    monkeypatch.setenv("BETTERSTACK_API_KEY", "k")

    state = {"created_policies": [], "patches": []}

    def _fake_request(method, path, api_key, body=None):
        if path.startswith("/slack-integrations"):
            return {
                "data": [
                    {"id": "102756", "attributes": {"slack_channel_id": "C0B2PM3TV0B"}},
                    {"id": "555555", "attributes": {"slack_channel_id": "C0B3QB0K1GQ"}},
                ]
            }
        if path.startswith("/urgencies"):
            if method == "GET":
                return {"data": []}
            if method == "POST":
                return {"data": {"id": "2", "attributes": body}}
        if path.startswith("/policies"):
            if method == "GET" and "?" in path:
                return {"data": []}
            if method == "POST":
                state["created_policies"].append(body["name"])
                step_id = len(state["created_policies"]) * 100
                return {"data": {"id": str(step_id), "attributes": body}}
        if path.startswith("/monitors") and "?" in path:
            return {"data": []}
        if path.startswith("/heartbeats") and "?" in path:
            return {"data": []}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.main() == 0
    assert state["created_policies"] == [
        mod.DEFAULT_CRITICAL_POLICY_NAME,
        mod.DEFAULT_ROUTINE_POLICY_NAME,
    ]
