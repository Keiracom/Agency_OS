"""
KEI-181 — Tenant Isolation Integration Test.

Proves read-isolation between two tenants on public.tasks using real psycopg
sessions against the live Supabase Postgres instance.

Requires: DATABASE_URL env var pointing at the Supabase direct/pooler connection.
Skipped automatically when DATABASE_URL is absent.

Mark: pytest.mark.integration
"""

from __future__ import annotations

import os
import uuid

import pytest

# Prefer INTEGRATION_DATABASE_URL (not overridden by tests/conftest.py).
# Fall back to DATABASE_URL if it looks like a real remote DSN (not localhost).
_RAW = os.environ.get("INTEGRATION_DATABASE_URL") or os.environ.get("DATABASE_URL", "")

# Normalise asyncpg DSN → psycopg3 compatible (remove +asyncpg if present)
_PG_DSN = _RAW.replace("+asyncpg", "").replace("postgresql+psycopg2", "postgresql")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_dsn() -> str:
    if not _PG_DSN or not _PG_DSN.startswith("postgresql"):
        pytest.skip("No real DATABASE_URL — skipping tenant isolation test")
    # Skip if this looks like the conftest.py localhost test placeholder
    if "localhost" in _PG_DSN or "127.0.0.1" in _PG_DSN:
        pytest.skip(
            "DATABASE_URL points at localhost (conftest.py override) — "
            "set INTEGRATION_DATABASE_URL to a real Supabase DSN to run"
        )
    return _PG_DSN


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT_2_ID = 2
_TENANT_2_NAME = "test-tenant-2-kei181"
_TASK_T1 = f"TEST-T1-{uuid.uuid4().hex[:8]}"
_TASK_T2 = f"TEST-T2-{uuid.uuid4().hex[:8]}"


def _open_connection(dsn: str):
    """Return a plain synchronous psycopg3 connection with autocommit=False."""
    try:
        import psycopg  # psycopg3
    except ImportError:
        pytest.skip("psycopg (v3) not installed — skipping tenant isolation test")
    return psycopg.connect(dsn, autocommit=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(pg_dsn: str):
    """Insert test tenants + tasks, yield, then delete on teardown."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()

    # Insert tenant 2 (idempotent)
    cur.execute(
        "INSERT INTO public.tenants (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        (_TENANT_2_ID, _TENANT_2_NAME),
    )

    # Insert one task per tenant
    for task_id, tid, title in [
        (_TASK_T1, 1, "dave-only-kei181"),
        (_TASK_T2, _TENANT_2_ID, "customer-only-kei181"),
    ]:
        cur.execute(
            """
            INSERT INTO public.tasks (id, tenant_id, title, status)
            VALUES (%s, %s, %s, 'pending')
            ON CONFLICT (id) DO NOTHING
            """,
            (task_id, tid, title),
        )

    conn.commit()
    conn.close()

    yield

    # Teardown
    conn2 = _open_connection(pg_dsn)
    cur2 = conn2.cursor()
    cur2.execute("DELETE FROM public.tasks WHERE id IN (%s, %s)", (_TASK_T1, _TASK_T2))
    cur2.execute("DELETE FROM public.tenants WHERE id = %s", (_TENANT_2_ID,))
    conn2.commit()
    conn2.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tenant1_sees_only_own_row(pg_dsn: str) -> None:
    """Session A (tenant_id=1) must see TEST-T1 but NOT TEST-T2."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()

    cur.execute("SET LOCAL agency_os.tenant_id = '1'")
    cur.execute(
        "SELECT id FROM public.tasks WHERE id IN (%s, %s)",
        (_TASK_T1, _TASK_T2),
    )
    visible_ids = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()

    assert _TASK_T1 in visible_ids, f"Tenant 1 should see {_TASK_T1}"
    assert _TASK_T2 not in visible_ids, f"Tenant 1 must NOT see {_TASK_T2}"


def test_tenant2_sees_only_own_row(pg_dsn: str) -> None:
    """Session B (tenant_id=2) must see TEST-T2 but NOT TEST-T1."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()

    cur.execute("SET LOCAL agency_os.tenant_id = '2'")
    cur.execute(
        "SELECT id FROM public.tasks WHERE id IN (%s, %s)",
        (_TASK_T1, _TASK_T2),
    )
    visible_ids = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()

    assert _TASK_T2 in visible_ids, f"Tenant 2 should see {_TASK_T2}"
    assert _TASK_T1 not in visible_ids, f"Tenant 2 must NOT see {_TASK_T1}"


def test_service_role_sees_both_rows(pg_dsn: str) -> None:
    """Session C (agency_os.tenant_id IS NULL) must see BOTH rows (daemon bypass)."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()

    # Do NOT set agency_os.tenant_id — simulates backend daemon via service-role bypass
    cur.execute(
        "SELECT id FROM public.tasks WHERE id IN (%s, %s)",
        (_TASK_T1, _TASK_T2),
    )
    visible_ids = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()

    assert _TASK_T1 in visible_ids, f"Service-role should see {_TASK_T1}"
    assert _TASK_T2 in visible_ids, f"Service-role should see {_TASK_T2}"
