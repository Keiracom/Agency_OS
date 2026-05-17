#!/usr/bin/env python3
"""completion_sync_worker.py — KEI-74 worker for the three-store completion sync queue.

Drains public.completion_sync_queue rows WHERE processed=false in batches.
Per row, dispatches by target_sink:
    linear        — POST Linear GraphQL issueUpdate setting state
    ceo_memory    — INSERT public.ceo_memory row keyed completion:<task_id>
    drive_manual  — invoke scripts/write_manual_mirror.py <task_id>

Marks processed=true on success; increments attempts + records error_message on
failure with exponential backoff (1s/5s/25s). Mirrors the KEI-54B tool_call_log_
indexer shape — SELECT FOR UPDATE SKIP LOCKED, deterministic per-sink dispatch,
fail-open at process level (transient sink failures retry from queue; terminal
exceptions log + sleep).

Usage:
    python3 scripts/orchestrator/completion_sync_worker.py            # daemon loop
    python3 scripts/orchestrator/completion_sync_worker.py --once     # one batch
    python3 scripts/orchestrator/completion_sync_worker.py --batch=20 # custom size
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import time
from urllib import error as urlerror
from urllib import request as urlrequest

# KEI-91 Gate 4 heartbeat tick via shared shim.
from _heartbeat_shim import heartbeat_tick as _heartbeat_tick  # noqa: E402

logger = logging.getLogger("completion_sync_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

LINEAR_API = "https://api.linear.app/graphql"
DEFAULT_BATCH_SIZE = 20
MAX_ATTEMPTS = 3
POLL_INTERVAL_SECONDS = 30.0
BACKOFF_LADDER_SECONDS = (1.0, 5.0, 25.0)
SCRIPT_ROOT = os.environ.get("AGENCY_OS_REPO", "/home/elliotbot/clawd/Agency_OS")


class SinkError(RuntimeError):
    """Transient sink-side failure — worker retries with backoff."""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL must be set")
    return dsn.replace("+asyncpg", "")


def _linear_state_id(target_status: str) -> str:
    return os.environ.get(f"LINEAR_STATE_ID_{target_status.upper()}", "")


def _sink_linear(task_id: str, target_status: str) -> None:
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        raise SinkError("LINEAR_API_KEY missing")
    state_id = _linear_state_id(target_status)
    if not state_id:
        raise SinkError(f"LINEAR_STATE_ID_{target_status.upper()} missing")
    body = json.dumps(
        {
            "query": "mutation($id:String!,$state:String!){issueUpdate(id:$id,input:{stateId:$state}){success}}",
            "variables": {"id": task_id, "state": state_id},
        }
    ).encode()
    req = urlrequest.Request(
        LINEAR_API,
        data=body,
        method="POST",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read())
    except (urlerror.URLError, OSError) as exc:
        raise SinkError(f"linear network: {exc}") from exc
    ok = ((payload.get("data") or {}).get("issueUpdate") or {}).get("success", False)
    if not ok:
        raise SinkError(f"linear rejected: {payload.get('errors') or payload}")


def _sink_ceo_memory(conn, task_id: str, target_status: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.ceo_memory (key, value, updated_at)
            VALUES (%s, %s::jsonb, NOW())
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
            """,
            (
                f"completion:{task_id}",
                json.dumps({"task_id": task_id, "status": target_status, "via": "kei74"}),
            ),
        )


def _sink_drive_manual(task_id: str) -> None:
    script = os.path.join(SCRIPT_ROOT, "scripts", "write_manual_mirror.py")
    if not os.path.isfile(script):
        raise SinkError(f"missing {script}")
    try:
        out = subprocess.run(
            ["python3", script, "--task-id", task_id],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SinkError("drive_manual timeout") from exc
    if out.returncode != 0:
        raise SinkError(f"drive_manual exit={out.returncode}: {out.stderr[:200]}")


def _due_now(row) -> bool:
    if row["attempts"] == 0 or not row["last_attempt_at"]:
        return True
    backoff = BACKOFF_LADDER_SECONDS[min(row["attempts"] - 1, len(BACKOFF_LADDER_SECONDS) - 1)]
    return (time.time() - row["last_attempt_at"].timestamp()) >= backoff


def _process_row(conn, row) -> bool:
    try:
        if row["target_sink"] == "linear":
            _sink_linear(row["task_id"], row["target_status"])
        elif row["target_sink"] == "ceo_memory":
            _sink_ceo_memory(conn, row["task_id"], row["target_status"])
        elif row["target_sink"] == "drive_manual":
            _sink_drive_manual(row["task_id"])
        else:
            raise SinkError(f"unknown sink {row['target_sink']!r}")
    except SinkError as exc:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.completion_sync_queue SET attempts=attempts+1, "
                "last_attempt_at=NOW(), error_message=%s, updated_at=NOW() WHERE id=%s",
                (str(exc)[:500], row["id"]),
            )
        logger.warning(
            "[%s/%s] attempt %d failed: %s",
            row["task_id"],
            row["target_sink"],
            row["attempts"] + 1,
            exc,
        )
        return False
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.completion_sync_queue SET processed=TRUE, last_attempt_at=NOW(), "
            "error_message=NULL, updated_at=NOW() WHERE id=%s",
            (row["id"],),
        )
    logger.info("[%s/%s] processed", row["task_id"], row["target_sink"])
    return True


def run_once(batch_size: int = DEFAULT_BATCH_SIZE) -> dict:
    import psycopg
    from psycopg.rows import dict_row

    stats = {"selected": 0, "processed": 0, "failed": 0, "abandoned": 0}
    with psycopg.connect(
        _dsn(), prepare_threshold=None, autocommit=False, row_factory=dict_row
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, task_id, target_sink, target_status, attempts, last_attempt_at "
                "FROM public.completion_sync_queue "
                "WHERE processed=FALSE AND attempts < %s "
                "ORDER BY created_at LIMIT %s FOR UPDATE SKIP LOCKED",
                (MAX_ATTEMPTS, batch_size),
            )
            rows = cur.fetchall()
        stats["selected"] = len(rows)
        for row in rows:
            if not _due_now(row):
                continue
            if _process_row(conn, row):
                stats["processed"] += 1
            else:
                stats["failed"] += 1
                if row["attempts"] + 1 >= MAX_ATTEMPTS:
                    stats["abandoned"] += 1
        conn.commit()
    return stats


def main() -> int:
    p = argparse.ArgumentParser(prog="completion_sync_worker")
    p.add_argument("--once", action="store_true", help="run one batch then exit")
    p.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE)
    args = p.parse_args()
    while True:
        try:
            stats = run_once(args.batch)
            if stats["selected"]:
                logger.info("batch %s", stats)
            # KEI-91 heartbeat — outcome = rows successfully processed.
            _heartbeat_tick(
                "completion-sync-worker",
                outcome_increment=int(stats.get("processed", 0)),
                status="ok" if stats.get("failed", 0) == 0 else "degraded",
            )
        except Exception as exc:  # noqa: BLE001 — daemon must survive
            logger.exception("batch failed: %s", exc)
            _heartbeat_tick(
                "completion-sync-worker",
                outcome_increment=0,
                status="error",
                error_message=str(exc)[:500],
            )
        if args.once:
            return 0
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
