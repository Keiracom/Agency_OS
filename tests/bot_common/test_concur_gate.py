"""tests for src/bot_common/concur_gate.py — R1 outbound concur gate.

Post KEI-38 (Dave verbatim 2026-05-14): the gate fires ONLY on a literal
[CONCUR:<callsign>] or [BLOCK:<callsign>] token. Substring-match on the
broad enforcer TRIGGER_PATTERNS list is gone — that list is for the LLM
governance pre-filter, not for the outbound concur gate.

Covers:
  - should_gate: anchored-regex token detection
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
# should_gate — anchored-token detection (KEI-38, Dave verbatim 2026-05-14)
# ─────────────────────────────────────────────────────────────────────────────


def test_should_gate_matches_concur_token() -> None:
    """Literal [CONCUR:<callsign>] token → gate fires."""
    assert concur_gate.should_gate("[CONCUR:max] release looks fine")


def test_should_gate_matches_block_token() -> None:
    """Literal [BLOCK:<callsign>] token → gate fires."""
    assert concur_gate.should_gate("[BLOCK:elliot] hold on the rebase")


def test_should_gate_case_insensitive_token() -> None:
    """Tokens are matched case-insensitively."""
    assert concur_gate.should_gate("[concur:scout] verified")
    assert concur_gate.should_gate("[Block:Aiden] stop")


def test_should_gate_does_not_match_prose_concur() -> None:
    """KEI-38 core fix — prose containing 'concur' must NOT trigger the gate."""
    assert not concur_gate.should_gate("we concur on this approach")
    assert not concur_gate.should_gate("shape-concur with hold")
    assert not concur_gate.should_gate("Max FINAL CONCUR on PR #842")


def test_should_gate_does_not_match_final_concur_token() -> None:
    """[FINAL CONCUR:<name>] is a merge-authorisation declaration, not a R1 trigger."""
    assert not concur_gate.should_gate("[FINAL CONCUR:ELLIOT] merging now")
    assert not concur_gate.should_gate("[FINAL CONCUR:max]")


def test_should_gate_does_not_match_concur_request_stub() -> None:
    """[CONCUR-REQUEST:<callsign>] is the hold-stub itself — breaks recursion."""
    assert not concur_gate.should_gate(
        "[CONCUR-REQUEST:AIDEN] requesting concurrence from peer on: PR merge"
    )


def test_should_gate_no_match_on_completion_prose() -> None:
    """Old TRIGGER_PATTERNS substrings (merged, committed, PR #N, done) no longer gate.

    This is the KEI-38 unblock for Max — factual completion claims pass through
    without requiring peer concur. Peer-review discipline lives elsewhere.
    """
    assert not concur_gate.should_gate("Just committed the fix.")
    assert not concur_gate.should_gate("PR merged to main.")
    assert not concur_gate.should_gate("Looking at PR #715 right now.")
    assert not concur_gate.should_gate("PR MERGED to main.")
    assert not concur_gate.should_gate("Task done, all stores written.")


def test_should_gate_no_match_on_plain_text() -> None:
    """Plain status text without trigger tokens → no gate."""
    assert not concur_gate.should_gate("Hello team, standing by for next dispatch.")


def test_should_gate_no_match_on_empty_brackets() -> None:
    """[CONCUR:] with empty callsign → no gate (anchored regex requires [a-z]+ after colon)."""
    assert not concur_gate.should_gate("[CONCUR:] missing callsign")


def test_should_gate_matches_token_with_hyphenated_callsign() -> None:
    """Callsigns with hyphens or underscores are valid (e.g. atlas-bot)."""
    assert concur_gate.should_gate("[CONCUR:atlas-bot] noted")
    assert concur_gate.should_gate("[BLOCK:test_user] stop")


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
    """No R1 trigger token → (True, None) regardless of peer concur."""
    allow, replacement = concur_gate.gate_check(
        "Standing by, no shipping happening.", "aiden", "fake-token"
    )
    assert allow is True
    assert replacement is None


def test_gate_check_prose_concur_allows() -> None:
    """KEI-38: prose 'we concur' must pass through without peer-concur lookup."""
    # Patch has_peer_concur to fail loudly if called — the gate must short-circuit
    # at should_gate=False before reaching the Slack lookup.
    with patch.object(
        concur_gate, "has_peer_concur", side_effect=AssertionError("should not be called")
    ):
        allow, replacement = concur_gate.gate_check(
            "we concur on this approach", "max", "fake-token"
        )
    assert allow is True
    assert replacement is None


def test_gate_check_trigger_with_concur_allows() -> None:
    """[CONCUR:<callsign>] token AND peer concur in history → (True, None)."""
    with patch.object(concur_gate, "has_peer_concur", return_value=True):
        allow, replacement = concur_gate.gate_check(
            "[CONCUR:max] verified the diff", "aiden", "fake-token"
        )
    assert allow is True
    assert replacement is None


def test_gate_check_trigger_without_concur_blocks(tmp_path, monkeypatch) -> None:
    """[CONCUR:<callsign>] token + NO peer concur → (False, replacement) + hold file."""
    # Redirect _pending_dir to tmp_path so we don't touch real /tmp
    monkeypatch.setattr(concur_gate, "_pending_dir", lambda cs: tmp_path / cs)
    text = "[CONCUR:max] verified the diff"
    with patch.object(concur_gate, "has_peer_concur", return_value=False):
        allow, replacement = concur_gate.gate_check(text, "aiden", "fake-token")
    assert allow is False
    assert replacement is not None
    assert "[CONCUR-REQUEST:AIDEN]" in replacement
    # Hold file written under tmp_path
    hold_dir = tmp_path / "aiden"
    assert hold_dir.exists()
    hold_files = list(hold_dir.glob("*.txt"))
    assert len(hold_files) == 1
    assert hold_files[0].read_text() == text


def test_gate_check_topic_sha_in_replacement(tmp_path, monkeypatch) -> None:
    """Replacement message references the held file by topic-sha."""
    monkeypatch.setattr(concur_gate, "_pending_dir", lambda cs: tmp_path / cs)
    text = "[BLOCK:elliot] hold on the rebase"
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


# ─────────────────────────────────────────────────────────────────────────────
# _eligible_reviewers — Agency_OS-yvlr51 routing-fix (CONCUR-REQUEST signaling)
# ─────────────────────────────────────────────────────────────────────────────


def test_eligible_reviewers_fallback_when_no_agent_health() -> None:
    """Agency_OS-yvlr51 negative path — ceo:agent_health absent → all non-author callsigns.

    The polling-loop infra that populates ceo:agent_health (KEI-63 follow-up)
    does not exist yet. The fallback MUST return the full 7-callsign roster
    minus the author, so the CONCUR-REQUEST stub advertises every peer that
    can validly release the gate. This is what unblocks the V1-chain
    specific-callsign-stuck failure mode Dave diagnosed 2026-05-14.
    """
    result = concur_gate._eligible_reviewers("aiden")
    expected = sorted({"elliot", "max", "atlas", "orion", "scout", "nova"})
    assert result == expected
    # Author always excluded, case-insensitive.
    assert "aiden" not in concur_gate._eligible_reviewers("AIDEN")


def test_gate_check_replacement_advertises_eligible_reviewers(tmp_path, monkeypatch) -> None:
    """CONCUR-REQUEST stub must list eligible non-author peers in its body."""
    monkeypatch.setattr(concur_gate, "_pending_dir", lambda cs: tmp_path / cs)
    with patch.object(concur_gate, "has_peer_concur", return_value=False):
        _, replacement = concur_gate.gate_check(
            "[CONCUR:max] verified the diff", "aiden", "fake-token"
        )
    assert "Eligible reviewers:" in replacement
    eligible_line = next(
        ln for ln in replacement.splitlines() if ln.startswith("Eligible reviewers:")
    )
    for peer in ("elliot", "max", "atlas", "orion", "scout", "nova"):
        assert peer in eligible_line
    # Author not in the eligible-reviewers line itself.
    assert "aiden" not in eligible_line
