"""conftest.py — Prefect ephemeral server fixture for orchestration/flows tests.

All tests under tests/orchestration/flows/ call Prefect @flow and @task
decorated functions via .fn(), which triggers the Prefect task engine and
requires a Prefect server. In CI there is no live server, so we spin up a
temporary in-process SQLite-backed server for the test session.

The fixture uses prefect.settings.temporary_settings to:
  - Clear PREFECT_API_URL (overrides the Railway URL set in the environment)
  - Enable PREFECT_SERVER_ALLOW_EPHEMERAL_MODE so Prefect auto-starts a
    local in-process server

Scope: session — one ephemeral server for the whole test session.
"""

from __future__ import annotations

import pytest
from prefect.settings import (
    PREFECT_API_URL,
    PREFECT_SERVER_ALLOW_EPHEMERAL_MODE,
    temporary_settings,
)


@pytest.fixture(scope="session", autouse=True)
def prefect_ephemeral_server():
    """Start a temporary in-process Prefect server for the test session.

    This is required because the flow tests call task.fn() / flow.fn() which
    still triggers Prefect's AsyncClientContext, which attempts to connect to
    PREFECT_API_URL. The Railway URL in the environment has no live server in
    CI, so we redirect to an ephemeral local server instead.
    """
    with temporary_settings(
        updates={
            PREFECT_API_URL: None,
            PREFECT_SERVER_ALLOW_EPHEMERAL_MODE: True,
        }
    ):
        yield
