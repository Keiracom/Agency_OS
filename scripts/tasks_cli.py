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

# Shared help text for --callsign across subcommands (Sonar S1192 — avoid
# duplicating the same string literal across multiple add_argument calls).
_CALLSIGN_HELP = "override CALLSIGN env"

# Canonical column list shared by ready/show paths. Single source of truth
# (avoids Sonar new_duplicated_lines_density on the column projection).
_READY_COLUMNS = (
    "id, title, priority, status, claimed_by, claimed_at, "
    "dependencies, tags, linear_url, created_at, updated_at"
)

# KEI-53 Phase B — personalised score subquery joining agent_profiles.
# JSONB key-exists (?) gates the cast so non-matching tags don't error.
_PERSONALISED_SCORE_SUBQUERY = """COALESCE(
    (SELECT SUM((ap.capability_weights->>tag)::float)
     FROM public.agent_profiles ap,
          unnest(t.tags) AS tag
     WHERE ap.callsign = %s
       AND ap.capability_weights ? tag),
    0.0
) AS personalised_score"""


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
    """List available tasks ordered by priority ASC then created_at ASC.

    KEI-53 Phase B: if --agent <callsign> is supplied, re-rank by
    personalised affinity score = SUM(capability_weight × matching_tag).
    Adds `personalised_score` to each row; preserves existing JSON shape
    (no renames) per Max's tasks-cli compat note.
    """
    import psycopg

    limit = max(1, min(args.limit, 250))
    agent = (args.agent or "").strip().lower() if getattr(args, "agent", None) else ""
    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            if agent:
                # KEI-53 — personalised path. Tie-break per Max note #2:
                # personalised_score DESC, priority ASC, created_at ASC.
                sql = (
                    f"SELECT t.{', t.'.join(_READY_COLUMNS.split(', '))}, "
                    f"{_PERSONALISED_SCORE_SUBQUERY} "
                    "FROM public.tasks t WHERE t.status = 'available' AND t.claimed_by IS NULL "
                    "ORDER BY personalised_score DESC, "
                    "t.priority ASC, t.created_at ASC LIMIT %s"
                )
                cur.execute(sql, (agent, limit))
            else:
                sql = (
                    f"SELECT {_READY_COLUMNS} FROM public.tasks "
                    "WHERE status = 'available' AND claimed_by IS NULL "
                    "ORDER BY priority ASC, created_at ASC LIMIT %s"
                )
                cur.execute(sql, (limit,))
            rows = _rows_to_dicts(cur)
    except psycopg.Error:
        logger.exception("ready query failed")
        return 2
    if args.json:
        print(json.dumps(rows, default=str))
    else:
        for r in rows:
            score_suffix = ""
            if agent and "personalised_score" in r:
                score_suffix = f"  [score={r['personalised_score']:.2f}]"
            print(f"  P{r['priority']:>1}  {r['id']:<24}  {r['title']}{score_suffix}")
        suffix = f" (personalised for {agent})" if agent else ""
        print(f"\n{len(rows)} available{suffix}")
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    """Atomically claim one task (by id, or the next available).

    KEI-71: refuse the claim when the resolved callsign is the
    DEFAULT_CALLSIGN sentinel ('unknown') — Elliot Dave-direct callout
    2026-05-14T08:30Z: silent sentinel-writes (`claimed_by='unknown'`)
    leak when an agent omits `CALLSIGN=<callsign>` from the env. Fail
    fast at the validation layer so the operator notices the env gap
    instead of orphan-claiming a row.
    """
    import psycopg

    cs = _callsign(args.callsign)
    if cs == DEFAULT_CALLSIGN:
        print(
            "ERROR: callsign resolves to the DEFAULT_CALLSIGN sentinel "
            f"({DEFAULT_CALLSIGN!r}). Set CALLSIGN=<your_callsign> in the env or "
            "pass --callsign explicitly. Refusing to write a sentinel claim.",
            file=sys.stderr,
        )
        return 1
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
                         AND claimed_by IS NULL
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
    except psycopg.Error:
        logger.exception("claim query failed")
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
    except psycopg.Error:
        logger.exception("complete query failed")
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
    except psycopg.Error:
        logger.exception("show query failed")
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


def cmd_deprecate(args: argparse.Namespace) -> int:
    """KEI-63 — mark a discovery_log row deprecated. Excludes it from bd claim
    context injection (KEI-55 pipeline) and future Weaviate retrieval (KEI-46/47).

    Acceptance: discovery_log.mark_deprecated() flips deprecated=True on the
    most recent row with the given KEI. load_active_discoveries() then excludes it.
    """
    import importlib.util

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "discovery_log",
        os.path.join(repo_root, "scripts", "orchestrator", "discovery_log.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    callsign = (args.callsign or os.environ.get("CALLSIGN", "")).strip().lower()
    if not callsign:
        print("ERROR: --callsign required or set CALLSIGN env", file=sys.stderr)
        return 2

    try:
        row = mod.mark_deprecated(kei=args.id, reason=args.reason, by=callsign)
    except mod.DiscoveryLogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(row, default=str))
    else:
        print(
            f"deprecated {row['kei']} (by {row['deprecated_by']}, "
            f"reason={row['deprecated_reason']!r}, at {row['deprecated_at']})"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="subcmd", required=True)

    p_ready = sub.add_parser("ready", help="list available tasks")
    p_ready.add_argument("--json", action="store_true")
    p_ready.add_argument("--limit", type=int, default=50)
    p_ready.add_argument(
        "--agent",
        help="KEI-53 — personalise ranking via agent_profiles.capability_weights",
    )
    p_ready.set_defaults(func=cmd_ready)

    p_claim = sub.add_parser("claim", help="atomically claim a task")
    p_claim.add_argument("--id", help="specific task id; omit to take next available")
    p_claim.add_argument("--callsign", help=_CALLSIGN_HELP)
    p_claim.add_argument("--json", action="store_true")
    p_claim.set_defaults(func=cmd_claim)

    p_complete = sub.add_parser("complete", help="mark task done")
    p_complete.add_argument("id", help="task id")
    p_complete.add_argument("--callsign", help=_CALLSIGN_HELP)
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

    p_deprecate = sub.add_parser(
        "deprecate",
        help="KEI-63 — mark a discovery_log entry deprecated (filtered from bd claim)",
    )
    p_deprecate.add_argument("id", help="KEI of the discovery to deprecate")
    p_deprecate.add_argument("--reason", required=True, help="why deprecated")
    p_deprecate.add_argument("--callsign", help=_CALLSIGN_HELP)
    p_deprecate.add_argument("--json", action="store_true")
    p_deprecate.set_defaults(func=cmd_deprecate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
