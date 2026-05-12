"""tests for src/bot_common/concur_gate.py — R1 outbound concur gate.

concur_gate.py shipped without dedicated test coverage. This file fills
the gap with mock-based unit tests covering:
  - should_gate: trigger pattern detection (uses TRIGGER_PATTERNS)
  - has_peer_concur: Slack history lookup (mocked urlopen)
  - gate_check: main entry — allow-as-is vs replacement-with-CONCUR-REQUEST
  - env_skip: env bypass parsing
  - Side effects: pending file written under /tmp/<callsign>-pending-concur/
  - Topic-sha keying for hold files

All Slack HTTP traffic mocked via urllib.request.urlopen patches.
"""

from __future__ import annotations

import json
import os
from io import BytesIO
from unittest.mock import patch
from urllib.error import URLError

import pytest

from src.bot_common import concur_gate

# ─────────────────────────────────────────────────────────────────────────────
# should_gate — trigger pattern detection
# ─────────────────────────────────────────────────────────────────────────────


def test_should_gate_matches_committed_keyword() -> None:
    """`commit` is in TRIGGER_PATTERNS (committal verb)."""
    assert concur_gate.should_gate("Just committed the fix.")


def test_should_gate_matches_merged_keyword() -> None:
    assert concur_gate.should_gate("PR merged to main.")


def test_should_gate_matches_pr_hash() -> None:
    """`pr #` substring triggers."""
    assert concur_gate.should_gate("Looking at PR #715 right now.")


def test_should_gate_case_insensitive() -> None:
    """should_gate lowercases the text first."""
    assert concur_gate.should_gate("PR MERGED to main.")


def test_should_gate_no_match_on_plain_text() -> None:
    """Plain status text without trigger words → no gate."""
    assert not concur_gate.should_gate("Hello team, standing by for next dispatch.")


# ─────────────────────────────────────────────────────────────────────────────
# has_peer_concur — Slack history lookup (mocked)
# ─────────────────────────────────────────────────────────────────────────────


def _fake_slack_response(messages: list[dict], ok: bool = True) -> BytesIO:
    body = json.dumps({"ok": ok, "messages": messages}).encode("utf-8")
    return BytesIO(body)


def test_has_peer_concur_found() -> None:
    """`[CONCUR:aiden]` in recent history → True."""
    messages = [
        {"text": "[ELLIOT] [CONCUR:aiden] verified the diff"},
        {"text": "[AIDEN] working on it"},
    ]

    class FakeResponse:
        def __init__(self, body: BytesIO) -> None:
            self._body = body

        def read(self) -> bytes:
            return self._body.read()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(
        concur_gate.urllib.request,
        "urlopen",
        return_value=FakeResponse(_fake_slack_response(messages)),
    ):
        assert concur_gate.has_peer_concur("aiden", "fake-token") is True


def test_has_peer_concur_case_insensitive_lookup() -> None:
    """`[CONCUR:AIDEN]` (uppercase) still resolves for callsign='aiden'."""
    messages = [{"text": "[ELLIOT] [CONCUR:AIDEN] looks good"}]

    class FakeResponse:
        def read(self) -> bytes:
            return _fake_slack_response(messages).read()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(concur_gate.urllib.request, "urlopen", return_value=FakeResponse()):
        assert concur_gate.has_peer_concur("aiden", "fake-token") is True


def test_has_peer_concur_not_found() -> None:
    """No concur tag for this callsign → False."""
    messages = [
        {"text": "[ELLIOT] [CONCUR:max] PR looks fine"},
        {"text": "[MAX] working on the build"},
    ]

    class FakeResponse:
        def read(self) -> bytes:
            return _fake_slack_response(messages).read()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(concur_gate.urllib.request, "urlopen", return_value=FakeResponse()):
        assert concur_gate.has_peer_concur("aiden", "fake-token") is False


def test_has_peer_concur_network_failure_returns_false() -> None:
    """urlopen raising URLError → False (conservative — don't allow without peer)."""
    with patch.object(concur_gate.urllib.request, "urlopen", side_effect=URLError("network")):
        assert concur_gate.has_peer_concur("aiden", "fake-token") is False


