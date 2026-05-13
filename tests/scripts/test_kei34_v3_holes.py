"""Tests for KEI-34 v3 — 2 holes per Elliot DISPATCH-PROPOSAL ts ~1778637010."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "elliot_polling_loop.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("elliot_polling_loop_v3", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["elliot_polling_loop_v3"] = m
    spec.loader.exec_module(m)
    return m


# ── HOLE A — system-wide long-running-subprocess detection ─────────────────


def test_long_running_pattern_re_matches_cognee_ingest(mod):
    """Canonical Max Cognee ingest command matches the long-running pattern allowlist."""
    cmd = "/home/elliotbot/clawd/Agency_OS/.venv/bin/python3 scripts/cognee_ingest.py --streams 2"
    assert mod._LONG_RUNNING_CMD_RE.search(cmd) is not None


def test_long_running_pattern_re_matches_pipeline_runner(mod):
    cmd = "python3 scripts/pipeline_runner.py --cohort small"
    assert mod._LONG_RUNNING_CMD_RE.search(cmd) is not None


def test_long_running_pattern_re_no_match_incidental_python(mod):
    """pytest / mypy / etc. — should NOT match (false-positive prevention)."""
    assert mod._LONG_RUNNING_CMD_RE.search("python3 -m pytest tests/") is None
    assert mod._LONG_RUNNING_CMD_RE.search("python3 -m mypy src/") is None
    assert mod._LONG_RUNNING_CMD_RE.search("/usr/bin/python3 manage.py runserver") is None


def test_system_wide_long_running_returns_bool(mod):
    """Smoke test — actual runtime may or may not have a matching process."""
    out = mod._system_wide_long_running_subprocess()
    assert isinstance(out, bool)


def test_system_wide_long_running_no_ps_returns_false(mod, monkeypatch):
    """Fail-open: ps subprocess error returns False."""
    def _fake_run(*args, **kwargs):
        raise FileNotFoundError("ps not found")
    monkeypatch.setattr(subprocess, "run", _fake_run)
    assert mod._system_wide_long_running_subprocess() is False


# ── HOLE B — long-running-track silent escalation ──────────────────────────


def test_poll_long_running_silent_no_state_file_returns_empty(mod, monkeypatch, tmp_path):
    """Missing callsign-last-post.json → empty list."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Make sure the state path doesn't exist
    assert mod.poll_long_running_silent() == []


def test_poll_long_running_silent_fires_when_active_and_silent(mod, monkeypatch, tmp_path):
    """Active long-running subprocess + last post >30 min ago → fires."""
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".local" / "state" / "agency-os"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "callsign-last-post.json"
    forty_min_ago = (datetime.now(UTC) - timedelta(minutes=40)).isoformat()
    state_path.write_text(json.dumps({"max": forty_min_ago}))
    # Stub _agent_has_active_subprocess: only max active
    monkeypatch.setattr(mod, "_agent_has_active_subprocess", lambda cs: cs == "max")
    out = mod.poll_long_running_silent()
    assert any(cs == "max" and mins >= 30 for cs, mins in out)


def test_poll_long_running_silent_silent_but_no_subprocess_passes(mod, monkeypatch, tmp_path):
    """Silent for 30+ min but no active subprocess → no-op (not a 'track' agent)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".local" / "state" / "agency-os"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "callsign-last-post.json"
    forty_min_ago = (datetime.now(UTC) - timedelta(minutes=40)).isoformat()
    state_path.write_text(json.dumps({"max": forty_min_ago}))
    monkeypatch.setattr(mod, "_agent_has_active_subprocess", lambda cs: False)
    assert mod.poll_long_running_silent() == []


def test_poll_long_running_silent_active_but_recent_post_passes(mod, monkeypatch, tmp_path):
    """Active subprocess but posted in last 30 min → no-op."""
    monkeypatch.setenv("HOME", str(tmp_path))
    state_dir = tmp_path / ".local" / "state" / "agency-os"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "callsign-last-post.json"
    ten_min_ago = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
    state_path.write_text(json.dumps({"max": ten_min_ago}))
    monkeypatch.setattr(mod, "_agent_has_active_subprocess", lambda cs: cs == "max")
    assert mod.poll_long_running_silent() == []


def test_compose_dispatches_long_running_silent_emits_to_ceo(mod):
    sig = mod.CycleSignals(
        bd_ready=[],
        linear_stale=[],
        idle_agents=[],
        prefect_failures=[],
        long_running_silent_callsigns=[("max", 80)],
    )
    dispatches = mod.compose_dispatches(sig)
    ceo_msgs = [m for ch, m in dispatches if ch == mod.CEO_CHANNEL_NAME]
    sweep = [m for m in ceo_msgs if "Long-running track silent" in m]
    assert len(sweep) == 1
    assert "max running long task with no progress-post for 80m" in sweep[0]
