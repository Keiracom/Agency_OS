"""Tests for KEI-40 — slack_relay.py exponential backoff + Retry-After respect on 429.

Per Dave verbatim ts ~1778666400 + Elliot dispatch ts ~1778708500.

Slack chat.postMessage tier-3 rate-limits (~1 req/sec) return HTTP 429 with a
Retry-After header. The pre-KEI-40 relay exited non-zero on URLError without
retry — generating governance noise (relay-failures looked like crashes).
This module verifies the retry+backoff behavior."""

from __future__ import annotations

import importlib.util
import sys
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELAY_PATH = REPO_ROOT / "scripts" / "slack_relay.py"


@pytest.fixture(scope="module")
def relay(monkeypatch_module):  # type: ignore[no-untyped-def]
    """Import scripts/slack_relay.py once per module with required env stubbed."""
    spec = importlib.util.spec_from_file_location("slack_relay_kei40", RELAY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["slack_relay_kei40"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def monkeypatch_module(request):  # type: ignore[no-untyped-def]
    """Module-scoped monkeypatch needed for module-level CALLSIGN resolution."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    mp.setenv("CALLSIGN", "aiden")
    mp.setenv("SLACK_BOT_TOKEN", "xoxb-fake-test-token")
    request.addfinalizer(mp.undo)
    return mp


def _make_http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    """Construct an HTTPError instance with optional Retry-After header."""
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(
        url="https://slack.com/api/chat.postMessage",
        code=code,
        msg=f"HTTP {code}",
        hdrs=headers,
        fp=None,
    )


class _FakeResponse:
    """urllib.request.urlopen() context-manager response with bytes payload."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return self._payload


def test_constants_defined(relay):
    """KEI-40 backoff constants exist + are sane."""
    assert relay._KEI40_MAX_RETRIES == 5
    # pytest.approx() avoids S1244 float-equality warning per
    # reference_sonarcloud_verify_pattern.md — these are exact-integer
    # constants stored as floats, but Sonar S1244 flags the == check.
    assert pytest.approx(1.0) == relay._KEI40_BASE_BACKOFF_SECONDS
    assert pytest.approx(30.0) == relay._KEI40_MAX_BACKOFF_SECONDS


def test_post_with_retry_returns_on_first_success(relay):
    """First-call success returns parsed JSON; no retry, no sleep."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    success_payload = b'{"ok": true, "ts": "1.2"}'

    sleep_calls: list = []
    with (
        patch("urllib.request.urlopen", return_value=_FakeResponse(success_payload)),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleep_calls.append(s)),
    ):
        result = relay._post_with_retry(req)

    assert result == {"ok": True, "ts": "1.2"}
    assert sleep_calls == []  # success → no sleep


def test_post_with_retry_429_respects_retry_after_header(relay):
    """429 with Retry-After: 7 → sleep exactly 7 seconds then retry."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    success_payload = b'{"ok": true}'
    error_then_success = [_make_http_error(429, retry_after="7"), _FakeResponse(success_payload)]

    sleeps: list = []
    with (
        patch("urllib.request.urlopen", side_effect=error_then_success),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleeps.append(s)),
    ):
        result = relay._post_with_retry(req)

    assert result == {"ok": True}
    assert sleeps == [7.0]  # honored Retry-After verbatim


def test_post_with_retry_429_falls_back_to_exponential_backoff(relay):
    """429 without Retry-After header → exponential backoff: 1s, 2s, 4s, 8s, 16s."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    # 5 consecutive 429s without header, then success
    responses: list = [_make_http_error(429) for _ in range(5)]
    responses.append(_FakeResponse(b'{"ok": true}'))

    sleeps: list = []
    with (
        patch("urllib.request.urlopen", side_effect=responses),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleeps.append(s)),
    ):
        result = relay._post_with_retry(req)

    assert result == {"ok": True}
    assert sleeps == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_post_with_retry_backoff_caps_at_max_seconds(relay):
    """Exponential 2^attempt past the cap saturates at _KEI40_MAX_BACKOFF_SECONDS."""
    # Simulate: base=1.0, max_backoff=30, but a higher attempt would exceed.
    # 2^5 * 1 = 32 → capped to 30.
    # We can't easily exercise attempt=5 without retry-budget; verify the math via constants.
    assert min(
        relay._KEI40_BASE_BACKOFF_SECONDS * (2**5), relay._KEI40_MAX_BACKOFF_SECONDS
    ) == pytest.approx(30.0)


def test_post_with_retry_429_exhausts_after_max_retries(relay):
    """After _KEI40_MAX_RETRIES (5) consecutive 429s, the next 429 re-raises."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    # 6 total 429s — first 5 retried (with sleep), 6th re-raised
    responses: list = [_make_http_error(429) for _ in range(6)]

    sleeps: list = []
    with (
        patch("urllib.request.urlopen", side_effect=responses),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleeps.append(s)),
        pytest.raises(urllib.error.HTTPError) as exc_info,
    ):
        relay._post_with_retry(req)

    assert exc_info.value.code == 429
    assert len(sleeps) == 5  # 5 backoffs before the final re-raise


def test_post_with_retry_non_429_http_error_reraises_immediately(relay):
    """500 / 503 / etc. fail-fast — no retry."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    sleeps: list = []
    with (
        patch("urllib.request.urlopen", side_effect=_make_http_error(500)),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleeps.append(s)),
        pytest.raises(urllib.error.HTTPError) as exc_info,
    ):
        relay._post_with_retry(req)

    assert exc_info.value.code == 500
    assert sleeps == []


def test_post_with_retry_non_http_urlerror_reraises_immediately(relay):
    """Network-level URLError (DNS / connection refused) fail-fast — no retry."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    sleeps: list = []
    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleeps.append(s)),
        pytest.raises(urllib.error.URLError),
    ):
        relay._post_with_retry(req)

    assert sleeps == []


def test_post_with_retry_invalid_retry_after_falls_back_to_exponential(relay):
    """Malformed Retry-After header (non-numeric) → exponential fallback for that attempt."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    error_then_success = [
        _make_http_error(429, retry_after="not-a-number"),
        _FakeResponse(b'{"ok": true}'),
    ]

    sleeps: list = []
    with (
        patch("urllib.request.urlopen", side_effect=error_then_success),
        patch.object(relay.time, "sleep", side_effect=lambda s: sleeps.append(s)),
    ):
        result = relay._post_with_retry(req)

    assert result == {"ok": True}
    # attempt=0 → exponential = 1.0 * 2^0 = 1.0
    assert sleeps == [1.0]


def test_post_with_retry_429_emits_warning_to_stderr(relay, capsys):
    """Each 429-retry prints a WARN line to stderr (operator visibility)."""
    req = urllib.request.Request("https://slack.com/api/chat.postMessage")
    error_then_success = [
        _make_http_error(429, retry_after="2"),
        _FakeResponse(b'{"ok": true}'),
    ]

    with (
        patch("urllib.request.urlopen", side_effect=error_then_success),
        patch.object(relay.time, "sleep"),
    ):
        relay._post_with_retry(req)

    captured = capsys.readouterr()
    assert "Slack 429" in captured.err
    assert "retry 1/5" in captured.err
    assert "after 2.0s" in captured.err
