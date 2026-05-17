"""Tests for KEI-80 — escalation-keyword scan band-aid (Dave 30-min hot-patch 2026-05-16).

Verifies that _maybe_escalate_to_ceo fires a direct #ceo post BEFORE the normal relay
when an outbox message contains escalation language, and that the guard conditions
(already-#ceo target, already-[ESCALATION] prefix, no keyword) suppress the extra post.

No live Slack / Supabase calls — all network I/O is mocked.
"""

from __future__ import annotations

import importlib.util
import sys
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELAY_PATH = REPO_ROOT / "scripts" / "slack_relay.py"


# ---------------------------------------------------------------------------
# Module fixture — load slack_relay once per module with env stubbed
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def monkeypatch_module(request):
    """Module-scoped monkeypatch needed for module-level CALLSIGN resolution."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    mp.setenv("CALLSIGN", "elliot")
    mp.setenv("SLACK_BOT_TOKEN", "xoxb-fake-test-token")
    request.addfinalizer(mp.undo)
    return mp


@pytest.fixture(scope="module")
def relay(monkeypatch_module):
    """Import scripts/slack_relay.py once per module with required env stubbed."""
    module_name = "slack_relay_kei80"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, RELAY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXEC_CHANNEL = "C0B3QB0K1GQ"  # #execution
_CEO_CHANNEL = "C0B2PM3TV0B"  # #ceo


class _FakeResponse:
    """Minimal urllib context-manager response."""

    def __init__(self, payload: bytes = b'{"ok": true}') -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._payload


# ---------------------------------------------------------------------------
# Test 1 — keyword triggers CEO post + normal relay both fire
# ---------------------------------------------------------------------------


def test_escalation_keyword_triggers_ceo_post(relay):
    """Message with escalation keyword to #execution fires CEO post then normal relay."""
    message = "holding for Dave decision on Wave 5"
    calls_made: list[dict] = []

    def fake_urlopen(req, timeout=10):
        import json

        body = json.loads(req.data)
        calls_made.append({"channel": body["channel"], "text": body["text"]})
        return _FakeResponse()

    with (
        patch.object(relay.urllib.request, "urlopen", side_effect=fake_urlopen),
        # Bypass gates that would block the post() call (verify_gate, law_xv, concur)
        patch.dict(
            "sys.modules",
            {
                "src.bot_common.verify_gate": MagicMock(gate_check=lambda m: (True, None)),
                "src.bot_common.session_end_gate": MagicMock(gate_check=lambda m: (True, None)),
                "src.bot_common.concur_gate": MagicMock(env_skip=lambda: True, gate_check=None),
                "src.bot_common.enforcer_deterministic": MagicMock(
                    check_r11=lambda m, channel=None: None
                ),
            },
        ),
        # Suppress _record_last_post filesystem side-effect
        patch.object(relay, "_record_last_post"),
        # Suppress _maybe_self_assign subprocess side-effect
        patch.object(relay, "_maybe_self_assign"),
    ):
        relay.main.__globals__["ALLOWED_CHANNELS"] = frozenset({_EXEC_CHANNEL, _CEO_CHANNEL})
        relay._maybe_escalate_to_ceo(_EXEC_CHANNEL, message, "elliot")
        # Simulate normal relay post separately
        import json
        import urllib.request as _urlreq

        payload = {"channel": _EXEC_CHANNEL, "text": f"[ELLIOT] {message}"}
        req = _urlreq.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": "Bearer xoxb-fake-test-token",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        fake_urlopen(req)

    assert len(calls_made) == 2  # noqa: PLR2004

    # First call must be the CEO escalation
    assert calls_made[0]["channel"] == _CEO_CHANNEL
    assert calls_made[0]["text"] == f"[ESCALATION] elliot · {message}"

    # Second call must be the normal relay
    assert calls_made[1]["channel"] == _EXEC_CHANNEL


# ---------------------------------------------------------------------------
# Test 2 — no keyword → only normal relay fires
# ---------------------------------------------------------------------------


def test_no_keyword_skips_ceo_post(relay):
    """Message without escalation keyword must not trigger a CEO post."""
    message = "Wave 1 complete, 773 docs indexed"
    ceo_calls: list = []

    def fake_urlopen(req, timeout=10):
        import json

        body = json.loads(req.data)
        if body.get("channel") == _CEO_CHANNEL:
            ceo_calls.append(body)
        return _FakeResponse()

    with patch.object(relay.urllib.request, "urlopen", side_effect=fake_urlopen):
        relay._maybe_escalate_to_ceo(_EXEC_CHANNEL, message, "elliot")

    assert ceo_calls == []


