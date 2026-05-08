"""conftest.py — Prefect ephemeral server fixture for orchestration/flows tests.

All tests under tests/orchestration/flows/ call Prefect @flow and @task
decorated functions via .fn(), which triggers the Prefect task engine and
requires a Prefect server. In CI there is no live server, so we spin up a
temporary in-process SQLite-backed server for the test session.

The fixture uses prefect.settings.temporary_settings to:
  - Clear PREFECT_API_URL (overrides the Railway URL set in the environment)
  - Enable PREFECT_SERVER_ALLOW_EPHEMERAL_MODE so Prefect auto-starts a
    local in-process server
  - Point PREFECT_HOME at a clean tmp dir so alembic migration state is
    fresh (avoids "Can't locate revision …" when the user's ~/.prefect
    db was created against a different Prefect version)

Scope: session — one ephemeral server for the whole test session.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from prefect.settings import (
    PREFECT_API_URL,
    PREFECT_HOME,
    PREFECT_SERVER_ALLOW_EPHEMERAL_MODE,
    PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS,
    temporary_settings,
)


@pytest.fixture(autouse=True)
def prefect_ephemeral_server():
    """Start a temporary in-process Prefect server per test.

    Per-function scope — each test that calls asyncio.run() creates a new
    event loop, and Prefect's ephemeral server holds resources bound to a
    specific loop. Reusing a stale ephemeral context across asyncio.run()
    calls causes "Timed out while attempting to connect to ephemeral
    Prefect API server" failures in subsequent tests.

    Each test gets a fresh PREFECT_HOME tmp dir so the SQLite migration
    state and the ephemeral server resolve cleanly. Startup timeout is
    raised from the 20s default to 60s to absorb cold-start variance on
    CI runners and on machines with a slow first SQLite migration pass.
    """
    with tempfile.TemporaryDirectory(prefix="prefect-test-home-") as tmp_home:
        with temporary_settings(
            updates={
                PREFECT_API_URL: None,
                PREFECT_SERVER_ALLOW_EPHEMERAL_MODE: True,
                PREFECT_HOME: Path(tmp_home),
                PREFECT_SERVER_EPHEMERAL_STARTUP_TIMEOUT_SECONDS: 60,
            }
        ):
            yield
