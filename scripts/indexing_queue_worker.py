#!/usr/bin/env python3
"""indexing_queue_worker.py — KEI-61: pulls from public.indexing_queue,
processes via LlamaIndex+Weaviate (stub until KEI-46+KEI-49 build ships),
writes audit_logs on success, retries up to 3 times on failure, alerts
#ceo on terminal failure.

Designed to run as a systemd Type=simple service (infra/systemd/indexing-queue-worker.service).
Idempotent: stuck 'processing' rows older than 10 minutes are reset to
'pending' on startup via the reset_stuck_indexing_rows() RPC.

Env:
  DATABASE_URL or SUPABASE_DB_URL — postgres DSN.
  INDEXING_WORKER_ID — worker identifier (default: hostname + pid).
  INDEXING_BATCH_SIZE — rows per poll (default: 5).
  INDEXING_POLL_INTERVAL_SECONDS — wait between polls (default: 10).
  INDEXING_MAX_ATTEMPTS — terminal-fail threshold (default: 3).
  INDEXING_PROCESSOR_BACKEND — 'stub' (default) | 'llamaindex' once KEI-46+49 ship.
  SLACK_RELAY_PATH — path to scripts/slack_relay.py for #ceo alerts.

Exit codes:
  0 — clean shutdown on SIGTERM/SIGINT.
  1 — operator misconfig (no DSN).
  2 — fatal DB error after retries.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# KEI-91 Gate 4 heartbeat tick via shared shim. The shim lives one dir down
# (scripts/orchestrator/_heartbeat_shim.py); put that dir on sys.path so the
# import works the same way as the scripts/orchestrator/*.py wires.
_SHIM_DIR = Path(__file__).resolve().parent / "orchestrator"
if str(_SHIM_DIR) not in sys.path:
    sys.path.insert(0, str(_SHIM_DIR))
from _heartbeat_shim import heartbeat_tick as _heartbeat_tick  # noqa: E402

logger = logging.getLogger("indexing_queue_worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

DEFAULT_BATCH_SIZE = 5
DEFAULT_POLL_INTERVAL = 10
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKEND = "stub"
DEFAULT_SLACK_RELAY = "/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py"
_RUNNING = True


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise SystemExit("ERROR: DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _processor_id() -> str:
    explicit = os.environ.get("INDEXING_WORKER_ID")
    if explicit:
        return explicit
    return f"{socket.gethostname()}.{os.getpid()}"


@dataclass(frozen=True)
class QueueRow:
    id: str
    source: str
    payload: dict
    attempts: int


def _row_to_dataclass(row: tuple, cols: list[str]) -> QueueRow:
    rec = dict(zip(cols, row, strict=False))
    return QueueRow(
        id=str(rec["id"]),
        source=rec["source"],
        payload=rec["payload"],
        attempts=int(rec["attempts"]),
    )


def claim_batch(conn: Any, batch_size: int, processor: str) -> list[QueueRow]:
    """Atomic batch claim via the SQL function (SELECT FOR UPDATE SKIP LOCKED)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM public.claim_queue_batch(%s, %s)",
            (batch_size, processor),
        )
        cols = [c.name for c in cur.description]
        rows = cur.fetchall()
    conn.commit()
    return [_row_to_dataclass(r, cols) for r in rows]


def reset_stuck(conn: Any, stuck_minutes: int = 10) -> int:
    """Reclaim 'processing' rows that exceeded the timeout — called on startup."""
    with conn.cursor() as cur:
        cur.execute("SELECT public.reset_stuck_indexing_rows(%s)", (stuck_minutes,))
        n = cur.fetchone()[0]
    conn.commit()
    return int(n or 0)


def process_row(row: QueueRow) -> dict:
    """Return a dict that will end up in audit_logs.event_data on success.

    Backend selection:
      'stub' — no-op, just records the row was seen. Used until KEI-46+49 ship.
      'llamaindex' — placeholder for the real path (to be implemented in
                     a follow-up PR after KEI-49 build lands).
    """
    backend = os.environ.get("INDEXING_PROCESSOR_BACKEND", DEFAULT_BACKEND)
    if backend == "stub":
        return {
            "event": "indexed",
            "source": row.source,
            "backend": "stub",
            "payload_size": len(json.dumps(row.payload)),
            "note": "stub backend — LlamaIndex/Weaviate pipeline not yet built (KEI-46+49)",
        }
    if backend == "llamaindex":
        # Follow-up PR will wire this. For now, mark as failed-with-known-reason
        # so the operator can re-flip the env var when the real backend ships.
        raise RuntimeError("llamaindex backend not yet implemented — KEI-49 build pending")
    raise RuntimeError(f"unknown INDEXING_PROCESSOR_BACKEND: {backend!r}")


