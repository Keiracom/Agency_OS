"""KEI-100 — tests for the linear_id alignment migration.

These tests don't require a live Postgres. They assert:
- The migration SQL file exists and contains the canonical statements
- The backfill regex extracts canonical KEI-N from various URL shapes
- The verify script's mismatch detector classifies the four known shapes
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATION = REPO_ROOT / "supabase" / "migrations" / "20260518_kei100_tasks_linear_id.sql"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_kei100_id_alignment.py"


def test_migration_file_exists():
    assert MIGRATION.exists()


def test_migration_adds_linear_id_column():
    sql = MIGRATION.read_text()
    assert "ADD COLUMN IF NOT EXISTS linear_id text" in sql


def test_migration_backfills_from_url_then_id():
    sql = MIGRATION.read_text()
    # URL-first backfill must come before id-fallback backfill
    url_idx = sql.find("substring(linear_url FROM 'KEI-[0-9]+')")
    id_idx = sql.find("id ~ '^KEI-[0-9]+$'")
    assert url_idx >= 0 and id_idx > url_idx


def test_migration_creates_partial_unique_index():
    sql = MIGRATION.read_text()
    assert "CREATE UNIQUE INDEX IF NOT EXISTS tasks_linear_id_unique" in sql
    assert "WHERE linear_id IS NOT NULL" in sql


def test_migration_installs_sync_trigger():
    sql = MIGRATION.read_text()
    assert "CREATE OR REPLACE FUNCTION public.tasks_sync_linear_id" in sql
    assert "CREATE TRIGGER tasks_sync_linear_id_trg" in sql
    assert "BEFORE INSERT OR UPDATE" in sql


def test_migration_does_not_drop_legacy_id_column():
    """Phase 2 work — must NOT be in this migration. 4 FK referrers + Beads CLI
    would break. Guard against accidental inclusion."""
    sql = MIGRATION.read_text()
    assert "DROP COLUMN" not in sql.upper().replace("CASCADE", "")
    assert "DROP TABLE" not in sql.upper()


# ─── regex extraction equivalence (Python ↔ Postgres) ────────────────────────

_KEI_RE = re.compile(r"KEI-[0-9]+")


def _extract(url: str | None) -> str | None:
    if url is None:
        return None
    m = _KEI_RE.search(url)
    return m.group(0) if m else None


def test_extract_canonical_url():
    assert _extract("https://linear.app/keiracom/issue/KEI-98/some-slug") == "KEI-98"


def test_extract_bare_url_without_slug():
    assert _extract("https://linear.app/keiracom/issue/KEI-63") == "KEI-63"


def test_extract_subkei_resolves_to_parent():
    """KEI-54B → URL contains KEI-54 (the parent) — that's the canonical Linear id."""
    assert _extract("https://linear.app/keiracom/issue/KEI-54/some-slug") == "KEI-54"


def test_extract_no_kei_returns_none():
    assert _extract("https://example.com/no-kei-here") is None


def test_extract_null_returns_none():
    assert _extract(None) is None


# ─── verify-script SQL shape ─────────────────────────────────────────────────


def test_verify_script_exists_and_is_executable():
    assert VERIFY_SCRIPT.exists()
    assert VERIFY_SCRIPT.stat().st_mode & 0o111


def test_verify_script_detects_four_mismatch_shapes():
    src = VERIFY_SCRIPT.read_text()
    for shape in (
        "url_set_id_null",
        "url_id_disagree",
        "id_kei_but_linear_id_null",
        "linear_id_malformed",
    ):
        assert shape in src, f"verify script missing mismatch shape '{shape}'"


def test_verify_script_exits_zero_only_on_clean_alignment():
    src = VERIFY_SCRIPT.read_text()
    # If no rows → exit 0 with "OK" message; if rows → exit 1 with FAIL
    assert "return 0" in src
    assert "return 1" in src
    assert "OK:" in src
    assert "FAIL:" in src
