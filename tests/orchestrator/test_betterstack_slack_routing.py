"""Tests for scripts/orchestrator/betterstack_slack_routing.py — PR-C verify-only.

The script is a read-only diagnostic: it hits BS v2 /slack-integrations,
inspects the response for an #alerts integration (channel C0B2EJU53EK),
prints READY/NOT-READY to stderr, and always exits 0. Tests cover:

  - find_alerts_integration: by channel id, by channel name, missing case
  - report: READY path (#alerts present) and NOT-READY path (runbook printed)
  - main: missing API key → still returns 0 (operator-diagnostic discipline)
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


# find_alerts_integration ─────────────────────────────────────────────────────


def test_find_alerts_integration_match_by_channel_id(mod):
    integrations = [
        {
            "id": "999",
            "attributes": {
                "slack_channel_id": "C0B2EJU53EK",
                "slack_channel_name": "#alerts",
            },
        },
    ]
    result = mod.find_alerts_integration(integrations)
    assert result is not None
    assert result["id"] == "999"


def test_find_alerts_integration_match_by_channel_name(mod):
    integrations = [
        {
            "id": "888",
            "attributes": {
                "slack_channel_id": "OTHER",
                "slack_channel_name": "alerts",
            },
        },
    ]
    result = mod.find_alerts_integration(integrations)
    assert result is not None
    assert result["id"] == "888"


def test_find_alerts_integration_missing_returns_none(mod):
    integrations = [
        {
            "id": "102756",
            "attributes": {
                "slack_channel_id": "C0B2PM3TV0B",
                "slack_channel_name": "#ceo",
            },
        },
    ]
    assert mod.find_alerts_integration(integrations) is None


def test_find_alerts_integration_empty_list_returns_none(mod):
    assert mod.find_alerts_integration([]) is None


# report ──────────────────────────────────────────────────────────────────────


def test_report_ready_when_alerts_integration_present(mod, capsys):
    integrations = [
        {
            "id": "999",
            "attributes": {
                "slack_channel_id": "C0B2EJU53EK",
                "slack_channel_name": "#alerts",
                "slack_status": "active",
            },
        },
    ]
    rc = mod.report(integrations)
    assert rc == 0
    captured = capsys.readouterr()
    assert "READY" in captured.err
    assert "id=999" in captured.err


def test_report_not_ready_prints_oauth_runbook(mod, capsys):
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
    assert "NOT READY" in captured.err
    assert "OAuth required" in captured.err
    assert "team/integrations/slack" in captured.err


def test_report_no_integrations_prints_runbook(mod, capsys):
    rc = mod.report([])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Existing slack integrations: 0" in captured.err
    assert "OAuth required" in captured.err


# main ────────────────────────────────────────────────────────────────────────


def test_main_missing_api_key_returns_zero(mod, monkeypatch):
    """Operator-diagnostic: never block. Missing key → return 0 silently-with-stderr."""
    monkeypatch.delenv("BETTERSTACK_API_KEY", raising=False)
    rc = mod.main()
    assert rc == 0
