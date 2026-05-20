"""KEI-211 — Dispatcher heartbeat watchdog (task-progress liveness).

Complements ``src.dispatcher.watchdog`` (process-liveness via tmux capture-pane
hash + container HTTP probe) by watching the *task* layer instead: any task
that has been ``status='active'`` for longer than the configured stale
threshold without writing ``heartbeat_at`` is flagged as a zombie and
published to NATS so ``heartbeat_reaper`` can take cleanup action.

Detection model:

  • Polls ``public.tasks`` every ``poll_interval_s`` seconds (default 60s).
  • A row is a zombie when ``status='active'`` AND
    ``heartbeat_at < NOW() - stale_threshold_s`` (default 300s = 5 min).
    Rows with ``heartbeat_at IS NULL`` are EXCLUDED — KEI-105 documents
    that null heartbeat is legitimate for legacy / yet-to-tick rows, and
    failing-open here is required to avoid paging on baseline state.
  • Each zombie publishes one event on NATS subject
    ``keiracom.agent.status.{callsign}`` and writes one
    ``agent_memories`` row with ``source_type='watchdog_observation'``.

Fail-open by design — any leg (DB read, NATS publish, agent_memories log)
that raises is logged and silently skipped so a single bad task or a
transient NATS outage doesn't tear down the whole supervisor.

Env contract:

  • ``SUPABASE_DB_URL`` or ``DATABASE_URL`` — psycopg DSN. ``+asyncpg``
    suffix is stripped (KEI-207 / KEI-54B prior art).
  • ``NATS_URL`` — NATS server URL (default ``nats://127.0.0.1:4222``).
  • ``HEARTBEAT_STALE_THRESHOLD_S`` — override default 300 if needed.
  • ``HEARTBEAT_POLL_INTERVAL_S`` — override default 60 if needed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_STALE_THRESHOLD_S = 300
DEFAULT_POLL_INTERVAL_S = 60
NATS_URL_ENV = "NATS_URL"
DEFAULT_NATS_URL = "nats://127.0.0.1:4222"
NATS_SUBJECT_TEMPLATE = "keiracom.agent.status.{callsign}"

# DSN scheme suffix to strip — mirrors spend_tracker / claim_queue_metrics_export.
_ASYNCPG_DSN_PREFIX = "+asyncpg"


@dataclass(frozen=True)
class ZombieEvent:
    """Single zombie task detection. Emitted to NATS + logged to agent_memories."""

    task_id: str
    callsign: str
    last_heartbeat_at: datetime
    stale_seconds: int


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace(_ASYNCPG_DSN_PREFIX, "").replace("postgresql+asyncpg://", "postgresql://", 1)


def poll_once(threshold_seconds: int = DEFAULT_STALE_THRESHOLD_S) -> list[ZombieEvent]:
    """Return zombie events from one poll of public.tasks.

    Synchronous; uses psycopg with prepare_threshold=None (Supabase pgbouncer
    txn-mode compatibility per reference_psycopg_supabase_pgbouncer.md).
    """
    import psycopg  # noqa: PLC0415 — optional at import time

    sql = """
        SELECT id::text, callsign, heartbeat_at,
               EXTRACT(EPOCH FROM (NOW() - heartbeat_at))::bigint AS stale_seconds
          FROM public.tasks
         WHERE status = 'active'
           AND heartbeat_at IS NOT NULL
           AND heartbeat_at < NOW() - make_interval(secs => %s)
    """
    with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
        cur.execute(sql, (threshold_seconds,))
        rows = cur.fetchall()
    return [
        ZombieEvent(
            task_id=r[0],
            callsign=r[1],
            last_heartbeat_at=r[2],
            stale_seconds=int(r[3]),
        )
        for r in rows
    ]


async def _nats_publish(url: str, subject: str, payload: bytes) -> None:
    """Single-message NATS publish. Extracted as a seam for testability —
    tests patch this helper rather than the inline import.
    """
    import nats.aio.client as nats_client  # noqa: PLC0415 — optional dep

    nc = nats_client.Client()
    await nc.connect(url, connect_timeout=2)
    try:
        await nc.publish(subject, payload)
        await nc.flush()
    finally:
        await nc.close()


async def publish_zombie(event: ZombieEvent) -> bool:
    """Publish one zombie event to NATS keiracom.agent.status.<callsign>.

    Returns True on successful publish. False on any failure (NATS down,
    optional dep missing) — fail-open per module contract.
    """
    url = os.environ.get(NATS_URL_ENV, DEFAULT_NATS_URL)
    subject = NATS_SUBJECT_TEMPLATE.format(callsign=event.callsign)
    payload = json.dumps(
        {
            "type": "zombie_detected",
            "task_id": event.task_id,
            "callsign": event.callsign,
            "last_heartbeat_at": event.last_heartbeat_at.isoformat(),
            "stale_seconds": event.stale_seconds,
        }
    ).encode()
    try:
        await _nats_publish(url, subject, payload)
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("NATS publish failed for task=%s: %s", event.task_id, exc)
        return False


def log_observation(event: ZombieEvent) -> bool:
    """Write one watchdog_observation row to public.agent_memories.

    Fail-open — caller continues to next event on any DB error.
    """
    try:
        import psycopg  # noqa: PLC0415

        content = (
            f"watchdog: task {event.task_id} ({event.callsign}) zombie — "
            f"heartbeat last seen {event.last_heartbeat_at.isoformat()} "
            f"({event.stale_seconds}s ago)"
        )
        metadata = {
            "task_id": event.task_id,
            "stale_seconds": event.stale_seconds,
            "last_heartbeat_at": event.last_heartbeat_at.isoformat(),
        }
        with psycopg.connect(_dsn(), prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.agent_memories
                    (id, callsign, source_type, content, typed_metadata,
                     created_at, valid_from, state)
                VALUES (gen_random_uuid(), %s, 'watchdog_observation', %s,
                        %s::jsonb, NOW(), NOW(), 'confirmed')
                """,
                (event.callsign, content, json.dumps(metadata)),
            )
            conn.commit()
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("agent_memories log failed for task=%s: %s", event.task_id, exc)
        return False


