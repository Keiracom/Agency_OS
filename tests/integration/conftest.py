"""tests/integration/conftest.py — env-gated fixtures for live Supabase tests.

GOV-PHASE1-COMPREHENSIVE-FIX-AIDEN-SCOPE — D8.

Skips integration tests cleanly when SUPABASE_URL or SUPABASE_SERVICE_KEY is
absent (local dev without prod creds). Provides a `cleanup_rows` fixture so
each test can register synthetic rows for deletion at teardown.

The repo-root tests/conftest.py force-sets placeholder values
("https://test.supabase.co" + "test-service-key") so the rest of the unit
suite hits a stub. Live integration tests need the real creds, so we
re-load them from the env file at module import — but only if the current
values look like placeholders, so callers who exported real values into the
shell still take precedence.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


_ENV_FILE = Path(
    os.environ.get(
        "AGENCY_OS_ENV_FILE", "/home/elliotbot/.config/agency-os/.env",
    )
)
_PLACEHOLDER_URL = "https://test.supabase.co"
_PLACEHOLDER_KEY = "test-service-key"


def _restore_real_env_if_placeholder() -> None:
    """If tests/conftest.py overrode SUPABASE_* with placeholders, re-read
    the real values from the agency-os env file. No-op if file missing or
    callers already exported real values."""
    if (
        os.environ.get("SUPABASE_URL") not in (None, "", _PLACEHOLDER_URL)
        and os.environ.get("SUPABASE_SERVICE_KEY")
        not in (None, "", _PLACEHOLDER_KEY)
    ):
        return
    if not _ENV_FILE.is_file():
        return
    real: dict[str, str] = {}
    for raw in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
            real[key] = value
    for key, value in real.items():
        if value and os.environ.get(key) in (
            None, "", _PLACEHOLDER_URL, _PLACEHOLDER_KEY,
        ):
            os.environ[key] = value


_restore_real_env_if_placeholder()


def _has_supabase_env() -> bool:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return False
    if url == _PLACEHOLDER_URL or key == _PLACEHOLDER_KEY:
        return False
    return True


@pytest.fixture(autouse=True)
def _skip_if_no_supabase_env(request: pytest.FixtureRequest) -> None:
    """Auto-skip any test in tests/integration/ if creds env vars are missing."""
    if request.node.get_closest_marker("integration") is None:
        return
    if not _has_supabase_env():
        pytest.skip(
            "SUPABASE_URL and/or SUPABASE_SERVICE_KEY not set; "
            "skipping live integration test"
        )


@pytest.fixture()
def cleanup_rows() -> Iterator[list[tuple[str, str, str]]]:
    """Yield a list the test appends `(table, column, value)` tuples to.

    On teardown, each registered row is deleted via the supabase client.
    Best-effort — exceptions in cleanup are surfaced as warnings, not raised,
    so a failure in one cleanup does not mask the original test failure.
    """
    registry: list[tuple[str, str, str]] = []
    yield registry
    if not _has_supabase_env() or not registry:
        return
    # Use the MCP path for cleanup — supabase-py via service_role lacks
    # DELETE on some governance tables (RLS), but the MCP bridge runs with
    # full privilege. This keeps cleanup reliable without weakening RLS.
    try:
        from src.governance._mcp_helpers import (
            _quote, supabase_mcp_execute_sql,
        )
    except ImportError:
        return
    for table, column, value in registry:
        sql = (
            f"DELETE FROM public.{table} "
            f"WHERE {column} = '{_quote(str(value))}';"
        )
        try:
            supabase_mcp_execute_sql(sql)
        except Exception as exc:  # pragma: no cover - cleanup is best-effort
            import warnings

            warnings.warn(
                f"[integration cleanup] {table} {column}={value} failed: {exc}",
                stacklevel=1,
            )
