#!/usr/bin/env python3
"""ceo_decision_sweeper.py — KEI-79 timeout sweeper for awaiting escalations.

Postgres lacks time-based triggers, so a separate hourly cron sweeps
ceo_decisions rows older than 7 days WHERE status='awaiting' and flips
them to status='timeout', resolved_by='system_timeout'. The trg_ceo_
decisions_cascade trigger then bumps the originating tasks row to
status='cancelled'.

Idempotent: re-running re-evaluates the age-window predicate; rows
already past 'awaiting' are no-op'd by the WHERE clause.
"""

from __future__ import annotations

import argparse
import logging
import os

import psycopg

logger = logging.getLogger("ceo_decision_sweeper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TIMEOUT_DAYS = 7


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def sweep(dry_run: bool = False) -> dict:
    stats = {"awaiting": 0, "timed_out": 0}
    with psycopg.connect(_dsn(), prepare_threshold=None, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, task_id FROM public.ceo_decisions "
                "WHERE status='awaiting' AND requested_at < NOW() - INTERVAL %s",
                (f"{TIMEOUT_DAYS} days",),
            )
            overdue = cur.fetchall()
            stats["awaiting"] = len(overdue)
            if dry_run or not overdue:
                logger.info(
                    "[%s] %d overdue awaiting rows%s",
                    "dry-run" if dry_run else "sweep",
                    len(overdue),
                    "" if not overdue else f" (oldest task_id={overdue[0][1]})",
                )
                return stats
            cur.execute(
                "UPDATE public.ceo_decisions SET status='timeout', "
                "resolved_by='system_timeout', resolved_at=NOW(), updated_at=NOW() "
                "WHERE status='awaiting' AND requested_at < NOW() - INTERVAL %s "
                "RETURNING id",
                (f"{TIMEOUT_DAYS} days",),
            )
            stats["timed_out"] = len(cur.fetchall())
        conn.commit()
    logger.info("sweep complete: %s", stats)
    return stats


def main() -> int:
    p = argparse.ArgumentParser(prog="ceo_decision_sweeper")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sweep(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
