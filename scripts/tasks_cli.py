#!/usr/bin/env python3
"""tasks_cli.py — KEI-22: Supabase tasks SSOT CLI.

Replaces `bd ready/claim/complete` against the Beads Dolt DB with direct
queries against `public.tasks` in Supabase (project jatzvazlbusedwsnqxzr).
Dave directive 2026-05-14: tasks table is now the queue source of truth;
Beads `bd ready` is bypassed.

Subcommands:
  ready     List tasks WHERE status='available', ordered by priority/created_at.
  claim     Atomically claim one task (SELECT FOR UPDATE SKIP LOCKED + UPDATE).
  complete  Mark a claimed task done (UPDATE status='done', claimed_by=NULL).
  show      Display single-task detail.

Env:
  DATABASE_URL or SUPABASE_DB_URL — postgres DSN to Supabase pooler.
  TASKS_CALLSIGN or CALLSIGN — claimant identifier (default: 'unknown').

JSON output (--json) preserves the consumer-facing shape of `bd ready --json`:
each item has at least {"id", "title", "priority"} plus the extra columns
present in public.tasks (status, claimed_by, dependencies, tags, linear_url).

Exit codes:
  0 — happy path (including "nothing to claim" on `claim --any`).
  1 — operator misconfig (no DSN, missing required arg, etc.).
  2 — database error (connection or query failure).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger("tasks_cli")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DEFAULT_CALLSIGN = "unknown"


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise SystemExit("ERROR: DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _callsign(arg: str | None) -> str:
    return (
        (arg or os.environ.get("TASKS_CALLSIGN") or os.environ.get("CALLSIGN") or DEFAULT_CALLSIGN)
        .strip()
        .lower()
    )


def _rows_to_dicts(cur: Any) -> list[dict]:
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, r, strict=False)) for r in cur.fetchall()]


def cmd_ready(args: argparse.Namespace) -> int:
    """List available tasks ordered by priority ASC then created_at ASC."""
    import psycopg

    limit = max(1, min(args.limit, 250))
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, priority, status, claimed_by, claimed_at,
                       dependencies, tags, linear_url, created_at, updated_at
                FROM public.tasks
                WHERE status = 'available'
                ORDER BY priority ASC, created_at ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = _rows_to_dicts(cur)
    except psycopg.Error as exc:
        logger.error("ready query failed: %s", exc)
        return 2
    if args.json:
        print(json.dumps(rows, default=str))
    else:
        for r in rows:
            print(f"  P{r['priority']:>1}  {r['id']:<24}  {r['title']}")
        print(f"\n{len(rows)} available")
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    """Atomically claim one task (by id, or the next available)."""
    import psycopg

    cs = _callsign(args.callsign)
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            if args.id:
                cur.execute(
                    """
                    UPDATE public.tasks
                       SET status = 'active', claimed_by = %s,
                           claimed_at = NOW(), updated_at = NOW()
                     WHERE id = %s
                       AND status = 'available'
                       AND (claimed_by IS NULL OR claimed_by = %s)
                     RETURNING id, title, priority, status, claimed_by, linear_url
                    """,
                    (cs, args.id, cs),
                )
            else:
                cur.execute(
                    """
                    WITH next AS (
                      SELECT id
                        FROM public.tasks
                       WHERE status = 'available'
                       ORDER BY priority ASC, created_at ASC
                       FOR UPDATE SKIP LOCKED
                       LIMIT 1
                    )
                    UPDATE public.tasks t
                       SET status = 'active', claimed_by = %s,
                           claimed_at = NOW(), updated_at = NOW()
                      FROM next
                     WHERE t.id = next.id
                     RETURNING t.id, t.title, t.priority, t.status, t.claimed_by, t.linear_url
                    """,
                    (cs,),
                )
            row = cur.fetchone()
            conn.commit()
    except psycopg.Error as exc:
        logger.error("claim query failed: %s", exc)
        return 2
    if row is None:
        if args.json:
            print("null")
        else:
            print("nothing to claim" if not args.id else f"could not claim {args.id}")
        return 0
    cols = ["id", "title", "priority", "status", "claimed_by", "linear_url"]
    claimed = dict(zip(cols, row, strict=False))
    if args.json:
        print(json.dumps(claimed))
    else:
        print(f"claimed {claimed['id']} by {claimed['claimed_by']}: {claimed['title']}")
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    """Mark a claimed task done."""
    import psycopg

    cs = _callsign(args.callsign)
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.tasks
                   SET status = 'done',
                       claimed_by = NULL,
                       claimed_at = NULL,
                       updated_at = NOW()
                 WHERE id = %s
                   AND (claimed_by = %s OR %s = 'force')
                 RETURNING id, title, status
                """,
                (args.id, cs, args.force_mode),
            )
            row = cur.fetchone()
            conn.commit()
    except psycopg.Error as exc:
        logger.error("complete query failed: %s", exc)
        return 2
    if row is None:
        if args.json:
            print("null")
        else:
            print(f"could not complete {args.id} (not claimed by {cs}?)")
        return 1
    if args.json:
        print(json.dumps({"id": row[0], "title": row[1], "status": row[2]}))
    else:
        print(f"completed {row[0]}: {row[1]}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Display single-task detail."""
    import psycopg

    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, priority, status, claimed_by, claimed_at,
                       dependencies, tags, linear_url, created_at, updated_at
                FROM public.tasks
                WHERE id = %s
                """,
                (args.id,),
            )
            rows = _rows_to_dicts(cur)
    except psycopg.Error as exc:
        logger.error("show query failed: %s", exc)
        return 2
    if not rows:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rows[0], default=str))
    else:
        r = rows[0]
        print(f"{r['id']} [P{r['priority']}] {r['status']}")
        print(f"  title:      {r['title']}")
        print(f"  claimed_by: {r['claimed_by']}")
        print(f"  linear_url: {r['linear_url']}")
        print(f"  deps:       {r['dependencies']}")
        print(f"  tags:       {r['tags']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p_ready = sub.add_parser("ready", help="list available tasks")
    p_ready.add_argument("--json", action="store_true")
    p_ready.add_argument("--limit", type=int, default=50)
    p_ready.set_defaults(func=cmd_ready)

    p_claim = sub.add_parser("claim", help="atomically claim a task")
    p_claim.add_argument("--id", help="specific task id; omit to take next available")
    p_claim.add_argument("--callsign", help="override CALLSIGN env")
    p_claim.add_argument("--json", action="store_true")
    p_claim.set_defaults(func=cmd_claim)

    p_complete = sub.add_parser("complete", help="mark task done")
    p_complete.add_argument("id", help="task id")
    p_complete.add_argument("--callsign", help="override CALLSIGN env")
    p_complete.add_argument(
        "--force-mode",
        default="strict",
        choices=["strict", "force"],
        help="force=allow completion regardless of claimed_by (admin)",
    )
    p_complete.add_argument("--json", action="store_true")
    p_complete.set_defaults(func=cmd_complete)

    p_show = sub.add_parser("show", help="show task detail")
    p_show.add_argument("id")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
