#!/usr/bin/env python3
"""reconcile_three_stores.py — KEI-230 K4 — belt-and-braces 3-store reconciler.

Walks Linear + Postgres public.tasks + bd-Dolt, builds a canonical join
table on (KEI-N, bd_id), detects drift (present in 1-of-3, 2-of-3, or
all-3-but-divergent), and emits sync_events to backfill the missing
rows. The K3 sync_orchestrator drains the events and writes to the
target stores.

Generalises scripts/reconcile_linear_supabase.py — which only does the
Linear→Postgres direction one-shot — to a 3-way reconciler safe to run
on a 30-min systemd timer.

Usage:
    python3 scripts/reconcile_three_stores.py            # dry-run summary
    python3 scripts/reconcile_three_stores.py --apply    # emit events to sync_events
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

logger = logging.getLogger("reconcile_three_stores")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_LINEAR_TEAM_ID_DEFAULT = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"  # Keiracom
_BD_BIN_DEFAULT = os.path.expanduser("~/.local/bin/bd")

# Linear StateType → public.tasks.status. Mirrors webhook mapping.
# KEI-235-followup: Postgres tasks_status_check CHECK constraint allows
# (available, active, pending_review, ready_for_execution, done, blocked,
# dismissed) — NOT 'cancelled'. Linear's `canceled` therefore maps to
# Postgres `dismissed`. CheckViolations on the old (canceled→cancelled)
# mapping froze ~30 sync events 2026-05-19 14:42 UTC.
LINEAR_STATE_TO_TASK_STATUS: dict[str, str] = {
    "backlog": "available",
    "unstarted": "available",
    "triage": "available",
    "started": "active",
    "completed": "done",
    "canceled": "dismissed",
}


# ---------------------------------------------------------------------------
# Store readers.
# ---------------------------------------------------------------------------


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _bd_bin() -> str:
    return os.environ.get("AGENCY_OS_BD_BIN", _BD_BIN_DEFAULT)


def _fetch_linear_issues(api_key: str, team_id: str) -> list[dict[str, Any]]:
    """Paginate through all Linear issues for the team."""
    # KEI-233: Linear schema changed — team.id filter now requires ID! not String!.
    # Old `$teamId: String!` was accepted historically; current Linear validates
    # strictly and returns GRAPHQL_VALIDATION_FAILED on a mismatch.
    query = """
    query($teamId: ID!, $after: String) {
      issues(filter: { team: { id: { eq: $teamId } } }, first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes { identifier title priority url state { type name } }
      }
    }
    """
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body = json.dumps(
            {"query": query, "variables": {"teamId": team_id, "after": cursor}}
        ).encode()
        req = urllib.request.Request(
            _LINEAR_GRAPHQL_URL,
            data=body,
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read() or "null")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Linear GraphQL page failed: %s", exc)
            return out
        page = ((payload or {}).get("data") or {}).get("issues") or {}
        out.extend(page.get("nodes") or [])
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
    return out


def _fetch_postgres_tasks(conn: Any) -> list[dict[str, Any]]:
    """SELECT * FROM public.tasks. Returns minimal projection for join."""
    out: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, bd_id, title, status, priority, linear_url, updated_at FROM public.tasks"
        )
        for row in cur.fetchall():
            out.append(
                {
                    "id": row[0],
                    "bd_id": row[1],
                    "title": row[2],
                    "status": row[3],
                    "priority": row[4],
                    "linear_url": row[5],
                    "updated_at": row[6],
                }
            )
    return out


def _fetch_bd_issues() -> list[dict[str, Any]]:
    """Return bd issues (open + in_progress + closed)."""
    try:
        proc = subprocess.run(  # noqa: S603 — controlled args
            [_bd_bin(), "list", "--all", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("bd list --all --json failed: %s", exc)
        return []
    if proc.returncode != 0:
        return []
    try:
        return json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Join + drift detection.
# ---------------------------------------------------------------------------


def _kei_from_url(url: str | None) -> str | None:
    """Extract KEI-N from a Linear URL of any shape."""
    if not url:
        return None
    parts = url.split("/issue/", 1)
    if len(parts) != 2:
        return None
    return parts[1].split("/", 1)[0]


def build_join_table(
    linear_issues: list[dict[str, Any]],
    postgres_rows: list[dict[str, Any]],
    bd_issues: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build {canonical_kei: {linear, postgres, bd}} — None if absent from store."""
    table: dict[str, dict[str, Any]] = {}
    for iss in linear_issues:
        kei = iss.get("identifier")
        if kei:
            table.setdefault(kei, {})["linear"] = iss
    for row in postgres_rows:
        kei = row["id"] if row["id"].startswith("KEI-") else _kei_from_url(row.get("linear_url"))
        if kei:
            table.setdefault(kei, {})["postgres"] = row
    for iss in bd_issues:
        ref = iss.get("external_ref")
        kei = _kei_from_url(ref)
        if kei:
            table.setdefault(kei, {})["bd"] = iss
    return table


