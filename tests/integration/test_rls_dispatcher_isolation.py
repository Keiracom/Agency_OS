"""
KEI-111E — Dispatcher customer RLS isolation integration test.

Mirrors the KEI-181 tenant isolation test shape against the two
customer-facing tables covered by this PR:
  * public.dispatcher_customers
  * public.customer_api_keys

Proves read-isolation between two simulated dispatcher customers using real
psycopg sessions against the live Supabase Postgres instance.

Requires: INTEGRATION_DATABASE_URL (or DATABASE_URL when it points at a real
remote DSN, not the conftest.py localhost placeholder). Skipped otherwise.

Mark: pytest.mark.integration
"""

from __future__ import annotations

import os
import uuid

import pytest

_RAW = os.environ.get("INTEGRATION_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
_PG_DSN = _RAW.replace("+asyncpg", "").replace("postgresql+psycopg2", "postgresql")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_dsn() -> str:
    if not _PG_DSN or not _PG_DSN.startswith("postgresql"):
        pytest.skip("No real DATABASE_URL — skipping RLS isolation test")
    if "localhost" in _PG_DSN or "127.0.0.1" in _PG_DSN:
        pytest.skip(
            "DATABASE_URL points at localhost (conftest.py override) — "
            "set INTEGRATION_DATABASE_URL to a real Supabase DSN to run"
        )
    return _PG_DSN


# ---------------------------------------------------------------------------
# Fixtures: two customers + two API keys, one per customer
# ---------------------------------------------------------------------------

_USER_A = str(uuid.uuid4())
_USER_B = str(uuid.uuid4())
_CUST_A = str(uuid.uuid4())
_CUST_B = str(uuid.uuid4())
_KEY_A = str(uuid.uuid4())
_KEY_B = str(uuid.uuid4())


def _open_connection(dsn: str):
    try:
        import psycopg  # psycopg3
    except ImportError:
        pytest.skip("psycopg (v3) not installed — skipping RLS isolation test")
    return psycopg.connect(dsn, autocommit=False)


@pytest.fixture(scope="module", autouse=True)
def seed_and_cleanup(pg_dsn: str):
    """Seed 2 customers + 2 keys; yield; teardown on exit."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()

    # auth.users rows — required because dispatcher_customers.supabase_user_id
    # has ON DELETE CASCADE referencing auth.users(id). Insert with the
    # service-role bypass active (default session has no
    # agency_os.dispatcher_user_id set, so null-var bypass applies).
    for u in (_USER_A, _USER_B):
        cur.execute(
            """
            INSERT INTO auth.users (id, instance_id, email, created_at, updated_at, aud, role)
            VALUES (%s::uuid, '00000000-0000-0000-0000-000000000000'::uuid,
                    %s, NOW(), NOW(), 'authenticated', 'authenticated')
            ON CONFLICT (id) DO NOTHING
            """,
            (u, f"rls-test-{u[:8]}@example.test"),
        )

    for cust_id, user_id, email in [
        (_CUST_A, _USER_A, f"a-{_USER_A[:8]}@rls.test"),
        (_CUST_B, _USER_B, f"b-{_USER_B[:8]}@rls.test"),
    ]:
        cur.execute(
            """
            INSERT INTO public.dispatcher_customers
              (id, supabase_user_id, email, tier)
            VALUES (%s::uuid, %s::uuid, %s, 'free')
            ON CONFLICT (id) DO NOTHING
            """,
            (cust_id, user_id, email),
        )

    for key_id, cust_id in [(_KEY_A, _CUST_A), (_KEY_B, _CUST_B)]:
        cur.execute(
            """
            INSERT INTO public.customer_api_keys
              (id, customer_id, provider, encrypted_key, lookup_hash)
            VALUES (%s::uuid, %s::uuid, 'anthropic', '\\x00'::bytea, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (key_id, cust_id, f"rls-hash-{key_id[:32]}"),
        )

    conn.commit()
    conn.close()

    yield

    conn2 = _open_connection(pg_dsn)
    cur2 = conn2.cursor()
    cur2.execute(
        "DELETE FROM public.customer_api_keys WHERE id IN (%s::uuid, %s::uuid)",
        (_KEY_A, _KEY_B),
    )
    cur2.execute(
        "DELETE FROM public.dispatcher_customers WHERE id IN (%s::uuid, %s::uuid)",
        (_CUST_A, _CUST_B),
    )
    cur2.execute(
        "DELETE FROM auth.users WHERE id IN (%s::uuid, %s::uuid)",
        (_USER_A, _USER_B),
    )
    conn2.commit()
    conn2.close()


# ---------------------------------------------------------------------------
# dispatcher_customers isolation
# ---------------------------------------------------------------------------


def test_user_a_sees_only_own_customer_row(pg_dsn: str) -> None:
    """Session as user A must see CUST_A but NOT CUST_B."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()
    cur.execute(f"SET LOCAL agency_os.dispatcher_user_id = '{_USER_A}'")
    cur.execute(
        "SELECT id::text FROM public.dispatcher_customers WHERE id IN (%s::uuid, %s::uuid)",
        (_CUST_A, _CUST_B),
    )
    visible = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()
    assert _CUST_A in visible, f"User A should see own customer row {_CUST_A}"
    assert _CUST_B not in visible, f"User A must NOT see other-customer row {_CUST_B}"


def test_user_b_sees_only_own_customer_row(pg_dsn: str) -> None:
    """Session as user B must see CUST_B but NOT CUST_A."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()
    cur.execute(f"SET LOCAL agency_os.dispatcher_user_id = '{_USER_B}'")
    cur.execute(
        "SELECT id::text FROM public.dispatcher_customers WHERE id IN (%s::uuid, %s::uuid)",
        (_CUST_A, _CUST_B),
    )
    visible = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()
    assert _CUST_B in visible, f"User B should see own customer row {_CUST_B}"
    assert _CUST_A not in visible, f"User B must NOT see other-customer row {_CUST_A}"


# ---------------------------------------------------------------------------
# customer_api_keys isolation (chained via dispatcher_customers)
# ---------------------------------------------------------------------------


def test_user_a_sees_only_own_api_key(pg_dsn: str) -> None:
    """Session as user A must see KEY_A but NOT KEY_B."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()
    cur.execute(f"SET LOCAL agency_os.dispatcher_user_id = '{_USER_A}'")
    cur.execute(
        "SELECT id::text FROM public.customer_api_keys WHERE id IN (%s::uuid, %s::uuid)",
        (_KEY_A, _KEY_B),
    )
    visible = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()
    assert _KEY_A in visible, f"User A should see own api key {_KEY_A}"
    assert _KEY_B not in visible, f"User A must NOT see other-customer api key {_KEY_B}"


def test_user_b_sees_only_own_api_key(pg_dsn: str) -> None:
    """Session as user B must see KEY_B but NOT KEY_A."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()
    cur.execute(f"SET LOCAL agency_os.dispatcher_user_id = '{_USER_B}'")
    cur.execute(
        "SELECT id::text FROM public.customer_api_keys WHERE id IN (%s::uuid, %s::uuid)",
        (_KEY_A, _KEY_B),
    )
    visible = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()
    assert _KEY_B in visible, f"User B should see own api key {_KEY_B}"
    assert _KEY_A not in visible, f"User B must NOT see other-customer api key {_KEY_A}"


# ---------------------------------------------------------------------------
# Backend (null-var) bypass — backend daemons that haven't set the var
# must still see both rows (KEI-181 parity).
# ---------------------------------------------------------------------------


def test_backend_null_var_sees_both_customers(pg_dsn: str) -> None:
    """No agency_os.dispatcher_user_id set → null-var bypass → see all rows."""
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()
    cur.execute(
        "SELECT id::text FROM public.dispatcher_customers WHERE id IN (%s::uuid, %s::uuid)",
        (_CUST_A, _CUST_B),
    )
    visible = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()
    assert _CUST_A in visible
    assert _CUST_B in visible


def test_backend_null_var_sees_both_api_keys(pg_dsn: str) -> None:
    conn = _open_connection(pg_dsn)
    cur = conn.cursor()
    cur.execute(
        "SELECT id::text FROM public.customer_api_keys WHERE id IN (%s::uuid, %s::uuid)",
        (_KEY_A, _KEY_B),
    )
    visible = {row[0] for row in cur.fetchall()}
    conn.rollback()
    conn.close()
    assert _KEY_A in visible
    assert _KEY_B in visible
