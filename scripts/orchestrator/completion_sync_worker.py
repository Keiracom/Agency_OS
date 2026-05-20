#!/usr/bin/env python3
"""completion_sync_worker.py — KEI-74 worker for the three-store completion sync queue.

Drains public.completion_sync_queue rows WHERE processed=false in batches.
Per row, dispatches by target_sink:
    linear        — no-op since Agency_OS-1x3x (Part 4). Linear is read-only
                    for automated processes; Supabase→Linear status goes via
                    the one-way push (linear_oneway_push.py) only.
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
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# KEI-91 Gate 4 heartbeat tick via shared shim.
from _heartbeat_shim import heartbeat_tick as _heartbeat_tick  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.governance.ceo_memory_writer import upsert_ceo_memory_key  # noqa: E402

logger = logging.getLogger("completion_sync_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

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


def _sink_linear(task_id: str, target_status: str) -> None:
    """Linear sink — HARD-LOCKED to no-op (Dave ratified LAW 2026-05-20).

    Agency_OS-1x3x Part 4: Linear is read-only for every automated process.
    Supabase→Linear status propagation happens ONLY via the controlled
    one-way push (scripts/orchestrator/linear_oneway_push.py) — the sole
    sanctioned Linear writer. This sink previously POSTed an issueUpdate
    mutation; that competing writer is retired.

    The function is retained (not deleted) so any completion_sync_queue row
    still enqueued with target_sink='linear' fails SAFE — it is marked
    processed without a Linear write, rather than erroring or reviving the
    write path. ceo_memory + drive_manual sinks are unaffected.
    """
    logger.info(
        "[%s/linear] no-op — Linear writes go via the one-way push only (target_status=%s ignored)",
        task_id,
        target_status,
    )


def _sink_ceo_memory(task_id: str, target_status: str) -> None:
    callsign = os.environ.get("CALLSIGN", "system")
    upsert_ceo_memory_key(
        callsign,
        f"completion:{task_id}",
        {"task_id": task_id, "status": target_status, "via": "kei74"},
    )


def _sink_drive_manual(task_id: str) -> None:
    """Invoke the Drive mirror for the originating task.

    KEI-173: rc=2 means MANUAL.md is unchanged since the last successful
    mirror (write_manual_mirror.py outcome 'refused_unchanged'). Drive is
    already consistent — no work to do — so the sink treats it as success,
    not a SinkError. Otherwise repeated completions between Manual edits
    would each retry 3× and abandon, polluting the queue.
    """
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
    if out.returncode == 0:
        return
    if out.returncode == 2:
        logger.info("[%s/drive_manual] MANUAL.md unchanged — Drive already current", task_id)
        return
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
            _sink_ceo_memory(row["task_id"], row["target_status"])
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
