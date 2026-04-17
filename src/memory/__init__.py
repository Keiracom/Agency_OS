"""
src/memory/__init__.py
Canonical interface for writing agent memories to Supabase.

All agent_memories writes must go through store() — this enforces:
  - Source-type validation against VALID_SOURCE_TYPES
  - Consistent payload shape and headers
  - Single place to add rate limiting or circuit-breaking later

Usage:
    from src.memory import store
    await store(callsign="elliot", source_type="pattern", content="...", tags=["pattern"])
"""

import logging
import os

import httpx

from .types import VALID_SOURCE_TYPES

logger = logging.getLogger(__name__)

_SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
_AGENT_MEMORIES_TABLE = "agent_memories"


def _headers() -> dict[str, str]:
    key = _SUPABASE_KEY or os.getenv("SUPABASE_SERVICE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def store(
    *,
    callsign: str,
    source_type: str,
    content: str,
    tags: list[str] | None = None,
    typed_metadata: dict | None = None,
) -> dict:
    """Write one row to agent_memories. Returns the created row.

    Raises ValueError for invalid source_type.
    Raises httpx.HTTPStatusError on Supabase errors.
    """
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_type {source_type!r}. "
            f"Must be one of: {sorted(VALID_SOURCE_TYPES)}"
        )

    url = f"{_SUPABASE_URL}/rest/v1/{_AGENT_MEMORIES_TABLE}"
    payload: dict = {
        "callsign": callsign,
        "source_type": source_type,
        "content": content,
    }
    if tags is not None:
        payload["tags"] = tags
    if typed_metadata is not None:
        payload["typed_metadata"] = typed_metadata

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=_headers(), json=payload, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else payload
