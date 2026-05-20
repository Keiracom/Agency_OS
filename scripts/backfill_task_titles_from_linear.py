#!/usr/bin/env python3
"""backfill_task_titles_from_linear.py — Part 1 title backfill (Dave directive 2026-05-20).

Reads every Keiracom-team issue's {identifier, title} from the Linear GraphQL
API and writes the title into public.tasks for rows that have no usable title
(NULL / '' / '(no title)'). public.tasks.id IS the Linear identifier (KEI-N),
so the join is a direct id match — no mapping table.

LAW compliance: Linear-READ + Supabase-WRITE only. This script issues no
Linear mutation. The ratified LAW (2026-05-20) forbids writing Linear, not
reading it.

Usage:
    python3 scripts/backfill_task_titles_from_linear.py            # dry-run
    python3 scripts/backfill_task_titles_from_linear.py --apply    # mutate Postgres

Idempotent. The UPDATE's WHERE clause re-filters on the bad-title predicate,
so re-running only touches rows still missing a title. Safe to wire into a
periodic timer.

Env:
    LINEAR_API_KEY                 — Linear personal API key (Authorization header)
    DATABASE_URL / SUPABASE_DB_URL — Postgres DSN to the Supabase pooler
    LINEAR_TEAM_ID                 — override the Keiracom team UUID (optional)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.request
from typing import Any

logger = logging.getLogger("backfill_task_titles")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

LINEAR_API_URL = "https://api.linear.app/graphql"
# Keiracom team UUID — single source of truth is src/api/webhooks/linear.py
# (LINEAR_TEAM_ID_DEFAULT); duplicated here to keep scripts/ free of a src/
# import dependency. Env LINEAR_TEAM_ID overrides.
LINEAR_TEAM_ID_DEFAULT = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"

# Titles Postgres treats as "no usable title" — same predicate the UPDATE uses.
_BAD_TITLES = ("", "(no title)")

_ISSUES_QUERY = """
query($teamId: ID!, $cursor: String) {
  issues(
    first: 250
    after: $cursor
    includeArchived: true
    filter: { team: { id: { eq: $teamId } } }
  ) {
    nodes { identifier title }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _linear_api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY")
    if not key:
        raise RuntimeError("LINEAR_API_KEY must be set")
    return key


def _team_id() -> str:
    return os.environ.get("LINEAR_TEAM_ID", LINEAR_TEAM_ID_DEFAULT)


def fetch_linear_titles() -> dict[str, str]:
    """Return {identifier: title} for every issue on the Keiracom team.

    Paginates the Linear issues connection (250/page) until hasNextPage is
    false. includeArchived=true so Done/Cancelled issues — whose titles we
    still need for backfill — are not silently dropped.
    """
    key = _linear_api_key()
    team_id = _team_id()
    titles: dict[str, str] = {}
    cursor: str | None = None
    while True:
        body = json.dumps(
            {"query": _ISSUES_QUERY, "variables": {"teamId": team_id, "cursor": cursor}}
        ).encode()
        req = urllib.request.Request(  # noqa: S310 — fixed https Linear endpoint
            LINEAR_API_URL,
            data=body,
            headers={"Authorization": key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            payload = json.loads(resp.read())
        if "errors" in payload:
            raise RuntimeError(f"Linear GraphQL errors: {payload['errors']}")
        conn = payload["data"]["issues"]
        for node in conn["nodes"]:
            titles[node["identifier"]] = node["title"]
        page = conn["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
    logger.info("fetched %d issue titles from Linear", len(titles))
    return titles


def plan_backfill(conn: Any, linear_titles: dict[str, str]) -> dict[str, Any]:
    """Partition bad-title task rows into {matched: [(id, title)], unmatched: [id]}.

    A row is "unmatched" when its identifier has no Linear issue, or the Linear
    issue itself has no usable title — either way the backfill cannot fix it
    and the row is surfaced for human triage.
    """
    result: dict[str, Any] = {"matched": [], "unmatched": []}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM public.tasks "
            "WHERE title IS NULL OR title = '' OR title = '(no title)' "
            "ORDER BY id"
        )
        bad_ids = [row[0] for row in cur.fetchall()]
    for task_id in bad_ids:
        linear_title = linear_titles.get(task_id)
        if not linear_title or linear_title in _BAD_TITLES:
            result["unmatched"].append(task_id)
        else:
            result["matched"].append((task_id, linear_title))
    return result


def apply_backfill(conn: Any, matched: list[tuple[str, str]]) -> int:
    """Write title for matched rows. Returns count written.

    The WHERE clause re-asserts the bad-title predicate so a row that gained a
    title between plan and apply is left untouched (idempotent, race-safe).
    """
    written = 0
    with conn.cursor() as cur:
        for task_id, title in matched:
            cur.execute(
                "UPDATE public.tasks SET title = %s, updated_at = NOW() "
                "WHERE id = %s "
                "AND (title IS NULL OR title = '' OR title = '(no title)')",
                (title, task_id),
            )
            written += cur.rowcount
    conn.commit()
    return written


def count_remaining(conn: Any) -> int:
    """Verify gate — rows still lacking a usable title after the run."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM public.tasks "
            "WHERE title IS NULL OR title = '' OR title = '(no title)'"
        )
        return int(cur.fetchone()[0])


def _print_summary(plan: dict[str, Any], applied: int | None, remaining: int | None) -> None:
    print(f"matched (have Linear title):  {len(plan['matched'])}")
    print(f"unmatched (no Linear title):  {len(plan['unmatched'])}")
    if applied is not None:
        print(f"applied (rows updated):       {applied}")
    if remaining is not None:
        print(f"remaining bad-title rows:     {remaining}")
    if plan["unmatched"]:
        print("\nUnmatched ids (no Linear issue, or Linear issue has no title):")
        for task_id in plan["unmatched"]:
            print(f"  {task_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Mutate Postgres (default dry-run)")
    args = parser.parse_args(argv)

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed; pip install psycopg")
        return 2

    linear_titles = fetch_linear_titles()
    if not linear_titles:
        logger.warning("Linear returned 0 issues — backfill aborted")
        return 1

    with psycopg.connect(_dsn(), prepare_threshold=None) as conn:
        plan = plan_backfill(conn, linear_titles)
        applied: int | None = None
        remaining: int | None = None
        if args.apply:
            applied = apply_backfill(conn, plan["matched"])
            logger.info("applied %d rows", applied)
            remaining = count_remaining(conn)
    _print_summary(plan, applied, remaining)
    return 0


if __name__ == "__main__":
    sys.exit(main())