def mark_done(conn: Any, row_id: str, audit_event: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.indexing_queue
               SET status = 'done',
                   indexed_at = NOW(),
                   error = NULL
             WHERE id = %s
            """,
            (row_id,),
        )
        # Audit log uses the existing public.audit_logs schema (action enum +
        # engine/operation/resource_type/metadata). action='create' = the
        # indexing event creates a downstream Weaviate record (LlamaIndex
        # backend, when KEI-49 build lands); for the stub backend it records
        # that the queue row was processed.
        cur.execute(
            """
            INSERT INTO public.audit_logs
                (action, engine, operation, resource_type, resource_id, metadata, success)
            VALUES ('create', 'indexing_worker', 'indexed', 'indexing_queue', %s::uuid, %s::jsonb, true)
            """,
            (row_id, json.dumps(audit_event)),
        )
    conn.commit()


def mark_failed(conn: Any, row_id: str, error_text: str, attempts: int, max_attempts: int) -> bool:
    """Returns True if the row hit the terminal-fail threshold."""
    terminal = attempts >= max_attempts
    new_status = "failed" if terminal else "pending"
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE public.indexing_queue
               SET status = %s,
                   error = %s,
                   processor = NULL
             WHERE id = %s
            """,
            (new_status, error_text[:2000], row_id),
        )
    conn.commit()
    return terminal


def alert_ceo(row_id: str, error_text: str) -> None:
    """Best-effort #ceo alert on terminal failure. Never raises."""
    relay = os.environ.get("SLACK_RELAY_PATH", DEFAULT_SLACK_RELAY)
    if not os.path.isfile(relay):
        logger.warning("slack_relay.py not found at %s — skipping alert", relay)
        return
    msg = (
        f"[INDEXING-QUEUE-FAILED] row={row_id} attempts=max ({error_text[:200]}). "
        "Manual triage required: SELECT * FROM public.indexing_queue WHERE id='" + row_id + "';"
    )
    try:
        env = os.environ.copy()
        env["CONCUR_GATE_SKIP"] = "1"
        env["CALLSIGN"] = "scout"
        subprocess.run(  # noqa: S603
            ["python3", relay, "-c", "ceo", msg],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        logger.exception("alert_ceo subprocess failed")


def process_batch(conn: Any, batch: list[QueueRow], max_attempts: int) -> dict[str, int]:
    counters = {"done": 0, "retry": 0, "failed": 0}
    for row in batch:
        try:
            event = process_row(row)
            mark_done(conn, row.id, event)
            counters["done"] += 1
            logger.info("indexed row=%s source=%s", row.id, row.source)
        except Exception as exc:  # noqa: BLE001 — worker discipline: surface ALL errors as row failures
            terminal = mark_failed(conn, row.id, repr(exc), row.attempts, max_attempts)
            if terminal:
                counters["failed"] += 1
                alert_ceo(row.id, repr(exc))
                logger.exception("row %s FAILED terminal", row.id)
            else:
                counters["retry"] += 1
                logger.warning("row %s retry (%d/%d): %s", row.id, row.attempts, max_attempts, exc)
    return counters


def _install_signal_handlers() -> None:
    def _stop(_sig: int, _frame: Any) -> None:
        global _RUNNING
        _RUNNING = False
        logger.info("shutdown signal received — finishing current batch")

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)


def run(
    batch_size: int = DEFAULT_BATCH_SIZE,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    max_iterations: int | None = None,
) -> int:
    import psycopg

    processor = _processor_id()
    iteration = 0
    try:
        with psycopg.connect(_dsn()) as conn:
            reset = reset_stuck(conn)
            if reset:
                logger.info("startup: reset %d stuck rows back to pending", reset)
            while _RUNNING:
                batch = claim_batch(conn, batch_size, processor)
                if batch:
                    counters = process_batch(conn, batch, max_attempts)
                    logger.info(
                        "batch: claimed=%d done=%d retry=%d failed=%d",
                        len(batch),
                        counters["done"],
                        counters["retry"],
                        counters["failed"],
                    )
                    # KEI-91 heartbeat — outcome = rows done this batch.
                    _heartbeat_tick(
                        "indexing-queue-worker",
                        outcome_increment=int(counters.get("done", 0)),
                        status="ok" if counters.get("failed", 0) == 0 else "degraded",
                    )
                else:
                    logger.debug("queue empty; sleeping %ds", poll_interval)
                    # Heartbeat even when queue is empty so the monitor sees
                    # liveness; outcome=0 is correct (no work was available,
                    # not that work was attempted and failed).
                    _heartbeat_tick(
                        "indexing-queue-worker",
                        outcome_increment=0,
                        status="ok",
                    )
                iteration += 1
                if max_iterations is not None and iteration >= max_iterations:
                    break
                if _RUNNING:
                    time.sleep(poll_interval)
    except psycopg.Error:
        logger.exception("fatal DB error — worker exiting")
        return 2
    logger.info("clean shutdown after %d iterations", iteration)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("INDEXING_BATCH_SIZE", DEFAULT_BATCH_SIZE)),
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=int(os.environ.get("INDEXING_POLL_INTERVAL_SECONDS", DEFAULT_POLL_INTERVAL)),
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=int(os.environ.get("INDEXING_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)),
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Stop after N polls; useful for tests/one-shots",
    )
    args = parser.parse_args(argv)
    _install_signal_handlers()
    return run(
        batch_size=max(1, args.batch_size),
        poll_interval=max(1, args.poll_interval),
        max_attempts=max(1, args.max_attempts),
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    raise SystemExit(main())
