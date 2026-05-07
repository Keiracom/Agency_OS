"""tests/e2e/test_campaign_schema_smoke.py — EXPLAIN-based schema gate.

Runs `EXPLAIN` against the live Postgres schema for the SQL queries used by
campaign_sender (scripts/campaign_sender.py) and CampaignExecutor
(src/engines/campaign_executor.py). Catches schema drift the moment a column
is renamed or removed — the failure mode Dave's "mocked tests can hide
schema bugs" lesson called out.

EXPLAIN is read-only and cheap (no rows scanned, just plan generation). It
fails fast with a clear error if any referenced column or table is missing.

Skips cleanly when DATABASE_URL is absent (local dev without prod creds).
Runs in CI whenever DATABASE_URL is configured.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_ENV_FILE = Path(
    os.environ.get(
        "AGENCY_OS_ENV_FILE",
        "/home/elliotbot/.config/agency-os/.env",
    )
)


_PLACEHOLDER_DSN = "postgresql+asyncpg://test:test@localhost:5432/test_db"


def _load_env_if_needed() -> None:
    """Re-read the agency-os env file if DATABASE_URL is missing or placeholder.

    `tests/conftest.py` force-sets a placeholder DSN at module load. Live
    integration tests need the real value, so we re-read the env file when
    the current value matches the placeholder. Mirrors the pattern in
    `tests/e2e/conftest.py` for SUPABASE_* keys.
    """
    current = os.environ.get("DATABASE_URL", "")
    if current and current != _PLACEHOLDER_DSN:
        return
    if not _ENV_FILE.is_file():
        return
    for raw in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key in {"DATABASE_URL", "DATABASE_URL_MIGRATIONS"}:
            os.environ[key] = val.strip().strip('"').strip("'")


def _psycopg_dsn() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_MIGRATIONS") or ""
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    elif url.startswith("postgres+asyncpg://"):
        url = "postgresql://" + url[len("postgres+asyncpg://") :]
    return url


@pytest.fixture(scope="module")
def db_conn():
    """Yield a live psycopg connection or skip the module if creds missing."""
    _load_env_if_needed()
    dsn = _psycopg_dsn()
    if not dsn:
        pytest.skip("DATABASE_URL not configured — schema smoke tests need live DB")
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        pytest.skip("psycopg not installed")
    try:
        conn = psycopg.connect(dsn, prepare_threshold=None, connect_timeout=5)
    except Exception as exc:
        pytest.skip(f"could not connect to DB: {exc}")
    try:
        yield conn
    finally:
        conn.close()


# SQL queries copied verbatim from the production code paths. If either
# script changes its WHERE/SELECT, this test should be updated in the same
# PR (LAW XIII for in-tree code).

CAMPAIGN_SENDER_SQL = """
    SELECT bu.id::text, bu.dm_email, bu.dm_name, bu.display_name,
           bu.state, bu.suburb, bu.gmb_category, bu.dm_email_confidence
    FROM public.business_universe bu
    LEFT JOIN public.global_suppression gs
      ON LOWER(gs.email) = LOWER(bu.dm_email)
    WHERE bu.dm_email IS NOT NULL
      AND gs.email IS NULL
      AND bu.gmb_category ILIKE %s
      AND (NOT %s OR bu.dm_email_verified = TRUE)
      AND COALESCE(bu.dm_email_confidence, 0) >= %s
    ORDER BY bu.dm_email_confidence DESC NULLS LAST, bu.id
    LIMIT %s