def _linear_canonical_status(linear_iss: dict[str, Any]) -> str | None:
    """Return the Postgres-shaped status mapped from Linear state, or None."""
    state_type = (linear_iss.get("state") or {}).get("type") or ""
    return LINEAR_STATE_TO_TASK_STATUS.get(state_type)


def _has_field_drift(entry: dict[str, Any]) -> bool:
    """True if a KEI present in all 3 stores has a stale Postgres status.

    Treats Linear as canonical. Postgres-only buckets (`dismissed`, `blocked`)
    have no Linear equivalent — never flagged as drift. Postgres `done` /
    `cancelled` are sticky (matches the orchestrator's done-preservation
    invariant in `_dispatch_postgres`); never re-opened automatically here.
    """
    stores = entry["stores"]
    linear_iss = stores.get("linear") or {}
    pg_row = stores.get("postgres") or {}
    canonical = _linear_canonical_status(linear_iss)
    if canonical is None:
        return False
    actual = pg_row.get("status")
    if actual in ("dismissed", "blocked"):
        return False
    if actual in ("done", "cancelled"):
        return False
    # NULL pg.status counts as drift — the row exists but has no status set,
    # so propagating Linear's canonical value is strictly an improvement.
    return actual != canonical


def detect_drift(table: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Classify each KEI into one of five buckets — four presence buckets plus
    `field_drift` for KEIs present in all three stores but with a stale
    Postgres status vs Linear (KEI-233)."""
    out: dict[str, list[dict[str, Any]]] = {
        "in_all_three": [],
        "missing_postgres": [],
        "missing_bd": [],
        "missing_linear": [],
        "field_drift": [],
    }
    for kei, stores in table.items():
        # `is not None` (not truthiness) — an empty dict {} from a row with
        # all-NULL fields still counts as "present in this store".
        has = {k for k in ("linear", "postgres", "bd") if stores.get(k) is not None}
        entry = {"kei": kei, "stores": stores}
        if has == {"linear", "postgres", "bd"}:
            out["in_all_three"].append(entry)
            if _has_field_drift(entry):
                out["field_drift"].append(entry)
        elif "postgres" not in has:
            out["missing_postgres"].append(entry)
        elif "bd" not in has:
            out["missing_bd"].append(entry)
        elif "linear" not in has:
            out["missing_linear"].append(entry)
    return out


def _build_create_payload(kei: str, stores: dict[str, Any]) -> dict[str, Any]:
    """Pick the canonical record from whichever stores have it.

    Used for the `missing_*` buckets where the store-being-backfilled has
    no row yet — Linear is preferred as the seed because it's where Dave
    creates KEIs (title/priority/intent live there first).
    """
    linear_iss = stores.get("linear") or {}
    bd_iss = stores.get("bd") or {}
    pg_row = stores.get("postgres") or {}
    title = linear_iss.get("title") or pg_row.get("title") or bd_iss.get("title") or "(no title)"
    linear_state_type = (linear_iss.get("state") or {}).get("type") or ""
    status = (
        LINEAR_STATE_TO_TASK_STATUS.get(linear_state_type) or pg_row.get("status") or "available"
    )
    priority = linear_iss.get("priority") or pg_row.get("priority")
    url = (
        linear_iss.get("url")
        or pg_row.get("linear_url")
        or f"https://linear.app/keiracom/issue/{kei}"
    )
    return {
        "id": kei,
        "bd_id": bd_iss.get("id") or pg_row.get("bd_id"),
        "title": title,
        "status": status,
        "priority": priority,
        "linear_url": url,
    }


def _build_postgres_payload(kei: str, stores: dict[str, Any]) -> dict[str, Any]:
    """KEI-237 — build payload from Postgres-as-canonical for field_drift events.

    Under the Dave 2026-05-19 policy (bd=CLI, Postgres=canonical,
    Linear=mirror), field-level drift between Postgres and another store
    is resolved by propagating Postgres's value OUT, never the reverse.
    The orchestrator's `_dispatch_linear` (per KEI-236) only writes
    Linear on terminal `close`/`reopen` transitions, so `update` events
    from this path effectively only correct bd-Dolt — Linear stays
    where it is until a real terminal transition flows from Postgres.
    """
    bd_iss = stores.get("bd") or {}
    pg_row = stores.get("postgres") or {}
    linear_iss = stores.get("linear") or {}
    return {
        "id": kei,
        "bd_id": pg_row.get("bd_id") or bd_iss.get("id"),
        "title": pg_row.get("title") or linear_iss.get("title") or "(no title)",
        "status": pg_row.get("status") or "available",
        "priority": pg_row.get("priority"),
        "linear_url": pg_row.get("linear_url")
        or linear_iss.get("url")
        or f"https://linear.app/keiracom/issue/{kei}",
    }


def _emit_events(conn: Any, drift: dict[str, list[dict[str, Any]]]) -> int:
    """Insert sync_events to backfill missing stores. Returns event count emitted."""
    emitted = 0
    with conn.cursor() as cur:
        # Each "missing X" bucket emits an event from the FIRST present store as origin.
        # K3 then dispatches to the OTHER two (including the missing one).
        for entry in drift["missing_postgres"]:
            origin = "linear" if entry["stores"].get("linear") else "bd"
            payload = _build_create_payload(entry["kei"], entry["stores"])
            cur.execute(
                "SELECT public.fn_emit_sync_event(%s, %s, %s, %s, %s::jsonb)",
                (origin, "create", entry["kei"], payload["bd_id"], json.dumps(payload)),
            )
            emitted += 1
        for entry in drift["missing_bd"]:
            origin = "linear" if entry["stores"].get("linear") else "postgres"
            payload = _build_create_payload(entry["kei"], entry["stores"])
            cur.execute(
                "SELECT public.fn_emit_sync_event(%s, %s, %s, %s, %s::jsonb)",
                (origin, "create", entry["kei"], payload["bd_id"], json.dumps(payload)),
            )
            emitted += 1
        for entry in drift["missing_linear"]:
            origin = "bd" if entry["stores"].get("bd") else "postgres"
            payload = _build_create_payload(entry["kei"], entry["stores"])
            cur.execute(
                "SELECT public.fn_emit_sync_event(%s, %s, %s, %s, %s::jsonb)",
                (origin, "create", entry["kei"], payload["bd_id"], json.dumps(payload)),
            )
            emitted += 1
        # KEI-237 — field-drift bucket: under the new policy Postgres is
        # canonical, so we emit origin=postgres with the Postgres-side
        # payload. The orchestrator (KEI-236) will dispatch to bd (fixes
        # bd-Dolt) but skip the Linear write for `update` events — Linear
        # stays where it is until a real terminal transition flows out
        # via `close`/`reopen` events from the trigger.
        for entry in drift["field_drift"]:
            payload = _build_postgres_payload(entry["kei"], entry["stores"])
            cur.execute(
                "SELECT public.fn_emit_sync_event(%s, %s, %s, %s, %s::jsonb)",
                ("postgres", "update", entry["kei"], payload["bd_id"], json.dumps(payload)),
            )
            emitted += 1
    conn.commit()
    return emitted


def _print_summary(drift: dict[str, list[dict[str, Any]]], emitted: int | None) -> None:
    print(f"in_all_three:    {len(drift['in_all_three'])}")
    print(f"missing_postgres:{len(drift['missing_postgres'])}")
    print(f"missing_bd:      {len(drift['missing_bd'])}")
    print(f"missing_linear:  {len(drift['missing_linear'])}")
    print(f"field_drift:     {len(drift.get('field_drift', []))}")
    if emitted is not None:
        print(f"events_emitted:  {emitted}")
    for bucket in ("missing_postgres", "missing_bd", "missing_linear", "field_drift"):
        if drift.get(bucket):
            print(f"\n{bucket} (first 5):")
            for entry in drift[bucket][:5]:
                if bucket == "field_drift":
                    l = entry["stores"].get("linear") or {}
                    p = entry["stores"].get("postgres") or {}
                    print(
                        f"  {entry['kei']} linear={(l.get('state') or {}).get('type', '?')} pg_status={p.get('status')}"
                    )
                else:
                    print(f"  {entry['kei']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Emit sync_events (default dry-run)")
    args = parser.parse_args(argv)

    api_key = os.environ.get("LINEAR_API_KEY", "")
    team_id = os.environ.get("LINEAR_TEAM_ID", _LINEAR_TEAM_ID_DEFAULT)
    if not api_key:
        logger.error("LINEAR_API_KEY not set")
        return 2

    logger.info("Fetching Linear …")
    linear_issues = _fetch_linear_issues(api_key, team_id)
    logger.info("  → %d Linear issues", len(linear_issues))

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg not installed")
        return 2

    with psycopg.connect(_dsn(), prepare_threshold=None) as conn:
        logger.info("Fetching Postgres …")
        postgres_rows = _fetch_postgres_tasks(conn)
        logger.info("  → %d postgres tasks", len(postgres_rows))

        logger.info("Fetching bd-Dolt …")
        bd_issues = _fetch_bd_issues()
        logger.info("  → %d bd issues", len(bd_issues))

        table = build_join_table(linear_issues, postgres_rows, bd_issues)
        drift = detect_drift(table)
        emitted: int | None = None
        if args.apply:
            emitted = _emit_events(conn, drift)
            logger.info("emitted %d sync_events", emitted)
    _print_summary(drift, emitted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
