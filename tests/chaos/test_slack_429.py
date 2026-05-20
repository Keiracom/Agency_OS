"""KEI-133 — Slack API 429 rate-limit chaos scenario.

Slack returns HTTP 429 with a Retry-After header when an app exceeds its
posting budget. The contract: callers must respect Retry-After, back off,
and retry — NOT hammer the endpoint or drop the message silently.

`feedback_socket_mode_single_connection` and the existing slack_relay
exponential-backoff path (PR #847 KEI-40) anchor this contract.
"""

from __future__ import annotations

import pytest


class _MockSlackResponse:
    """Minimal Slack response shape — status_code + headers + ok flag."""

    def __init__(self, status: int, retry_after: str | None = None) -> None:
        self.status_code = status
        self.headers = {"Retry-After": retry_after} if retry_after else {}
        self.ok = status == 200


def _slack_post_with_backoff(
    initial_response: _MockSlackResponse,
    next_response: _MockSlackResponse,
    sleep_fn,
) -> tuple[bool, list[float]]:
    """Encodes the canonical 429-handling contract:
    1. On 429, read Retry-After (default 1s if absent).
    2. Sleep for that interval.
    3. Retry once.
    Returns (final_ok, [slept_seconds]).
    """
    sleeps: list[float] = []
    if initial_response.status_code == 429:
        retry_after_s = float(initial_response.headers.get("Retry-After", "1"))
        sleep_fn(retry_after_s)
        sleeps.append(retry_after_s)
        return next_response.ok, sleeps
    return initial_response.ok, sleeps


@pytest.mark.timeout(10)
def test_429_with_retry_after_header_backs_off_then_succeeds() -> None:
    """Slack 429 with Retry-After: 2 → sleep 2s → retry → 200 OK."""
    sleeps_captured: list[float] = []

    def fake_sleep(s: float) -> None:
        sleeps_captured.append(s)

    initial = _MockSlackResponse(status=429, retry_after="2")
    retry = _MockSlackResponse(status=200)
    ok, slept = _slack_post_with_backoff(initial, retry, fake_sleep)

    assert ok is True
    assert slept == [2.0]
    assert sleeps_captured == [2.0]


@pytest.mark.timeout(10)
def test_429_without_retry_after_falls_back_to_one_second() -> None:
    """Missing Retry-After: caller defaults to 1s instead of zero — never
    hot-spin the API."""
    sleeps_captured: list[float] = []

    initial = _MockSlackResponse(status=429, retry_after=None)
    retry = _MockSlackResponse(status=200)
    ok, slept = _slack_post_with_backoff(initial, retry, sleeps_captured.append)

    assert ok is True
    assert slept == [1.0]
    assert sleeps_captured == [1.0]


@pytest.mark.timeout(10)
def test_consecutive_429_does_not_drop_message_silently() -> None:
    """If the retry also returns 429, the function reports failure (ok=False)
    — caller is responsible for next-level handling (queue, alert, etc.).
    Never returns True on an un-acked Slack message."""
    initial = _MockSlackResponse(status=429, retry_after="1")
    retry = _MockSlackResponse(status=429, retry_after="2")
    ok, slept = _slack_post_with_backoff(initial, retry, lambda _: None)

    assert ok is False
    assert slept == [1.0]
