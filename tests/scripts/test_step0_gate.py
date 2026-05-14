"""tests for scripts/slack_relay.py — KEI-72 Step-0-RESTATE gate.

Verifies _has_recent_step0_restate scans the right inbox/processed/
directory + matches the marker + returns False when:
  - the inbox dir doesn't exist
  - no recent message contains the marker
  - JSON files are malformed
  - the marker is older than _STEP0_INBOX_SCAN_DEPTH messages back

Also verifies _maybe_self_assign refuses to invoke bd ready/claim when
the gate fails (the integration check Elliot cares about).

Inbox path resolution uses the AGENCY_OS_RELAY_INBOX_BASE env var so
tests redirect into pytest's tmp_path without monkeypatching the Path
constructor.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "slack_relay.py"


def _load_slack_relay():
    """Reload the module under a non-clone CALLSIGN so the self-assign path runs."""
    os.environ.setdefault("SLACK_BOT_TOKEN", "test-token")
    os.environ["CALLSIGN"] = "elliot"  # not in _CLONE_CALLSIGNS
    spec = importlib.util.spec_from_file_location("slack_relay_kei72", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["slack_relay_kei72"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_inbox_message(inbox_dir: Path, name: str, text: str) -> Path:
    inbox_dir.mkdir(parents=True, exist_ok=True)
    p = inbox_dir / name
    p.write_text(json.dumps({"type": "text", "text": text, "sender": "test"}))
    return p


# ─── _has_recent_step0_restate ─────────────────────────────────────────────


def test_step0_present_returns_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Marker present in recent inbox → True."""
    callsign = "elliot"
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg1.json", "[STEP-0-RESTATE:ELLIOT] objective scope")
    assert mod._has_recent_step0_restate(callsign) is True


def test_step0_absent_returns_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    callsign = "elliot"
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg1.json", "some unrelated message")
    _write_inbox_message(inbox, "msg2.json", "[READY:elliot] but no step 0")
    assert mod._has_recent_step0_restate(callsign) is False


def test_step0_inbox_dir_missing_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No inbox dir for the callsign → False (no crash)."""
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    # No directory written at tmp_path/telegram-relay-elliot/processed.
    assert mod._has_recent_step0_restate("elliot") is False


def test_step0_malformed_json_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A malformed JSON file in processed/ must not crash the scan."""
    callsign = "elliot"
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    inbox.mkdir(parents=True)
    (inbox / "bad.json").write_text("not json at all {")
    _write_inbox_message(inbox, "good.json", "[STEP-0-RESTATE:ELLIOT] valid")
    assert mod._has_recent_step0_restate(callsign) is True


def test_step0_scan_depth_respected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If the marker is OLDER than _STEP0_INBOX_SCAN_DEPTH messages back, no match."""
    callsign = "elliot"
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    # Write the marker first (oldest mtime).
    _write_inbox_message(inbox, "msg_oldest.json", "[STEP-0-RESTATE:ELLIOT] ancient")
    time.sleep(0.01)
    # Write SCAN_DEPTH + 1 newer messages without the marker.
    for i in range(mod._STEP0_INBOX_SCAN_DEPTH + 1):
        _write_inbox_message(inbox, f"msg_new_{i}.json", f"newer-{i} no marker")
        time.sleep(0.005)
    assert mod._has_recent_step0_restate(callsign) is False


# ─── _maybe_self_assign integration ─────────────────────────────────────────


def test_self_assign_refuses_when_no_step0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """KEI-72 acceptance: _maybe_self_assign refuses to invoke bd when no Step 0."""
    callsign = "elliot"
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg.json", "no step 0 here")

    bd_calls: list[list[str]] = []

    def boom_subprocess_run(cmd: list[str], **kw: object):
        bd_calls.append(cmd)
        raise AssertionError(f"bd should NOT have been called: {cmd}")

    with patch("subprocess.run", boom_subprocess_run):
        mod._maybe_self_assign("[READY:elliot] continuing")
    assert bd_calls == []
    captured = capsys.readouterr()
    assert "refusing claim" in captured.err
    assert "STEP-0-RESTATE" in captured.err


def test_self_assign_proceeds_when_step0_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When Step 0 marker IS in inbox, _maybe_self_assign should proceed to bd ready."""
    callsign = "elliot"
    monkeypatch.setenv("AGENCY_OS_RELAY_INBOX_BASE", str(tmp_path))
    mod = _load_slack_relay()
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg.json", "[STEP-0-RESTATE:ELLIOT] continuing dispatch X")

    bd_calls: list[list[str]] = []

    class FakeCompleted:
        def __init__(self, *, returncode: int = 0, stdout: str = "[]") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_subprocess_run(cmd: list[str], **kw: object):
        bd_calls.append(cmd)
        return FakeCompleted(returncode=0, stdout="[]")

    with patch("subprocess.run", fake_subprocess_run):
        mod._maybe_self_assign("[READY:elliot] continuing")
    assert any("ready" in cmd for cmd in bd_calls), f"expected bd ready call, got {bd_calls}"


@pytest.fixture(autouse=True)
def _clean_callsign_env(monkeypatch: pytest.MonkeyPatch):
    """Ensure each test gets a fresh CALLSIGN=elliot (non-clone)."""
    monkeypatch.setenv("CALLSIGN", "elliot")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    yield
