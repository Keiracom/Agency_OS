"""Tests for migration 20260524_0scg — ceo_memory.context NOT NULL + CHECK enum.

Live-integration tests against the Supabase DB. Each test runs inside a
SAVEPOINT that is rolled back on exit, so no test data persists in the
real table.

Skipped if SUPABASE_DB_DSN is not set (CI runs that lack DB access).

Three required test paths per Agency_OS-0scg dispatch:
  (1) positive — INSERT with valid context value lands
  (2) negative — INSERT without context raises NotNullViolation (NOT NULL)
  (3) invalid enum — INSERT with bogus context raises CheckViolation (CHECK)

Plus housekeeping:
  (4) backfill-completeness — zero existing rows with NULL context (proves the
      migration's step-3 sanity gate worked AND no race-condition NULL row
      slipped in between migration apply and test run).

KEI-87 trigger interaction: ceo_memory_write_guard blocks 'ceo:*' writes
without agency_os.callsign IN ('elliot','dave'). We use 'test:0scg:*' keys
in this test file so the trigger short-circuits (NEW.key NOT LIKE 'ceo:%'
→ early RETURN NEW) and we don't have to set the session var.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest

DSN = os.environ.get("SUPABASE_DB_DSN", "").strip()
SKIP_REASON = "SUPABASE_DB_DSN unset — live ceo_memory constraint tests skip"


@pytest.fixture()
def conn():
    """Per-test psycopg connection wrapped in an outer transaction we
    rollback at teardown. The migration's apply-side state is unchanged."""
    if not DSN:
        pytest.skip(SKIP_REASON)
    cn = psycopg.connect(DSN, autocommit=False)
    try:
        yield cn
    finally:
        cn.rollback()
        cn.close()


def _unique_test_key() -> str:
    """test:0scg:<uuid4> — avoids KEI-87 ceo:* write-guard."""
    return f"test:0scg:{uuid.uuid4().hex[:12]}"


def test_positive_insert_with_valid_context_lands(conn):
    """Path (1) — INSERT with valid context value succeeds for each enum
    value. All four enum values exercised in one test for compact coverage."""
    for value in ("fleet", "product", "archive", "both"):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.ceo_memory (key, value, context) VALUES (%s, %s::jsonb, %s)",
                (_unique_test_key(), '{"smoke": "0scg-positive"}', value),
            )
            assert cur.rowcount == 1
    # Outer fixture rolls back; nothing persists.


def test_negative_insert_without_context_raises_not_null(conn):
    """Path (2) — INSERT omitting context raises NotNullViolation."""
    with conn.cursor() as cur, pytest.raises(psycopg.errors.NotNullViolation):
        cur.execute(
            "INSERT INTO public.ceo_memory (key, value) VALUES (%s, %s::jsonb)",
            (_unique_test_key(), '{"smoke": "0scg-negative-null"}'),
        )


def test_negative_insert_with_invalid_enum_raises_check_violation(conn):
    """Path (3) — INSERT with context value outside the enum raises
    CheckViolation against ceo_memory_context_check."""
    with conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
        cur.execute(
            "INSERT INTO public.ceo_memory (key, value, context) VALUES (%s, %s::jsonb, %s)",
            (
                _unique_test_key(),
                '{"smoke": "0scg-negative-enum"}',
                "not_a_real_enum_value",
            ),
        )


def test_backfill_completeness_zero_null_rows(conn):
    """Path (4) — existing rows all have non-null context (proves migration
    backfill landed + no race-condition NULL slipped past the post-migration
    NOT NULL constraint).
    """
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM public.ceo_memory WHERE context IS NULL")
        null_count = cur.fetchone()[0]
        assert null_count == 0, (
            f"{null_count} ceo_memory rows have NULL context post-migration — "
            "backfill incomplete or constraint missing."
        )


def test_check_constraint_is_present(conn):
    """Structural assertion: ceo_memory_context_check CHECK constraint
    exists with the expected enum body. Catches a future drop-of-constraint
    that would invalidate paths (1)-(3) silently."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
              AND t.relname = 'ceo_memory'
              AND c.conname = 'ceo_memory_context_check'
            """
        )
        row = cur.fetchone()
        assert row is not None, "ceo_memory_context_check constraint missing"
        defn = row[0]
        for needed in ("fleet", "product", "archive", "both"):
            assert needed in defn, f"enum value {needed!r} missing from CHECK body: {defn}"


def test_context_column_is_not_null(conn):
    """Structural assertion: context column declared NOT NULL.
    Catches a future ALTER SET NULL regression."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'ceo_memory'
              AND column_name = 'context'
            """
        )
        row = cur.fetchone()
        assert row is not None, "context column missing from ceo_memory"
        assert row[0] == "NO", f"context column should be NOT NULL, got is_nullable={row[0]!r}"
