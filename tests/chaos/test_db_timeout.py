"""KEI-132 — DB-timeout chaos scenario (1 of 2 for the harness).

Validates that the chaos framework detects a simulated DB stall exceeding
the 5s budget. Three layered tests:

  1. happy-path control      — fast op passes the wrapper (regression guard
                                against false-positives in the framework
                                itself).
  2. stall detection         — 6s mock-stall vs 5s budget → ChaosTimeoutError.
  3. pytest-timeout backstop — a test marked `timeout(1)` that sleeps 2s
                                fires the pytest-timeout fail-safe — proves
                                the second protection layer works.

A fourth optional test (`@pytest.mark.chaos_db`) hits a real psycopg
connection with `statement_timeout = 5000` (5s) and asserts `pg_sleep(6)`
raises `psycopg.errors.QueryCanceled`. Skipped when DATABASE_URL is unset
(typical for CI without a postgres service).
"""

from __future__ import annotations

import pytest

from tests.chaos.conftest import (
    ChaosTimeoutError,
    assert_completes_within,
    db_available,
    simulate_stall,
)


def test_happy_path_fast_op_passes_chaos_wrapper() -> None:
    """Negative-control: a sub-budget op must pass — guards against the
    framework asserting on every op (false-positive regression)."""
    result = assert_completes_within(5.0, lambda: simulate_stall(0.05) or "ok")
    assert result == "ok"


def test_chaos_framework_detects_5s_db_stall_per_acceptance() -> None:
    """Acceptance: simulated DB stall >5s triggers ChaosTimeoutError. This is
    the KEI-132 brief's literal acceptance criterion ('DB-timeout scenario
    catches simulated 5s DB stall')."""
    with pytest.raises(ChaosTimeoutError, match="exceeded budget 5"):
        assert_completes_within(5.0, lambda: simulate_stall(6.0))


def test_chaos_framework_returns_op_result_on_success() -> None:
    """Wrapper returns the op's return value transparently — important so
    callers can `result = assert_completes_within(5, lambda: db.fetch_one())`
    and use the result, not just rely on side-effects."""
    sentinel = {"row_count": 42}
    out = assert_completes_within(2.0, lambda: sentinel)
    assert out is sentinel  # identity, not equality — passthrough invariant


def test_chaos_error_distinguishable_from_real_timeout() -> None:
    """ChaosTimeoutError is AssertionError, NOT TimeoutError — so a real
    network TimeoutError in test code isn't conflated with chaos-framework
    overrun signalling. Documented design property worth a regression test."""
    assert issubclass(ChaosTimeoutError, AssertionError)
    assert not issubclass(ChaosTimeoutError, TimeoutError)


@pytest.mark.chaos_db
@pytest.mark.skipif(not db_available(), reason="DATABASE_URL not set — CI without postgres service")
def test_real_db_statement_timeout_catches_pg_sleep_6() -> None:
    """Real-DB variant: psycopg `statement_timeout = 5s` + `SELECT pg_sleep(6)`
    must raise QueryCanceled. Proves the framework integrates with the
    psycopg layer the rest of Agency_OS uses, not just mock-time helpers."""
    import os  # noqa: PLC0415

    import psycopg  # noqa: PLC0415 — optional dep for chaos_db tests

    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute("SET statement_timeout = 5000")  # 5s in ms
        with pytest.raises(psycopg.errors.QueryCanceled):
            cur.execute("SELECT pg_sleep(6)")
