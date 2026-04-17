"""
FILE: src/memory/store.py
PURPOSE: Write a memory row to agent_memories via PostgREST.
         No embedding — v1 is text+tag+type only.
"""

import uuid
from datetime import datetime

import httpx

from . import ratelimit
from .client import MEMORIES_ENDPOINT, _supabase_headers, _supabase_url
from .types import VALID_SOURCE_TYPES


def store(
    callsign: str,
    source_type: str,
    content: str,
    typed_metadata: dict | None = None,
    tags: list[str] | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> uuid.UUID:
    """Persist a memory row. Returns the UUID of the inserted row.

    Raises:
        ValueError: source_type not in VALID_SOURCE_TYPES.
        RateLimitExceeded: daily write cap hit.
        RuntimeError: Supabase HTTP error or connection failure.
    """
    if source_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_type {source_type!r}. "
            f"Must be one of: {sorted(VALID_SOURCE_TYPES)}"
        )

    ratelimit.check_and_increment()

    payload: dict = {
        "callsign": callsign,
        "source_type": source_type,
        "content": content,
        "typed_metadata": typed_metadata or {},
        "tags": tags or [],
    }
    # Only include valid_from/valid_to if explicitly provided;
    # DB DEFAULT now() fires when omitted.
    if valid_from is not None:
        payload["valid_from"] = valid_from.isoformat()
    if valid_to is not None:
        payload["valid_to"] = valid_to.isoformat()

    url = _supabase_url() + MEMORIES_ENDPOINT
    headers = _supabase_headers()

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"Supabase returned {response.status_code}: {response.text}"
            )
        row = response.json()
        # PostgREST returns a list when Prefer: return=representation
        if isinstance(row, list):
            row = row[0]
        return uuid.UUID(row["id"])
    except httpx.HTTPError as exc:
        raise RuntimeError(f"HTTP error storing memory: {exc}") from exc