async def run_one_cycle(threshold_seconds: int = DEFAULT_STALE_THRESHOLD_S) -> dict[str, Any]:
    """One poll → publish → log cycle. Returns counters for caller visibility."""
    try:
        zombies = poll_once(threshold_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("poll_once failed (skipping cycle): %s", exc)
        return {"polled": 0, "published": 0, "logged": 0, "errors": 1}

    published = 0
    logged = 0
    for event in zombies:
        if await publish_zombie(event):
            published += 1
        if log_observation(event):
            logged += 1
    return {
        "polled": len(zombies),
        "published": published,
        "logged": logged,
        "errors": 0,
    }


async def run_forever(
    poll_interval_s: int = DEFAULT_POLL_INTERVAL_S,
    threshold_seconds: int = DEFAULT_STALE_THRESHOLD_S,
) -> None:
    """Long-running poll loop. Use as a systemd-managed service entrypoint."""
    logger.info(
        "heartbeat_watchdog starting — poll=%ds threshold=%ds",
        poll_interval_s,
        threshold_seconds,
    )
    while True:
        counters = await run_one_cycle(threshold_seconds)
        if counters["polled"] > 0:
            logger.info("heartbeat_watchdog cycle: %s", counters)
        await asyncio.sleep(poll_interval_s)


def main() -> None:
    """Entry-point for systemd / CLI. Reads thresholds from env, runs forever."""
    threshold = int(os.environ.get("HEARTBEAT_STALE_THRESHOLD_S", str(DEFAULT_STALE_THRESHOLD_S)))
    interval = int(os.environ.get("HEARTBEAT_POLL_INTERVAL_S", str(DEFAULT_POLL_INTERVAL_S)))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_forever(poll_interval_s=interval, threshold_seconds=threshold))


if __name__ == "__main__":
    main()
