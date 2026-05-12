"""Tests for scripts/orchestrator/betterstack_routing_policy.py — PR-C-v2.

Idempotency contract:
  - ensure_urgency: match by name; create if missing.
  - ensure_policy: match by name; PATCH if step drift; POST if missing.
  - _step_drift: detect mismatch on len/type/urgency_id/member_type.
  - apply_policy_to_*: PATCH only if policy_id missing/different.
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


# _step_drift ─────────────────────────────────────────────────────────────────


def test_step_drift_correct_step_returns_false(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "all_slack_integrations"}],
        }
    ]
    assert mod._step_drift(steps, 42) is False


def test_step_drift_wrong_urgency_returns_true(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "all_slack_integrations"}],
        }
    ]
    assert mod._step_drift(steps, 999) is True


def test_step_drift_no_steps_returns_true(mod):
    assert mod._step_drift([], 42) is True


def test_step_drift_wrong_type_returns_true(mod):
    steps = [{"type": "time_branching", "urgency_id": 42, "step_members": []}]
    assert mod._step_drift(steps, 42) is True


def test_step_drift_wrong_member_type_returns_true(mod):
    steps = [
        {
            "type": "escalation",
            "urgency_id": 42,
            "step_members": [{"type": "current_on_call"}],
        }
    ]
    assert mod._step_drift(steps, 42) is True


def test_step_drift_too_many_steps_returns_true(mod):
    steps = [
        {"type": "escalation", "urgency_id": 42, "step_members": [{"type": "all_slack_integrations"}]},
        {"type": "escalation", "urgency_id": 42, "step_members": [{"type": "all_slack_integrations"}]},
    ]
    assert mod._step_drift(steps, 42) is True


# ensure_urgency ──────────────────────────────────────────────────────────────


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
    assert captured_body == {"name": "Critical", "email": True, "push": False, "sms": False, "call": False}


# ensure_policy ───────────────────────────────────────────────────────────────


def test_ensure_policy_reuses_when_correct(mod, monkeypatch):
    existing_step = {
        "type": "escalation",
        "urgency_id": 42,
        "step_members": [{"type": "all_slack_integrations"}],
    }
    calls: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        calls.append((method, path))
        if path == "/policies?per_page=100":
            return {
                "data": [
                    {"id": "300", "attributes": {"name": "Critical", "steps": [existing_step]}},
                ]
            }
        raise AssertionError(f"no further calls expected: {method} {path}")

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_policy("k", "Critical", 42)
    assert result is not None
    assert result["id"] == "300"


def test_ensure_policy_patches_on_drift(mod, monkeypatch):
    stale = {"type": "escalation", "urgency_id": 99, "step_members": []}
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        if path == "/policies?per_page=100":
            return {"data": [{"id": "301", "attributes": {"name": "Critical", "steps": [stale]}}]}
        if method == "PATCH":
            return {"data": {"id": "301", "attributes": {"steps": body["steps"]}}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    result = mod.ensure_policy("k", "Critical", 42)
    assert result is not None
    patches = [c for c in captured if c[0] == "PATCH"]
    assert len(patches) == 1
    assert patches[0][1] == "/policies/301"


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
    result = mod.ensure_policy("k", "Critical", 42)
    assert result is not None
    posts = [c for c in captured if c[0] == "POST"]
    assert len(posts) == 1
    assert posts[0][2]["name"] == "Critical"
    step = posts[0][2]["steps"][0]
    assert step["type"] == "escalation"
    assert step["urgency_id"] == 42
    assert step["step_members"] == [{"type": "all_slack_integrations"}]


# apply_policy_to_monitor ─────────────────────────────────────────────────────


def test_apply_policy_to_monitor_skips_if_already_set(mod, monkeypatch):
    def _fake_request(method, path, api_key, body=None):
        if method == "GET":
            return {"data": {"attributes": {"policy_id": 42}}}
        raise AssertionError("must not PATCH when policy_id already matches")

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.apply_policy_to_monitor("k", "4400037", 42) is False


def test_apply_policy_to_monitor_patches_when_unset(mod, monkeypatch):
    captured: list[tuple] = []

    def _fake_request(method, path, api_key, body=None):
        captured.append((method, path, body))
        if method == "GET":
            return {"data": {"attributes": {"policy_id": None}}}
        if method == "PATCH":
            return {"data": {"attributes": {"policy_id": 42}}}
        return None

    monkeypatch.setattr(mod, "_request", _fake_request)
    assert mod.apply_policy_to_monitor("k", "4400037", 42) is True
    patches = [c for c in captured if c[0] == "PATCH"]
    assert len(patches) == 1
    assert patches[0][2] == {"policy_id": 42}


# main ────────────────────────────────────────────────────────────────────────


def test_main_missing_api_key_returns_2(mod, monkeypatch):
    monkeypatch.delenv("BETTERSTACK_API_KEY", raising=False)
    assert mod.main() == 2
