#!/usr/bin/env python3
"""agent_memories_indexer.py — Agency_OS-lsyd: public.agent_memories → Weaviate AgentMemories.

Sibling to elliot_memories_indexer (KEI-109): same target Weaviate class,
different source schema. Reads `public.agent_memories` — the multi-callsign
memory table (callsign, source_type, content, typed_metadata, tags,
created_at, state, valid_to, supersedes_id, ...) — and POSTs one Weaviate
AgentMemories object per (id, created_at) tuple. Deterministic UUID makes
the POST idempotent.

Filters out archived rows (`state != 'archived'`) and rows whose temporal
validity has lapsed (`valid_to IS NULL OR valid_to > NOW()`).

The `agent` Weaviate property is set per-row from the source `callsign`
column (NOT fixed like elliot_memories_indexer's 'elliot') so retrieval
can scope by callsign.

source_name="agent_memories" (distinct from elliot_memories_indexer's
"elliot_memories") so deterministic UUIDs from the two indexers do not
collide even if the underlying row ids ever overlap.

Discovered + filed alongside PR #1046 (KEI-70st) which only covered
elliot_internal.memories (1665 rows). public.agent_memories has 7400+ rows
non-archived across multiple callsigns (elliot/dave/aiden/max/system/...) —
all previously uncovered.

Daemon/--once dispatch + signal handling + heartbeat reporting come from
indexer_base.run_db_indexer (KEI-109 dedup extraction).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from indexer_base import BaseIndexer, deterministic_uuid, run_db_indexer

logger = logging.getLogger("agent_memories_indexer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

AGENT_MEMORIES_CLASS = "AgentMemories"
SOURCE_NAME = "agent_memories"
POLL_SECONDS = int(os.environ.get("AGENT_MEMORIES_POLL_SECONDS", "30"))
BATCH_SIZE_DEFAULT = int(os.environ.get("AGENT_MEMORIES_BATCH_SIZE", "200"))
CURSOR_PATH = Path(os.environ.get(
    "AGENT_MEMORIES_CURSOR_PATH",
    "/home/elliotbot/clawd/Agency_OS/.agent_memories_indexer.cursor"
))

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
class AgentMemoryRow:
    id: str
    callsign: str
    source_type: str
    content: str
    typed_metadata: Any
    tags: Any
    created_at: Any


class AgentMemoriesIndexer(BaseIndexer[AgentMemoryRow]):
    """public.agent_memories → AgentMemories concrete indexer (Agency_OS-lsyd)."""

    source_name = SOURCE_NAME
    target_class = AGENT_MEMORIES_CLASS
    class_schema = AGENT_MEMORIES_SCHEMA

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        self._cursor_created_at, self._cursor_id = self._load_cursor()
        logger.info("indexer cursor loaded: created_at=%s id=%s", self._cursor_created_at, self._cursor_id)

    def _load_cursor(self) -> tuple[str | None, str | None]:
        if not CURSOR_PATH.exists():
            return None, None
        try:
            d = json.loads(CURSOR_PATH.read_text())
            return d.get("last_created_at"), d.get("last_id")
        except (json.JSONDecodeError, OSError):
            return None, None

    def _save_cursor(self, created_at: Any, row_id: str) -> None:
        try:
            CURSOR_PATH.write_text(json.dumps({
                "last_created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                "last_id": row_id,
            }))
        except OSError as e:
            logger.warning("cursor save failed: %s", e)

    def fetch_batch(self, batch_size: int) -> list[AgentMemoryRow]:
        with self._conn.cursor() as cur:
            if self._cursor_created_at and self._cursor_id:
                cur.execute(
                    "SELECT id::text, callsign, source_type, content, typed_metadata, "
                    "tags, created_at "
                    "FROM public.agent_memories "
                    "WHERE state != 'archived' "
                    "AND (valid_to IS NULL OR valid_to > NOW()) "
                    "AND (created_at, id::text) > (%s, %s) "
                    "ORDER BY created_at NULLS LAST, id ASC LIMIT %s",
                    (self._cursor_created_at, self._cursor_id, batch_size),
                )
            else:
                cur.execute(
                    "SELECT id::text, callsign, source_type, content, typed_metadata, "
                    "tags, created_at "
                    "FROM public.agent_memories "
                    "WHERE state != 'archived' "
                    "AND (valid_to IS NULL OR valid_to > NOW()) "
                    "ORDER BY created_at NULLS LAST, id ASC LIMIT %s",
                    (batch_size,),
                )
            rows = [AgentMemoryRow(*r) for r in cur.fetchall()]
        # advance cursor on the last row of this batch
        if rows:
            last = rows[-1]
            self._cursor_created_at = last.created_at.isoformat() if hasattr(last.created_at, "isoformat") else str(last.created_at)
            self._cursor_id = last.id
            self._save_cursor(last.created_at, last.id)
        return rows

    def build_object(self, row: AgentMemoryRow) -> dict:
        return build_memory(row)


def build_memory(row: AgentMemoryRow) -> dict:
    raw_text = json.dumps(
        {
            "id": row.id,
            "callsign": row.callsign,
            "source_type": row.source_type,
            "content": row.content,
            "typed_metadata": row.typed_metadata,
            "tags": list(row.tags) if row.tags else [],
        },
        default=str,
        sort_keys=True,
    )
    env_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]
    kei = ""
    if isinstance(row.typed_metadata, dict):
        kei = str(row.typed_metadata.get("kei") or row.typed_metadata.get("directive_kei") or "")
    return {
        "class": AGENT_MEMORIES_CLASS,
        "id": deterministic_uuid(
            SOURCE_NAME,
            f"{row.id}:v{row.created_at.isoformat() if row.created_at else '0'}",
        ),
        "properties": {
            "raw_text": raw_text,
            "environment_hash": env_hash,
            "created_at": (
                row.created_at.isoformat() if row.created_at else "1970-01-01T00:00:00Z"
            ),
            "agent": row.callsign or "unknown",
            "kei": kei,
        },
    }


if __name__ == "__main__":
    run_db_indexer(
        AgentMemoriesIndexer,
        unit_name="agent-memories-indexer",
        default_batch=BATCH_SIZE_DEFAULT,
        poll_seconds=POLL_SECONDS,
    )
