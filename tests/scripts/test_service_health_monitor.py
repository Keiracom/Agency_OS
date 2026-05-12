"""tests for scripts/alerts/service_health_monitor.py — Dave System Health Outcome 1.

Mocks subprocess.run (systemctl/journalctl) + urllib.request.urlopen (Slack)
so tests run without systemd or network. Covers:
  - Active service → not in failures
  - Failed/inactive service → in failures
  - Alert formatting + Slack post
  - callsign extraction
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MONITOR_PATH = REPO_ROOT / "scripts" / "alerts" / "service_health_monitor.py"


@pytest.fixture(scope="module")
def monitor():
    """Load service_health_monitor.py as a module."""
    spec = importlib.util.spec_from_file_location("service_health_monitor", MONITOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["service_health_monitor"] = mod
    spec.loader.exec_module(mod)
    return mod


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ─────────────────────────────────────────────────────────────────────────────
# callsign_from_service_name
# ─────────────────────────────────────────────────────────────────────────────


def test_callsign_from_aiden_relay_watcher(monitor) -> None:
    assert monitor.callsign_from_service_name("aiden-relay-watcher") == "aiden"


def test_callsign_from_atlas_inbox_watcher(monitor) -> None:
    assert monitor.callsign_from_service_name("atlas-inbox-watcher") == "atlas"


def test_callsign_from_central_listener(monitor) -> None:
    """Central listener has no callsign prefix → 'central'."""
    assert monitor.callsign_from_service_name("agency-os-slack-central-listener") == "central"


def test_callsign_from_unknown_service(monitor) -> None:
    assert monitor.callsign_from_service_name("some-other-service") == "central"


# ─────────────────────────────────────────────────────────────────────────────
# get_service_state
# ─────────────────────────────────────────────────────────────────────────────


def test_get_service_state_active(monitor) -> None:
    with patch.object(monitor.subprocess, "run", return_value=_completed(0, "active\n")):
        assert monitor.get_service_state("any-service") == "active"


def test_get_service_state_inactive(monitor) -> None:
    with patch.object(monitor.subprocess, "run", return_value=_completed(3, "inactive\n")):
        assert monitor.get_service_state("any-service") == "inactive"


def test_get_service_state_failed(monitor) -> None:
    with patch.object(monitor.subprocess, "run", return_value=_completed(3, "failed\n")):
        assert monitor.get_service_state("any-service") == "failed"


def test_get_service_state_subprocess_failure(monitor) -> None:
    """systemctl missing or timeout → 'unknown'."""
    with patch.object(monitor.subprocess, "run", side_effect=FileNotFoundError("systemctl")):
        # systemctl_user catches the exception and returns rc=1 + error string;
        # is_active path treats that as non-active state.
        assert monitor.get_service_state("any-service") != "active"


# ─────────────────────────────────────────────────────────────────────────────
# check_all_services
# ─────────────────────────────────────────────────────────────────────────────


def test_check_all_services_all_active(monitor) -> None:
    """All services active → empty failures list."""
    with (
        patch.object(monitor, "get_service_state", return_value="active"),
        patch.object(monitor, "get_recent_log", return_value="ok"),
    ):
        failures = monitor.check_all_services()
    assert failures == []


def test_check_all_services_one_failed(monitor) -> None:
    """One service failed → one entry in failures with callsign + state + log."""

    def state_lookup(service):
        if service == "aiden-relay-watcher":
            return "failed"
        return "active"

    with (
        patch.object(monitor, "get_service_state", side_effect=state_lookup),
        patch.object(monitor, "get_recent_log", return_value="boom"),
    ):
        failures = monitor.check_all_services()
    assert len(failures) == 1
    assert failures[0]["service"] == "aiden-relay-watcher"
    assert failures[0]["callsign"] == "aiden"
    assert failures[0]["state"] == "failed"
    assert failures[0]["log"] == "boom"


# ─────────────────────────────────────────────────────────────────────────────
# format_alert
# ─────────────────────────────────────────────────────────────────────────────


def test_format_alert_contains_service_and_state(monitor) -> None:
    text = monitor.format_alert(
        {"service": "aiden-relay-watcher", "callsign": "aiden", "state": "failed", "log": "boom"}
    )
    assert "aiden-relay-watcher" in text
    assert "failed" in text
    assert "boom" in text
    assert "callsign=aiden" in text


def test_format_alert_handles_empty_log(monitor) -> None:
    text = monitor.format_alert({"service": "x", "callsign": "y", "state": "inactive", "log": ""})
    assert "(no recent log)" in text


# ─────────────────────────────────────────────────────────────────────────────
# post_to_slack
# ─────────────────────────────────────────────────────────────────────────────


def test_post_to_slack_missing_token_returns_false(monitor, monkeypatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    assert monitor.post_to_slack("test") is False


def test_post_to_slack_success(monitor, monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps({"ok": True, "ts": "1.234"}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(monitor.urllib.request, "urlopen", return_value=FakeResponse()):
        assert monitor.post_to_slack("test") is True


def test_post_to_slack_network_failure_returns_false(monitor, monkeypatch) -> None:
    """urlopen raising URLError → False (best-effort)."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    from urllib.error import URLError

    with patch.object(monitor.urllib.request, "urlopen", side_effect=URLError("network")):
        assert monitor.post_to_slack("test") is False


def test_post_to_slack_api_not_ok_returns_false(monitor, monkeypatch) -> None:
    """Slack API ok=false → False."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps({"ok": False, "error": "invalid_auth"}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(monitor.urllib.request, "urlopen", return_value=FakeResponse()):
        assert monitor.post_to_slack("test") is False


# ─────────────────────────────────────────────────────────────────────────────
# main entry
# ─────────────────────────────────────────────────────────────────────────────


def test_main_returns_zero_when_all_active(monitor) -> None:
    with patch.object(monitor, "check_all_services", return_value=[]):
        assert monitor.main() == 0


def test_main_alerts_on_failure(monitor) -> None:
    """When a service fails, main() calls post_to_slack and returns 0."""
    fake_failure = {
        "service": "aiden-relay-watcher",
        "callsign": "aiden",
        "state": "failed",
        "log": "boom",
    }
    post_calls: list[str] = []

    def fake_post(text, channel=monitor.EXECUTION_CHANNEL):
        post_calls.append(text)
        return True

    with (
        patch.object(monitor, "check_all_services", return_value=[fake_failure]),
        patch.object(monitor, "post_to_slack", side_effect=fake_post),
    ):
        assert monitor.main() == 0
    assert len(post_calls) == 1
    assert "aiden-relay-watcher" in post_calls[0]
