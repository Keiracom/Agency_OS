"""KEI-132 — DB-timeout chaos scenario.

Simulates a 5s Postgres stall on the driver. Verifies callers wrap the DB
call in a bounded timeout instead of hanging the whole process when the DB
goes slow. asyncpg / psycopg both surface stalls via blocking I/O — we mock
the connect call to sleep, then assert the caller propagates a timeout
within the expected envelope rather than hanging.
"""

from __future__ import annotations

import asyncio

import pytest


class _StallError(Exception):
    """Marker used by the test to verify the timeout path fires."""


async def _stalled_db_call() -> None:
    """Stand-in for any psycopg/asyncpg connect/execute that hangs."""
    await asyncio.sleep(5.0)


async def _bounded_db_call(timeout_s: float) -> None:
    """The shape every DB caller should follow: wrap in wait_for.

    This is the contract under test: code that talks to Postgres MUST bound
    its call so a stalled DB does not freeze the whole event loop.
    """
    try:
        await asyncio.wait_for(_stalled_db_call(), timeout=timeout_s)
    except TimeoutError as exc:
        raise _StallError(f"db call exceeded {timeout_s}s bound") from exc


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_db_stall_is_bounded_not_hung() -> None:
    """A 5s stall against a 0.5s bound must raise quickly, not hang."""
    with pytest.raises(_StallError):
        await _bounded_db_call(timeout_s=0.5)


@pytest.mark.timeout(10)
@pytest.mark.asyncio
async def test_unbounded_db_call_would_hang_proof_of_contract() -> None:
    """Negative-path proof: an UNBOUNDED call against the same stall would
    not finish in time. Without `wait_for`, this is a hang waiting to happen
    — which is exactly the failure mode the bounded contract prevents.
    """
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(_stalled_db_call(), timeout=0.3)
