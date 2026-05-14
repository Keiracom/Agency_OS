"""Tests for scripts/orchestrator/betterstack_slack_routing.py — KEI-20 readiness probe.

Probes BS v2 /slack-integrations for both target channels:
  - #ceo       (C0B2PM3TV0B)  — critical-policy target
  - #execution (C0B3QB0K1GQ)  — routine-policy target (gated on OAuth)

Always exits 0 (operator-diagnostic, never blocks).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "betterstack_slack_routing.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("bs_slack_routing", SCRIPT_PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules["bs_slack_routing"] = m
    spec.loader.exec_module(m)
    return m


# ─── find_integration_by_channel_id ──────────────────────────────────────────


def test_find_integration_by_channel_id_match(mod):
    integrations = [
        {"id": "999", "attributes": {"slack_channel_id": "C0B2EJU53EK"}},
        {"id": "102756", "attributes": {"slack_channel_id": "C0B2PM3TV0B"}},
    ]
    result = mod.find_integration_by_channel_id(integrations, "C0B2PM3TV0B")
    assert result is not None
    assert result["id"] == "102756"


def test_find_integration_by_channel_id_miss_returns_none(mod):
    integrations = [{"id": "999", "attributes": {"slack_channel_id": "C0B2EJU53EK"}}]
    assert mod.find_integration_by_channel_id(integrations, "C0B3QB0K1GQ") is None


def test_find_integration_by_channel_id_empty_returns_none(mod):
    assert mod.find_integration_by_channel_id([], "C0B2PM3TV0B") is None


# ─── report ──────────────────────────────────────────────────────────────────


def test_report_both_present_prints_two_ready_lines(mod, capsys):
    integrations = [
        {
            "id": "102756",
            "attributes": {
                "slack_channel_id": "C0B2PM3TV0B",
                "slack_channel_name": "#ceo",
                "slack_status": "active",
            },
        },
        {
            "id": "200000",
            "attributes": {
                "slack_channel_id": "C0B3QB0K1GQ",
                "slack_channel_name": "#execution",
                "slack_status": "active",
            },
        },
    ]
    rc = mod.report(integrations)
    assert rc == 0
    captured = capsys.readouterr()
    assert "READY — #ceo integration found (id=102756)" in captured.err
    assert "READY — #execution integration found (id=200000)" in captured.err


def test_report_ceo_only_prints_execution_gate(mod, capsys):
    integrations = [
        {
            "id": "102756",
            "attributes": {
                "slack_channel_id": "C0B2PM3TV0B",
                "slack_channel_name": "#ceo",
                "slack_status": "active",
            },
        },
    ]
    rc = mod.report(integrations)
    assert rc == 0
    captured = capsys.readouterr()
    assert "READY — #ceo integration found" in captured.err
    assert "DEFERRED — no #execution integration found" in captured.err
    assert "team/integrations/slack" in captured.err


def test_report_no_integrations_prints_both_runbooks(mod, capsys):
    rc = mod.report([])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Existing slack integrations: 0" in captured.err
    assert "NOT READY — no #ceo integration found" in captured.err
    assert "DEFERRED — no #execution integration found" in captured.err
    # Both OAuth runbooks should fire.
    assert captured.err.count("Open https://uptime.betterstack.com") == 2


# ─── main ────────────────────────────────────────────────────────────────────


def test_main_missing_api_key_returns_zero(mod, monkeypatch):
    """Operator-diagnostic: never block. Missing key → return 0."""
    monkeypatch.delenv("BETTERSTACK_API_KEY", raising=False)
    rc = mod.main()
    assert rc == 0


def test_channel_id_env_overrides(mod, monkeypatch):
    monkeypatch.setenv("AGENCY_OS_BETTERSTACK_CEO_CHANNEL_ID", "C_FAKE_CEO")
    monkeypatch.setenv("AGENCY_OS_BETTERSTACK_EXECUTION_CHANNEL_ID", "C_FAKE_EXEC")
    assert mod._ceo_channel_id() == "C_FAKE_CEO"
    assert mod._execution_channel_id() == "C_FAKE_EXEC"
