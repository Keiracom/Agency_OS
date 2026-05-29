"""PG→Valkey producer bridge for the work loop (Agency_OS-nkc0).

The Postgres producer signal already exists: the `kei45_emit_task_event` trigger
(migration 20260514_kei45_tasks_realtime.sql) fires `pg_notify('task_event', ...)`
with `event_type='new_available'` when a task becomes available. Postgres can't
publish to Valkey directly, so THIS bridge is the missing link — it LISTENs on the
`task_event` channel, filters `new_available`, maps each event to the consumer's
message contract, and PUBLISHes to Valkey `keiracom:tasks:available`.

Phase-1 (Dave personal cutover) is single-tenant: every task publishes under
`FLEET_TENANT_ID` (env, default `default`). Multi-tenant tenant resolution is a
later KEI. `backend=container`; `callsign` from the task's `claimed_by`
(fallback `worker`).

Fail-open: an unparseable / non-new_available event is skipped (not published),
never raised — one bad event must not kill the bridge.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from src.dispatcher.valkey_pool import get_valkey_client
from src.keiracom_system.work_loop.consumer import TASKS_CHANNEL

logger = logging.getLogger(__name__)

PG_NOTIFY_CHANNEL = "task_event"
NEW_AVAILABLE = "new_available"
# Phase-1 spawn backend is scrubbed-tmux (Agency_OS-87ei, Elliot-decided): reuse
# the working tmux spawn under env -i (no .env inheritance) — no container image
# to build. Env-overridable so the container fast-follow flips this to "container".
DEFAULT_BACKEND = os.environ.get("WORK_LOOP_BACKEND", "tmux")
DEFAULT_CALLSIGN = "worker"
DEFAULT_FLEET_TENANT_ID = "default"
# Recall keys consumed by the dispatcher (spawn_recall): brief + task_type feed
# the prior-context query. Without them the recall arm queries with an empty
# brief + default task_type. Task types per the spawn-governance §2 contract.
KNOWN_TASK_TYPES = ("build", "review", "research", "devops")
DEFAULT_TASK_TYPE = "build"


def _fleet_tenant_id() -> str:
    return os.environ.get("FLEET_TENANT_ID") or DEFAULT_FLEET_TENANT_ID


def _dsn() -> str | None:
    dsn = os.environ.get("SUPABASE_DB_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgresql+psycopg://", "postgresql://", 1
    )


def task_event_to_message(payload: str | dict[str, Any], fleet_tenant_id: str) -> str | None:
    """Map a kei45 `task_event` payload → the consumer's message JSON.

    Returns None (skip) for unparseable payloads, non-`new_available` events, or
    events missing a task id.
    """
    try:
        d = payload if isinstance(payload, dict) else json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        logger.warning("work-loop bridge: unparseable task_event payload")
        return None
    if not isinstance(d, dict) or d.get("event_type") != NEW_AVAILABLE:
        return None
    task_id = d.get("id")
    if not task_id:
        return None
    task_id = str(task_id)
    title = d.get("title")
    tags = d.get("tags") if isinstance(d.get("tags"), list) else []
    task_type = next((t for t in tags if t in KNOWN_TASK_TYPES), DEFAULT_TASK_TYPE)
    return json.dumps(
        {
            "task_id": task_id,
            "tenant_id": fleet_tenant_id,
            "backend": DEFAULT_BACKEND,
            "spawn_kwargs": {
                "callsign": d.get("claimed_by") or DEFAULT_CALLSIGN,
                "task_id": task_id,
                "title": title,
                # brief + task_type feed the dispatcher's spawn_recall block so the
                # recall-active run isn't empty (Agency_OS-g9xx).
                "brief": title,
                "task_type": task_type,
                "priority": d.get("priority"),
                "tags": tags or None,
            },
        }
    )


async def publish_task_event(
    valkey: Any,
    payload: str | dict[str, Any],
    fleet_tenant_id: str,
    *,
    channel: str = TASKS_CHANNEL,
) -> bool:
    """Map one `task_event` and PUBLISH it to Valkey. True if published, else False."""
    msg = task_event_to_message(payload, fleet_tenant_id)
    if msg is None:
        return False
    await valkey.publish(channel, msg)
    return True


async def run_bridge(  # pragma: no cover — asyncpg LISTEN wiring, exercised via publish_task_event
    *, dsn: str | None = None, valkey: Any = None, fleet_tenant_id: str | None = None
) -> None:
    """LISTEN on the PG `task_event` channel → publish `new_available` to Valkey.

    Runs until cancelled. The asyncpg listener callback is synchronous, so it
    hands payloads to a queue the main coroutine drains + publishes.
    """
    dsn = dsn or _dsn()
    if not dsn:
        raise RuntimeError("work-loop bridge requires DATABASE_URL/SUPABASE_DB_DSN")
    valkey = valkey or get_valkey_client()
    fleet_tenant_id = fleet_tenant_id or _fleet_tenant_id()
    from src.utils.asyncpg_connection import get_asyncpg_connection

    conn = await get_asyncpg_connection(dsn)
    queue: asyncio.Queue[str] = asyncio.Queue()

    def _on_notify(_conn: Any, _pid: int, _channel: str, payload: str) -> None:
        queue.put_nowait(payload)

    await conn.add_listener(PG_NOTIFY_CHANNEL, _on_notify)
    logger.info(
        "work-loop bridge LISTENing on PG '%s' → Valkey '%s' (fleet_tenant=%s)",
        PG_NOTIFY_CHANNEL,
        TASKS_CHANNEL,
        fleet_tenant_id,
    )
    try:
        while True:
            payload = await queue.get()
            try:
                if await publish_task_event(valkey, payload, fleet_tenant_id):
                    logger.info("work-loop bridge published a new_available task")
            except Exception:  # noqa: BLE001 — one bad event never kills the bridge
                logger.warning("work-loop bridge: publish failed", exc_info=True)
    finally:
        await conn.remove_listener(PG_NOTIFY_CHANNEL, _on_notify)
        await conn.close()


def main() -> None:  # pragma: no cover — process entrypoint
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bridge())


if __name__ == "__main__":  # pragma: no cover
    main()
