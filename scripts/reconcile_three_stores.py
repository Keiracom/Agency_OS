#!/usr/bin/env python3
"""reconcile_three_stores.py — KEI-230 K4 — belt-and-braces 3-store reconciler.

Walks Linear + Postgres public.tasks + bd-Dolt, builds a canonical join
table on (KEI-N, bd_id), and detects drift (present in 1-of-3, 2-of-3,
or all-3-but-divergent).

KEI-237 (Dave ratified 2026-05-20) — the reconciler RAISES A FLAG for
human review; it does NOT auto-fix. ALL drift buckets (field_drift AND
the three missing_* buckets) are flag-only. `--apply` posts ONE
consolidated drift alert to the existing Slack alert path (#ceo by
default) — the same channel the other scripts/alerts/* monitors use. It
no longer emits sync_events and creates no new table. Propagation is
handled by a controlled one-way push and/or a human acting on the
alert — never by this detector. This removes the auto-fix feedback loop
(reconciler emits event → orchestrator writes store → trigger emits
event → …).

Generalises scripts/reconcile_linear_supabase.py — which only does the
Linear→Postgres direction one-shot — to a 3-way reconciler safe to run
on a 30-min systemd timer.

Usage:
    python3 scripts/reconcile_three_stores.py            # dry-run summary
    python3 scripts/reconcile_three_stores.py --apply    # post drift alert
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

# KEI-237 — drift alerts route to the existing Slack alert path (same bot-token
# chat.postMessage the scripts/alerts/* monitors use). #ceo is the human-review
# surface; env-overridable.
_SLACK_API_URL = "https://slack.com/api/chat.postMessage"
_CEO_CHANNEL_DEFAULT = "C0B2PM3TV0B"

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

    KEI-237 (c) — comparison is tightened: both sides are normalised
    (strip + lower-case) so field-format noise (casing, surrounding
    whitespace) cannot raise a false flag. Only the mapped `status` enum
    is compared — timestamps (updated_at etc.) are never compared, so
    timestamp jitter cannot drift-flag either.
    """
    stores = entry["stores"]
    linear_iss = stores.get("linear") or {}
    pg_row = stores.get("postgres") or {}
    canonical = _linear_canonical_status(linear_iss)
    if canonical is None:
        return False
    norm_actual = str(pg_row.get("status") or "").strip().lower()
    norm_canonical = str(canonical).strip().lower()
    # Postgres-only / sticky terminal statuses — not drift.
    if norm_actual in ("dismissed", "blocked", "done", "cancelled"):
        return False
    # NULL/empty pg.status with a real canonical IS drift — the row exists
    # but has no status set; the canonical value is worth surfacing.
    if not norm_actual:
        return True
    return norm_actual != norm_canonical


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


# Drift buckets that become reviewable flags. `in_all_three` is the
# healthy bucket — never flagged.
_FLAG_BUCKETS = ("missing_postgres", "missing_bd", "missing_linear", "field_drift")


def post_to_slack(text: str, channel: str) -> bool:
    """Best-effort Slack post via bot-token chat.postMessage. Returns True on ok.

    Mirrors the proven pattern in scripts/alerts/service_health_monitor.py —
    the existing alert path. No retry, no exception propagation: a drift
    alert that fails to post must not crash the timer.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post drift alert")
        return False
    payload = json.dumps(
        {"channel": channel, "text": text, "username": "DriftReconciler", "icon_emoji": ":mag:"}
    ).encode("utf-8")
    req = urllib.request.Request(
        _SLACK_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return bool(json.loads(r.read()).get("ok"))
    except (OSError, json.JSONDecodeError) as exc:
        # urllib.error.URLError subclasses OSError — OSError covers it.
        logger.warning("Slack drift-alert post failed: %s", exc)
        return False


def _field_drift_detail(entry: dict[str, Any]) -> str:
    """One-line linear-state vs pg-status detail for a field_drift entry."""
    linear_iss = entry["stores"].get("linear") or {}
    pg_row = entry["stores"].get("postgres") or {}
    state = (linear_iss.get("state") or {}).get("type", "?")
    return f"{entry['kei']} (linear={state} pg={pg_row.get('status')})"


def _format_drift_alert(drift: dict[str, list[dict[str, Any]]]) -> str | None:
    """Build the consolidated drift alert text. None when there is no drift.

    One message summarising every flagged bucket — KEI lists for the
    missing_* buckets, linear-vs-pg detail for field_drift. The reviewer
    resolves manually or via the controlled one-way push.
    """
    total = sum(len(drift.get(b, [])) for b in _FLAG_BUCKETS)
    if total == 0:
        return None
    lines = [f"[DRIFT] reconcile_three_stores — {total} KEI(s) need human review"]
    for bucket in _FLAG_BUCKETS:
        entries = drift.get(bucket, [])
        if not entries:
            continue
        if bucket == "field_drift":
            detail = ", ".join(_field_drift_detail(e) for e in entries[:20])
        else:
            detail = ", ".join(e["kei"] for e in entries[:20])
        more = f" (+{len(entries) - 20} more)" if len(entries) > 20 else ""
        lines.append(f"  {bucket} ({len(entries)}): {detail}{more}")
    lines.append("Flag-only — no auto-fix. Resolve manually or via the one-way push.")
    return "\n".join(lines)


def _post_drift_alert(drift: dict[str, list[dict[str, Any]]]) -> int:
    """Post one consolidated drift alert to #ceo. Returns flagged-KEI count.

    KEI-237 — replaces sync_event emission. The reconciler DETECTS and
    FLAGS via the existing Slack alert path; it does not auto-fix and
    creates no new table.
    """
    text = _format_drift_alert(drift)
    if text is None:
        logger.info("no drift — no alert posted")
        return 0
    channel = os.environ.get("DRIFT_ALERT_CHANNEL", _CEO_CHANNEL_DEFAULT)
    ok = post_to_slack(text, channel)
    total = sum(len(drift.get(b, [])) for b in _FLAG_BUCKETS)
    logger.info("drift alert posted=%s — %d KEI(s) flagged", ok, total)
    return total


def _print_summary(drift: dict[str, list[dict[str, Any]]], flagged: int | None) -> None:
    print(f"in_all_three:    {len(drift['in_all_three'])}")
    print(f"missing_postgres:{len(drift['missing_postgres'])}")
    print(f"missing_bd:      {len(drift['missing_bd'])}")
    print(f"missing_linear:  {len(drift['missing_linear'])}")
    print(f"field_drift:     {len(drift.get('field_drift', []))}")
    if flagged is not None:
        print(f"alert_flagged:   {flagged}")
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
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Post the drift alert to Slack #ceo (default dry-run, no alert)",
    )
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
    flagged: int | None = None
    if args.apply:
        flagged = _post_drift_alert(drift)
    _print_summary(drift, flagged)
    return 0


if __name__ == "__main__":
    sys.exit(main())
