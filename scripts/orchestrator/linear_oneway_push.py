#!/usr/bin/env python3
"""linear_oneway_push.py — Agency_OS-1x3x — controlled one-way Supabase→Linear push.

The SOLE sanctioned Linear writer. Per the ratified architecture (Dave
2026-05-20): Linear is the master record + read-only for every agent and
automated process; Supabase public.tasks is the read-write replica; task
STATUS changes propagate Supabase→Linear via THIS push and nothing else.

Design — strictly one-way:
  * Reads public.tasks. Reads nothing from Linear. Writes nothing to
    Supabase except its own watermark / create-intent bookkeeping.
  * Writes Linear only — issueUpdate (status) and issueCreate (GAP-A).
  * STATUS path — pushes ONLY terminal status transitions: a task reaching
    a terminal status (done / dismissed / cancelled) or reopening out of
    one. Pure available↔active churn is never pushed.
  * CREATE path (GAP-A) — a task explicitly opted-in via
    linear_create_pending=TRUE with no Linear issue yet → issueCreate, then
    record linear_url back. The opt-in flag is mandatory: public.tasks
    holds non-KEI operational rows (REVIEW-PR-*, smoke tests) that must
    never be mirrored. Crash-safe: the intent is consumed BEFORE the
    create, so a crash yields a recoverable missed-create, never a
    duplicate. Dormant until the KEI-create redirect sites set the flag.

Idempotency + loop-safety:
  * linear_synced_status is the watermark — the status value last pushed.
    A transition is pending only when status <> linear_synced_status and
    a terminal status is on one side. After a successful Linear write the
    push sets linear_synced_status = status; a re-run then skips. No
    double-write.
  * The watermark UPDATE touches only linear_synced_status, so the
    KEI-228 emit trigger's Agency_OS-1x3x guard skips it — the push never
    echoes back into sync_events as a Supabase change.
  * The Linear write is actor-tagged: Linear records the actor as the API
    key's user (LINEAR_VIEWER_ID). The Linear webhook's KEI-238 self-echo
    suppression drops updates whose actor == LINEAR_VIEWER_ID — so a push
    that lands does not echo back as a Supabase change. LINEAR_VIEWER_ID
    MUST be set in the environment (the install script verifies it).

This is a SEPARATE clean component — NOT a revival of sync_orchestrator's
_dispatch_linear (hard-locked no-op since Part 2). It runs as a systemd
service so the PreToolUse ad-hoc-agent Linear-write block does not gate
it; this is the sanctioned path.

Usage:
    python3 scripts/orchestrator/linear_oneway_push.py            # dry-run
    python3 scripts/orchestrator/linear_oneway_push.py --apply    # push to Linear

Exit codes:
  0  clean (dry-run, or every pending push succeeded)
  1  one or more pushes failed (logged + alerted — fail-loud)
  2  invocation/config error (no DSN, no LINEAR_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import urllib.request
from typing import Any

logger = logging.getLogger("linear_oneway_push")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_NATS_BIN = "/usr/local/bin/nats"
_ALERT_SUBJECT = "keiracom.elliot.inbox"

# Postgres terminal statuses — reaching or leaving one of these is the only
# transition class the push propagates. tasks_status_check allows
# 'dismissed' (Linear canceled maps there); 'cancelled' kept for legacy rows.
TERMINAL_STATUSES = ("done", "dismissed", "cancelled")

# public.tasks.status → LINEAR_STATE_ID_<SUFFIX> env var. The push resolves
# the target Linear workflow-state UUID from these env vars — it never reads
# Linear to discover state ids.
_STATUS_TO_STATE_SUFFIX: dict[str, str] = {
    "done": "DONE",
    "dismissed": "CANCELED",
    "cancelled": "CANCELED",
    "available": "TODO",
    "active": "ACTIVE",
    "pending_review": "IN_REVIEW",
    "ready_for_execution": "ACTIVE",
    "blocked": "ACTIVE",
}

_ISSUE_UPDATE_MUTATION = (
    "mutation($id:String!,$state:String!){issueUpdate(id:$id,input:{stateId:$state}){success}}"
)

# GAP-A — Keiracom Linear team UUID (issueCreate needs teamId). Env override.
_LINEAR_TEAM_ID_DEFAULT = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"
_ISSUE_CREATE_MUTATION = (
    "mutation($input:IssueCreateInput!){issueCreate(input:$input){success issue{identifier url}}}"
)
# Titles Postgres treats as "no usable title" — never create a Linear issue
# from one (mirrors the Part 1 backfill predicate).
_BAD_TITLES = ("", "(no title)")


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


def _linear_state_id(status: str) -> str:
    """Resolve a public.tasks.status to its Linear workflow-state UUID."""
    suffix = _STATUS_TO_STATE_SUFFIX.get(status)
    if not suffix:
        return ""
    return os.environ.get(f"LINEAR_STATE_ID_{suffix}", "")


def _linear_team_id() -> str:
    """Keiracom Linear team UUID for issueCreate. Has a default — never fails."""
    return os.environ.get("LINEAR_TEAM_ID", _LINEAR_TEAM_ID_DEFAULT)


def is_terminal_transition(status: str | None, synced: str | None) -> bool:
    """True when (status, watermark) is a terminal transition worth pushing.

    Terminal transition = the status changed AND a terminal status is on one
    side: a CLOSE (reaching done/cancelled) or a REOPEN (leaving one). Two
    non-terminal statuses differing (available↔active) is plain workflow
    churn — not pushed. A never-pushed non-terminal task (synced is NULL,
    status non-terminal) is likewise skipped.
    """
    if status == synced:
        return False
    return status in TERMINAL_STATUSES or synced in TERMINAL_STATUSES


def fetch_pending(conn: Any) -> list[dict[str, str | None]]:
    """Return tasks whose terminal-transition status has not reached Linear.

    The SQL is a coarse candidate filter (KEI rows whose status differs from
    the watermark); is_terminal_transition() is the precise gate.
    """
    out: list[dict[str, str | None]] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, status, linear_synced_status FROM public.tasks "
            "WHERE id LIKE 'KEI-%' AND status IS DISTINCT FROM linear_synced_status"
        )
        rows = cur.fetchall()
    for row in rows:
        if is_terminal_transition(row[1], row[2]):
            out.append({"id": row[0], "status": row[1], "synced": row[2]})
    return out


def _linear_graphql(api_key: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """POST a GraphQL op to Linear and return the parsed payload.

    Shared by every Linear write (issueUpdate, issueCreate). Raises
    RuntimeError on transport failure or top-level GraphQL errors. The
    caller inspects payload['data'] for the operation-specific result.
    """
    body = json.dumps({"query": query, "variables": variables}).encode()
    # S310: the URL is the fixed https Linear GraphQL endpoint, not user input.
    req = urllib.request.Request(  # noqa: S310
        _LINEAR_GRAPHQL_URL,
        data=body,
        method="POST",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            payload = json.loads(resp.read() or "null")
    except (OSError, json.JSONDecodeError) as exc:
        # urllib.error.URLError is an OSError subclass — OSError covers it.
        raise RuntimeError(f"linear network error: {exc}") from exc
    if payload and payload.get("errors"):
        raise RuntimeError(f"linear GraphQL errors: {payload['errors']}")
    return payload or {}


def _apply_task_update(conn: Any, sql: str, params: tuple) -> None:
    """Run one bookkeeping UPDATE on public.tasks and commit. Shared by the
    watermark / create-intent writers — each passes its own literal SQL."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
    conn.commit()


