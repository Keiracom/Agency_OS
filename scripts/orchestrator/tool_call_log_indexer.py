#!/usr/bin/env python3
"""tool_call_log_indexer.py — KEI-54 Stage B worker (KEI-54B).

Drains public.tool_call_log rows WHERE indexed=false into the Weaviate
ToolCalls collection. Idempotent via deterministic UUID (Weaviate object id
== tool_call_log.id), retries transient failures with exponential backoff,
marks rows indexed=true on success and writes an audit_logs entry per
batch outcome.

Acceptance criterion (KEI-54B verbatim from tasks-table):
    Worker daemon processes public.tool_call_log rows WHERE indexed=false
    in batches of N. Per row: build Weaviate document, POST to :8090
    sessions or new tool_calls collection, UPDATE indexed=true on success,
    retry up to 3x exp backoff on transient failures. Idempotency key =
    tool_call_log.id (UUID).

Companion to:
- Aiden KEI-54 Stage A (PR #874) — tool_call_log schema + producer SDK
- Scout KEI-61 (PR #876) — indexing_queue worker (same shape: SKIP LOCKED,
  retry, audit_logs)
- Atlas KEI-48 (PR #868) — Weaviate native binary on :8090

Schema bootstrap: this script ensures the ToolCalls Weaviate class exists
on every startup (idempotent class create — Weaviate returns 200 if already
present, no-op).

Usage:
    python3 scripts/orchestrator/tool_call_log_indexer.py             # daemon loop
    python3 scripts/orchestrator/tool_call_log_indexer.py --once      # one batch
    python3 scripts/orchestrator/tool_call_log_indexer.py --batch=10  # custom batch size
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import time
from dataclasses import dataclass
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

logger = logging.getLogger("tool_call_log_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = os.environ.get("WEAVIATE_PORT", "8090")
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR python:S5332 loopback-only
TOOL_CALLS_CLASS = "ToolCalls"
DEFAULT_BATCH_SIZE = 50
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
POLL_INTERVAL_SECONDS = 30.0

_TOOL_CALLS_SCHEMA = {
    "class": TOOL_CALLS_CLASS,
    "description": "Tool calls indexed from public.tool_call_log (KEI-54B).",
    "vectorizer": "none",
    "properties": [
        {"name": "callsign", "dataType": ["text"]},
        {"name": "session_uuid", "dataType": ["text"]},
        {"name": "tool_name", "dataType": ["text"]},
        {"name": "tool_input", "dataType": ["text"]},
        {"name": "tool_output_excerpt", "dataType": ["text"]},
        {"name": "started_at", "dataType": ["date"]},
        {"name": "duration_ms", "dataType": ["int"]},
        {"name": "exit_code", "dataType": ["int"]},
    ],
}


class IndexerError(RuntimeError):
    """Raised on terminal indexer failure. Transient failures retry inline."""


@dataclass
class ToolCallRow:
    id: str
    callsign: str
    session_uuid: str | None
    tool_name: str
    tool_input: dict[str, Any]
    tool_output_excerpt: str | None
    started_at: str
    duration_ms: int | None
    exit_code: int | None


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        raise IndexerError("DATABASE_URL / SUPABASE_DB_URL env required")
    # Strip SQLAlchemy-style driver tags ('+asyncpg' / '+psycopg2') so the
    # plain libpq parser inside psycopg can handle the URL.
    return dsn.replace("+asyncpg", "").replace("+psycopg2", "")


def _http_request(method: str, path: str, body: dict | None = None, timeout: float = 10.0):
    url = f"{WEAVIATE_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urlrequest.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    return urlrequest.urlopen(req, timeout=timeout)  # noqa: S310 — fixed loopback URL


def ensure_tool_calls_class_exists() -> None:
    """Create the ToolCalls class if not present. Idempotent."""
    try:
        with _http_request("GET", f"/v1/schema/{TOOL_CALLS_CLASS}"):
            logger.info("class %s already exists", TOOL_CALLS_CLASS)
            return
    except urlerror.HTTPError as exc:
        if exc.code != 404:
            raise
    logger.info("creating Weaviate class %s", TOOL_CALLS_CLASS)
    with _http_request("POST", "/v1/schema", _TOOL_CALLS_SCHEMA) as resp:
        if resp.status >= 300:
            raise IndexerError(f"class create failed: {resp.status}")


def claim_batch(conn: Any, batch_size: int) -> list[ToolCallRow]:
    """Pull next N unindexed rows. Not SELECT FOR UPDATE — Stage A produces
    rows that are exclusively owned by this worker process; multi-worker
    deployment would need SKIP LOCKED, which is a Stage B+ scope.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, callsign, session_uuid, tool_name, tool_input,
                   tool_output_excerpt, started_at, duration_ms, exit_code
            FROM public.tool_call_log
            WHERE indexed = FALSE
            ORDER BY started_at ASC
            LIMIT %s
            """,
            (batch_size,),
        )
        rows = cur.fetchall()
    return [
        ToolCallRow(
            id=str(r[0]),
            callsign=r[1],
            session_uuid=str(r[2]) if r[2] else None,
            tool_name=r[3],
            tool_input=r[4] or {},
            tool_output_excerpt=r[5],
            started_at=r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6]),
            duration_ms=r[7],
            exit_code=r[8],
        )
        for r in rows
    ]


def build_weaviate_doc(row: ToolCallRow) -> dict[str, Any]:
    return {
        "class": TOOL_CALLS_CLASS,
        "id": row.id,  # deterministic — idempotent re-POST
        "properties": {
            "callsign": row.callsign,
            "session_uuid": row.session_uuid or "",
            "tool_name": row.tool_name,
            "tool_input": json.dumps(row.tool_input),
            "tool_output_excerpt": row.tool_output_excerpt or "",
            "started_at": row.started_at,
            "duration_ms": row.duration_ms or 0,
            "exit_code": row.exit_code if row.exit_code is not None else -1,
        },
    }


def index_row(row: ToolCallRow) -> bool:
    """POST to Weaviate with exponential backoff. Returns True on success.
    Idempotency: PUT-semantic via deterministic id; if 422 (already exists),
    treat as success.
    """
    doc = build_weaviate_doc(row)
    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with _http_request("POST", "/v1/objects", doc) as resp:
                if 200 <= resp.status < 300:
                    return True
                logger.warning("index_row %s rc=%s attempt=%d", row.id, resp.status, attempt)
        except urlerror.HTTPError as exc:
            if exc.code == 422:
                logger.info("index_row %s already exists (422 = idempotent no-op)", row.id)
                return True
            logger.warning("index_row %s HTTPError=%s attempt=%d", row.id, exc.code, attempt)
        except (urlerror.URLError, TimeoutError, OSError) as exc:
            logger.warning("index_row %s transient %s attempt=%d", row.id, exc, attempt)
        if attempt < MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2
    logger.error("index_row %s exhausted retries", row.id)
    return False


def mark_indexed(conn: Any, row_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.tool_call_log SET indexed = TRUE, indexed_at = NOW() WHERE id = %s",
            (row_id,),
        )
    conn.commit()


def write_audit(conn: Any, batch_outcome: dict[str, int]) -> None:
    """Write one row to public.audit_logs per batch outcome.

    Schema uses `metadata` jsonb (not `payload`); action is a USER-DEFINED
    enum — we use 'create' since 'index' isn't in the enum. engine +
    operation give the discriminator.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.audit_logs
                (action, resource_type, engine, operation, success, metadata)
            VALUES ('create', 'tool_call_log', 'tool_call_log_indexer', 'batch', %s, %s::jsonb)
            """,
            (
                batch_outcome.get("failed", 0) == 0,
                json.dumps(batch_outcome),
            ),
        )
    conn.commit()


def process_batch(conn: Any, batch_size: int) -> dict[str, int]:
    rows = claim_batch(conn, batch_size)
    outcome = {"claimed": len(rows), "done": 0, "failed": 0}
    for row in rows:
        if index_row(row):
            mark_indexed(conn, row.id)
            outcome["done"] += 1
        else:
            outcome["failed"] += 1
    logger.info("batch: %s", outcome)
    if rows:
        write_audit(conn, outcome)
    return outcome


def run(batch_size: int, poll_interval: float, max_iterations: int | None = None) -> int:
    import psycopg  # noqa: PLC0415 — defer import for unit test mockability

    ensure_tool_calls_class_exists()
    iterations = 0
    stop = {"flag": False}

    def _shutdown(signum, frame):  # noqa: ARG001
        logger.info("signal %d received", signum)
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    while not stop["flag"]:
        # prepare_threshold=None disables psycopg's prepared-statement caching.
        # Supabase pooler runs in transaction-mode pgbouncer which doesn't
        # preserve PREPARE statements across transactions; without this disable
        # psycopg raises InvalidSqlStatementName on the second statement of
        # any batch (mark_indexed loop fails on row 2).
        with psycopg.connect(_dsn(), prepare_threshold=None) as conn:
            process_batch(conn, batch_size)
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(poll_interval)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="single batch then exit")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--poll", type=float, default=POLL_INTERVAL_SECONDS)
    args = parser.parse_args(argv)
    return run(args.batch, args.poll, max_iterations=1 if args.once else None)


if __name__ == "__main__":
    raise SystemExit(main())
