"""
FILE: src/memory/store.py
PURPOSE: Write a memory row to agent_memories via PostgREST.
         Auto-generates embedding via OpenAI text-embedding-3-small on every write.
"""

import logging
import os
import uuid
from datetime import datetime

import httpx

from . import ratelimit
from .client import MEMORIES_ENDPOINT, _supabase_headers, _supabase_url
from .types import VALID_SOURCE_TYPES

logger = logging.getLogger(__name__)

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")


def _generate_embedding(text: str) -> list[float] | None:
    """Generate embedding via OpenAI text-embedding-3-small. Best-effort."""
    if not OPENAI_API_KEY:
        return None
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": text[:8000]},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()["data"][0]["embedding"]
    except Exception as exc:
        logger.warning(f"[store] embedding generation failed: {exc}")
    return None


def store(
    callsign: str,
    source_type: str,
    content: str,
    typed_metadata: dict | None = None,
    tags: list[str] | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    state: str = "tentative",
    trust: str = "agent_extracted",
    confidence: float = 0.8,
) -> uuid.UUID:
    """Persist a memory row with auto-generated embedding. Returns UUID.

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

    # Auto-generate embedding for immediate semantic searchability
    embedding = _generate_embedding(content)

    payload: dict = {
        "callsign": callsign,
        "source_type": source_type,
        "content": content,
        "typed_metadata": typed_metadata or {},
        "tags": tags or [],
        "state": state,
        "trust": trust,
        "confidence": confidence,
    }
    if embedding:
        payload["embedding"] = embedding
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
