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


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
