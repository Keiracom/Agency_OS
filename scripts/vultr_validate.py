#!/usr/bin/env python3
"""
KEI-241  Vultr Postgres Migration — Validation Script
Author:  [AIDEN]
Date:    2026-05-28
Branch:  aiden/vultr-postgres-migration

Connects to both SUPABASE_DATABASE_URL (source) and VULTR_POSTGRES_DSN (target)
via psycopg3, then verifies data integrity across 7 tables.

Checks performed:
  - Row count comparison for each table (source vs target).
  - Spot-check: 3 random ceo_memory keys present on target.
  - Spot-check: most recent 5 tasks rows have matching id+status on both.
  - Column existence: keiracom_tenants.max_concurrent_tasks present on target.

Exit codes:
  0 — all checks PASS
  1 — one or more FAIL

Usage:
  SUPABASE_DATABASE_URL="postgres://..." \\
  VULTR_POSTGRES_DSN="postgres://..." \\
  python3 scripts/vultr_validate.py [--table TABLE_NAME]
"""

import argparse
import os
import random
import sys

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg (psycopg3) not installed. Run: pip install psycopg[binary]")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Tables to validate. Order is FK-safe but irrelevant for read-only checks.
# ---------------------------------------------------------------------------
ALL_TABLES = [
    "public.ceo_memory",
    "public.tasks",
    "public.task_verifications",
    "public.completion_sync_queue",
    "public.keiracom_tenants",
    "public.keiracom_spawn_attribution",
    "public.keiracom_paused_tasks",
]

# Result accumulator — (table_or_check, status, message)
results: list[tuple[str, str, str]] = []


def pass_(label: str, msg: str) -> None:
    results.append((label, "PASS", msg))
    print(f"  PASS  {label}: {msg}")


def fail_(label: str, msg: str) -> None:
    results.append((label, "FAIL", msg))
    print(f"  FAIL  {label}: {msg}", file=sys.stderr)


def warn_(label: str, msg: str) -> None:
    results.append((label, "WARN", msg))
    print(f"  WARN  {label}: {msg}")


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def connect(dsn: str, label: str) -> "psycopg.Connection":
    try:
        conn = psycopg.connect(dsn, autocommit=True)
        return conn
    except Exception as exc:
        print(f"ERROR: Could not connect to {label}: {exc}", file=sys.stderr)
        sys.exit(1)


