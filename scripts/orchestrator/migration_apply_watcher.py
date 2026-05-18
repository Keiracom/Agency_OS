#!/usr/bin/env python3
"""migration_apply_watcher.py — KEI-188 migration apply gate (systemd timer entry-point).

Runs every 10 minutes via migration-apply-watcher.timer. For each *.sql file
that landed on main in the last 2 hours, checks whether the schema change it
describes is present in Supabase information_schema. If not, and the file has
been around longer than MIGRATION_APPLY_TIMEOUT_MIN (default 15 min), posts a
plain-English #ceo alert and writes a governance_debt row to ceo_memory.

Idempotent: re-running with an existing `pending` debt row produces no second
alert. When the schema change is later detected, the row flips to `resolved`.

Usage:
    python3 scripts/orchestrator/migration_apply_watcher.py            # one pass
    python3 scripts/orchestrator/migration_apply_watcher.py --dry-run  # log only
"""

from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import re
import subprocess
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import psycopg

logger = logging.getLogger("migration_apply_watcher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MIGRATION_APPLY_TIMEOUT_MIN: int = int(os.environ.get("MIGRATION_APPLY_TIMEOUT_MIN", "15"))
SOURCE_DOC_WATCHER = "migration_apply_watcher"

# Regex patterns to extract schema targets from SQL migration files.
# Split into two simpler patterns to keep Sonar S5843 complexity ≤20.
_ALTER_TABLE_NAME_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?(\w+)",
    re.IGNORECASE,
)
_ALTER_COLUMN_NAME_RE = re.compile(
    r"\bADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
    re.IGNORECASE,
)
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?(\w+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MigrationTarget:
    filename: str
    table: str
    column: str | None  # None means "just check the table exists"
    is_idempotent_create: bool  # CREATE TABLE IF NOT EXISTS


def parse_migration_targets(filename: str, sql: str) -> list[MigrationTarget]:
    """Extract schema check targets from a migration SQL file (best-effort)."""
    targets: list[MigrationTarget] = []

    for m_table in _ALTER_TABLE_NAME_RE.finditer(sql):
        # Find the column name in the remainder of the same ALTER statement.
        rest = sql[m_table.end() :]
        m_col = _ALTER_COLUMN_NAME_RE.search(rest)
        if m_col is None:
            continue
        targets.append(
            MigrationTarget(
                filename=filename,
                table=m_table.group(1),
                column=m_col.group(1),
                is_idempotent_create=False,
            )
        )

    for m in _CREATE_TABLE_RE.finditer(sql):
        is_idempotent = bool(
            re.search(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS", m.group(0), re.IGNORECASE)
        )
        targets.append(
            MigrationTarget(
                filename=filename,
                table=m.group(1),
                column=None,
                is_idempotent_create=is_idempotent,
            )
        )

    return targets


def recent_migration_files(since_hours: int = 2) -> list[tuple[str, _dt.datetime]]:
    """Return list of (filepath, commit_timestamp) for *.sql files committed to
    main in the last `since_hours` hours."""
    result: list[tuple[str, _dt.datetime]] = []
    try:
        out = subprocess.check_output(
            [
                "git",
                "log",
                f"--since={since_hours} hours ago",
                "--name-only",
                "--pretty=format:%aI",
                "--",
                "supabase/migrations/*.sql",
            ],
            text=True,
        )
    except subprocess.CalledProcessError:
        logger.warning("git log failed — skipping migration scan")
        return result

    current_ts: _dt.datetime | None = None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # Lines that look like ISO timestamps are the commit timestamps.
        with suppress(ValueError):
            current_ts = _dt.datetime.fromisoformat(line)
            continue
        if line.endswith(".sql") and current_ts is not None:
            result.append((line, current_ts))

    return result


def schema_check_table(conn: psycopg.Connection, table: str) -> bool:
    """Return True if `table` exists in public schema."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            LIMIT 1
            """,
            (table,),
        )
        return cur.fetchone() is not None


def schema_check_column(conn: psycopg.Connection, table: str, column: str) -> bool:
    """Return True if `column` exists in `table` in the public schema."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
            LIMIT 1
            """,
            (table, column),
        )
        return cur.fetchone() is not None


def schema_applied(conn: psycopg.Connection, target: MigrationTarget) -> bool:
    """Return True if the target schema object is present in Supabase."""
    if target.column is not None:
        return schema_check_column(conn, target.table, target.column)
    return schema_check_table(conn, target.table)


def debt_key(filename: str) -> str:
    return f"governance_debt:migration_apply_{Path(filename).name}"


def get_debt_row(conn: psycopg.Connection, key: str) -> dict | None:
    """Return the ceo_memory value dict for the given debt key, or None."""
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM public.ceo_memory WHERE key = %s", (key,))
        row = cur.fetchone()
        if row is None:
            return None
        val = row[0]
        if isinstance(val, dict):
            return val
        import json as _json

        with suppress(ValueError, TypeError):
            return _json.loads(val)
        return None


