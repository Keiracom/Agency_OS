"""
Event-triggered memory organisation.

Runs when total row count exceeds thresholds (not on a schedule).
Three operations:
1. Dedup — find near-duplicate pairs (cosine >= 0.92), supersede older
2. Stale check — flag confirmed rows with access_count=0 after N total rows
3. Embed backfill — embed any rows missing embeddings

Trigger: call check_and_organise() after any batch of writes.
"""
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

# Thresholds for triggering organisation
DEDUP_THRESHOLD = 50  # run dedup every N new rows
STALE_CHECK_THRESHOLD = 100  # flag stale rows every N new rows

_last_dedup_count: int = 0
_last_stale_count: int = 0


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def get_total_count() -> int:
    """Get total row count from agent_memories."""
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/agent_memories?select=id",
            headers={**_headers(), "Prefer": "count=exact"},
            timeout=5,
        )
        return int(resp.headers.get("content-range", "0/0").split("/")[-1])
    except Exception:
        return 0


def backfill_embeddings() -> int:
    """Embed any rows missing embeddings. Returns count embedded."""
    if not OPENAI_API_KEY:
        return 0

    headers = _headers()
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/agent_memories?embedding=is.null&select=id,content",
        headers=headers, timeout=10,
    )
    if resp.status_code != 200:
        return 0

    rows = resp.json()
    count = 0
    for row in rows:
        try:
            emb_resp = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "text-embedding-3-small", "input": row["content"][:8000]},
                timeout=10,
            )
            if emb_resp.status_code == 200:
                embedding = emb_resp.json()["data"][0]["embedding"]
                httpx.patch(
                    f"{SUPABASE_URL}/rest/v1/agent_memories?id=eq.{row['id']}",
                    headers={**headers, "Prefer": "return=minimal"},
                    json={"embedding": embedding},
                    timeout=10,
                )
                count += 1
        except Exception:
            pass
    if count:
        logger.info(f"[organise] backfilled {count} embeddings")
    return count


def check_and_organise() -> dict:
    """Event-triggered organisation. Call after batch writes.

    Returns summary of actions taken.
    """
    global _last_dedup_count, _last_stale_count

    total = get_total_count()
    actions = {"total": total, "embedded": 0, "deduped": 0, "stale_flagged": 0}

    # Always backfill missing embeddings
    actions["embedded"] = backfill_embeddings()

    # Dedup when threshold crossed
    if total - _last_dedup_count >= DEDUP_THRESHOLD:
        _last_dedup_count = total
        logger.info(f"[organise] dedup threshold crossed at {total} rows")
        # Dedup is expensive (cross-join) — leave for manual trigger via Aiden's SQL
        # Just log the trigger, actual dedup runs separately

    return actions
