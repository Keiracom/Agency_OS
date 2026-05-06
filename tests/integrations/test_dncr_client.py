"""
Tests for DNCRClient — 12 cases covering happy path, degraded modes, cache, and normalisation.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from integrations.dncr_client import DNCRClient, DNCRResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(
    status_code: int, json_body: dict | None = None, raise_exc: Exception | None = None
) -> MagicMock:
    """Build a mock httpx.Client that returns a controlled response."""
    mock_client = MagicMock(spec=httpx.Client)
    if raise_exc:
        mock_client.get.side_effect = raise_exc
    else:
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        if json_body is not None:
            mock_resp.json.return_value = json_body
        else:
            mock_resp.json.side_effect = ValueError("no body")
        mock_client.get.return_value = mock_resp
    return mock_client


_BASE_TIME = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _fixed_now(t: datetime = _BASE_TIME):
    return lambda: t


# ---------------------------------------------------------------------------
# 1. Happy path — registered=True
# ---------------------------------------------------------------------------


class TestHappyPathRegistered:
    def test_registered_true(self):
        mock_http = _mock_response(
            200, {"registered": True, "registered_at": "2025-01-01T00:00:00Z"}
        )
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000000")
        assert result.registered is True
        assert result.registered_at == datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# 2. Happy path — registered=False
# ---------------------------------------------------------------------------


class TestHappyPathNotRegistered:
    def test_registered_false(self):
        mock_http = _mock_response(200, {"registered": False})
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000001")
        assert result.registered is False
        assert result.status == "ok"


# ---------------------------------------------------------------------------
# 3. Missing API key — degraded:no_api_key, no HTTP call made
# ---------------------------------------------------------------------------


class TestMissingApiKey:
    def test_no_api_key_returns_degraded(self, monkeypatch):
        monkeypatch.delenv("DNCR_API_KEY", raising=False)
        mock_http = _mock_response(200, {"registered": True})
        client = DNCRClient(api_key=None, http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000002")
        assert result.registered is None
        assert result.status == "degraded:no_api_key"
        mock_http.get.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Network timeout — degraded:network
# ---------------------------------------------------------------------------


class TestNetworkTimeout:
    def test_timeout_returns_degraded(self):
        mock_http = _mock_response(
            0,
            raise_exc=httpx.TimeoutException("timed out"),
        )
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000003")
        assert result.status == "degraded:network"
        assert result.registered is None


# ---------------------------------------------------------------------------
# 5. HTTP 500 — degraded:network
# ---------------------------------------------------------------------------


class TestHTTP500:
    def test_500_returns_degraded_network(self):
        mock_http = _mock_response(500)
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000004")
        assert result.status == "degraded:network"


# ---------------------------------------------------------------------------
# 6. HTTP 429 — degraded:rate_limited
# ---------------------------------------------------------------------------


class TestHTTP429:
    def test_rate_limited(self):
        mock_http = _mock_response(429)
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000005")
        assert result.status == "degraded:rate_limited"
        assert result.registered is None


# ---------------------------------------------------------------------------
# 7. Invalid JSON — degraded:parse
# ---------------------------------------------------------------------------


class TestInvalidJSON:
    def test_bad_json_returns_degraded_parse(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("bad json")
        mock_http = MagicMock(spec=httpx.Client)
        mock_http.get.return_value = mock_resp
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("+61400000006")
        assert result.status == "degraded:parse"


# ---------------------------------------------------------------------------
# 8. Cache hit — HTTP client called once
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_second_call_uses_cache(self):
        mock_http = _mock_response(200, {"registered": True, "registered_at": None})
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        r1 = client.lookup("+61400000007")
        r2 = client.lookup("+61400000007")
        assert r1.status == "ok"
        assert r2.status == "ok"
        assert mock_http.get.call_count == 1


# ---------------------------------------------------------------------------
# 9. Cache expiry — second call re-fetches
# ---------------------------------------------------------------------------


class TestCacheExpiry:
    def test_expired_cache_refetches(self):
        call_count = {"n": 0}
        base = _BASE_TIME

        def advancing_now():
            # First call at base, second call at base + 25 hours (past 24hr TTL)
            t = base if call_count["n"] < 2 else base + timedelta(hours=25)
            call_count["n"] += 1
            return t

        mock_http = _mock_response(200, {"registered": False})
        client = DNCRClient(
            api_key="test-key", http_client=mock_http, cache_ttl_hours=24, now_fn=advancing_now
        )

        client.lookup("+61400000008")  # populates cache; now_fn returns base
        # Advance internal clock past TTL for cache check
        # Override now_fn to return expired time
        client._now = lambda: base + timedelta(hours=25)
        client.lookup("+61400000008")  # cache miss — should re-fetch

        assert mock_http.get.call_count == 2


# ---------------------------------------------------------------------------
# 10. Degraded result NOT cached — second call retries
# ---------------------------------------------------------------------------


class TestDegradedNotCached:
    def test_degraded_not_cached_retry_succeeds(self):
        mock_http = MagicMock(spec=httpx.Client)
        fail_resp = MagicMock()
        fail_resp.status_code = 500

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"registered": False}

        mock_http.get.side_effect = [fail_resp, ok_resp]

        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        r1 = client.lookup("+61400000009")
        r2 = client.lookup("+61400000009")

        assert r1.status == "degraded:network"
        assert r2.status == "ok"
        assert mock_http.get.call_count == 2


# ---------------------------------------------------------------------------
# 11. Phone normalisation — variants map to same cache entry
# ---------------------------------------------------------------------------


class TestPhoneNormalisation:
    def test_variants_share_cache_entry(self):
        mock_http = _mock_response(200, {"registered": True})
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())

        client.lookup("+61 400 000 000")
        client.lookup("+61400000000")
        client.lookup("+61-400-000-000")

        # All three normalise to "+61400000000" — only one HTTP call
        assert mock_http.get.call_count == 1


# ---------------------------------------------------------------------------
# 12. Never raises — pathological inputs return DNCRResult
# ---------------------------------------------------------------------------


class TestNeverRaises:
    def test_empty_string_no_raise(self):
        mock_http = _mock_response(200, {"registered": False})
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("")
        assert isinstance(result, DNCRResult)

    def test_garbage_input_no_raise(self):
        mock_http = _mock_response(200, {"registered": False})
        client = DNCRClient(api_key="test-key", http_client=mock_http, now_fn=_fixed_now())
        result = client.lookup("not-a-phone-!!!!")
        assert isinstance(result, DNCRResult)
