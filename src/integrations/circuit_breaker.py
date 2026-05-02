"""
FILE: src/integrations/circuit_breaker.py
PURPOSE: Reusable failure-based circuit breaker for external API providers.
         Three states: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (recovering).
         NOT a spend limiter — that is handled by src/integrations/anthropic.py.
PHASE: Integrations
DEPENDENCIES: None (stdlib only)
CONSUMERS: Any integration that wraps external HTTP calls.

Usage (decorator):
    @circuit_breaker("brightdata", failure_threshold=5, recovery_timeout=60)
    async def my_api_call(...):
        ...

Usage (instance):
    cb = get_circuit_breaker("leadmagic")
    async with cb:
        result = await api_call()
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State + Exception
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing — reject all calls
    HALF_OPEN = "half_open"  # Testing recovery — allow limited calls


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is OPEN and the call is rejected."""

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(f"Circuit OPEN for '{provider}'. Retry after {retry_after:.1f}s.")


# ---------------------------------------------------------------------------
# Core circuit breaker class
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """
    Async-safe three-state circuit breaker.

    State transitions:
        CLOSED  --[N failures]--> OPEN
        OPEN    --[timeout expires]--> HALF_OPEN
        HALF_OPEN --[success]--> CLOSED
        HALF_OPEN --[failure]--> OPEN
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # State helpers (all called under lock)
    # ------------------------------------------------------------------

    def _transition(self, new_state: CircuitState) -> None:
        old = self._state
        self._state = new_state
        logger.warning(
            "circuit_breaker state_transition provider=%s %s -> %s",
            self.provider,
            old.value,
            new_state.value,
        )
        if new_state == CircuitState.OPEN:
            self._opened_at = time.monotonic()
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._opened_at = None
            self._half_open_calls = 0

    def _seconds_until_retry(self) -> float:
        if self._opened_at is None:
            return 0.0
        elapsed = time.monotonic() - self._opened_at
        return max(0.0, self.recovery_timeout_seconds - elapsed)

    async def _check_state(self) -> None:
        """
        Evaluate current state; may auto-transition OPEN -> HALF_OPEN.
        Raises CircuitOpenError if call must be rejected.
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                remaining = self._seconds_until_retry()
                if remaining > 0:
                    raise CircuitOpenError(self.provider, remaining)
                # Timeout expired — probe with a single call
                self._transition(CircuitState.HALF_OPEN)

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    # Another probe already in-flight — reject this one
                    raise CircuitOpenError(self.provider, self.recovery_timeout_seconds)
                self._half_open_calls += 1

    async def _record_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._transition(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def _record_failure(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._transition(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._transition(CircuitState.OPEN)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def call(self, coro: Any) -> Any:
        """
        Execute an awaitable through the circuit breaker.

        Usage:
            result = await cb.call(some_coroutine(...))
        """
        await self._check_state()
        try:
            result = await coro
            await self._record_success()
            return result
        except CircuitOpenError:
            raise  # Don't count our own rejections as failures
        except Exception:
            await self._record_failure()
            raise


# ---------------------------------------------------------------------------
# Per-provider registry
# ---------------------------------------------------------------------------

_registry: dict[str, CircuitBreaker] = {}
_registry_lock = asyncio.Lock()


def get_circuit_breaker(
    provider: str,
    failure_threshold: int = 5,
    recovery_timeout_seconds: float = 60.0,
    half_open_max_calls: int = 1,
) -> CircuitBreaker:
    """
    Return the existing CircuitBreaker for this provider, or create one.
    Parameters are only applied on first creation — subsequent calls return
    the same instance regardless of parameters passed.
    """
    if provider not in _registry:
        _registry[provider] = CircuitBreaker(
            provider=provider,
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            half_open_max_calls=half_open_max_calls,
        )
    return _registry[provider]


def reset_circuit_breaker(provider: str) -> None:
    """Remove a provider's circuit breaker from the registry (useful in tests)."""
    _registry.pop(provider, None)


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def circuit_breaker(
    provider: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    half_open_max_calls: int = 1,
) -> Callable:
    """
    Decorator that wraps an async function with a named circuit breaker.

    Example:
        @circuit_breaker("brightdata", failure_threshold=5, recovery_timeout=60)
        async def call_bright_data(...):
            ...
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cb = get_circuit_breaker(
                provider,
                failure_threshold=failure_threshold,
                recovery_timeout_seconds=recovery_timeout,
                half_open_max_calls=half_open_max_calls,
            )
            return await cb.call(fn(*args, **kwargs))

        return wrapper

    return decorator
