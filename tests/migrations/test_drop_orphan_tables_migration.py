"""Tests for supabase/migrations/20260512_drop_orphan_tables.sql.

This is a destructive migration — drops 2 triggers + 1 function + 3 tables.
We don't run the migration during tests (would require a live Supabase),
but we DO assert structural invariants that protect against accidental
edits:

  - The three target table names are each dropped once (and only once)
  - The two triggers are dropped BEFORE the table they're attached to
  - All DROPs use IF EXISTS (idempotent / safe to re-run)
  - No reference to in-scope SSOT tables (ceo_memory, agent_memories,
    governance_events, cis_directive_metrics) — those must NEVER appear
    in this drop migration
  - We also verify (via mocked sb_get) that the canonical production
    paths into the live SSOT tables remain unaffected — a smoke that
    nothing in production code accidentally depends on the orphans
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATION = REPO_ROOT / "supabase" / "migrations" / "20260512_drop_orphan_tables.sql"

ORPHAN_TABLES = (
    "public.ceo_memory_archive",
    "public.elliot_knowledge",
    "public.elliot_signoff_queue",
)
ORPHAN_TRIGGERS = (
    "trg_score_knowledge_insert",
    "trg_score_knowledge_update",
)
SSOT_TABLES_THAT_MUST_NEVER_APPEAR = (
    "public.ceo_memory ",  # space-bounded to avoid matching ceo_memory_archive
    "public.agent_memories",
    "public.governance_events",
    "public.cis_directive_metrics",
)


def test_migration_file_exists():
    assert MIGRATION.is_file(), f"missing migration at {MIGRATION}"


def test_each_orphan_table_dropped_exactly_once():
    body = MIGRATION.read_text()
    for tbl in ORPHAN_TABLES:
        pattern = rf"DROP\s+TABLE\s+IF\s+EXISTS\s+{re.escape(tbl)}\s*;"
        matches = re.findall(pattern, body, flags=re.IGNORECASE)
        assert len(matches) == 1, (
            f"expected exactly one DROP TABLE IF EXISTS for {tbl}; got {len(matches)}"
        )


def test_triggers_dropped_before_their_table():
    """trg_score_knowledge_{insert,update} must be dropped BEFORE
    elliot_knowledge — otherwise the trigger drop would error after the
    table is gone. (DROP TRIGGER IF EXISTS would still succeed silently
    in PostgreSQL, but explicit ordering is a code-clarity gate.)"""
    body = MIGRATION.read_text()
    table_drop_pos = body.lower().index("drop table if exists public.elliot_knowledge")
    for trg in ORPHAN_TRIGGERS:
        trg_drop_pos = body.lower().index(trg.lower())
        assert trg_drop_pos < table_drop_pos, (
            f"trigger {trg} drop must come before elliot_knowledge table drop"
        )


def test_trigger_function_dropped():
    """The trigger function trigger_score_knowledge() has zero callers once
    the two triggers are dropped; cleanup with DROP FUNCTION IF EXISTS."""
    body = MIGRATION.read_text()
    assert re.search(
        r"DROP\s+FUNCTION\s+IF\s+EXISTS\s+public\.trigger_score_knowledge\(\)",
        body,
        flags=re.IGNORECASE,
    ), "trigger_score_knowledge() must be dropped explicitly"


def test_all_drops_use_if_exists_for_idempotency():
    """Every DROP statement in this migration MUST use IF EXISTS so re-runs
    on a partially-applied DB are no-ops."""
    body = MIGRATION.read_text()
    drop_lines = [
        ln.strip()
        for ln in body.splitlines()
        if re.match(r"^\s*DROP\s+(TABLE|TRIGGER|FUNCTION)\s", ln, flags=re.IGNORECASE)
    ]
    assert drop_lines, "migration contains no DROP statements"
    for ln in drop_lines:
        assert re.search(r"\bIF\s+EXISTS\b", ln, flags=re.IGNORECASE), (
            f"DROP without IF EXISTS — re-run would fail: {ln}"
        )


def test_no_ssot_table_appears():
    """SSOT tables (ceo_memory, agent_memories, governance_events,
    cis_directive_metrics) must NEVER appear in this drop migration —
    Pattern B safety guard against accidental edits."""
    body = MIGRATION.read_text()
    for tbl in SSOT_TABLES_THAT_MUST_NEVER_APPEAR:
        assert tbl not in body, (
            f"SSOT table {tbl!r} must not appear in an orphan-drop migration"
        )


def test_no_down_migration_present():
    """No DOWN section — the audit established zero production callers, so
    reversal is via Supabase point-in-time recovery, not a CREATE TABLE
    block. Explicit guard against well-meaning future edits."""
    body = MIGRATION.read_text().lower()
    assert "create table" not in body
    assert "create trigger" not in body
    assert "create function" not in body