def push_to_linear(api_key: str, kei: str, state_id: str) -> None:
    """POST a single issueUpdate mutation. Raises RuntimeError on any failure.

    Linear's issueUpdate accepts the KEI-N identifier as `id` (proven by the
    legacy completion_sync_worker path).
    """
    payload = _linear_graphql(api_key, _ISSUE_UPDATE_MUTATION, {"id": kei, "state": state_id})
    ok = ((payload.get("data") or {}).get("issueUpdate") or {}).get("success")
    if not ok:
        raise RuntimeError(f"linear rejected issueUpdate: {payload}")


def mark_synced(conn: Any, kei: str, status: str | None) -> None:
    """Advance the watermark after a successful push. The KEI-228 emit
    trigger's watermark guard skips this UPDATE — no sync_event echo."""
    _apply_task_update(
        conn, "UPDATE public.tasks SET linear_synced_status = %s WHERE id = %s", (status, kei)
    )


# ───────────────────────── GAP-A: KEI creation path ─────────────────────────


def fetch_create_pending(conn: Any) -> list[dict[str, Any]]:
    """Return tasks opted-in for Linear creation that have no Linear issue yet.

    Candidate = linear_create_pending = TRUE AND no linear_url. The opt-in flag
    is mandatory: public.tasks holds non-KEI operational rows (REVIEW-PR-*,
    smoke tests) with no linear_url that must never be mirrored — only an
    explicitly-flagged row is a create candidate. A junk title is also skipped.
    """
    out: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, description, priority FROM public.tasks "
            "WHERE linear_create_pending IS TRUE "
            "AND (linear_url IS NULL OR linear_url = '')"
        )
        rows = cur.fetchall()
    for row in rows:
        title = row[1]
        if not title or title in _BAD_TITLES:
            logger.warning("create skipped for %s — no usable title", row[0])
            continue
        out.append({"id": row[0], "title": title, "description": row[2], "priority": row[3]})
    return out


