"""
Tests for src/integrations/circuit_breaker.py

Covers:
  1. Circuit opens after N failures
  2. Open circuit rejects calls (raises CircuitOpenError)
  3. Circuit transitions to HALF_OPEN after recovery timeout
  4. Circuit closes after successful half-open call
  5. Circuit reopens after failed half-open call
  6. Decorator works on async functions
"""

from __future__ import annotations

import asyncio
import time

import pytest

from src.integrations.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker,
    reset_circuit_breaker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fail():
    raise ValueError("simulated failure")


async def _ok():
    return "ok"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_cb(request):
    """Yield a fresh CircuitBreaker for each test; clean up registry after."""
    provider = f"test_{request.node.name}"
    cb = CircuitBreaker(
        provider=provider,
        failure_threshold=3,
        recovery_timeout_seconds=0.2,  # short for tests
        half_open_max_calls=1,
    )
    yield cb, provider
    reset_circuit_breaker(provider)


# ---------------------------------------------------------------------------
# Test 1 — circuit opens after N failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_circuit_opens_after_n_failures(isolated_cb):
    cb, _ = isolated_cb
    assert cb.state == CircuitState.CLOSED

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(_fail())

    assert cb.state == CircuitState.OPEN
    assert cb.failure_count >= 3


# ---------------------------------------------------------------------------
# Test 2 — open circuit rejects calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_circuit_rejects_calls(isolated_cb):
    cb, _ = isolated_cb

    # Drive open
    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(_fail())

    assert cb.state == CircuitState.OPEN

    with pytest.raises(CircuitOpenError) as exc_info:
        await cb.call(_ok())

    assert "OPEN" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 3 — OPEN -> HALF_OPEN after recovery timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transitions_to_half_open_after_timeout(isolated_cb):
    cb, _ = isolated_cb

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(_fail())

    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout (0.2s in fixture)
    await asyncio.sleep(0.25)

    # Next call should be allowed (HALF_OPEN probe)
    result = await cb.call(_ok())
    assert result == "ok"
    assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Test 4 — circuit closes after successful half-open call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_closes_after_successful_half_open(isolated_cb):
    cb, _ = isolated_cb

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(_fail())

    await asyncio.sleep(0.25)  # let recovery timeout expire

    # Probe succeeds -> should close
    await cb.call(_ok())
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


# ---------------------------------------------------------------------------
# Test 5 — circuit reopens after failed half-open call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reopens_after_failed_half_open(isolated_cb):
    cb, _ = isolated_cb

    for _ in range(3):
        with pytest.raises(ValueError):
            await cb.call(_fail())

    await asyncio.sleep(0.25)  # recovery timeout expires -> HALF_OPEN probe allowed

    # Probe fails -> should reopen
    with pytest.raises(ValueError):
        await cb.call(_fail())

    assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Test 6 — decorator works on async functions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decorator_wraps_async_function():
    provider = "decorator_test"
    reset_circuit_breaker(provider)

    call_count = 0

    @circuit_breaker(provider, failure_threshold=2, recovery_timeout=0.2)
    async def guarded():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    # Two failures should open the circuit
    with pytest.raises(RuntimeError):
        await guarded()
    with pytest.raises(RuntimeError):
        await guarded()

    cb = get_circuit_breaker(provider)
    assert cb.state == CircuitState.OPEN

    # Third call is rejected by circuit, not the underlying function
    # Use try/except so pytest doesn't GC an unawaited coroutine
    try:
        await guarded()
        pytest.fail("Expected CircuitOpenError")
    except CircuitOpenError:
        pass

    assert call_count == 2  # function body only ran twice, not three times

    reset_circuit_breaker(provider)
