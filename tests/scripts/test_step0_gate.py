"""tests for scripts/slack_relay.py — KEI-72 Step-0-RESTATE gate.

Verifies _has_recent_step0_restate scans the right inbox/processed/
directory + matches the marker case-insensitively (via callsign.upper())
+ returns False when:
  - the inbox dir doesn't exist
  - no recent message contains the marker
  - JSON files are malformed

Also verifies _maybe_self_assign refuses to invoke bd ready/claim when
the gate fails (the integration check Elliot cares about).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
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


def test_step0_present_via_tmp_path(tmp_path: Path, monkeypatch) -> None:
    """tmp_path-based: writes a STEP-0-RESTATE message + asserts True."""
    mod = _load_slack_relay()
    callsign = "elliot"
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg1.json", "[STEP-0-RESTATE:ELLIOT] objective scope")

    # Patch Path constructor to redirect /tmp/telegram-relay-* to tmp_path.
    real_path_cls = mod.Path

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return inbox
        return real_path_cls(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    assert mod._has_recent_step0_restate(callsign) is True


def test_step0_absent_returns_false(tmp_path: Path, monkeypatch) -> None:
    mod = _load_slack_relay()
    callsign = "elliot"
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg1.json", "some unrelated message")
    _write_inbox_message(inbox, "msg2.json", "[READY:elliot] but no step 0")

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return inbox
        return Path(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    assert mod._has_recent_step0_restate(callsign) is False


def test_step0_inbox_dir_missing_returns_false(tmp_path: Path, monkeypatch) -> None:
    mod = _load_slack_relay()
    callsign = "elliot"
    missing = tmp_path / "does-not-exist"

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return missing
        return Path(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    assert mod._has_recent_step0_restate(callsign) is False


def test_step0_malformed_json_skipped(tmp_path: Path, monkeypatch) -> None:
    """A malformed JSON file in processed/ must not crash the scan."""
    mod = _load_slack_relay()
    callsign = "elliot"
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    inbox.mkdir(parents=True)
    (inbox / "bad.json").write_text("not json at all {")
    _write_inbox_message(inbox, "good.json", "[STEP-0-RESTATE:ELLIOT] valid")

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return inbox
        return Path(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    assert mod._has_recent_step0_restate(callsign) is True


def test_step0_scan_depth_respected(tmp_path: Path, monkeypatch) -> None:
    """If the marker is OLDER than _STEP0_INBOX_SCAN_DEPTH messages back, no match."""
    mod = _load_slack_relay()
    callsign = "elliot"
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    # Write the marker first (oldest mtime).
    _write_inbox_message(inbox, "msg_oldest.json", "[STEP-0-RESTATE:ELLIOT] ancient")
    # Write SCAN_DEPTH + 1 newer messages without the marker.
    import time

    time.sleep(0.01)
    for i in range(mod._STEP0_INBOX_SCAN_DEPTH + 1):
        _write_inbox_message(inbox, f"msg_new_{i}.json", f"newer-{i} no marker")
        time.sleep(0.005)

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return inbox
        return Path(s)

    monkeypatch.setattr(mod, "Path", fake_path)
    assert mod._has_recent_step0_restate(callsign) is False


# ─── _maybe_self_assign integration ─────────────────────────────────────────


def test_self_assign_refuses_when_no_step0(tmp_path: Path, monkeypatch, capsys) -> None:
    """KEI-72 acceptance: _maybe_self_assign refuses to invoke bd when no Step 0."""
    mod = _load_slack_relay()
    callsign = "elliot"
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg.json", "no step 0 here")

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return inbox
        return Path(s)

    monkeypatch.setattr(mod, "Path", fake_path)

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


def test_self_assign_proceeds_when_step0_present(tmp_path: Path, monkeypatch) -> None:
    """When Step 0 marker IS in inbox, _maybe_self_assign should proceed to bd ready."""
    mod = _load_slack_relay()
    callsign = "elliot"
    inbox = tmp_path / f"telegram-relay-{callsign}" / "processed"
    _write_inbox_message(inbox, "msg.json", "[STEP-0-RESTATE:ELLIOT] continuing dispatch X")

    def fake_path(s: str) -> Path:
        if s == f"/tmp/telegram-relay-{callsign}/processed":
            return inbox
        return Path(s)

    monkeypatch.setattr(mod, "Path", fake_path)

    bd_calls: list[list[str]] = []

    class FakeCompleted:
        def __init__(self, *, returncode: int = 0, stdout: str = "[]") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_subprocess_run(cmd: list[str], **kw: object):
        bd_calls.append(cmd)
        # bd ready returns empty → _maybe_self_assign exits without claim.
        return FakeCompleted(returncode=0, stdout="[]")

    with patch("subprocess.run", fake_subprocess_run):
        mod._maybe_self_assign("[READY:elliot] continuing")
    # bd ready should have been called (the gate let us through), even though
    # nothing was claimed (empty queue).
    assert any("ready" in cmd for cmd in bd_calls), f"expected bd ready call, got {bd_calls}"


@pytest.fixture(autouse=True)
def _clean_callsign_env(monkeypatch):
    """Ensure each test gets a fresh CALLSIGN=elliot (non-clone)."""
    monkeypatch.setenv("CALLSIGN", "elliot")
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    yield
