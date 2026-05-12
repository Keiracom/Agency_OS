"""Tests for the anchored [READY:<callsign>] regex (PR #783 v2)."""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path("/home/elliotbot/clawd/Agency_OS-aiden")
SCRIPT_PATH = REPO_ROOT / "scripts" / "slack_relay.py"


def _load_slack_relay():
    # Module-level code reads SLACK_BOT_TOKEN + resolves CALLSIGN; ensure both
    # are set before import.
    import os

    os.environ.setdefault("SLACK_BOT_TOKEN", "test-token")
    os.environ.setdefault("CALLSIGN", "aiden")
    spec = importlib.util.spec_from_file_location("slack_relay_test", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["slack_relay_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_anchored_start_of_message_fires():
    mod = _load_slack_relay()
    assert mod._is_ready_marker("[READY:aiden] starting work", "aiden") is True


def test_anchored_after_callsign_tag_fires():
    mod = _load_slack_relay()
    assert mod._is_ready_marker("[AIDEN] [READY:aiden] starting work", "aiden") is True


def test_anchored_start_of_line_fires():
    mod = _load_slack_relay()
    assert mod._is_ready_marker("Some preamble\n[READY:aiden] continuing", "aiden") is True


def test_prose_reference_does_not_fire():
    """The empirical false-positive that fired on PR #783's own announce:
    '[READY:aiden] emission' embedded mid-sentence with no line-anchor."""
    mod = _load_slack_relay()
    prose = "Next live [READY:aiden] emission should see [self-assign] claimed <id>"
    assert mod._is_ready_marker(prose, "aiden") is False


def test_wrong_callsign_does_not_fire():
    mod = _load_slack_relay()
    assert mod._is_ready_marker("[READY:max] not me", "aiden") is False


def test_case_insensitive_matches():
    mod = _load_slack_relay()
    assert mod._is_ready_marker("[ready:AIDEN] case insensitive", "aiden") is True


# ─── Clone-callsign role-filter (Agency_OS-g41) ────────────────────────
#
# Clone callsigns (atlas/orion/scout) must skip-claim entirely — polling loop
# is their canonical dispatch path. Empirical evidence: Scout false-positive
# auto-claims on Agency_OS-dhe + Agency_OS-yvz this session, both research
# [READY:scout] in doc-completion posts that triggered primary build claims.


def test_clone_callsign_skips_self_assign(monkeypatch):
    """Clones (scout/orion/atlas) MUST NOT spawn bd subprocess, even with
    an anchored [READY:<clone>] in the message body."""
    mod = _load_slack_relay()
    monkeypatch.setattr(mod, "CALLSIGN", "scout")

    def _raise_if_called(*args, **kwargs):
        raise AssertionError("subprocess.run must not be invoked for clone callsigns")

    import subprocess

    monkeypatch.setattr(subprocess, "run", _raise_if_called)

    # Returns None without raising — proves the guard fired before any subprocess.
    assert mod._maybe_self_assign("[READY:scout] doc done") is None


def test_primary_callsign_proceeds_past_clone_guard(monkeypatch):
    """Primary callsigns (aiden/max/elliot) must still proceed past the clone
    guard and reach the subprocess path (which we sentinel-trip)."""
    mod = _load_slack_relay()
    monkeypatch.setattr(mod, "CALLSIGN", "aiden")

    calls = []
    import subprocess

    def _capture(*args, **kwargs):
        calls.append(args[0] if args else None)
        # Return a fake CompletedProcess that bails the rest of the function.
        return subprocess.CompletedProcess(args=args[0] if args else [], returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", _capture)

    mod._maybe_self_assign("[READY:aiden] starting work")
    assert any(c and c[0] == "bd" for c in calls), (
        f"expected bd subprocess invocation; got {calls!r}"
    )


def test_clone_callsigns_set_matches_channel_access_map():
    """Defensive: the clone set must equal the clone keys in _channel_access."""
    mod = _load_slack_relay()
    channel_clones = {"atlas", "orion", "scout"}
    assert frozenset(channel_clones) == mod._CLONE_CALLSIGNS


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
