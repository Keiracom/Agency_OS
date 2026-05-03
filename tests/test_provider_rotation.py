"""
Tests: _with_retry helper in email_waterfall.py

Covers:
- Transient error (TimeoutException) triggers 1 retry before returning None
- Non-transient error (ValueError) does NOT retry
- Successful result on retry is returned
- None return (not found — no exception) passes through without retry
"""

from __future__ import annotations

import pytest

from src.pipeline.email_waterfall import TRANSIENT_EXCEPTIONS, _with_retry

# ── Helpers ───────────────────────────────────────────────────────────────────


def _first_transient_exception():
    """Build a transient exception instance for testing."""
    # Use ConnectionError which is always in TRANSIENT_EXCEPTIONS
    return ConnectionError("simulated connection error")


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestWithRetryTransient:
    """Transient error should retry once, then return None."""

    @pytest.mark.asyncio
    async def test_transient_retries_once_then_returns_none(self):
        call_count = 0

        async def always_transient():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("timeout-like error")

        result = await _with_retry(always_transient, retries=1, backoff=0.0, label="test")

        assert result is None
        assert call_count == 2  # initial + 1 retry

    @pytest.mark.asyncio
    async def test_transient_success_on_retry_is_returned(self):
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("first call fails")
            return "found_email@example.com"

        result = await _with_retry(fail_then_succeed, retries=1, backoff=0.0, label="test")

        assert result == "found_email@example.com"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_transient_with_httpx_timeout(self):
        """TimeoutException (httpx) should be treated as transient if httpx available."""
        try:
            from httpx import TimeoutException
        except ImportError:
            pytest.skip("httpx not installed")

        call_count = 0

        async def httpx_timeout():
            nonlocal call_count
            call_count += 1
            raise TimeoutException("request timed out")

        result = await _with_retry(httpx_timeout, retries=1, backoff=0.0, label="hunter-email")

        assert result is None
        assert call_count == 2  # retried once


class TestWithRetryNonTransient:
    """Non-transient errors should NOT retry."""

    @pytest.mark.asyncio
    async def test_non_transient_does_not_retry(self):
        call_count = 0

        async def always_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad api key")

        result = await _with_retry(always_value_error, retries=1, backoff=0.0, label="test")

        assert result is None
        assert call_count == 1  # no retry

    @pytest.mark.asyncio
    async def test_runtime_error_does_not_retry(self):
        call_count = 0

        async def runtime_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("credit exhausted")

        result = await _with_retry(runtime_fail, retries=1, backoff=0.0, label="leadmagic-email")

        assert result is None
        assert call_count == 1  # no retry


class TestWithRetryNotFound:
    """Provider returns None (not found) — no exception, no retry needed."""

    @pytest.mark.asyncio
    async def test_none_return_passes_through_without_retry(self):
        call_count = 0

        async def not_found():
            nonlocal call_count
            call_count += 1
            return None

        result = await _with_retry(not_found, retries=1, backoff=0.0, label="test")

        assert result is None
        assert call_count == 1  # no retry — None is not an exception

    @pytest.mark.asyncio
    async def test_falsy_value_passes_through(self):
        """Empty string, False, 0 — not an error, no retry."""
        call_count = 0

        async def returns_empty():
            nonlocal call_count
            call_count += 1
            return ""

        result = await _with_retry(returns_empty, retries=1, backoff=0.0, label="test")

        assert result == ""
        assert call_count == 1


class TestTransientExceptionsTuple:
    """TRANSIENT_EXCEPTIONS must include ConnectionError and OSError at minimum."""

    def test_connection_error_is_transient(self):
        assert issubclass(ConnectionError, TRANSIENT_EXCEPTIONS)

    def test_os_error_is_transient(self):
        assert issubclass(OSError, TRANSIENT_EXCEPTIONS)

    def test_value_error_is_not_transient(self):
        assert not issubclass(ValueError, TRANSIENT_EXCEPTIONS)

    def test_runtime_error_is_not_transient(self):
        assert not issubclass(RuntimeError, TRANSIENT_EXCEPTIONS)
