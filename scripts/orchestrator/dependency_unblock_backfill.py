#!/usr/bin/env python3
"""dependency_unblock_backfill.py — KEI-78 one-shot retroactive sweep.

Scans tasks WHERE status='blocked' AND dependencies IS NOT NULL. For each, calls
fn_unblock_dependents over every distinct done-state dep id — same code path the
trigger uses on live writes. Catches anything that became unblockable BEFORE the
trigger landed (or while it was dropped).

Idempotent: tasks already 'available' are no-op'd.
"""

from __future__ import annotations

import argparse
import logging
import os

import psycopg

logger = logging.getLogger("dependency_unblock_backfill")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def backfill(dry_run: bool = False) -> dict:
    stats = {"blocked_scanned": 0, "unblocked": 0, "candidate_done_deps": 0}
    with psycopg.connect(_dsn(), prepare_threshold=None, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT unnest(dependencies) FROM public.tasks "
                "WHERE status='blocked' AND dependencies IS NOT NULL"
            )
            candidate_deps = [r[0] for r in cur.fetchall() if r[0]]
            stats["candidate_done_deps"] = len(candidate_deps)
            cur.execute("SELECT COUNT(*) FROM public.tasks WHERE status='blocked'")
            stats["blocked_scanned"] = cur.fetchone()[0]
        if dry_run:
            logger.info(
                "[dry-run] %d blocked tasks, %d distinct deps would be re-checked",
                stats["blocked_scanned"],
                stats["candidate_done_deps"],
            )
            return stats
        for dep_id in candidate_deps:
            with conn.cursor() as cur:
                cur.execute("SELECT public.fn_unblock_dependents(%s)", (dep_id,))
                stats["unblocked"] += cur.fetchone()[0]
        conn.commit()
    return stats


def main() -> int:
    p = argparse.ArgumentParser(prog="dependency_unblock_backfill")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    stats = backfill(dry_run=args.dry_run)
    logger.info("backfill complete: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
