#!/usr/bin/env python3
"""bd_resolve.py — KEI-79 CLI for resolving an awaiting ceo_decisions row.

Flips an awaiting escalation to resolved and restores the task to active so
the original claimant can resume.  Two-write transaction, fail-open Slack
notification after commit.

Usage:
    bd resolve --task <id> --pick <option> [--outcome <text>] [--callsign <c>]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ---------------------------------------------------------------------------
# Helpers (shared pattern — mirrors bd_escalate.py)
# ---------------------------------------------------------------------------


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _callsign(override: str | None = None) -> str:
    if override:
        return override
    return os.environ.get("CALLSIGN") or os.environ.get("TASKS_CALLSIGN") or "dave"


def _sanitize(value: str) -> str:
    """Strip newlines/CRs from user-supplied strings before logging (S5145)."""
    return value.replace("\n", " ").replace("\r", " ") if value else value


# ---------------------------------------------------------------------------
# Core logic — extracted for testability (S3776: keeps main() shallow)
# ---------------------------------------------------------------------------


def fetch_awaiting_decision(cur: object, task_id: str) -> tuple[str, list[str]]:
    """Return (decision_id, options) for the most-recent awaiting row.

    Raises SystemExit(2) with a human-readable message when none exists.
    """
    cur.execute(  # type: ignore[attr-defined]
        "SELECT id, options FROM public.ceo_decisions "
        "WHERE task_id=%s AND status='awaiting' "
        "ORDER BY requested_at DESC LIMIT 1",
        (task_id,),
    )
    row = cur.fetchone()  # type: ignore[attr-defined]
    if row is None:
        print(f"no awaiting decision for task {task_id}", file=sys.stderr)
        raise SystemExit(2)
    decision_id: str = str(row[0])
    options: list[str] = list(row[1]) if row[1] else []
    return decision_id, options


def validate_pick(pick: str, options: list[str], task_id: str) -> None:
    """Exit 2 if pick is not in the declared options list."""
    if options and pick not in options:
        formatted = ", ".join(options)
        print(f"pick '{pick}' not in options [{formatted}]", file=sys.stderr)
        raise SystemExit(2)


def apply_resolve(
    cur: object,
    decision_id: str,
    task_id: str,
    pick: str,
    outcome: str | None,
    resolved_by: str,
) -> None:
    """Write both UPDATE statements inside the caller's transaction."""
    cur.execute(  # type: ignore[attr-defined]
        "UPDATE public.ceo_decisions "
        "SET status='resolved', dave_choice=%s, decision_outcome=%s, "
        "    resolved_by=%s, resolved_at=NOW(), updated_at=NOW() "
        "WHERE id=%s",
        (pick, outcome, resolved_by, decision_id),
    )
    # WHERE status='escalated' guards against double-applying on a task that
    # was manually unstuck — fail-soft policy: ceo_decisions still resolved
    # but tasks row untouched.
    cur.execute(  # type: ignore[attr-defined]
        "UPDATE public.tasks "
        "SET status='active', updated_at=NOW() "
        "WHERE id=%s AND status='escalated'",
        (task_id,),
    )


def _build_ceo_text(resolved_by: str, task_id: str, pick: str, outcome: str | None) -> str:
    lines = [
        f"*[RESOLVED:{resolved_by}]* {task_id}",
        f"  - Decision: {pick}",
    ]
    if outcome:
        lines.append(f"  - Outcome: {outcome}")
    lines.append("  - Task restored to active — claimant can resume.")
    return "\n".join(lines)


def _post_resolution(resolved_by: str, task_id: str, pick: str, outcome: str | None) -> None:
    """Best-effort #ceo notification — never raises."""
    try:
        from src.slack_bot.direct_post import post_to_ceo

        text = _build_ceo_text(resolved_by, task_id, pick, outcome)
        post_to_ceo(text)
    except Exception as exc:  # noqa: BLE001
        print(f"warn: ceo post failed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def resolve(args: argparse.Namespace) -> int:
    import psycopg

    resolved_by = _callsign(args.callsign)
    task_id: str = args.task
    pick: str = args.pick
    outcome: str | None = args.outcome

    try:
        with psycopg.connect(_dsn(), prepare_threshold=None, autocommit=False) as conn:
            with conn.cursor() as cur:
                decision_id, options = fetch_awaiting_decision(cur, task_id)
                validate_pick(pick, options, task_id)
                apply_resolve(cur, decision_id, task_id, pick, outcome, resolved_by)
            conn.commit()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: transaction failed: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "task_id": _sanitize(task_id),
                "pick": _sanitize(pick),
                "resolved_by": _sanitize(resolved_by),
                "outcome": _sanitize(outcome) if outcome else None,
            }
        )
    )

    try:
        _post_resolution(resolved_by, task_id, pick, outcome)
    except Exception as exc:  # noqa: BLE001
        print(f"warn: ceo post failed: {exc}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bd resolve")
    p.add_argument("--task", required=True, help="task ID (e.g. KEI-79)")
    p.add_argument("--pick", required=True, help="option value that matches ceo_decisions.options")
    p.add_argument("--outcome", default=None, help="free-text decision outcome (optional)")
    p.add_argument("--callsign", default=None, help="override resolved_by (default: CALLSIGN env)")
    args = p.parse_args(argv)
    return resolve(args)


if __name__ == "__main__":
    raise SystemExit(main())
