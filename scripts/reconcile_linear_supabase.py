#!/usr/bin/env python3
"""reconcile_linear_supabase.py — Linear ↔ Supabase public.tasks reconciliation.

Usage:
  python scripts/reconcile_linear_supabase.py [--apply]

Default is dry-run (prints planned changes, no writes). Pass --apply to mutate.

Algorithm:
  1. Pull all open Linear issues from team Keiracom via Linear GraphQL (paginated).
  2. For each Linear issue: upsert public.tasks with id=identifier, preserving
     done→done state (Max Note 1: never reopen a closed row).
  3. Mark any Supabase open row whose id does NOT match a Linear identifier as
     status='done' with metadata.reconcile_reason='orphan_no_linear_match_<ts>'.
     Rows already done/cancelled are left untouched (done-preservation guarantee).
  4. Print verbatim diff summary at end.

State-preservation contract (Max Note 1):
  A Supabase row already in status=done stays done even if Linear has a matching
  issue (possibly now under a different identifier). The upsert targets the Linear
  identifier key, so an old local KEI-N row (orphan) receives the orphan-reason
  while the correct KEI-M row is created/updated reflecting Linear's true state.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("reconcile_linear_supabase")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# KEI-100 review note 3: import the canonical team-ID constant from the
# webhook module rather than duplicating the literal here. Repo-root must
# be on sys.path because reconcile_linear_supabase.py is invoked as a
# standalone script (`python scripts/reconcile_linear_supabase.py`).
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from src.api.webhooks.linear import LINEAR_TEAM_ID_DEFAULT as _DEFAULT_TEAM_ID  # noqa: E402

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"

# Mirror of LINEAR_STATE_TO_TASK_STATUS from src/api/webhooks/linear.py
LINEAR_STATE_TO_TASK_STATUS: dict[str, str] = {
    "backlog": "available",
    "unstarted": "available",
    "triage": "available",
    "started": "active",
    "completed": "done",
    "canceled": "cancelled",
}


# ---------------------------------------------------------------------------
# Linear API helpers
# ---------------------------------------------------------------------------


def _linear_graphql(api_key: str, query: str, variables: dict | None = None) -> dict | None:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        _LINEAR_GRAPHQL_URL,
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read() or "null")
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Linear GraphQL failed: %s", exc)
        return None


def _fetch_all_linear_issues(api_key: str, team_id: str) -> list[dict[str, Any]]:
    """Paginate through all Linear issues for the team (open + completed)."""
    query = """
    query($teamId: String!, $after: String) {
      issues(
        filter: { team: { id: { eq: $teamId } } }
        first: 100
        after: $after
      ) {
        pageInfo { hasNextPage endCursor }
        nodes {
          identifier
          title
          priority
          url
          state { type name }
        }
      }
    }
    """
    issues: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        variables: dict[str, Any] = {"teamId": team_id}
        if cursor:
            variables["after"] = cursor
        resp = _linear_graphql(api_key, query, variables)
        if resp is None:
            logger.warning("Linear paginate returned None; stopping at %d issues", len(issues))
            break
        data = (resp.get("data") or {}).get("issues") or {}
        nodes = data.get("nodes") or []
        issues.extend(nodes)
        page_info = data.get("pageInfo") or {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return issues


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------


def _get_dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.error("DATABASE_URL / SUPABASE_DB_URL not set")
        sys.exit(2)
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1).replace("+asyncpg", "")


def _fetch_supabase_tasks(conn: Any) -> list[dict[str, Any]]:
    """Return all tasks rows (id, status, metadata) for reconciliation."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, status, metadata FROM public.tasks")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Core reconciliation logic (pure — testable without DB side-effects)
# ---------------------------------------------------------------------------


