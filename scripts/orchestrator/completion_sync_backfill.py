#!/usr/bin/env python3
"""completion_sync_backfill.py — KEI-74 one-shot backfill for stale closures.

Sweeps public.tasks WHERE status IN ('done', 'cancelled') AND there is no
unprocessed completion_sync_queue row for any of the 3 sinks. For each missing
sink, INSERTs a queue row via the same fn_enqueue_completion_sync function the
trigger uses — single code path, no duplication.

Idempotent: re-runs INSERT only the missing sinks via the partial unique index.
"""

from __future__ import annotations

import argparse
import logging
import os

logger = logging.getLogger("completion_sync_backfill")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def backfill(dry_run: bool = False, only_ids: list[str] | None = None) -> dict:
    import psycopg

    stats = {"tasks_scanned": 0, "rows_enqueued": 0}
    where_id = "AND id = ANY(%s)" if only_ids else ""
    params: tuple = (only_ids,) if only_ids else ()
    with psycopg.connect(_dsn(), prepare_threshold=None, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, status FROM public.tasks "
                f"WHERE status IN ('done','cancelled') {where_id} ORDER BY updated_at DESC",
                params,
            )
            tasks = cur.fetchall()
        stats["tasks_scanned"] = len(tasks)
        if dry_run:
            logger.info("[dry-run] %d closed tasks would be enqueued for fan-out", len(tasks))
            return stats
        for task_id, status in tasks:
            with conn.cursor() as cur:
                cur.execute("SELECT public.fn_enqueue_completion_sync(%s, %s)", (task_id, status))
                stats["rows_enqueued"] += 1
        conn.commit()
    return stats


def main() -> int:
    p = argparse.ArgumentParser(prog="completion_sync_backfill")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--ids", nargs="*", help="restrict to specific task ids")
    args = p.parse_args()
    stats = backfill(dry_run=args.dry_run, only_ids=args.ids or None)
    logger.info("backfill complete: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
