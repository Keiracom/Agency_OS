#!/usr/bin/env python3
"""ceo_memory_indexer.py — KEI-85 phase A: index public.ceo_memory into Weaviate Decisions.

Reads `public.ceo_memory` (live prod schema: key text, value jsonb, updated_at
timestamptz, version int — verified via Supabase MCP information_schema query
2026-05-17) and POSTs one Weaviate Decisions object per (key, version) tuple.
Deterministic UUID makes the POST idempotent — same row always maps to same
Weaviate id, so repeated runs are no-ops (422 already-exists is treated as
success).

ceo_memory has no `indexed` boolean, so we don't mark rows. The indexer is
convergent: every batch sweeps all rows and Weaviate dedups.

Cursor optimisation (not yet wired): `updated_at > $cursor` reduces the per-batch
scan to changed rows. Out of scope for phase A — full scan is cheap at current
ceo_memory cardinality (<5K rows expected) and the dedup path is fast.

Usage:
    python3 scripts/orchestrator/ceo_memory_indexer.py             # daemon loop
    python3 scripts/orchestrator/ceo_memory_indexer.py --once      # one batch
    python3 scripts/orchestrator/ceo_memory_indexer.py --batch=200 # custom batch
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any

import psycopg
from _heartbeat_shim import heartbeat_tick as _heartbeat_tick
from indexer_base import (
    BaseIndexer,
    aggregate_count,
    deterministic_uuid,
)

logger = logging.getLogger("ceo_memory_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DECISIONS_CLASS = "Decisions"
SOURCE_NAME = "ceo_memory"
POLL_SECONDS = int(os.environ.get("CEO_MEMORY_POLL_SECONDS", "30"))
BATCH_SIZE_DEFAULT = int(os.environ.get("CEO_MEMORY_BATCH_SIZE", "200"))

# Decisions class already exists per infra/weaviate/schema.py with the
# 5 mandatory properties (raw_text, environment_hash, created_at, agent, kei).
# This indexer relies on ensure_class returning fast when already present.
DECISIONS_SCHEMA = {
    "class": DECISIONS_CLASS,
    "vectorizer": "none",
    "properties": [
        {"name": "raw_text", "dataType": ["text"]},
        {"name": "environment_hash", "dataType": ["text"]},
        {"name": "created_at", "dataType": ["date"]},
        {"name": "agent", "dataType": ["text"]},
        {"name": "kei", "dataType": ["text"]},
    ],
}


@dataclass(frozen=True)
class CeoMemoryRow:
    key: str
    value: Any
    updated_at: Any
    version: int


_shutdown_requested = False


def _signal_handler(signum: int, _frame: Any) -> None:
    global _shutdown_requested
    logger.info("signal %s received — shutdown", signum)
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def _dsn() -> str:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not raw:
        raise SystemExit("indexer: DATABASE_URL or SUPABASE_DB_URL must be set")
    # psycopg expects plain `postgresql://`; some env vars use `postgresql+asyncpg://`.
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


class CeoMemoryIndexer(BaseIndexer[CeoMemoryRow]):
    """ceo_memory → Decisions concrete indexer (KEI-85 phase A)."""

    source_name = SOURCE_NAME
    target_class = DECISIONS_CLASS
    class_schema = DECISIONS_SCHEMA

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def fetch_batch(self, batch_size: int) -> list[CeoMemoryRow]:
        with self._conn.cursor() as cur:
            cur.execute(
                # Stable secondary sort on `key` to make the LIMIT deterministic
                # when multiple rows share the same updated_at timestamp.
                "SELECT key, value, updated_at, COALESCE(version, 1) "
                "FROM public.ceo_memory "
                "ORDER BY updated_at NULLS LAST, key ASC LIMIT %s",
                (batch_size,),
            )
            return [CeoMemoryRow(*r) for r in cur.fetchall()]

    def build_object(self, row: CeoMemoryRow) -> dict:
        return build_decision(row)


def build_decision(row: CeoMemoryRow) -> dict:
    raw_text = json.dumps({"key": row.key, "value": row.value}, default=str, sort_keys=True)
    env_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    kei = ""
    if isinstance(row.value, dict):
        kei = str(row.value.get("kei") or row.value.get("directive_kei") or "")
    return {
        "class": DECISIONS_CLASS,
        "id": deterministic_uuid(SOURCE_NAME, f"{row.key}:v{row.version}"),
        "properties": {
            "raw_text": raw_text,
            "environment_hash": env_hash,
            "created_at": (
                row.updated_at.isoformat() if row.updated_at else "1970-01-01T00:00:00Z"
            ),
            "agent": "system",
            "kei": kei,
        },
    }


def main() -> None:
    """Indexer entry point. Raises SystemExit on missing config; otherwise
    runs until SIGTERM/SIGINT in daemon mode, or exits after one batch in
    --once mode. Returns None — exit code is implicit (0 on clean shutdown,
    non-zero only if SystemExit was raised by a config error path).
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE_DEFAULT)
    args = parser.parse_args()

    logger.info(
        "indexer start source=%s class=%s batch=%d", SOURCE_NAME, DECISIONS_CLASS, args.batch
    )

    # prepare_threshold=None per reference_psycopg_supabase_pgbouncer (KEI-54B
    # PR #881): Supabase pooler is pgbouncer txn-mode and drops PREPARE between
    # leases. Without this, psycopg3 auto-prepares after 5 executions and the
    # next batch hits DuplicatePreparedStatement → InvalidSqlStatementName loop.
    # PR #1046 fixed this same bug in indexer_base.run_db_indexer; ceo_memory
    # has its own main() that bypasses run_db_indexer (predates KEI-109 dedup
    # extraction), so the fix must be reapplied here. Anchored Decisions count
    # stuck at 300 — Agency_OS-hzk5.
    with psycopg.connect(_dsn(), autocommit=True, prepare_threshold=None) as conn:
        indexer = CeoMemoryIndexer(conn)
        indexer.ensure_target_class()

        if args.once:
            outcome = indexer.index_once(args.batch)
            logger.info(
                "once outcome=%s class_count=%s",
                outcome.to_dict(),
                aggregate_count(DECISIONS_CLASS),
            )
            _heartbeat_tick(
                "ceo-memory-indexer",
                outcome_increment=outcome.success,
                status="ok" if outcome.failed == 0 else "degraded",
            )
            return
        while not _shutdown_requested:
            try:
                outcome = indexer.index_once(args.batch)
                logger.info(
                    "batch outcome=%s class_count=%s",
                    outcome.to_dict(),
                    aggregate_count(DECISIONS_CLASS),
                )
                _heartbeat_tick(
                    "ceo-memory-indexer",
                    outcome_increment=outcome.success,
                    status="ok" if outcome.failed == 0 else "degraded",
                )
            except Exception as exc:  # noqa: BLE001 — broad on purpose: any exception is a heartbeat-worthy signal
                logger.exception("batch failed — sleeping then continuing")
                _heartbeat_tick(
                    "ceo-memory-indexer",
                    outcome_increment=0,
                    status="error",
                    error_message=str(exc)[:500],
                )
            for _ in range(POLL_SECONDS):
                if _shutdown_requested:
                    break
                time.sleep(1)
    logger.info("indexer exiting cleanly")


if __name__ == "__main__":
    main()
    sys.exit(0)
