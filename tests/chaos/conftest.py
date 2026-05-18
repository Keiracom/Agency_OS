"""KEI-132 — pytest fixtures + helpers for the chaos harness.

Two-layer timeout protection on every chaos test:

  1. Per-test default `@pytest.mark.timeout(10)` — pytest-timeout backstop so
     a runaway thread can't hang CI. Overridable per-test.
  2. Scenario-level helpers (`assert_completes_within`, `simulate_stall`)
     that raise specific exceptions when the chaos behaviour fires —
     callers assert on those directly so test failures are diagnostic.

CI runs `pytest tests/chaos -v --timeout=10` with NO `|| true` mask.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TypeVar

import pytest

T = TypeVar("T")


def pytest_configure(config: pytest.Config) -> None:
    """Register chaos-specific markers so `pytest --strict-markers` doesn't reject them."""
    config.addinivalue_line(
        "markers",
        "chaos_db: requires a reachable DATABASE_URL (real psycopg connection). "
        "Skipped when env var unset.",
    )
    config.addinivalue_line(
        "markers",
        "chaos_redis: requires a reachable REDIS_URL. Skipped when env var unset.",
    )


@pytest.fixture(autouse=True)
def _chaos_default_timeout(request: pytest.FixtureRequest) -> None:
    """Apply a 10s pytest-timeout to every chaos test that doesn't set its own.

    pytest-timeout markers stack; explicit `@pytest.mark.timeout(N)` on a test
    wins. This fixture is a safety net for tests that forget to mark.
    """
    if not request.node.get_closest_marker("timeout"):
        request.node.add_marker(pytest.mark.timeout(10))


class ChaosTimeoutError(AssertionError):
    """Raised when `assert_completes_within(...)` exceeds its budget.

    Distinct from `TimeoutError` so chaos-framework failures are
    distinguishable from real network/IO timeouts in test output.
    """


def assert_completes_within(seconds: float, op: Callable[[], T]) -> T:
    """Run `op()` and assert it returns within `seconds`. Raises
    ChaosTimeoutError on overrun. Returns op's return value on success.

    Synchronous wall-clock measurement — fine for the deterministic
    scenarios we run in CI. For real async work use the real op + the
    pytest-timeout marker instead.
    """
    start = time.monotonic()
    result = op()
    elapsed = time.monotonic() - start
    if elapsed > seconds:
        raise ChaosTimeoutError(f"chaos: operation took {elapsed:.2f}s, exceeded budget {seconds}s")
    return result


def simulate_stall(seconds: float) -> None:
    """Mock-stall helper for the DB / network / IO scenarios. Sleeps
    deterministically. Use inside an `assert_completes_within(...)` wrapper
    to validate the scenario detects stalls correctly."""
    time.sleep(seconds)


def db_available() -> bool:
    """True iff DATABASE_URL (or SUPABASE_DB_URL) is set AND is a psycopg-
    parseable DSN (starts with `postgresql://` or `postgres://`). Filters out
    SQLAlchemy-style `postgresql+asyncpg://` DSNs that psycopg can't parse —
    those are valid in other parts of the codebase but unusable for the real
    psycopg.connect() path the chaos_db tests exercise."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or ""
    return dsn.startswith(("postgresql://", "postgres://"))


__all__ = [
    "ChaosTimeoutError",
    "assert_completes_within",
    "db_available",
    "simulate_stall",
]