def upsert_debt_row(
    conn: psycopg.Connection,
    key: str,
    *,
    filename: str,
    status: str,
) -> None:
    import json as _json

    now_iso = _dt.datetime.now(_dt.UTC).isoformat()
    value = _json.dumps(
        {
            "source": SOURCE_DOC_WATCHER,
            "filename": Path(filename).name,
            "status": status,
            "updated_at": now_iso,
        }
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.ceo_memory (key, value, updated_at)
            VALUES (%s, %s::jsonb, NOW())
            ON CONFLICT (key) DO UPDATE
              SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
            """,
            (key, value),
        )


def _dsn() -> str:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        raise SystemExit("migration_apply_watcher: DATABASE_URL or SUPABASE_DB_URL must be set")
    # pgbouncer-safe: strip +asyncpg variant and disable prepared statements
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def emit_ceo_alert(filename: str, *, dry_run: bool = False) -> None:
    """Post plain-English #ceo alert — no file paths, env vars, or code fences."""
    name = Path(filename).name
    msg = (
        f"*Migration Apply Gap Detected*\n"
        f"- A database migration has been merged but not yet applied.\n"
        f"- Migration: {name}\n"
        f"- Action required: apply this migration via Supabase MCP to unblock downstream features.\n"
        f"- This alert will clear automatically once the migration is applied."
    )
    if dry_run:
        logger.info("dry-run alert: %s", msg)
        return
    relay = Path(__file__).resolve().parents[1] / "slack_relay.py"
    if not relay.exists():
        logger.warning("slack_relay.py not found — alert logged only: %s", msg)
        return
    with suppress(subprocess.SubprocessError, OSError):
        subprocess.run(
            ["python3", str(relay), "-c", "ceo", msg],
            check=False,
            timeout=15,
        )


def process_migration(
    conn: psycopg.Connection,
    filepath: str,
    commit_ts: _dt.datetime,
    *,
    now: _dt.datetime,
    dry_run: bool,
) -> None:
    """Evaluate one migration file and act accordingly."""
    age_min = (now - commit_ts).total_seconds() / 60.0
    key = debt_key(filepath)

    # Try to read the SQL to extract targets.
    try:
        sql_text = Path(filepath).read_text(encoding="utf-8")
    except OSError:
        logger.warning("Cannot read %s — skipping", filepath)
        return

    targets = parse_migration_targets(filepath, sql_text)
    if not targets:
        logger.info("%s: no parseable schema targets — skipping", filepath)
        return

    applied = all(schema_applied(conn, t) for t in targets if not t.is_idempotent_create)
    non_idempotent = [t for t in targets if not t.is_idempotent_create]

    # Idempotent-only migrations: skip entirely — IF NOT EXISTS means pre-existing is fine.
    if not non_idempotent:
        logger.info("%s: all targets are idempotent — no alert", filepath)
        return

    applied = all(schema_applied(conn, t) for t in non_idempotent)

    if applied:
        existing = get_debt_row(conn, key)
        if existing and existing.get("status") == "pending":
            logger.info("%s: schema now applied — resolving debt row", filepath)
            upsert_debt_row(conn, key, filename=filepath, status="resolved")
        else:
            logger.info("%s: applied, no pending debt — nothing to do", filepath)
        return

    # Not applied. Check timeout.
    if age_min < MIGRATION_APPLY_TIMEOUT_MIN:
        logger.info(
            "%s: not applied yet, within window (%.1f min < %d min threshold)",
            filepath,
            age_min,
            MIGRATION_APPLY_TIMEOUT_MIN,
        )
        return

    # Past timeout — check idempotency before alerting.
    existing = get_debt_row(conn, key)
    if existing and existing.get("status") == "pending":
        logger.info("%s: debt already pending — skipping duplicate alert", filepath)
        return

    logger.warning("%s: migration not applied after %.1f min — firing alert", filepath, age_min)
    emit_ceo_alert(filepath, dry_run=dry_run)
    if not dry_run:
        upsert_debt_row(conn, key, filename=filepath, status="pending")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    now = _dt.datetime.now(_dt.UTC)
    migrations = recent_migration_files()
    if not migrations:
        logger.info("no recent migration files found — nothing to do")
        return

    try:
        with psycopg.connect(_dsn(), autocommit=True, prepare_threshold=None) as conn:
            for filepath, commit_ts in migrations:
                process_migration(conn, filepath, commit_ts, now=now, dry_run=args.dry_run)
    except psycopg.OperationalError as exc:
        logger.exception("DB connection failed: %s", exc)
        sys.exit(1)

    logger.info("migration_apply_watcher: scan complete — %d files checked", len(migrations))


if __name__ == "__main__":
    main()
