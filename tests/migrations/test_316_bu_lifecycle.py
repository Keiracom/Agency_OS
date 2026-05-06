"""
Structural audit tests for migration 316_bu_lifecycle.sql.

These tests validate the migration file as text — no live DB required.
Full up/down DB testing is deferred to CI with real Postgres (testing.postgresql
or a Supabase branch), since the migration uses PostgreSQL-specific syntax
(enum types, TIMESTAMPTZ, partial indexes) that cannot run on SQLite.
"""

import re
from pathlib import Path

import pytest

MIGRATION_PATH = Path(__file__).parents[2] / "alembic" / "versions" / "316_bu_lifecycle.sql"


@pytest.fixture(scope="module")
def migration_sql() -> str:
    return MIGRATION_PATH.read_text()


# 1. File exists
def test_migration_file_exists():
    assert MIGRATION_PATH.exists(), f"Migration file not found: {MIGRATION_PATH}"


# 2. All 5 new columns present
@pytest.mark.parametrize(
    "column",
    [
        "outreach_status",
        "last_outreach_at",
        "signal_snapshot_at",
        "signal_delta",
        "agency_notes",
    ],
)
def test_column_present(migration_sql, column):
    assert column in migration_sql, f"Column '{column}' not found in migration"


# 3. All enum values present
@pytest.mark.parametrize(
    "value",
    [
        "'pending'",
        "'active'",
        "'replied'",
        "'converted'",
        "'suppressed'",
    ],
)
def test_enum_value_present(migration_sql, value):
    assert value in migration_sql, f"Enum value {value} not found in migration"


# 4. Backfill UPDATE present
def test_backfill_update_present(migration_sql):
    assert re.search(
        r"UPDATE\s+business_universe\s+SET\s+outreach_status",
        migration_sql,
        re.IGNORECASE,
    ), "Backfill UPDATE business_universe SET outreach_status not found"


# 5. Index on outreach_status present
def test_index_on_outreach_status(migration_sql):
    assert "idx_bu_outreach_status" in migration_sql, (
        "Index idx_bu_outreach_status not found in migration"
    )
    assert re.search(
        r"CREATE INDEX IF NOT EXISTS idx_bu_outreach_status\s+ON business_universe \(outreach_status\)",
        migration_sql,
        re.IGNORECASE,
    ), "Index creation on outreach_status not found with expected syntax"


# 6a. Idempotent: IF NOT EXISTS appears at least once
def test_if_not_exists_present(migration_sql):
    assert migration_sql.upper().count("IF NOT EXISTS") >= 1, (
        "Migration is not idempotent — no IF NOT EXISTS found"
    )


# 6b. Enum wrapped in DO $$ ... END$$ block
def test_enum_in_do_block(migration_sql):
    assert re.search(
        r"DO\s+\$\$.*?END\$\$",
        migration_sql,
        re.DOTALL,
    ), "Enum creation not wrapped in DO $$...END$$ idempotency block"