def create_in_linear(
    api_key: str, team_id: str, title: str, description: str | None, priority: int | None
) -> str:
    """POST a single issueCreate mutation; return the new Linear issue URL.

    Raises RuntimeError on any failure. The only Linear-create WRITE in the
    component. New issues take the team's default workflow state — the status
    path syncs the real status on a later tick.
    """
    issue_input: dict[str, Any] = {"teamId": team_id, "title": title}
    if description:
        issue_input["description"] = description
    if priority is not None and 0 <= priority <= 4:
        issue_input["priority"] = priority
    payload = _linear_graphql(api_key, _ISSUE_CREATE_MUTATION, {"input": issue_input})
    result = (payload.get("data") or {}).get("issueCreate") or {}
    if not result.get("success") or not (result.get("issue") or {}).get("url"):
        raise RuntimeError(f"linear rejected issueCreate: {payload}")
    return str(result["issue"]["url"])


def consume_create_intent(conn: Any, task_id: str) -> None:
    """Clear linear_create_pending BEFORE the issueCreate — crash-safe.

    Consuming the intent first means a crash mid-create yields a recoverable
    missed-create, never a corrupting duplicate Linear issue. A clean failure
    re-arms the flag (rearm_create_intent) so the next tick retries.
    """
    _apply_task_update(
        conn, "UPDATE public.tasks SET linear_create_pending = FALSE WHERE id = %s", (task_id,)
    )


def record_created_url(conn: Any, task_id: str, url: str) -> None:
    """Record the new Linear URL on the task row — the create watermark."""
    _apply_task_update(
        conn, "UPDATE public.tasks SET linear_url = %s WHERE id = %s", (url, task_id)
    )


def rearm_create_intent(conn: Any, task_id: str) -> None:
    """Re-set linear_create_pending after a CLEAN create failure so the next
    tick retries. Only an actual crash (not a clean failure) leaves the intent
    consumed — that surfaces as a missed-create, never a duplicate."""
    _apply_task_update(
        conn, "UPDATE public.tasks SET linear_create_pending = TRUE WHERE id = %s", (task_id,)
    )


