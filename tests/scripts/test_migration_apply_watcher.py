"""Unit tests for scripts/orchestrator/migration_apply_watcher.py (KEI-188).

No DB / no Slack / no git. Pure-function and mock-based tests.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import migration_apply_watcher as maw  # noqa: E402

_NOW = _dt.datetime(2026, 5, 18, 12, 0, 0, tzinfo=_dt.UTC)
_RECENT_TS = _NOW - _dt.timedelta(minutes=30)  # within 2hr window, past timeout
_FRESH_TS = _NOW - _dt.timedelta(minutes=5)  # within timeout window

_FAKE_SQL = "ALTER TABLE public.foo ADD COLUMN bar TEXT;"


# ── test 1 ──────────────────────────────────────────────────────────────────


def test_no_recent_migrations_no_alert():
    """Empty git log → process_migration never called → no alert posted."""
    with (
        patch.object(maw, "recent_migration_files", return_value=[]),
        patch.object(maw, "emit_ceo_alert") as mock_alert,
        patch.object(maw, "psycopg"),
    ):
        maw.main([])
    mock_alert.assert_not_called()


# ── test 2 ──────────────────────────────────────────────────────────────────


def test_migration_applied_within_window_no_alert():
    """Schema change detected before timeout → no alert."""
    targets = [maw.MigrationTarget("m.sql", "foo", "bar", False)]
    conn = MagicMock()

    with (
        patch("pathlib.Path.read_text", return_value=_FAKE_SQL),
        patch.object(maw, "parse_migration_targets", return_value=targets),
        patch.object(maw, "schema_applied", return_value=True),
        patch.object(maw, "get_debt_row", return_value=None),
        patch.object(maw, "emit_ceo_alert") as mock_alert,
    ):
        maw.process_migration(
            conn, "supabase/migrations/m.sql", _RECENT_TS, now=_NOW, dry_run=False
        )
    mock_alert.assert_not_called()


# ── test 3 ──────────────────────────────────────────────────────────────────


def test_migration_not_applied_after_window_fires_alert():
    """Schema change absent after timeout → alert fired + debt row written."""
    targets = [maw.MigrationTarget("m.sql", "foo", "bar", False)]
    conn = MagicMock()

    with (
        patch("pathlib.Path.read_text", return_value=_FAKE_SQL),
        patch.object(maw, "parse_migration_targets", return_value=targets),
        patch.object(maw, "schema_applied", return_value=False),
        patch.object(maw, "get_debt_row", return_value=None),
        patch.object(maw, "emit_ceo_alert") as mock_alert,
        patch.object(maw, "upsert_debt_row") as mock_upsert,
    ):
        maw.process_migration(
            conn, "supabase/migrations/m.sql", _RECENT_TS, now=_NOW, dry_run=False
        )
    mock_alert.assert_called_once()
    mock_upsert.assert_called_once_with(
        maw.debt_key("supabase/migrations/m.sql"),
        filename="supabase/migrations/m.sql",
        status="pending",
    )


# ── test 4 ──────────────────────────────────────────────────────────────────


def test_alert_clears_when_apply_detected():
    """Existing pending debt row flips to resolved when schema now applied."""
    targets = [maw.MigrationTarget("m.sql", "foo", "bar", False)]
    existing_debt = {"status": "pending", "filename": "m.sql"}
    conn = MagicMock()

    with (
        patch("pathlib.Path.read_text", return_value=_FAKE_SQL),
        patch.object(maw, "parse_migration_targets", return_value=targets),
        patch.object(maw, "schema_applied", return_value=True),
        patch.object(maw, "get_debt_row", return_value=existing_debt),
        patch.object(maw, "upsert_debt_row") as mock_upsert,
    ):
        maw.process_migration(
            conn, "supabase/migrations/m.sql", _RECENT_TS, now=_NOW, dry_run=False
        )
    mock_upsert.assert_called_once_with(
        maw.debt_key("supabase/migrations/m.sql"),
        filename="supabase/migrations/m.sql",
        status="resolved",
    )


# ── test 5 ──────────────────────────────────────────────────────────────────


def test_idempotent_no_double_alert():
    """Re-running with existing pending debt row → no duplicate alert."""
    targets = [maw.MigrationTarget("m.sql", "foo", "bar", False)]
    existing_debt = {"status": "pending"}
    conn = MagicMock()

    with (
        patch("pathlib.Path.read_text", return_value=_FAKE_SQL),
        patch.object(maw, "parse_migration_targets", return_value=targets),
        patch.object(maw, "schema_applied", return_value=False),
        patch.object(maw, "get_debt_row", return_value=existing_debt),
        patch.object(maw, "emit_ceo_alert") as mock_alert,
    ):
        maw.process_migration(
            conn, "supabase/migrations/m.sql", _RECENT_TS, now=_NOW, dry_run=False
        )
    mock_alert.assert_not_called()


# ── test 6 ──────────────────────────────────────────────────────────────────


def test_parses_alter_table_target():
    """ALTER TABLE public.foo ADD COLUMN bar → target with table=foo, column=bar."""
    sql = "ALTER TABLE public.foo ADD COLUMN bar TEXT NOT NULL;"
    targets = maw.parse_migration_targets("20260518_test.sql", sql)
    assert len(targets) == 1
    assert targets[0].table == "foo"
    assert targets[0].column == "bar"
    assert not targets[0].is_idempotent_create


# ── test 7 ──────────────────────────────────────────────────────────────────


def test_parses_create_table_target():
    """CREATE TABLE public.foo → target with table=foo, column=None."""
    sql = "CREATE TABLE public.foo (id SERIAL PRIMARY KEY, name TEXT);"
    targets = maw.parse_migration_targets("20260518_test.sql", sql)
    assert any(t.table == "foo" and t.column is None for t in targets)


# ── test 8 ──────────────────────────────────────────────────────────────────


def test_ignores_idempotent_create():
    """CREATE TABLE IF NOT EXISTS for a pre-existing table is not flagged."""
    targets = [maw.MigrationTarget("m.sql", "existing_table", None, True)]
    conn = MagicMock()

    with (
        patch("pathlib.Path.read_text", return_value=_FAKE_SQL),
        patch.object(maw, "parse_migration_targets", return_value=targets),
        patch.object(maw, "emit_ceo_alert") as mock_alert,
    ):
        maw.process_migration(
            conn, "supabase/migrations/m.sql", _RECENT_TS, now=_NOW, dry_run=False
        )
    mock_alert.assert_not_called()


# ── test 9 ──────────────────────────────────────────────────────────────────


def test_within_timeout_window_no_alert():
    """Migration file is new (within timeout) → no alert even if schema absent."""
    targets = [maw.MigrationTarget("m.sql", "foo", "bar", False)]
    conn = MagicMock()

    with (
        patch("pathlib.Path.read_text", return_value=_FAKE_SQL),
        patch.object(maw, "parse_migration_targets", return_value=targets),
        patch.object(maw, "schema_applied", return_value=False),
        patch.object(maw, "emit_ceo_alert") as mock_alert,
    ):
        maw.process_migration(conn, "supabase/migrations/m.sql", _FRESH_TS, now=_NOW, dry_run=False)
    mock_alert.assert_not_called()
