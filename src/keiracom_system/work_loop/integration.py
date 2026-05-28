"""Wire the work-loop consumer into the dispatcher lifecycle (Agency_OS-innu).

Follow-up to PR #1275 (the consumer). Two seams the dispatcher calls:

  * ``release_on_exit(tenant_id, task_id)`` — invoked from the dispatcher exit
    hook (``/dispatcher/terminate``) when a spawn tears down: frees the tenant
    slot, then the consumer pops the per-tenant overflow and spawns the next.
  * ``reconcile_loop(interval_s)`` — a background task started in the dispatcher
    lifespan; periodically reclaims slots whose lease TTL lapsed (crashed agents
    that never hit the clean exit hook).

A module-level consumer singleton keeps one Valkey pool + spawn path for the
process. ``set_consumer`` is the test seam. Both entry points are fail-open —
the dispatcher's teardown and lifespan must never break on a work-loop error.
"""

from __future__ import annotations

import asyncio
import logging

from src.keiracom_system.work_loop.consumer import WorkLoopConsumer

logger = logging.getLogger(__name__)

DEFAULT_RECONCILE_INTERVAL_S = 60

_consumer: WorkLoopConsumer | None = None


def get_consumer() -> WorkLoopConsumer:
    """Lazy process-singleton consumer (real Valkey pool + dispatcher spawn)."""
    global _consumer  # noqa: PLW0603
    if _consumer is None:
        _consumer = WorkLoopConsumer()
    return _consumer


def set_consumer(consumer: WorkLoopConsumer | None) -> None:
    """Test seam — inject a fake/fakeredis-backed consumer (or reset to None)."""
    global _consumer  # noqa: PLW0603
    _consumer = consumer


async def release_on_exit(tenant_id: str, task_id: str) -> None:
    """Dispatcher exit-hook callback. Fail-open — never break teardown."""
    try:
        await get_consumer().release_slot(tenant_id, task_id)
    except Exception:  # noqa: BLE001 — a work-loop error must not fail termination
        logger.warning(
            "work-loop release_on_exit failed (tenant=%s task=%s)",
            tenant_id,
            task_id,
            exc_info=True,
        )


async def reconcile_loop(
    interval_s: int = DEFAULT_RECONCILE_INTERVAL_S, *, iterations: int | None = None
) -> None:
    """Periodically reclaim crashed-agent slots until cancelled.

    ``iterations`` bounds the loop for tests (None = run forever until the task
    is cancelled by the dispatcher lifespan). Errors are swallowed so a single
    bad sweep never kills the loop.
    """
    n = 0
    while iterations is None or n < iterations:
        try:
            reclaimed = await get_consumer().reconcile_all()
            if reclaimed:
                logger.info("work-loop reconcile reclaimed %d crashed-agent slot(s)", reclaimed)
        except Exception:  # noqa: BLE001 — one failed sweep never kills the loop
            logger.warning("work-loop reconcile sweep failed", exc_info=True)
        n += 1
        if iterations is None or n < iterations:
            await asyncio.sleep(interval_s)
