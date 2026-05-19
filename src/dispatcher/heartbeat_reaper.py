"""KEI-211 — Dispatcher heartbeat reaper (task-progress zombie cleanup).

Pairs with ``src.dispatcher.heartbeat_watchdog``. Watchdog detects zombies
and publishes one event per zombie on NATS
``keiracom.agent.status.{callsign}``; this reaper subscribes to that
wildcard subject and performs the cleanup actions:

  1. Mark the task ``status='failed'`` with ``released_at=NOW()`` in
     ``public.tasks``. Idempotent: the WHERE clause filters on
     ``status='active'`` so a task already reaped (or naturally completed)
     between watchdog detect and reaper handle is a no-op.
  2. Decrement the Valkey thread counter for the callsign:
     ``DECR thr:<callsign>``. Floor at 0 — a transient over-decrement is
     corrected by the session_manager on next session bind. Mirrors the
     ``rl:`` / ``spend:`` namespace convention documented in
     ``valkey_pool.py``.
  3. Write a ``reaper_observation`` row to ``public.agent_memories`` so
     the audit trail captures both detection (watchdog_observation by the
     watchdog) and remediation (this module).

Explicitly does NOT respawn — the dispatcher's session_manager handles
respawn on next claim. Out-of-process tmux kill is left to
``src.dispatcher.reaper`` (the tmux/container lifecycle reaper) which
runs independently.

Env contract identical to ``heartbeat_watchdog`` — DSN, NATS_URL — plus
``HEARTBEAT_REAPER_QUEUE_GROUP`` to enable multi-instance load-shedding
via NATS queue subscriptions when the dispatcher fleet scales out.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

NATS_URL_ENV = "NATS_URL"
DEFAULT_NATS_URL = "nats://127.0.0.1:4222"
NATS_SUBJECT_WILDCARD = "keiracom.agent.status.*"
QUEUE_GROUP_ENV = "HEARTBEAT_REAPER_QUEUE_GROUP"
DEFAULT_QUEUE_GROUP = "heartbeat_reaper"

# Valkey key family for per-callsign thread counts. See valkey_pool.py
# §"Key namespace contract" — <family>:<scope>:<period?>.
THREAD_COUNT_PREFIX = "thr"

# DSN scheme suffix — mirrors heartbeat_watchdog / spend_tracker.
_ASYNCPG_DSN_PREFIX = "+asyncpg"


@dataclass(frozen=True)
class ReapResult:
    task_id: str
    callsign: str
    task_marked_failed: bool
    valkey_decremented: bool
    audit_logged: bool


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace(_ASYNCPG_DSN_PREFIX, "").replace("postgresql+asyncpg://", "postgresql://", 1)


def thread_count_key(callsign: str) -> str:
    """Build the Valkey thread-count key. Refuses blank callsign per KEI-117A
    namespace contract — no unscoped keys.
    """
    if not callsign or not callsign.strip():
        raise ValueError("callsign must be a non-empty string")
    return f"{THREAD_COUNT_PREFIX}:{callsign.strip()}"


def _mark_task_failed(task_id: str) -> bool:
    """Idempotent UPDATE — only fires when row is still active."""
    try:
        import psycopg  # noqa: PLC0415

        with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.tasks
                   SET status = 'failed',
                       released_at = NOW()
                 WHERE id = %s::uuid
                   AND status = 'active'
                """,
                (task_id,),
            )
            updated = cur.rowcount
            conn.commit()
        return updated > 0
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("tasks UPDATE failed for task=%s: %s", task_id, exc)
        return False


async def _decrement_thread_count(callsign: str) -> bool:
    """DECR thr:<callsign>, floor at 0. Returns True on success."""
    try:
        from src.dispatcher.valkey_pool import get_valkey_client  # noqa: PLC0415

        client = await get_valkey_client()
        key = thread_count_key(callsign)
        new_value = await client.decr(key)
        if int(new_value) < 0:
            # Floor at 0 — transient over-decrement is corrected by
            # session_manager on next bind.
            await client.set(key, 0)
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("Valkey DECR %s failed: %s", callsign, exc)
        return False


def _log_reap_observation(task_id: str, callsign: str, task_marked: bool) -> bool:
    """Write reaper_observation row to public.agent_memories. Fail-open."""
    try:
        import psycopg  # noqa: PLC0415

        content = f"reaper: task {task_id} ({callsign}) reaped — task_marked_failed={task_marked}"
        metadata = {
            "task_id": task_id,
            "task_marked_failed": task_marked,
        }
        with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.agent_memories
                    (id, callsign, source_type, content, typed_metadata,
                     created_at, valid_from, state)
                VALUES (gen_random_uuid(), %s, 'reaper_observation', %s,
                        %s::jsonb, NOW(), NOW(), 'confirmed')
                """,
                (callsign, content, json.dumps(metadata)),
            )
            conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("reaper_observation log failed for task=%s: %s", task_id, exc)
        return False


async def reap_one(task_id: str, callsign: str) -> ReapResult:
    """Apply all three reap actions for one zombie task. Independent legs:
    each leg fails open so a NATS-delivered event always produces SOME audit
    trail even if one downstream is degraded.
    """
    task_marked = _mark_task_failed(task_id)
    decremented = await _decrement_thread_count(callsign)
    logged = _log_reap_observation(task_id, callsign, task_marked)
    return ReapResult(
        task_id=task_id,
        callsign=callsign,
        task_marked_failed=task_marked,
        valkey_decremented=decremented,
        audit_logged=logged,
    )


def parse_zombie_event(payload: bytes) -> dict[str, Any] | None:
    """Decode a watchdog NATS payload into (task_id, callsign).

    Returns None on any decode / shape error so the subscriber can log +
    skip without crashing the loop.
    """
    try:
        msg = json.loads(payload)
        if msg.get("type") != "zombie_detected":
            return None
        task_id = msg.get("task_id")
        callsign = msg.get("callsign")
        if not task_id or not callsign:
            return None
        return {"task_id": task_id, "callsign": callsign}
    except (json.JSONDecodeError, AttributeError, TypeError) as exc:
        logger.warning("malformed zombie event payload: %s", exc)
        return None


async def run_forever() -> None:
    """Long-running NATS-subscribe loop. Use as a systemd-managed service entrypoint."""
    import nats.aio.client as nats_client  # noqa: PLC0415

    url = os.environ.get(NATS_URL_ENV, DEFAULT_NATS_URL)
    queue_group = os.environ.get(QUEUE_GROUP_ENV, DEFAULT_QUEUE_GROUP)
    nc = nats_client.Client()
    await nc.connect(url, connect_timeout=2)
    logger.info(
        "heartbeat_reaper subscribed to %s (queue=%s)",
        NATS_SUBJECT_WILDCARD,
        queue_group,
    )

    async def _on_msg(msg: Any) -> None:
        parsed = parse_zombie_event(msg.data)
        if parsed is None:
            return
        result = await reap_one(parsed["task_id"], parsed["callsign"])
        logger.info("reap_one result: %s", result)

    await nc.subscribe(NATS_SUBJECT_WILDCARD, queue=queue_group, cb=_on_msg)
    # Sleep forever — subscription runs in the background. Never returns
    # under normal operation; systemd restarts on crash.
    while True:
        await asyncio.sleep(3600)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
