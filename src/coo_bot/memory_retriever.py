"""src/coo_bot/memory_retriever.py — context loader for the Max COO Opus prompt.

MAX-COO-PHASE-B / Phase B File 2.

Three retrievers + one assembler:

  get_relevant_memories(query, limit=5)
      ILIKE search on public.agent_memories. When MEMORY_RECALL_BACKEND in
      ('mem0', 'hybrid'), delegates to memory_listener.recall_via_mem0 for
      relationship-aware recall; otherwise direct Supabase query.

  get_high_value_memories(callsign='aiden', limit=10)
      Loads source_type IN (pattern, decision, dave_confirmed, verified_fact)
      rows for the given callsign, newest first.

  get_ceo_memory_keys(prefix)
      Loads public.ceo_memory rows whose `key` starts with `prefix`.

  assemble_context(query)
      Combines all three above into a single formatted block ready for
      Opus prompt injection.

Every external call is wrapped in try/except — a memory miss must never
block the COO bot from responding. Failures return [] / "" and log a
warning.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_HIGH_VALUE_SOURCE_TYPES = (
    "pattern",
    "decision",
    "dave_confirmed",
    "verified_fact",
)


def _supabase_client():
    """Build a service-role Supabase client. Returns None if env or pkg
    missing — callers degrade to []."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get(
        "SUPABASE_KEY",
        "",
    )
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore
    except ImportError:
        logger.warning("[memory_retriever] supabase package not installed")
        return None
    try:
        return create_client(url, key)
    except Exception as exc:
        logger.warning("[memory_retriever] supabase client init failed: %s", exc)
        return None


def _supabase_ilike_search(query: str, limit: int) -> list[dict[str, Any]]:
    client = _supabase_client()
    if client is None:
        return []
    try:
        response = (
            client.table("agent_memories")
            .select("id,content,source_type,callsign,created_at")
            .ilike("content", f"%{query}%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(getattr(response, "data", None) or [])
    except Exception as exc:
        logger.warning("[memory_retriever] ilike search failed: %s", exc)
        return []


async def get_relevant_memories(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Load relevant agent_memories rows for `query`.

    Routes through memory_listener.recall_via_mem0 when MEMORY_RECALL_BACKEND
    in ('mem0','hybrid'), otherwise direct Supabase ILIKE. Async because
    callers run inside the bot's event loop — we must await recall_via_mem0
    rather than spawn a nested asyncio.run() (which raises
    'cannot be called from a running event loop').
    """
    backend = os.environ.get("MEMORY_RECALL_BACKEND", "supabase").lower()
    if backend in ("mem0", "hybrid"):
        try:
            from src.telegram_bot.memory_listener import recall_via_mem0

            callsign = os.environ.get("CALLSIGN", "aiden")
            return await recall_via_mem0(query, callsign=callsign, limit=limit)
        except Exception as exc:
            logger.warning(
                "[memory_retriever] memory_listener path failed (%s); falling back to supabase",
                exc,
            )
    return _supabase_ilike_search(query, limit)


def get_high_value_memories(
    callsign: str = "aiden",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Load high-signal agent_memories for `callsign`, newest first."""
    client = _supabase_client()
    if client is None:
        return []
    try:
        response = (
            client.table("agent_memories")
            .select("id,content,source_type,callsign,created_at")
            .eq("callsign", callsign)
            .in_("source_type", list(_HIGH_VALUE_SOURCE_TYPES))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(getattr(response, "data", None) or [])
    except Exception as exc:
        logger.warning("[memory_retriever] high-value query failed: %s", exc)
        return []


def get_ceo_memory_keys(prefix: str) -> list[dict[str, Any]]:
    """Load public.ceo_memory rows whose `key` starts with `prefix`."""
    client = _supabase_client()
    if client is None:
        return []
    try:
        response = (
            client.table("ceo_memory")
            .select("key,value,updated_at")
            .like("key", f"{prefix}%")
            .order("updated_at", desc=True)
            .execute()
        )
        return list(getattr(response, "data", None) or [])
    except Exception as exc:
        logger.warning("[memory_retriever] ceo_memory query failed: %s", exc)
        return []


def _format_block(title: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"### {title}\n(none)\n"
    lines = [f"### {title}"]
    for row in rows:
        # ceo_memory rows expose key/value; agent_memories rows expose content.
        if "key" in row:
            lines.append(f"- {row['key']}: {row.get('value', '')}")
        else:
            src = row.get("source_type", "")
            lines.append(f"- [{src}] {row.get('content', '')}")
    return "\n".join(lines) + "\n"


async def assemble_context(query: str) -> str:
    """Build the combined context block injected into the Opus prompt.

    Async because get_relevant_memories is async (must await recall_via_mem0
    inside the bot's running event loop).
    """
    relevant = await get_relevant_memories(query)
    high_value = get_high_value_memories()
    ceo_keys = get_ceo_memory_keys("ceo:")
    parts = [
        _format_block("Relevant Memories", relevant),
        _format_block("High-Value Memories", high_value),
        _format_block("CEO Memory", ceo_keys),
    ]
    return "\n".join(parts)
