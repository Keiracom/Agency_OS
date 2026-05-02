"""
FILE: src/memory/store.py
PURPOSE: Write a memory row to agent_memories via PostgREST.
         Auto-generates embedding via OpenAI text-embedding-3-small on every write.
         Auto-populates supersedes_id when a new decision/verified_fact closely
         matches an existing row (connective writes — diagnostic FM-6).
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

# Connective-write tuning (diagnostic FM-6 — no connective structure).
# When a new claim-like memory closely matches an existing one, auto-link them
# so the memory graph becomes navigable (instead of flat, with the Pipeline-E-
# style contradictions piling up unresolved).
SUPERSEDE_THRESHOLD = 0.88  # cosine similarity required to treat new as supersession
SUPERSEDE_SOURCE_TYPES: set[str] = {"decision", "verified_fact", "dave_confirmed"}


def _generate_embedding(text: str) -> list[float] | None:
    """Generate embedding via OpenAI text-embedding-3-small. Best-effort."""
    if not OPENAI_API_KEY:
        return None
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": "text-embedding-3-small", "input": text[:8000]},
            timeout=10,
        )
        if resp.status_code == 200:
            emb_data = resp.json()
            try:
                from src.telegram_bot.openai_cost_logger import log_openai_call

                usage = emb_data.get("usage", {})
                log_openai_call(
                    callsign=os.environ.get("CALLSIGN", "unknown"),
                    use_case="store_embedding",
                    model="text-embedding-3-small",
                    input_tokens=usage.get("total_tokens", 0),
                )
            except Exception:
                pass
            return emb_data["data"][0]["embedding"]
    except Exception as exc:
        logger.warning(f"[store] embedding generation failed: {exc}")
    return None


def _find_supersede_candidate(
    embedding: list[float],
    source_type: str,
    callsign: str,
    new_state: str,
) -> str | None:
    """Look up an existing row this new write would supersede.

    Rules:
    - Same source_type, same callsign
    - Cosine similarity >= SUPERSEDE_THRESHOLD
    - Existing row must be in ('tentative', 'confirmed') — not already superseded
    - A tentative new row cannot supersede a confirmed existing row
      (protects curated memory from uncurated writes)

    Returns the candidate's id if found, else None. Best-effort — returns None on error.
    """
    if source_type not in SUPERSEDE_SOURCE_TYPES:
        return None
    try:
        rpc_url = _supabase_url() + "/rest/v1/rpc/match_agent_memories"
        headers = _supabase_headers()
        resp = httpx.post(
            rpc_url,
            headers=headers,
            json={
                "query_embedding": embedding,
                "match_count": 3,
                "match_threshold": SUPERSEDE_THRESHOLD,
            },
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        rows = resp.json() or []
        for row in rows:
            if row.get("source_type") != source_type:
                continue
            if row.get("callsign") != callsign:
                continue
            existing_state = row.get("state", "confirmed")
            if existing_state not in ("tentative", "confirmed"):
                continue
            # Guard: don't let tentative writes supersede confirmed rows
            if new_state == "tentative" and existing_state == "confirmed":
                continue
            return row.get("id")
    except Exception as exc:
        logger.warning(f"[store] supersede-candidate lookup failed: {exc}")
    return None


def _mark_superseded(row_id: str) -> None:
    """UPDATE the older row's state to 'superseded'. Best-effort, no-raise."""
    try:
        url = _supabase_url() + f"/rest/v1/agent_memories?id=eq.{row_id}"
        headers = {**_supabase_headers(), "Prefer": "return=minimal"}
        httpx.patch(url, headers=headers, json={"state": "superseded"}, timeout=5)
    except Exception as exc:
        logger.warning(f"[store] mark-superseded failed for {row_id}: {exc}")


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
            f"Invalid source_type {source_type!r}. Must be one of: {sorted(VALID_SOURCE_TYPES)}"
        )

    ratelimit.check_and_increment()

    # Auto-generate embedding for immediate semantic searchability
    embedding = _generate_embedding(content)

    # Connective write (FM-6): if this write is a claim-type and closely matches
    # an existing row, link them via supersedes_id and mark the older superseded.
    supersede_id: str | None = None
    if embedding is not None:
        supersede_id = _find_supersede_candidate(embedding, source_type, callsign, state)

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
    if supersede_id:
        payload["supersedes_id"] = supersede_id
    if valid_from is not None:
        payload["valid_from"] = valid_from.isoformat()
    if valid_to is not None:
        payload["valid_to"] = valid_to.isoformat()

    url = _supabase_url() + MEMORIES_ENDPOINT
    headers = _supabase_headers()

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Supabase returned {response.status_code}: {response.text}")
        row = response.json()
        # PostgREST returns a list when Prefer: return=representation
        if isinstance(row, list):
            row = row[0]
        # Now that the new row landed cleanly, retire the old one
        if supersede_id:
            _mark_superseded(supersede_id)
            logger.info(f"[store] connective write: new {source_type} supersedes {supersede_id}")
        # Trigger organisation check (every N writes)
        try:
            from .organise import increment_write_counter

            increment_write_counter()
        except Exception:
            pass  # never block store on organisation failure

        mem0_row_id = uuid.UUID(row["id"])

        # Parallel Mem0 write (feature-flagged, best-effort)
        if os.environ.get("MEM0_INTEGRATION_ENABLED", "").lower() == "true":
            try:
                from src.governance.mem0_adapter import Mem0Adapter

                adapter = Mem0Adapter()
                adapter.add(
                    content=content,
                    metadata={**(typed_metadata or {}), "supabase_id": str(mem0_row_id)},
                    callsign=callsign,
                    source_type=source_type,
                )
            except Exception as mem0_exc:
                logger.warning(f"[store] Mem0 parallel write failed (non-blocking): {mem0_exc}")

        return mem0_row_id
    except httpx.HTTPError as exc:
        raise RuntimeError(f"HTTP error storing memory: {exc}") from exc
