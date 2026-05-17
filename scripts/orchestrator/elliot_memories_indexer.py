#!/usr/bin/env python3
"""elliot_memories_indexer.py — KEI-109: elliot_internal.memories → Weaviate AgentMemories.

Reads `elliot_internal.memories` (id uuid, content text, type text, metadata
jsonb, updated_at timestamptz — verified via Supabase MCP 2026-05-17) and
POSTs one Weaviate AgentMemories object per (id, updated_at) tuple.
Deterministic UUID makes the POST idempotent.

Filters out soft-deleted (`deleted_at IS NULL`) and expired
(`expires_at IS NULL OR expires_at > NOW()`) rows. Convergent — every
batch sweeps the unexpired/undeleted set and Weaviate dedups.

The agent property is fixed to 'elliot' since source schema is
elliot_internal; future agent-scoped schemas get their own indexer.

Daemon/--once dispatch + signal handling + heartbeat reporting come from
indexer_base.run_db_indexer (KEI-109 dedup extraction).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import psycopg
from indexer_base import BaseIndexer, deterministic_uuid, run_db_indexer

logger = logging.getLogger("elliot_memories_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

AGENT_MEMORIES_CLASS = "AgentMemories"
SOURCE_NAME = "elliot_memories"
SOURCE_AGENT = "elliot"
POLL_SECONDS = int(os.environ.get("ELLIOT_MEMORIES_POLL_SECONDS", "30"))
BATCH_SIZE_DEFAULT = int(os.environ.get("ELLIOT_MEMORIES_BATCH_SIZE", "200"))

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


class ElliotMemoriesIndexer(BaseIndexer[ElliotMemoryRow]):
    """elliot_internal.memories → AgentMemories concrete indexer (KEI-109)."""

    source_name = SOURCE_NAME
    target_class = AGENT_MEMORIES_CLASS
    class_schema = AGENT_MEMORIES_SCHEMA

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def fetch_batch(self, batch_size: int) -> list[ElliotMemoryRow]:
        with self._conn.cursor() as cur:
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


if __name__ == "__main__":
    run_db_indexer(
        ElliotMemoriesIndexer,
        unit_name="elliot-memories-indexer",
        default_batch=BATCH_SIZE_DEFAULT,
        poll_seconds=POLL_SECONDS,
    )
