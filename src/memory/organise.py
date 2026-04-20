"""
Event-triggered memory organisation.

Runs when write count exceeds thresholds (not on a schedule).
Operations:
1. Embed backfill — rows missing embeddings (capped at 50 per run)
2. Stale archive — confirmed rows with access_count=0 after 200+ total → archived
3. Write counter — store() calls increment_write_counter() on every write

Trigger: store() calls increment_write_counter() after every write.
Every 25 writes, run_organisation() fires automatically.
"""
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")

ORGANISE_EVERY_N_WRITES = 25
EMBED_BATCH_LIMIT = 50
STALE_MIN_ROWS = 200

_write_counter: int = 0


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def increment_write_counter() -> None:
    """Call after every store(). Triggers organisation at threshold."""
    global _write_counter
    _write_counter += 1
    if _write_counter >= ORGANISE_EVERY_N_WRITES:
        _write_counter = 0
        try:
            result = run_organisation()
            if any(v > 0 for v in result.values()):
                logger.info(f"[organise] auto-triggered: {result}")
        except Exception as exc:
            logger.warning(f"[organise] auto-trigger failed: {exc}")


def backfill_embeddings(limit: int = EMBED_BATCH_LIMIT) -> int:
    """Embed rows missing embeddings. Capped at `limit` per call."""
    if not OPENAI_API_KEY:
        return 0

    headers = _headers()
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/agent_memories?embedding=is.null&select=id,content&limit={limit}",
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
                emb_data = emb_resp.json()
                try:
                    from src.telegram_bot.openai_cost_logger import log_openai_call
                    usage = emb_data.get("usage", {})
                    log_openai_call(
                        callsign=os.environ.get("CALLSIGN", "unknown"),
                        use_case="backfill_embedding",
                        model="text-embedding-3-small",
                        input_tokens=usage.get("total_tokens", 0),
                    )
                except Exception:
                    pass
                embedding = emb_data["data"][0]["embedding"]
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


def archive_stale(limit: int = 20) -> int:
    """Archive confirmed rows with access_count=0. Returns count archived."""
    headers = _headers()

    # Only run if we have enough rows
    try:
        count_resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/agent_memories?select=id",
            headers={**headers, "Prefer": "count=exact"}, timeout=5,
        )
        total = int(count_resp.headers.get("content-range", "0/0").split("/")[-1])
        if total < STALE_MIN_ROWS:
            return 0
    except Exception:
        return 0

    # Find stale: confirmed + never accessed + older than 7 days + not system reference facts
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        resp = httpx.get(
            f"{SUPABASE_URL}/rest/v1/agent_memories"
            f"?state=eq.confirmed&access_count=eq.0"
            f"&callsign=neq.system"
            f"&created_at=lt.{cutoff}"
            f"&select=id&limit={limit}",
            headers=headers, timeout=10,
        )
        if resp.status_code != 200:
            return 0

        stale_ids = [r["id"] for r in resp.json()]
        count = 0
        for sid in stale_ids:
            try:
                httpx.patch(
                    f"{SUPABASE_URL}/rest/v1/agent_memories?id=eq.{sid}",
                    headers={**headers, "Prefer": "return=minimal"},
                    json={"state": "archived"},
                    timeout=5,
                )
                count += 1
            except Exception:
                pass
        if count:
            logger.info(f"[organise] archived {count} stale rows")
        return count
    except Exception:
        return 0


def run_organisation() -> dict:
    """Run all organisation operations. Returns summary."""
    return {
        "embedded": backfill_embeddings(),
        "stale_archived": archive_stale(),
    }