def _emit_failure_alert(failures: list[tuple[str, str]]) -> None:
    """Fail-loud — publish a structured alert to elliot's inbox. The alert
    itself is best-effort (a NATS outage must not mask the push failure,
    which is already logged at ERROR)."""
    lines = "\n".join(f"  {kei}: {err}" for kei, err in failures)
    text = (
        f"[ALERT:linear-oneway-push] {len(failures)} Linear push/create op(s) "
        f"FAILED — Supabase→Linear sync NOT propagated:\n{lines}"
    )
    envelope = {"from": "linear-oneway-push", "kind": "blocker", "summary": text}
    try:
        # S603: fixed argument list, no shell, no user-controlled input.
        subprocess.run(  # noqa: S603
            [_NATS_BIN, "pub", _ALERT_SUBJECT, json.dumps(envelope)],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        # FileNotFoundError is an OSError subclass — OSError covers it.
        logger.exception("failure-alert NATS publish failed")


def _run_status_pushes(
    conn: Any, api_key: str, *, apply: bool, stats: dict[str, Any], failures: list
) -> None:
    """Status-transition push loop (Part 4). Mutates stats + failures."""
    for task in fetch_pending(conn):
        kei = str(task["id"])
        status = task["status"]
        stats["pending"] += 1
        if not apply:
            # Dry-run only counts; it never writes Linear, so it must not
            # resolve or require LINEAR_STATE_ID (absent in CI).
            logger.info("[dry-run] would push %s → %s", kei, status)
            continue
        state_id = _linear_state_id(status or "")
        if not state_id:
            msg = f"no LINEAR_STATE_ID for status {status!r}"
            logger.error("%s: %s", kei, msg)
            failures.append((kei, msg))
            stats["failed"] += 1
            continue
        try:
            push_to_linear(api_key, kei, state_id)
            mark_synced(conn, kei, status)
            stats["pushed"] += 1
            logger.info("pushed %s → %s", kei, status)
        except RuntimeError as exc:
            logger.exception("push failed for %s", kei)
            failures.append((kei, str(exc)))
            stats["failed"] += 1


def _run_creates(
    conn: Any, api_key: str, *, apply: bool, stats: dict[str, Any], failures: list
) -> None:
    """GAP-A KEI-creation loop. Mutates stats + failures. Crash-safe: the
    intent is consumed BEFORE issueCreate; a clean failure re-arms it."""
    team_id = _linear_team_id()
    for task in fetch_create_pending(conn):
        task_id = str(task["id"])
        stats["create_pending"] += 1
        if not apply:
            # Dry-run never writes — does not consume the intent or call Linear.
            logger.info("[dry-run] would create Linear issue for %s", task_id)
            continue
        consume_create_intent(conn, task_id)  # crash-safe: consume before write
        try:
            url = create_in_linear(
                api_key, team_id, task["title"], task["description"], task["priority"]
            )
            record_created_url(conn, task_id, url)
            stats["created"] += 1
            logger.info("created Linear issue for %s → %s", task_id, url)
        except RuntimeError as exc:
            rearm_create_intent(conn, task_id)  # clean failure — retry next tick
            logger.exception("create failed for %s", task_id)
            failures.append((task_id, str(exc)))
            stats["create_failed"] += 1


def run_once(conn: Any, api_key: str, *, apply: bool) -> dict[str, Any]:
    """Push pending terminal transitions AND create Linear issues for opted-in
    title-less tasks. Returns a stats dict."""
    stats: dict[str, Any] = {
        "pending": 0,
        "pushed": 0,
        "failed": 0,
        "create_pending": 0,
        "created": 0,
        "create_failed": 0,
    }
    failures: list[tuple[str, str]] = []
    _run_status_pushes(conn, api_key, apply=apply, stats=stats, failures=failures)
    _run_creates(conn, api_key, apply=apply, stats=stats, failures=failures)
    if failures:
        _emit_failure_alert(failures)
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write Linear (default dry-run)")
    args = parser.parse_args(argv)

    try:
        api_key = _linear_api_key()
        dsn = _dsn()
    except RuntimeError:
        logger.exception("startup config error")
        return 2

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed")
        return 2

    with psycopg.connect(dsn, prepare_threshold=None) as conn:
        stats = run_once(conn, api_key, apply=args.apply)

    print(
        f"status — pending: {stats['pending']}  pushed: {stats['pushed']}  "
        f"failed: {stats['failed']}\n"
        f"create — pending: {stats['create_pending']}  created: {stats['created']}  "
        f"failed: {stats['create_failed']}"
    )
    return 1 if (stats["failed"] or stats["create_failed"]) else 0


if __name__ == "__main__":
    sys.exit(main())
