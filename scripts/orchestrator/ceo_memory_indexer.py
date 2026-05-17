#!/usr/bin/env python3
"""ceo_memory_indexer.py — KEI-85 phase A: index public.ceo_memory into Weaviate Decisions.

Reads `public.ceo_memory` (key text, value jsonb, updated_at timestamptz, version int)
and POSTs one Weaviate Decisions object per (key, version) tuple. Deterministic UUID
makes the POST idempotent — same row always maps to same Weaviate id, so repeated
runs are no-ops (422 already-exists is treated as success).

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
from indexer_base import (
    aggregate_count,
    deterministic_uuid,
    ensure_class,
    post_object,
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


def fetch_batch(conn: psycopg.Connection, batch: int) -> list[CeoMemoryRow]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT key, value, updated_at, COALESCE(version, 1) "
            "FROM public.ceo_memory ORDER BY updated_at NULLS LAST LIMIT %s",
            (batch,),
        )
        return [CeoMemoryRow(*r) for r in cur.fetchall()]


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


def index_once(conn: psycopg.Connection, batch_size: int) -> dict[str, int]:
    rows = fetch_batch(conn, batch_size)
    success = 0
    failed = 0
    for row in rows:
        if post_object(build_decision(row)):
            success += 1
        else:
            failed += 1
    return {"selected": len(rows), "success": success, "failed": failed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--batch", type=int, default=BATCH_SIZE_DEFAULT)
    args = parser.parse_args()

    ensure_class(DECISIONS_CLASS, DECISIONS_SCHEMA)
    logger.info(
        "indexer start source=%s class=%s batch=%d", SOURCE_NAME, DECISIONS_CLASS, args.batch
    )

    with psycopg.connect(_dsn(), autocommit=True) as conn:
        if args.once:
            outcome = index_once(conn, args.batch)
            logger.info("once outcome=%s class_count=%s", outcome, aggregate_count(DECISIONS_CLASS))
            return 0
        while not _shutdown_requested:
            try:
                outcome = index_once(conn, args.batch)
                logger.info(
                    "batch outcome=%s class_count=%s", outcome, aggregate_count(DECISIONS_CLASS)
                )
            except Exception:
                logger.exception("batch failed — sleeping then continuing")
            for _ in range(POLL_SECONDS):
                if _shutdown_requested:
                    break
                time.sleep(1)
    logger.info("indexer exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
