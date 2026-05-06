"""
P5 — Tests for src/integrations/anthropic_rate_limit.py.

Pure mocks — never touches the real Anthropic API. Confirms:
  - _snapshot_from_headers parses each known counter
  - RateLimitSnapshot.headroom_for picks the most-restrictive signal
  - check_rate_limits caches per-model for PROBE_TTL_SECONDS
  - check_rate_limits FAILS OPEN on probe failure (no key, HTTP error)
  - check_rate_limits FAILS OPEN on invalid args
  - reset_cache clears the snapshot store
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from src.integrations import anthropic_rate_limit as arl

# ─── header parsing ────────────────────────────────────────────────────────


def test_snapshot_from_headers_parses_known_counters():
    headers = {
        "anthropic-ratelimit-requests-remaining": "42",
        "anthropic-ratelimit-tokens-remaining": "10000",
        "anthropic-ratelimit-input-tokens-remaining": "8000",
        "anthropic-ratelimit-output-tokens-remaining": "2000",
        "anthropic-ratelimit-requests-reset": "2026-04-26T10:00:00Z",
        "anthropic-ratelimit-tokens-reset": "2026-04-26T10:01:00Z",
    }
    snap = arl._snapshot_from_headers("claude-haiku-4-5", headers)
    assert snap.model == "claude-haiku-4-5"
    assert snap.requests_remaining == 42
    assert snap.tokens_remaining == 10_000
    assert snap.input_tokens_remaining == 8_000
    assert snap.output_tokens_remaining == 2_000
    assert snap.requests_reset_iso == "2026-04-26T10:00:00Z"


def test_snapshot_handles_missing_or_empty_headers():
    snap = arl._snapshot_from_headers("m", {})
    assert snap.requests_remaining is None
    assert snap.tokens_remaining is None
    assert snap.input_tokens_remaining is None
    assert snap.output_tokens_remaining is None


def test_snapshot_handles_non_integer_strings():
    snap = arl._snapshot_from_headers(
        "m",
        {
            "anthropic-ratelimit-tokens-remaining": "not-a-number",
        },
    )
    assert snap.tokens_remaining is None


# ─── headroom_for ──────────────────────────────────────────────────────────


def _snap(**kw):
    defaults = {
        "model": "m",
        "requests_remaining": 100,
        "tokens_remaining": 100_000,
        "input_tokens_remaining": 80_000,
        "output_tokens_remaining": 20_000,
        "requests_reset_iso": None,
        "tokens_reset_iso": None,
        "captured_at": 0.0,
    }
    defaults.update(kw)
    return arl.RateLimitSnapshot(**defaults)


def test_headroom_zero_requests_blocks():
    ok, reason = _snap(requests_remaining=0).headroom_for(1_000)
    assert ok is False
    assert "requests_remaining" in reason


def test_headroom_input_tokens_below_required_blocks():
    ok, reason = _snap(input_tokens_remaining=500).headroom_for(1_000)
    assert ok is False
    assert "input_tokens_remaining" in reason


def test_headroom_output_tokens_below_required_blocks():
    ok, reason = _snap(output_tokens_remaining=500).headroom_for(1_000)
    assert ok is False
    assert "output_tokens_remaining" in reason


def test_headroom_total_tokens_used_when_per_direction_absent():
    ok, reason = _snap(
        input_tokens_remaining=None,
        output_tokens_remaining=None,
        tokens_remaining=500,
    ).headroom_for(1_000)
    assert ok is False
    assert "tokens_remaining" in reason


def test_headroom_passes_when_all_above_required():
    ok, reason = _snap().headroom_for(1_000)
    assert ok is True
    assert reason == "ok"


def test_headroom_with_only_unknown_signals_passes():
    """All counters None → no evidence of insufficient headroom → True."""
    ok, _ = _snap(
        requests_remaining=None,
        tokens_remaining=None,
        input_tokens_remaining=None,
        output_tokens_remaining=None,
    ).headroom_for(1_000)
    assert ok is True


# ─── check_rate_limits — caching + fail-open ───────────────────────────────


@pytest.fixture(autouse=True)
def _reset_cache_between_tests():
    arl.reset_cache()
    yield
    arl.reset_cache()


def test_check_rate_limits_returns_true_when_no_api_key(monkeypatch):
    monkeypatch.setattr(arl.settings, "anthropic_api_key", "")
    assert arl.check_rate_limits("claude-haiku-4-5", 1_000) is True


def test_check_rate_limits_returns_true_on_http_error(monkeypatch):
    monkeypatch.setattr(arl.settings, "anthropic_api_key", "test-key")

    class _BoomClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            raise httpx.HTTPError("network down")

    monkeypatch.setattr(arl.httpx, "Client", _BoomClient)
    assert arl.check_rate_limits("claude-haiku-4-5", 1_000) is True


def _fake_response(headers: dict, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.text = "{}"
    r.headers = headers
    return r


def _client_with(response):
    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return response

    return _Client


def test_check_rate_limits_returns_false_when_below_required(monkeypatch):
    monkeypatch.setattr(arl.settings, "anthropic_api_key", "test-key")
    resp = _fake_response(
        {
            "anthropic-ratelimit-requests-remaining": "100",
            "anthropic-ratelimit-input-tokens-remaining": "500",
            "anthropic-ratelimit-output-tokens-remaining": "500",
        }
    )
    monkeypatch.setattr(arl.httpx, "Client", _client_with(resp))
    assert arl.check_rate_limits("m", 1_000) is False


def test_check_rate_limits_returns_true_when_above_required(monkeypatch):
    monkeypatch.setattr(arl.settings, "anthropic_api_key", "test-key")
    resp = _fake_response(
        {
            "anthropic-ratelimit-requests-remaining": "100",
            "anthropic-ratelimit-input-tokens-remaining": "9000",
            "anthropic-ratelimit-output-tokens-remaining": "9000",
        }
    )
    monkeypatch.setattr(arl.httpx, "Client", _client_with(resp))
    assert arl.check_rate_limits("m", 1_000) is True


def test_check_rate_limits_caches_per_model(monkeypatch):
    """Second call within TTL should NOT probe the API again."""
    monkeypatch.setattr(arl.settings, "anthropic_api_key", "test-key")
    calls = {"n": 0}

    class _CountingClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            calls["n"] += 1
            return _fake_response(
                {
                    "anthropic-ratelimit-requests-remaining": "10",
                    "anthropic-ratelimit-input-tokens-remaining": "5000",
                }
            )

    monkeypatch.setattr(arl.httpx, "Client", _CountingClient)
    arl.check_rate_limits("m", 1_000)
    arl.check_rate_limits("m", 500)
    assert calls["n"] == 1  # second call hit the cache
    # cache is per-model — different model triggers a new probe
    arl.check_rate_limits("other-model", 1_000)
    assert calls["n"] == 2


# ─── invalid args ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_model", [None, "", 123, []])
def test_invalid_model_fails_open(bad_model):
    assert arl.check_rate_limits(bad_model, 1_000) is True


@pytest.mark.parametrize("bad_required", [None, -1, "x", 1.5])
def test_invalid_required_tokens_fails_open(bad_required):
    assert arl.check_rate_limits("m", bad_required) is True


# ─── reset_cache ───────────────────────────────────────────────────────────


def test_reset_cache_clears_snapshots(monkeypatch):
    monkeypatch.setattr(arl.settings, "anthropic_api_key", "test-key")
    resp = _fake_response({"anthropic-ratelimit-requests-remaining": "100"})
    monkeypatch.setattr(arl.httpx, "Client", _client_with(resp))
    arl.check_rate_limits("m", 100)
    assert arl.cached_snapshot("m") is not None
    arl.reset_cache()
    assert arl.cached_snapshot("m") is None
