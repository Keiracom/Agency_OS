"""Tests for ops_failure_publish.py + peer_event_ceo_relay.py (Agency_OS-ja8d).

Coverage:
  - ops_failure_publish.build_envelope: correct keys, subprocess output in summary,
    subprocess exception swallowed.
  - peer_event_ceo_relay: OPS_FAILURE_SUBJECT in SUBJECTS; _handle_ops_failure
    posts to #ceo; per-unit throttle suppresses second call; subject-based routing
    when kind is absent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))

import ops_failure_publish as ofp  # noqa: E402
import peer_event_ceo_relay as relay  # noqa: E402

# ── ops_failure_publish ───────────────────────────────────────────────────────


def _make_completed_process(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_build_envelope_required_keys():
    """Envelope must contain from/kind/unit/summary/ts with correct values."""
    with patch("ops_failure_publish.subprocess.run") as mock_run:
        mock_run.return_value = _make_completed_process("some output line\n")
        env = ofp.build_envelope("test-unit.service")
    assert env["from"] == "ops-failure-alert"
    assert env["kind"] == "ops_failure"
    assert env["unit"] == "test-unit.service"
    assert "test-unit.service" in env["summary"]
    assert isinstance(env["ts"], float)
    assert env["ts"] > 0


def test_build_envelope_contains_subprocess_output():
    """Subprocess stdout lines appear in the envelope summary."""
    status_output = "Active: failed (Result: exit-code)\nMain PID: 1234"
    journal_output = "May 29 10:00:00 host test-unit[1234]: ERROR: something went wrong"

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_completed_process(status_output)
        return _make_completed_process(journal_output)

    with patch("ops_failure_publish.subprocess.run", side_effect=side_effect):
        env = ofp.build_envelope("test-unit.service", now=1000.0)

    assert "failed" in env["summary"]
    assert "ERROR: something went wrong" in env["summary"]
    assert env["ts"] == 1000.0


def test_build_envelope_swallows_subprocess_exception():
    """A subprocess.run raising an exception must not propagate — envelope still built."""
    with patch("ops_failure_publish.subprocess.run", side_effect=OSError("no such binary")):
        env = ofp.build_envelope("crash-unit.service")
    # Must still have required keys and not raise
    assert env["kind"] == "ops_failure"
    assert env["unit"] == "crash-unit.service"
    # summary may be sparse but must be a string
    assert isinstance(env["summary"], str)


def test_build_envelope_unit_echoed_in_summary():
    """unit name must appear in summary regardless of subprocess content."""
    with patch("ops_failure_publish.subprocess.run") as mock_run:
        mock_run.return_value = _make_completed_process("")
        env = ofp.build_envelope("my-special-unit.service")
    assert "my-special-unit.service" in env["summary"]


# ── peer_event_ceo_relay ──────────────────────────────────────────────────────


def test_ops_failure_subject_in_subjects():
    """OPS_FAILURE_SUBJECT must be present in SUBJECTS tuple."""
    assert relay.OPS_FAILURE_SUBJECT in relay.SUBJECTS
    assert relay.OPS_FAILURE_SUBJECT == "keiracom.ops.failure"


def _reset_relay_state():
    """Clear throttle + dedup dicts between sub-tests."""
    relay._throttle.clear()
    relay._dedup.clear()


def test_handle_envelope_ops_failure_posts_to_ceo(monkeypatch):
    """_handle_envelope on keiracom.ops.failure must call _post_ceo once."""
    _reset_relay_state()
    captured: list[tuple[str, str]] = []

    def fake_post_ceo(category: str, body: str) -> None:
        captured.append((category, body))

    monkeypatch.setattr(relay, "_post_ceo", fake_post_ceo)

    relay._handle_envelope(
        "keiracom.ops.failure",
        {
            "kind": "ops_failure",
            "unit": "weaviate-backup.service",
            "summary": "weaviate-backup.service entered FAILED state\nstatus=4/NOPERMISSION",
        },
    )

    assert len(captured) == 1
    category, body = captured[0]
    assert category == "Service failure"
    assert "weaviate-backup.service" in body


def test_handle_envelope_ops_failure_throttle(monkeypatch):
    """Second identical unit call within cooldown must NOT call _post_ceo again."""
    _reset_relay_state()
    captured: list[tuple[str, str]] = []

    def fake_post_ceo(category: str, body: str) -> None:
        captured.append((category, body))

    monkeypatch.setattr(relay, "_post_ceo", fake_post_ceo)

    envelope_first = {
        "kind": "ops_failure",
        "unit": "atlas-inbox-watcher.service",
        "summary": "atlas-inbox-watcher.service entered FAILED state\nfirst attempt",
    }
    envelope_second = {
        "kind": "ops_failure",
        "unit": "atlas-inbox-watcher.service",
        "summary": "atlas-inbox-watcher.service entered FAILED state\nsecond attempt",
    }

    # First call — should post
    relay._handle_envelope("keiracom.ops.failure", envelope_first)
    assert len(captured) == 1, "first call must post to #ceo"

    # Second call within cooldown (throttle set, _dedup cleared to isolate)
    relay._dedup.clear()
    relay._handle_envelope("keiracom.ops.failure", envelope_second)
    assert len(captured) == 1, "second call within cooldown must be throttled"


def test_handle_envelope_routes_by_subject_when_kind_missing(monkeypatch):
    """Subject keiracom.ops.failure must trigger _post_ceo even with no 'kind' field."""
    _reset_relay_state()
    captured: list[tuple[str, str]] = []

    def fake_post_ceo(category: str, body: str) -> None:
        captured.append((category, body))

    monkeypatch.setattr(relay, "_post_ceo", fake_post_ceo)

    relay._handle_envelope(
        "keiracom.ops.failure",
        {"unit": "x.service", "summary": "x down — connection refused"},
    )

    assert len(captured) == 1
    assert "x.service" in captured[0][1]