"""

CAMPAIGN_SENDER_QUALITY_GATES_SQL = """
    SELECT bu.id::text, bu.dm_email, bu.dm_name, bu.display_name,
           bu.state, bu.suburb, bu.gmb_category, bu.dm_email_confidence
    FROM public.business_universe bu
    LEFT JOIN public.global_suppression gs
      ON LOWER(gs.email) = LOWER(bu.dm_email)
    WHERE bu.dm_email IS NOT NULL
      AND gs.email IS NULL
      AND bu.dm_name IS NOT NULL
      AND LOWER(SPLIT_PART(bu.dm_email, '@', 1)) NOT IN (
          'hello', 'info', 'reception', 'admin', 'office',
          'contact', 'sales', 'enquiries', 'support', 'hi', 'team'
      )
      AND bu.gmb_category ILIKE %s
      AND (NOT %s OR bu.dm_email_verified = TRUE)
      AND COALESCE(bu.dm_email_confidence, 0) >= %s
    ORDER BY bu.dm_email_confidence DESC NULLS LAST, bu.id
    LIMIT %s
"""

# CampaignExecutor query (PR #564) — uses asyncpg's $N positional params.
# We rewrite to %s for psycopg here; the column references are what matters.
CAMPAIGN_EXECUTOR_SQL = """
    SELECT id::text, domain, dm_email, dm_name, display_name,
           gmb_category, state, suburb
    FROM public.business_universe bu
    WHERE dm_email IS NOT NULL
      AND dm_name IS NOT NULL
      AND dm_email_verified = true
      AND COALESCE(dm_email_confidence, 0) >= %s
      AND NOT EXISTS (
          SELECT 1 FROM public.global_suppression gs
          WHERE LOWER(gs.email) = LOWER(bu.dm_email)
      )
      AND gmb_category ILIKE %s
    ORDER BY COALESCE(dm_email_confidence, 0) DESC
    LIMIT %s
"""


def _explain(conn, sql: str, params: tuple) -> None:
    """Run EXPLAIN on the given SQL with placeholder params.

    EXPLAIN succeeds only if all referenced tables/columns exist. Wraps the
    query in EXPLAIN — does not execute the SELECT against rows.
    """
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN {sql}", params)
        plan = cur.fetchall()
    assert plan, "EXPLAIN returned an empty plan — should never happen"


def test_campaign_sender_query_explains(db_conn):
    """campaign_sender.py SQL must reference only existing BU columns."""
    _explain(db_conn, CAMPAIGN_SENDER_SQL, ("%dental%", True, 70, 10))


def test_campaign_sender_quality_gates_query_explains(db_conn):
    """campaign_sender.py post-PR-#572 SQL with quality gates must EXPLAIN."""
    _explain(db_conn, CAMPAIGN_SENDER_QUALITY_GATES_SQL, ("%dental%", True, 70, 10))


def test_campaign_executor_query_explains(db_conn):
    """src/engines/campaign_executor.py SQL must reference only existing columns.

    Catches the exact regression that triggered Aiden's REQUEST CHANGES on
    PR #564 — `company_name` and `industry` columns referenced that don't
    exist. After Elliot's fix (commit d16d574e) the columns are correct;
    this test locks them in so a future revert can't reintroduce the bug.
    """
    _explain(db_conn, CAMPAIGN_EXECUTOR_SQL, (70, "%dental%", 10))


def test_business_universe_has_required_columns(db_conn):
    """Direct check: every column the campaign code paths reference exists.

    Belt-and-braces alongside the EXPLAIN tests — names the columns explicitly
    so a missing one shows up as a readable assertion failure instead of a
    SQL error.
    """
    required = {
        "id",
        "dm_email",
        "dm_name",
        "display_name",
        "domain",
        "state",
        "suburb",
        "gmb_category",
        "dm_email_verified",
        "dm_email_confidence",
    }
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'business_universe'"
        )
        existing = {row[0] for row in cur.fetchall()}
    missing = required - existing
    assert not missing, f"BU is missing required columns: {sorted(missing)}"


def test_global_suppression_has_email_column(db_conn):
    """The suppression LEFT JOIN depends on global_suppression.email existing."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'global_suppression' "
            "AND column_name = 'email'"
        )
        rows = cur.fetchall()
    assert rows, "public.global_suppression.email column missing"
