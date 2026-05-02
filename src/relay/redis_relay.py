"""
FILE: src/relay/redis_relay.py
PURPOSE: Redis-backed relay transport (LPUSH/BRPOP) for inter-agent messaging
PHASE: Change 1b — dual-write alongside file-based relay
DEPENDENCIES:
  - src/integrations/redis.py (connection pool)
  - src/config/settings.py (REDIS_URL)
"""

import json
import logging
import os

import redis as redis_sync

from src.integrations.redis import get_redis

logger = logging.getLogger(__name__)


# ── Queue name builders ────────────────────────────────────────────────────────


def inbox_queue(callsign: str) -> str:
    return f"relay:inbox:{callsign}"


def outbox_queue(callsign: str) -> str:
    return f"relay:outbox:{callsign}"


def dispatch_queue(clone: str) -> str:
    return f"dispatch:{clone}"


# ── Async transport ────────────────────────────────────────────────────────────


async def push(queue: str, payload: dict) -> bool:
    """LPUSH payload to queue. Fail-open — returns False on error."""
    try:
        r = await get_redis()
        await r.lpush(queue, json.dumps(payload))
        return True
    except Exception as exc:
        logger.error("redis_relay.push failed queue=%s: %s", queue, exc)
        return False


async def pop(queue: str, timeout: int = 5) -> dict | None:
    """BRPOP from queue with timeout. Returns dict or None on timeout/error."""
    try:
        r = await get_redis()
        result = await r.brpop(queue, timeout=timeout)
        if result is None:
            return None
        _key, raw = result
        return json.loads(raw)
    except Exception as exc:
        logger.error("redis_relay.pop failed queue=%s: %s", queue, exc)
        return None


# ── Sync transport (for bash hooks) ───────────────────────────────────────────


def push_sync(queue: str, payload: dict) -> bool:
    """Synchronous LPUSH. For use from bash hooks via python3 -c. Fail-open."""
    try:
        r = redis_sync.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        r.lpush(queue, json.dumps(payload))
        return True
    except Exception as exc:
        logger.error("redis_relay.push_sync failed queue=%s: %s", queue, exc)
        return False
