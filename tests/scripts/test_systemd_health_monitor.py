"""Tests for scripts/orchestrator/systemd_health_monitor.py — KEI-141.

All subprocess calls are mocked; no real systemctl or tg invocations.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from subprocess import CompletedProcess

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "orchestrator" / "systemd_health_monitor.py"


@pytest.fixture(scope="module")
def mon():
    spec = importlib.util.spec_from_file_location("systemd_health_monitor", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["systemd_health_monitor"] = mod
    spec.loader.exec_module(mod)
    return mod


# ── list_failed_units ────────────────────────────────────────────────────────

_SYSTEMCTL_FAILED_OUTPUT = """\
orion-agent.service       loaded failed failed  Orion agent
atlas-agent.service       loaded failed failed  Atlas agent
cron.service              loaded failed failed  Cron daemon
"""


def test_list_failed_units_parses_systemctl_output(mon, monkeypatch):
    """Parses first token per line and returns matching fleet unit names."""
    fake = CompletedProcess(args=[], returncode=0, stdout=_SYSTEMCTL_FAILED_OUTPUT, stderr="")
    monkeypatch.setattr(
        "systemd_health_monitor.subprocess.run",
        lambda *a, **kw: fake,
    )
    result = mon.list_failed_units()
    assert "orion-agent.service" in result
    assert "atlas-agent.service" in result


def test_list_failed_units_filters_non_fleet(mon, monkeypatch):
    """Units not matching FLEET_PATTERNS are excluded."""
    fake = CompletedProcess(args=[], returncode=0, stdout=_SYSTEMCTL_FAILED_OUTPUT, stderr="")
    monkeypatch.setattr(
        "systemd_health_monitor.subprocess.run",
        lambda *a, **kw: fake,
    )
    result = mon.list_failed_units()
    assert "cron.service" not in result


def test_list_failed_units_empty_when_no_failures(mon, monkeypatch):
    """Empty stdout produces an empty list."""
    fake = CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    monkeypatch.setattr(
        "systemd_health_monitor.subprocess.run",
        lambda *a, **kw: fake,
    )
    result = mon.list_failed_units()
    assert result == []


# ── load_state ───────────────────────────────────────────────────────────────


def test_load_state_missing_returns_empty(mon, tmp_path):
    """Non-existent path returns {} without raising."""
    path = tmp_path / "nonexistent_state.json"
    assert mon.load_state(path) == {}


def test_load_state_malformed_returns_empty(mon, tmp_path):
    """Corrupt JSON content returns {} without raising."""
    path = tmp_path / "bad_state.json"
    path.write_text("this is not json {{{{")
    assert mon.load_state(path) == {}


# ── save_state ───────────────────────────────────────────────────────────────


def test_save_state_writes_json(mon, tmp_path):
    """Round-trip: save then load recovers the original dict."""
    path = tmp_path / "state.json"
    data = {"failed_units": ["orion-agent.service"], "updated_at": "2026-05-18T00:00:00+00:00"}
    mon.save_state(path, data)
    recovered = json.loads(path.read_text())
    assert recovered == data


def test_save_state_swallows_oserror(mon, tmp_path):
    """Read-only directory: save_state logs but does not raise."""
    ro_dir = tmp_path / "readonly"
    ro_dir.mkdir(mode=0o444)
    path = ro_dir / "state.json"
    # Should complete without raising even though write will fail
    mon.save_state(path, {"failed_units": []})
    # If we reach here the function did not raise
    ro_dir.chmod(0o755)  # restore so tmp_path cleanup works


# ── post_alert ───────────────────────────────────────────────────────────────


def test_post_alert_invokes_tg_cli_with_ceo_channel(mon, monkeypatch):
    """tg is called with -c ceo and the message string."""
    captured: list = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)
        return CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("systemd_health_monitor.subprocess.run", fake_run)
    result = mon.post_alert("/usr/local/bin/tg", "test alert")
    assert result is True
    assert len(captured) == 1
    cmd = captured[0]
    assert cmd[0] == "/usr/local/bin/tg"
    assert "-c" in cmd
    assert "ceo" in cmd
    assert "test alert" in cmd


def test_post_alert_returns_false_on_tg_failure(mon, monkeypatch):
    """Non-zero returncode from tg returns False without raising."""
    fake = CompletedProcess(args=[], returncode=1, stdout="", stderr="error from tg")
    monkeypatch.setattr(
        "systemd_health_monitor.subprocess.run",
        lambda *a, **kw: fake,
    )
    result = mon.post_alert("/usr/local/bin/tg", "fail message")
    assert result is False


# ── detect_changes ───────────────────────────────────────────────────────────


def test_detect_changes_newly_failed(mon):
    """Unit in failed_now but not in previously_failed → newly_failed."""
    newly, recovered = mon.detect_changes(
        failed_now=["orion-agent.service"],
        active_now=[],
        previously_failed=[],
    )
    assert "orion-agent.service" in newly
    assert recovered == []


def test_detect_changes_recovered(mon):
    """Unit in active_now that was previously_failed → recovered."""
    newly, recovered = mon.detect_changes(
        failed_now=[],
        active_now=["orion-agent.service"],
        previously_failed=["orion-agent.service"],
    )
    assert newly == []
    assert "orion-agent.service" in recovered


def test_detect_changes_persistent_failure_no_alert(mon):
    """Unit in both failed_now and previously_failed → no change (dedup)."""
    newly, recovered = mon.detect_changes(
        failed_now=["orion-agent.service"],
        active_now=[],
        previously_failed=["orion-agent.service"],
    )
    assert newly == []
    assert recovered == []


# ── main ─────────────────────────────────────────────────────────────────────


def test_main_alerts_on_newly_failed(mon, tmp_path, monkeypatch):
    """When a fleet unit is newly failed, main() calls tg with 🚨 and unit name."""
    state_path = tmp_path / "state.json"
    alerts_sent: list[str] = []

    monkeypatch.setattr(mon, "list_failed_units", lambda: ["orion-agent.service"])
    monkeypatch.setattr(mon, "list_active_units", lambda: [])
    monkeypatch.setattr(mon, "post_alert", lambda cli, msg: alerts_sent.append(msg) or True)

    rc = mon.main(["--state", str(state_path), "--tg-cli", "/usr/local/bin/tg"])

    assert rc == 0
    assert len(alerts_sent) == 1
    assert "orion-agent.service" in alerts_sent[0]
    assert "🚨" in alerts_sent[0]


def test_main_alerts_on_recovery(mon, tmp_path, monkeypatch):
    """When a previously-failed unit is now active, main() calls tg with ✅."""
    state_path = tmp_path / "state.json"
    # Seed state with a previously-failed unit
    state_path.write_text(json.dumps({"failed_units": ["orion-agent.service"]}))
    alerts_sent: list[str] = []

    monkeypatch.setattr(mon, "list_failed_units", lambda: [])
    monkeypatch.setattr(mon, "list_active_units", lambda: ["orion-agent.service"])
    monkeypatch.setattr(mon, "post_alert", lambda cli, msg: alerts_sent.append(msg) or True)

    rc = mon.main(["--state", str(state_path), "--tg-cli", "/usr/local/bin/tg"])

    assert rc == 0
    assert len(alerts_sent) == 1
    assert "orion-agent.service" in alerts_sent[0]
    assert "✅" in alerts_sent[0]


def test_main_no_alert_on_steady_state(mon, tmp_path, monkeypatch):
    """A unit that was failed last cycle and is still failed → no alert this cycle."""
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"failed_units": ["orion-agent.service"]}))
    alerts_sent: list[str] = []

    monkeypatch.setattr(mon, "list_failed_units", lambda: ["orion-agent.service"])
    monkeypatch.setattr(mon, "list_active_units", lambda: [])
    monkeypatch.setattr(mon, "post_alert", lambda cli, msg: alerts_sent.append(msg) or True)

    rc = mon.main(["--state", str(state_path), "--tg-cli", "/usr/local/bin/tg"])

    assert rc == 0
    assert alerts_sent == []


def test_main_exits_2_when_systemctl_missing(mon, tmp_path, monkeypatch):
    """FileNotFoundError from systemctl → exit code 2."""
    state_path = tmp_path / "state.json"

    def raise_fnf():
        raise FileNotFoundError("systemctl not found")

    monkeypatch.setattr(mon, "list_failed_units", raise_fnf)

    rc = mon.main(["--state", str(state_path), "--tg-cli", "/usr/local/bin/tg"])

    assert rc == 2