def test_has_peer_concur_slack_api_not_ok_returns_false() -> None:
    """Slack API returns ok=false → False."""

    class FakeResponse:
        def read(self) -> bytes:
            return json.dumps({"ok": False, "error": "invalid_auth"}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with patch.object(concur_gate.urllib.request, "urlopen", return_value=FakeResponse()):
        assert concur_gate.has_peer_concur("aiden", "fake-token") is False


# ─────────────────────────────────────────────────────────────────────────────
# gate_check — main entry
# ─────────────────────────────────────────────────────────────────────────────


def test_gate_check_no_trigger_allows() -> None:
    """No R1 trigger pattern → (True, None) regardless of peer concur."""
    allow, replacement = concur_gate.gate_check(
        "Standing by, no shipping happening.", "aiden", "fake-token"
    )
    assert allow is True
    assert replacement is None


def test_gate_check_trigger_with_concur_allows() -> None:
    """Trigger pattern present AND peer concur in history → (True, None)."""
    with patch.object(concur_gate, "has_peer_concur", return_value=True):
        allow, replacement = concur_gate.gate_check("PR merged to main.", "aiden", "fake-token")
    assert allow is True
    assert replacement is None


def test_gate_check_trigger_without_concur_blocks(tmp_path, monkeypatch) -> None:
    """Trigger pattern + NO peer concur → (False, replacement) + hold file written."""
    # Redirect _pending_dir to tmp_path so we don't touch real /tmp
    monkeypatch.setattr(concur_gate, "_pending_dir", lambda cs: tmp_path / cs)
    with patch.object(concur_gate, "has_peer_concur", return_value=False):
        allow, replacement = concur_gate.gate_check("PR merged to main.", "aiden", "fake-token")
    assert allow is False
    assert replacement is not None
    assert "[CONCUR-REQUEST:AIDEN]" in replacement
    assert "PR merged to main." in replacement.lower() or "merged" in replacement.lower()
    # Hold file written under tmp_path
    hold_dir = tmp_path / "aiden"
    assert hold_dir.exists()
    hold_files = list(hold_dir.glob("*.txt"))
    assert len(hold_files) == 1
    assert hold_files[0].read_text() == "PR merged to main."


def test_gate_check_topic_sha_in_replacement(tmp_path, monkeypatch) -> None:
    """Replacement message references the held file by topic-sha."""
    monkeypatch.setattr(concur_gate, "_pending_dir", lambda cs: tmp_path / cs)
    text = "PR merged to main."
    expected_sha = concur_gate._topic_sha(text)
    with patch.object(concur_gate, "has_peer_concur", return_value=False):
        _, replacement = concur_gate.gate_check(text, "aiden", "fake-token")
    assert expected_sha in replacement


# ─────────────────────────────────────────────────────────────────────────────
# env_skip
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_env_skip():
    prior = os.environ.pop("CONCUR_GATE_SKIP", None)
    yield
    if prior is not None:
        os.environ["CONCUR_GATE_SKIP"] = prior


def test_env_skip_default_false() -> None:
    assert concur_gate.env_skip() is False


def test_env_skip_one_true() -> None:
    os.environ["CONCUR_GATE_SKIP"] = "1"
    assert concur_gate.env_skip() is True


def test_env_skip_true_string() -> None:
    os.environ["CONCUR_GATE_SKIP"] = "true"
    assert concur_gate.env_skip() is True


def test_env_skip_yes_string() -> None:
    os.environ["CONCUR_GATE_SKIP"] = "yes"
    assert concur_gate.env_skip() is True


def test_env_skip_unrecognized_false() -> None:
    """Random non-truthy strings → False."""
    os.environ["CONCUR_GATE_SKIP"] = "maybe"
    assert concur_gate.env_skip() is False


# ─────────────────────────────────────────────────────────────────────────────
# _topic_sha — deterministic short hash
# ─────────────────────────────────────────────────────────────────────────────


def test_topic_sha_deterministic() -> None:
    assert concur_gate._topic_sha("hello") == concur_gate._topic_sha("hello")


def test_topic_sha_different_inputs_different_outputs() -> None:
    assert concur_gate._topic_sha("hello") != concur_gate._topic_sha("goodbye")


def test_topic_sha_length() -> None:
    """12-char prefix of sha1."""
    assert len(concur_gate._topic_sha("anything")) == 12
