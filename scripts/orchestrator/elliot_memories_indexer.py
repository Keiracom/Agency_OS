#!/usr/bin/env python3
"""elliot_memories_indexer.py — KEI-109: index elliot_internal.memories into Weaviate AgentMemories.

Reads `elliot_internal.memories` (live prod schema: id uuid, content text,
type text, metadata jsonb, created_at/updated_at/deleted_at/expires_at
timestamptz — verified via Supabase MCP information_schema query
2026-05-17) and POSTs one Weaviate AgentMemories object per (id, updated_at)
tuple. Deterministic UUID makes the POST idempotent — same row+timestamp
maps to same Weaviate id, so repeated runs are no-ops.

Filters:
  - deleted_at IS NULL (soft-delete tombstones skipped)
  - expires_at IS NULL OR expires_at > NOW() (expired rows skipped)

Convergent — like ceo_memory_indexer, every batch sweeps the unexpired
undeleted set and Weaviate dedups. Source agent is fixed to 'elliot' since
the source schema is elliot_internal.

Usage:
    python3 scripts/orchestrator/elliot_memories_indexer.py             # daemon
    python3 scripts/orchestrator/elliot_memories_indexer.py --once      # one batch
    python3 scripts/orchestrator/elliot_memories_indexer.py --batch=200 # custom
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

logger = logging.getLogger("elliot_memories_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

AGENT_MEMORIES_CLASS = "AgentMemories"
SOURCE_NAME = "elliot_memories"
SOURCE_AGENT = "elliot"  # fixed: indexer reads from elliot_internal schema
POLL_SECONDS = int(os.environ.get("ELLIOT_MEMORIES_POLL_SECONDS", "30"))
BATCH_SIZE_DEFAULT = int(os.environ.get("ELLIOT_MEMORIES_BATCH_SIZE", "200"))

# AgentMemories class shape — 5 mandatory BaseIndexer ABC properties.
AGENT_MEMORIES_SCHEMA = {
    "class": AGENT_MEMORIES_CLASS,
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
class ElliotMemoryRow:
    id: str
    content: str
    type: str
    metadata: Any
    updated_at: Any


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
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


class ElliotMemoriesIndexer(BaseIndexer[ElliotMemoryRow]):
    """elliot_internal.memories → AgentMemories concrete indexer (KEI-109)."""

    source_name = SOURCE_NAME
    target_class = AGENT_MEMORIES_CLASS
    class_schema = AGENT_MEMORIES_SCHEMA

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def fetch_batch(self, batch_size: int) -> list[ElliotMemoryRow]:
        with self._conn.cursor() as cur:
            # Stable secondary sort on `id` to make LIMIT deterministic
            # when multiple rows share the same updated_at.
            cur.execute(
                "SELECT id::text, content, type, metadata, updated_at "
                "FROM elliot_internal.memories "
                "WHERE deleted_at IS NULL "
                "AND (expires_at IS NULL OR expires_at > NOW()) "
                "ORDER BY updated_at NULLS LAST, id ASC LIMIT %s",
                (batch_size,),
            )
            return [ElliotMemoryRow(*r) for r in cur.fetchall()]

    def build_object(self, row: ElliotMemoryRow) -> dict:
        return build_memory(row)


def build_memory(row: ElliotMemoryRow) -> dict:
    raw_text = json.dumps(
        {"id": row.id, "type": row.type, "content": row.content, "metadata": row.metadata},
        default=str,
        sort_keys=True,
    )
    env_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    kei = ""
    if isinstance(row.metadata, dict):
        kei = str(row.metadata.get("kei") or row.metadata.get("directive_kei") or "")
    return {
        "class": AGENT_MEMORIES_CLASS,
        "id": deterministic_uuid(
            SOURCE_NAME,
            f"{row.id}:v{row.updated_at.isoformat() if row.updated_at else '0'}",
        ),
        "properties": {
            "raw_text": raw_text,
            "environment_hash": env_hash,
            "created_at": (
                row.updated_at.isoformat() if row.updated_at else "1970-01-01T00:00:00Z"
            ),
            "agent": SOURCE_AGENT,
            "kei": kei,
        },
    }


def main() -> None:
    """Indexer entry point. Raises SystemExit on missing config; otherwise
    runs until SIGTERM/SIGINT in daemon mode, or exits after one batch in
    --once mode.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE_DEFAULT)
    args = parser.parse_args()

    logger.info(
        "indexer start source=%s class=%s batch=%d",
        SOURCE_NAME,
        AGENT_MEMORIES_CLASS,
        args.batch,
    )

    with psycopg.connect(_dsn(), autocommit=True) as conn:
        indexer = ElliotMemoriesIndexer(conn)
        indexer.ensure_target_class()

        if args.once:
            outcome = indexer.index_once(args.batch)
            logger.info(
                "once outcome=%s class_count=%s",
                outcome.to_dict(),
                aggregate_count(AGENT_MEMORIES_CLASS),
            )
            _heartbeat_tick(
                "elliot-memories-indexer",
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
                    aggregate_count(AGENT_MEMORIES_CLASS),
                )
                _heartbeat_tick(
                    "elliot-memories-indexer",
                    outcome_increment=outcome.success,
                    status="ok" if outcome.failed == 0 else "degraded",
                )
            except Exception as exc:  # noqa: BLE001 — broad on purpose: any exception is a heartbeat-worthy signal
                logger.exception("batch failed — sleeping then continuing")
                _heartbeat_tick(
                    "elliot-memories-indexer",
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