def compute_reconciliation_plan(
    linear_issues: list[dict[str, Any]],
    supabase_tasks: list[dict[str, Any]],
    timestamp: str,
) -> dict[str, Any]:
    """Derive the full reconciliation plan without mutating anything.

    Returns:
      {
        "upserts": [{"identifier", "title", "status", "linear_url"}, ...],
        "orphans":  [{"id", "reason"}, ...],
      }

    State-preservation contract (Max Note 1):
      - Rows already done/cancelled in Supabase stay that way — we never reopen.
      - When Linear shows an issue as completed, the Supabase upsert sets status=done
        (matching Linear's state), but only for the row keyed by Linear's identifier.
      - Old Supabase rows whose ID doesn't match any Linear identifier receive
        orphan-reason in metadata and status=done — they are NOT deleted.
    """
    linear_by_identifier = {issue["identifier"]: issue for issue in linear_issues}
    supabase_by_id = {row["id"]: row for row in supabase_tasks}

    upserts: list[dict[str, Any]] = []
    for issue in linear_issues:
        identifier = issue["identifier"]
        state_type = (issue.get("state") or {}).get("type") or "unstarted"
        task_status = LINEAR_STATE_TO_TASK_STATUS.get(state_type, "available")
        existing = supabase_by_id.get(identifier)
        # Max Note 1: if already done in Supabase, keep done regardless of Linear state.
        if existing and existing.get("status") in ("done", "cancelled"):
            task_status = existing["status"]
        upserts.append(
            {
                "identifier": identifier,
                "title": issue.get("title") or "(no title)",
                "status": task_status,
                "linear_url": issue.get("url") or f"https://linear.app/keiracom/issue/{identifier}",
            }
        )

    linear_identifiers = set(linear_by_identifier.keys())
    orphans: list[dict[str, Any]] = []
    for row in supabase_tasks:
        row_id = row["id"]
        if row_id in linear_identifiers:
            continue  # handled by upserts
        # Only close rows that are currently open (preserve done/cancelled as-is).
        if row.get("status") in ("done", "cancelled"):
            continue
        orphans.append(
            {
                "id": row_id,
                "reason": f"orphan_no_linear_match_{timestamp}",
            }
        )

    return {"upserts": upserts, "orphans": orphans}


# ---------------------------------------------------------------------------
# DB mutation
# ---------------------------------------------------------------------------


def _apply_upserts(conn: Any, upserts: list[dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        for u in upserts:
            cur.execute(
                """
                INSERT INTO public.tasks (id, title, status, linear_url, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                  SET title      = EXCLUDED.title,
                      status     = CASE
                                     WHEN public.tasks.status IN ('done', 'cancelled')
                                     THEN public.tasks.status
                                     ELSE EXCLUDED.status
                                   END,
                      linear_url = COALESCE(public.tasks.linear_url, EXCLUDED.linear_url),
                      updated_at = NOW()
                """,
                (u["identifier"], u["title"], u["status"], u["linear_url"]),
            )


def _apply_orphans(conn: Any, orphans: list[dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        for o in orphans:
            cur.execute(
                """
                UPDATE public.tasks
                   SET status   = 'done',
                       metadata = jsonb_set(
                                    COALESCE(metadata, '{}'::jsonb),
                                    '{reconcile_reason}',
                                    %s::jsonb
                                  ),
                       updated_at = NOW()
                 WHERE id = %s AND status NOT IN ('done', 'cancelled')
                """,
                (json.dumps(o["reason"]), o["id"]),
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(apply: bool = False) -> None:
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        logger.error("LINEAR_API_KEY not set")
        sys.exit(2)

    team_id = os.environ.get("LINEAR_TEAM_ID", _DEFAULT_TEAM_ID)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    logger.info("Fetching Linear issues for team %s …", team_id)
    linear_issues = _fetch_all_linear_issues(api_key, team_id)
    logger.info("  → %d Linear issues fetched", len(linear_issues))

    dsn = _get_dsn()
    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed; pip install psycopg")
        sys.exit(2)

    # KEI-100 review note 2: prepare_threshold=None per
    # reference_psycopg_supabase_pgbouncer pin — Supabase pooler in txn-mode
    # drops PREPARE, which psycopg3 emits when reuse threshold (default 5)
    # is hit. Single-shot script, low impact, but the canonical guard.
    with psycopg.connect(dsn, connect_timeout=15, prepare_threshold=None) as conn:
        supabase_tasks = _fetch_supabase_tasks(conn)
        logger.info("  → %d Supabase tasks rows fetched", len(supabase_tasks))

        plan = compute_reconciliation_plan(linear_issues, supabase_tasks, timestamp)
        upserts = plan["upserts"]
        orphans = plan["orphans"]

        supabase_open_count = sum(
            1 for r in supabase_tasks if r.get("status") not in ("done", "cancelled")
        )

        if apply:
            logger.info("Applying %d upserts and %d orphan-closes …", len(upserts), len(orphans))
            _apply_upserts(conn, upserts)
            _apply_orphans(conn, orphans)
            conn.commit()
        else:
            logger.info("Dry-run mode — no writes. Pass --apply to mutate.")

    mode = "APPLIED" if apply else "DRY-RUN"
    print(
        f"[{mode}] {len(linear_issues)} Linear open issues / "
        f"{supabase_open_count} Supabase open rows / "
        f"{len(orphans)} orphans closed / "
        f"{len(upserts)} rows touched"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile Linear issues → Supabase public.tasks")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Default is dry-run.",
    )
    args = parser.parse_args()
    main(apply=args.apply)