def fetchone(conn: "psycopg.Connection", query: str, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchone()


def fetchall(conn: "psycopg.Connection", query: str, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Check: row count comparison
# ---------------------------------------------------------------------------

def check_row_count(src: "psycopg.Connection", tgt: "psycopg.Connection", table: str) -> None:
    label = f"row_count:{table}"
    try:
        src_row = fetchone(src, f"SELECT COUNT(*) FROM {table}")
        tgt_row = fetchone(tgt, f"SELECT COUNT(*) FROM {table}")

        if src_row is None or tgt_row is None:
            fail_(label, "COUNT(*) returned no row — table may not exist")
            return

        src_count = src_row[0]
        tgt_count = tgt_row[0]

        if src_count == tgt_count:
            pass_(label, f"source={src_count}, target={tgt_count}")
        elif tgt_count < src_count:
            # Target has fewer rows — data loss.
            fail_(label, f"source={src_count} > target={tgt_count} — rows missing on target")
        else:
            # Target has MORE rows than source — unusual but not a data loss.
            warn_(label, f"target={tgt_count} > source={src_count} — extra rows on target (acceptable if backfilled)")
    except Exception as exc:
        fail_(label, f"query error: {exc}")


# ---------------------------------------------------------------------------
# Spot-check: random ceo_memory keys on target
# ---------------------------------------------------------------------------

def check_ceo_memory_spot(src: "psycopg.Connection", tgt: "psycopg.Connection") -> None:
    label = "spot:ceo_memory_keys"
    try:
        rows = fetchall(src, "SELECT key FROM public.ceo_memory ORDER BY RANDOM() LIMIT 3")
        if not rows:
            warn_(label, "No rows in source ceo_memory — skipping spot check")
            return

        keys = [r[0] for r in rows]
        missing = []
        for key in keys:
            found = fetchone(tgt, "SELECT 1 FROM public.ceo_memory WHERE key = %s", (key,))
            if found is None:
                missing.append(key)

        if missing:
            fail_(label, f"Keys missing on target: {missing}")
        else:
            pass_(label, f"All 3 sampled keys present: {keys}")
    except Exception as exc:
        fail_(label, f"query error: {exc}")


# ---------------------------------------------------------------------------
# Spot-check: most recent 5 tasks rows match on both sides
# ---------------------------------------------------------------------------

def check_tasks_spot(src: "psycopg.Connection", tgt: "psycopg.Connection") -> None:
    label = "spot:tasks_recent_5"
    try:
        rows = fetchall(
            src,
            "SELECT id, status FROM public.tasks ORDER BY created_at DESC LIMIT 5"
        )
        if not rows:
            warn_(label, "No rows in source tasks — skipping spot check")
            return

        mismatches = []
        for task_id, src_status in rows:
            tgt_row = fetchone(
                tgt,
                "SELECT status FROM public.tasks WHERE id = %s",
                (task_id,)
            )
            if tgt_row is None:
                mismatches.append(f"{task_id}: missing on target")
            elif tgt_row[0] != src_status:
                mismatches.append(f"{task_id}: status src={src_status!r} tgt={tgt_row[0]!r}")

        if mismatches:
            fail_(label, f"Mismatches: {mismatches}")
        else:
            ids = [r[0] for r in rows]
            pass_(label, f"All 5 recent tasks match: {ids}")
    except Exception as exc:
        fail_(label, f"query error: {exc}")


# ---------------------------------------------------------------------------
# Spot-check: max_concurrent_tasks column exists on target
# ---------------------------------------------------------------------------

def check_max_concurrent_tasks_column(tgt: "psycopg.Connection") -> None:
    label = "spot:max_concurrent_tasks_column"
    try:
        row = fetchone(
            tgt,
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'keiracom_tenants'
              AND column_name = 'max_concurrent_tasks'
            """
        )
        if row is not None:
            pass_(label, "max_concurrent_tasks column exists on keiracom_tenants")
        else:
            fail_(label, "max_concurrent_tasks column MISSING on keiracom_tenants — run 003_add_max_concurrent_tasks.sql")
    except Exception as exc:
        fail_(label, f"query error: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="KEI-241 Vultr Postgres validation — compares Supabase source to Vultr target."
    )
    parser.add_argument(
        "--table",
        metavar="TABLE",
        help="Validate a single table only (e.g. public.tasks). "
             "Skips spot-checks unless the table matches.",
    )
    args = parser.parse_args()

    supabase_dsn = os.environ.get("SUPABASE_DATABASE_URL", "")
    vultr_dsn = os.environ.get("VULTR_POSTGRES_DSN", "")

    if not supabase_dsn:
        print("ERROR: SUPABASE_DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)
    if not vultr_dsn:
        print("ERROR: VULTR_POSTGRES_DSN is not set.", file=sys.stderr)
        sys.exit(1)

    print("KEI-241 Vultr Postgres validation")
    print(f"Source: SUPABASE_DATABASE_URL (set)")
    print(f"Target: VULTR_POSTGRES_DSN (set)")
    print()

    src_conn = connect(supabase_dsn, "Supabase (source)")
    tgt_conn = connect(vultr_dsn, "Vultr (target)")

    tables_to_check = ALL_TABLES
    if args.table:
        # Normalise: allow "tasks" or "public.tasks".
        tbl = args.table if "." in args.table else f"public.{args.table}"
        if tbl not in ALL_TABLES:
            print(f"WARNING: {tbl} is not in the known table list — proceeding anyway.")
        tables_to_check = [tbl]

    print("--- Row count checks ---")
    for table in tables_to_check:
        check_row_count(src_conn, tgt_conn, table)

    print()
    print("--- Spot checks ---")

    # Run spot checks if the relevant table is in scope (or no --table filter).
    if not args.table or "ceo_memory" in args.table:
        check_ceo_memory_spot(src_conn, tgt_conn)

    if not args.table or "tasks" in args.table:
        check_tasks_spot(src_conn, tgt_conn)

    check_max_concurrent_tasks_column(tgt_conn)

    src_conn.close()
    tgt_conn.close()

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print()
    total = len(results)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    warned = sum(1 for _, s, _ in results if s == "WARN")

    print(f"=== Summary: {passed}/{total} PASS  |  {failed} FAIL  |  {warned} WARN ===")

    if failed > 0:
        print("RESULT: FAIL — migration validation did not pass.", file=sys.stderr)
        sys.exit(1)

    print("RESULT: PASS — all checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
