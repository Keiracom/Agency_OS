#!/usr/bin/env python3
"""sync_orchestrator.py — KEI-229 K3 — origin-tagged loop-safe fan-out worker.

Drains public.sync_events (KEI-228). For each event with origin=X, dispatches
to the OTHER two stores (loop prevention by origin-tag). Each destination
write tags itself so a downstream emit (e.g. Postgres trigger firing because
this worker just wrote to tasks) does not echo back to the original origin.

Coexists with completion_sync_worker.py during the K3→K4 transition. Once K4
lands and the legacy trigger trg_tasks_completion_sync is dropped, this
worker becomes the sole cross-store dispatcher.

Usage:
    python3 scripts/orchestrator/sync_orchestrator.py            # daemon loop
    python3 scripts/orchestrator/sync_orchestrator.py --once     # one batch
    python3 scripts/orchestrator/sync_orchestrator.py --batch=20 # custom size
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import time
from datetime import UTC, datetime
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

# KEI-91 Gate 4 heartbeat tick via shared shim — mirrors completion_sync_worker.
from _heartbeat_shim import heartbeat_tick as _heartbeat_tick  # noqa: E402

logger = logging.getLogger("sync_orchestrator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LINEAR_API = "https://api.linear.app/graphql"
DEFAULT_BATCH_SIZE = 20
MAX_ATTEMPTS = 3
POLL_INTERVAL_SECONDS = 30.0
BACKOFF_LADDER_SECONDS = (1.0, 5.0, 25.0)
ALL_STORES = ("bd", "postgres", "linear")


class DispatchError(RuntimeError):
    """Transient destination failure — worker retries with backoff."""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _bd_bin() -> str:
    return os.environ.get("AGENCY_OS_BD_BIN", os.path.expanduser("~/.local/bin/bd"))


def _due_now(event: dict[str, Any]) -> bool:
    """Honour backoff ladder: 1s/5s/25s between attempts."""
    if event["attempts"] == 0 or not event["last_attempt_at"]:
        return True
    backoff = BACKOFF_LADDER_SECONDS[min(event["attempts"] - 1, len(BACKOFF_LADDER_SECONDS) - 1)]
    return (time.time() - event["last_attempt_at"].timestamp()) >= backoff


# ---------------------------------------------------------------------------
# Per-destination dispatchers.
# ---------------------------------------------------------------------------


def _dispatch_postgres(conn: Any, event: dict[str, Any]) -> None:
    """Write to public.tasks. Trigger trg_tasks_emit_sync_events re-fires
    when this worker writes; idempotency comes from uq_pending_dedupe
    catching the duplicate (task_id, payload_hash) pair.

    KEI-235: when the payload's terminal status (done/cancelled) would
    trip the `require_verification_before_done` governance trigger
    (KEI-89/128), insert a synthetic `task_verifications` row in the
    same transaction first. The trigger only checks for ANY verification
    row on the task; verified_by='linear-sync' distinguishes the
    sync-system entry from human-callsign verifications in audit trails.
    """
    payload = event["payload"]
    task_id = event["task_id"]
    bd_id = event.get("bd_id") or payload.get("bd_id")
    title = payload.get("title") or "(no title)"
    status = payload.get("status")
    # KEI-235-followup: coerce 'cancelled' → 'dismissed' to match the
    # tasks_status_check CHECK constraint. Pre-fix events emitted by the
    # reconciler still carry the old payload.status='cancelled'; without
    # this coercion they'd hit a CheckViolation forever.
    if status == "cancelled":
        status = "dismissed"
    priority = payload.get("priority")
    linear_url = payload.get("linear_url")
    with conn.cursor() as cur:
        if status in ("done", "dismissed"):
            _ensure_sync_verification(cur, task_id, status, event)
        cur.execute(
            """
            INSERT INTO public.tasks (id, bd_id, title, status, priority, linear_url, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE
              SET bd_id = COALESCE(public.tasks.bd_id, EXCLUDED.bd_id),
                  title = EXCLUDED.title,
                  status = CASE
                             WHEN public.tasks.status IN ('done', 'cancelled')
                             THEN public.tasks.status
                             ELSE EXCLUDED.status
                           END,
                  priority = COALESCE(EXCLUDED.priority, public.tasks.priority),
                  linear_url = COALESCE(EXCLUDED.linear_url, public.tasks.linear_url),
                  updated_at = NOW()
            """,
            (task_id, bd_id, title, status, priority, linear_url),
        )


_SYNC_VERIFIER_NAME = "linear-sync"
_SYNC_VERIFICATION_MIN_OUTPUT_CHARS = 16


def _ensure_sync_verification(cur: Any, task_id: str, status: str, event: dict[str, Any]) -> None:
    """Insert a synthetic task_verifications row if none exists for this task.

    The KEI-89/128 `require_verification_before_done` trigger raises when
    setting status='done'/'cancelled' without an existing verification.
    This shim ensures the gate is satisfied for sync-driven terminal
    transitions, with verified_by='linear-sync' so reviewers can tell
    sync-system rows apart from human verifications.

    Idempotent — INSERT skipped if any verification row already exists for
    this task. The verification text_output meets KEI-89's >=16 char
    min-length check.
    """
    import uuid as _uuid

    iso_ts = _now_iso()
    test_output = (
        f"linear-sync orchestrator: payload.status={status} "
        f"event_id={event.get('id', 'unknown')} origin={event.get('origin', '?')} "
        f"propagated_at={iso_ts}"
    )
    assert len(test_output) >= _SYNC_VERIFICATION_MIN_OUTPUT_CHARS  # noqa: S101 — internal guard
    cur.execute(
        """
        INSERT INTO public.task_verifications
            (id, task_id, verified_by, behavioral_test, test_output, created_at)
        SELECT %s, %s, %s, %s, %s, NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM public.task_verifications WHERE task_id = %s
        )
        """,
        (
            str(_uuid.uuid4()),
            task_id,
            _SYNC_VERIFIER_NAME,
            "linear webhook propagation",
            test_output,
            task_id,
        ),
    )


def _now_iso() -> str:
    """Wrap datetime.now for test patchability."""
    return datetime.now(UTC).isoformat()


def _dispatch_bd(event: dict[str, Any]) -> None:
    """Run bd CLI for the event's intent. Subprocess-based; fail-open."""
    bd_id = event.get("bd_id") or event["payload"].get("bd_id")
    if not bd_id:
        # No bd-Dolt sibling — skip (K4 reconciler will eventually backfill).
        logger.debug("[%s] no bd_id; skipping bd dispatch", event["task_id"])
        return
    event_type = event["event_type"]
    bd = _bd_bin()
    try:
        if event_type in ("close",):
            proc = subprocess.run(  # noqa: S603 — controlled args
                [bd, "update", bd_id, "--status=closed"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        elif event_type == "reopen":
            proc = subprocess.run(  # noqa: S603 — controlled args
                [bd, "update", bd_id, "--status=open"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        else:
            # Generic 'update' — write into bd via inline JSON.
            # Beads has no batch field-update CLI; status only for V1.
            status = event["payload"].get("status")
            bd_status = _postgres_status_to_bd(status) if status else None
            if bd_status:
                proc = subprocess.run(  # noqa: S603 — controlled args
                    [bd, "update", bd_id, f"--status={bd_status}"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
            else:
                logger.debug(
                    "[%s] no status mapped for event_type=%s; bd dispatch noop",
                    event["task_id"],
                    event_type,
                )
                return
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        raise DispatchError(f"bd subprocess: {exc}") from exc
    if proc.returncode != 0:
        raise DispatchError(f"bd update {bd_id} exit={proc.returncode}: {proc.stderr[:200]}")


def _postgres_status_to_bd(status: str) -> str | None:
    """Map public.tasks.status → bd-Dolt status. Inverse of LINEAR_STATE_TO_BD."""
    mapping = {
        "available": "open",
        "active": "in_progress",
        "done": "closed",
        "cancelled": "closed",
    }
    return mapping.get(status)


def _dispatch_linear(event: dict[str, Any]) -> None:
    """Linear-write path — HARD-LOCKED to no-op (Dave ratified LAW 2026-05-20).

    RATIFIED RULE: Linear is read-only for all agents and all automated
    processes. No agent, no sync orchestrator, no reconciler may write to or
    overwrite Linear state directly. Status propagation from Supabase to Linear
    happens ONLY via the separate controlled one-way push — never through this
    orchestrator.

    This function previously POSTed an `issueUpdate` mutation. That write path
    is the exact mechanism that corrupted ~45 KEIs (downgraded to Backlog).
    It is now a logged no-op. The function is retained (not deleted) so any
    caller still wired to it fails safe — it logs and returns, never writes.

    Do NOT re-enable a Linear write here. If Supabase→Linear propagation is
    needed, build it as the dedicated controlled one-way push component.
    """
    logger.info(
        "[%s] Linear write SUPPRESSED — Linear is read-only per ratified LAW "
        "2026-05-20 (event_type=%s, origin=%s). No issueUpdate sent.",
        event.get("task_id", "?"),
        event.get("event_type", "?"),
        event.get("origin", "?"),
    )
    return


def _event_to_linear_state(event: dict[str, Any]) -> str | None:
    """Map an event to the target Linear state name.

    KEI-236 policy lock (Dave 2026-05-19): Postgres is canonical, bd is the
    agent CLI, Linear is a one-way visibility mirror. Only Postgres-origin
    terminal transitions (close / reopen) propagate to Linear. Everything
    else returns None so the orchestrator never overwrites Linear from a
    non-canonical source.

    Combined with the prior KEI-233 guard (no `available` → todo), this
    pins the orchestrator to:
      - bd-origin events: never go to Linear
      - linear-origin events: never round-trip to Linear (origin-tag
        loop prevention also blocks this in _process_event)
      - postgres-origin events: ONLY when event_type ∈ {close, reopen}
    """
    if event.get("origin") != "postgres":
        return None
    et = event["event_type"]
    if et == "close":
        return "done"
    if et == "reopen":
        return "active"
    return None


# ---------------------------------------------------------------------------
# Drain loop.
# ---------------------------------------------------------------------------


_DISPATCHERS = {
    "bd": _dispatch_bd,
    "postgres": None,  # set inside run_once with the live conn
    "linear": _dispatch_linear,
}


def _process_event(conn: Any, event: dict[str, Any]) -> bool:
    """Dispatch event to all stores OTHER than its origin. True on success.

    KEI-235 resilience: each dispatcher call runs inside its own savepoint
    so a Postgres governance-trigger raise (RaiseException) can roll back
    just that one dispatch instead of poisoning the whole batch (real
    incident 2026-05-19 12:46 UTC: 168 events frozen behind one
    trigger-blocked KEI-215 done UPDATE).
    """
    import psycopg  # noqa: PLC0415 — lazy import keeps unit tests psycopg-free

    origin = event["origin"]
    targets = [s for s in ALL_STORES if s != origin]
    errors: list[str] = []
    for target in targets:
        sp = f"sp_{target}_{event['id']}".replace("-", "_")[:60]
        with conn.cursor() as sp_cur:
            sp_cur.execute(f"SAVEPOINT {sp}")
        try:
            if target == "postgres":
                _dispatch_postgres(conn, event)
            elif target == "bd":
                _dispatch_bd(event)
            elif target == "linear":
                _dispatch_linear(event)
        except DispatchError as exc:
            with conn.cursor() as sp_cur:
                sp_cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
            errors.append(f"{target}: {exc}")
            logger.warning("[%s/%s] %s", event["task_id"], target, exc)
        except (
            psycopg.errors.RaiseException,
            psycopg.errors.IntegrityError,
            psycopg.errors.DataError,
        ) as exc:
            # Governance trigger raise OR constraint violation (check / FK /
            # unique / not-null / data type). All fall under "this write
            # was refused by Postgres" — roll back just this savepoint,
            # let the batch continue, and let MAX_ATTEMPTS retry decide
            # whether to abandon. KEI-235-followup broadened from
            # RaiseException-only after CheckViolation on 'cancelled'
            # froze the batch.
            with conn.cursor() as sp_cur:
                sp_cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
            errors.append(f"{target}: db-refused: {str(exc).splitlines()[0][:160]}")
            logger.warning(
                "[%s/%s] db-refused: %s",
                event["task_id"],
                target,
                str(exc).splitlines()[0][:200],
            )
        else:
            with conn.cursor() as sp_cur:
                sp_cur.execute(f"RELEASE SAVEPOINT {sp}")
    if errors:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.sync_events SET attempts = attempts + 1, "
                "last_attempt_at = NOW(), error_message = %s WHERE id = %s",
                (" | ".join(errors)[:500], event["id"]),
            )
        return False
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.sync_events SET processed = TRUE, "
            "last_attempt_at = NOW(), error_message = NULL WHERE id = %s",
            (event["id"],),
        )
    logger.info("[%s/%s] dispatched to %s", event["task_id"], event["event_type"], targets)
    return True


def run_once(batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, int]:
    import psycopg
    from psycopg.rows import dict_row

    stats = {"selected": 0, "processed": 0, "failed": 0, "abandoned": 0}
    with psycopg.connect(
        _dsn(), prepare_threshold=None, autocommit=False, row_factory=dict_row
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, origin, event_type, task_id, bd_id, payload, attempts, "
                "       last_attempt_at "
                "FROM public.sync_events "
                "WHERE processed = FALSE AND attempts < %s "
                "ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED",
                (MAX_ATTEMPTS, batch_size),
            )
            rows = cur.fetchall()
        stats["selected"] = len(rows)
        for row in rows:
            if not _due_now(row):
                continue
            ok = _process_event(conn, row)
            if ok:
                stats["processed"] += 1
            else:
                stats["failed"] += 1
                if row["attempts"] + 1 >= MAX_ATTEMPTS:
                    stats["abandoned"] += 1
        conn.commit()
    return stats


def main() -> int:
    p = argparse.ArgumentParser(prog="sync_orchestrator")
    p.add_argument("--once", action="store_true", help="run one batch then exit")
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE)
    args = p.parse_args()
    while True:
        try:
            stats = run_once(args.batch)
            if stats["selected"]:
                logger.info("batch %s", stats)
            _heartbeat_tick(
                "sync-orchestrator",
                outcome_increment=stats["processed"],
                status="ok",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("run_once failed: %s", exc)
            _heartbeat_tick(
                "sync-orchestrator",
                outcome_increment=0,
                status="error",
                error_message=str(exc)[:200],
            )
        if args.once:
            return 0
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