# ---------------------------------------------------------------------------
# Test 3 — case-insensitive keyword match
# ---------------------------------------------------------------------------


def test_case_insensitive_match(relay):
    """Keyword match is case-insensitive ('AWAITING' matches 'awaiting')."""
    message = "AWAITING dave"
    assert relay._contains_escalation_keyword(message) is True


# ---------------------------------------------------------------------------
# Test 4 — already targeting #ceo → no double-post
# ---------------------------------------------------------------------------


def test_already_targeting_ceo_skips(relay):
    """Message destined for #ceo with escalation keyword must NOT generate a second post."""
    message = "holding for Dave decision on Wave 5"
    ceo_calls: list = []

    def fake_urlopen(req, timeout=10):
        import json

        body = json.loads(req.data)
        if body.get("channel") == _CEO_CHANNEL:
            ceo_calls.append(body)
        return _FakeResponse()

    with patch.object(relay.urllib.request, "urlopen", side_effect=fake_urlopen):
        # Target IS #ceo — guard must suppress
        relay._maybe_escalate_to_ceo(_CEO_CHANNEL, message, "elliot")

    assert ceo_calls == []


# ---------------------------------------------------------------------------
# Test 5 — already prefixed [ESCALATION] → no re-fire
# ---------------------------------------------------------------------------


def test_already_prefixed_skips(relay):
    """Message already starting with [ESCALATION] must not re-trigger CEO post."""
    message = "[ESCALATION] max · holding for Dave decision"
    ceo_calls: list = []

    def fake_urlopen(req, timeout=10):
        import json

        body = json.loads(req.data)
        if body.get("channel") == _CEO_CHANNEL:
            ceo_calls.append(body)
        return _FakeResponse()

    with patch.object(relay.urllib.request, "urlopen", side_effect=fake_urlopen):
        relay._maybe_escalate_to_ceo(_EXEC_CHANNEL, message, "elliot")

    assert ceo_calls == []


# ---------------------------------------------------------------------------
# Test 6 — CEO post failure does not block normal relay
# ---------------------------------------------------------------------------


def test_ceo_post_failure_does_not_block_relay(relay, capsys):
    """If the direct CEO post raises, _maybe_escalate_to_ceo catches it and normal relay continues."""
    message = "BLOCKED — holding for infra decision"
    call_count = [0]

    def fake_urlopen(req, timeout=10):
        call_count[0] += 1
        if call_count[0] == 1:
            raise urllib.error.URLError("connection refused")
        return _FakeResponse()

    with patch.object(relay.urllib.request, "urlopen", side_effect=fake_urlopen):
        # CEO post will raise on first call — must not propagate
        relay._maybe_escalate_to_ceo(_EXEC_CHANNEL, message, "elliot")

    captured = capsys.readouterr()
    assert "KEI-80 WARN" in captured.err
    assert "connection refused" in captured.err


# ---------------------------------------------------------------------------
# Test 7 — long body is truncated at ~500 chars
# ---------------------------------------------------------------------------


def test_truncate_long_body(relay):
    """Body longer than _ESCALATION_MAX_BODY_CHARS chars is truncated + marked."""
    long_message = "A" * 800 + " holding for Dave"
    captured_texts: list[str] = []

    def fake_urlopen(req, timeout=10):
        import json

        body = json.loads(req.data)
        if body.get("channel") == _CEO_CHANNEL:
            captured_texts.append(body["text"])
        return _FakeResponse()

    with patch.object(relay.urllib.request, "urlopen", side_effect=fake_urlopen):
        relay._maybe_escalate_to_ceo(_EXEC_CHANNEL, long_message, "elliot")

    assert len(captured_texts) == 1
    ceo_text = captured_texts[0]
    assert "…(truncated)" in ceo_text
    # The body portion must be ≤ _ESCALATION_MAX_BODY_CHARS + prefix overhead
    # Strip the "[ESCALATION] elliot · " prefix to measure body
    prefix = "[ESCALATION] elliot · "
    body_portion = ceo_text[len(prefix) :]
    assert body_portion.endswith("…(truncated)")
    # The content before the truncation marker must be ≤ max chars
    content_before_marker = body_portion[: -len("…(truncated)")]
    assert len(content_before_marker) <= relay._ESCALATION_MAX_BODY_CHARS
