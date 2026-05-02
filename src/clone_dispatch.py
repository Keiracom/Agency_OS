"""
C1 Runtime Dispatch Gate — Clone Architecture.

Before dispatching any task to a sub-agent, parent queries tier_registry.
If task_class is Tier A, blocks sub-agent dispatch and routes to clone.

Usage:
    from src.clone_dispatch import check_tier, dispatch_to_clone

    tier = await check_tier("test-pollution-hunt")
    if tier == "A":
        await dispatch_to_clone("atlas", task_brief)
    else:
        # sub-agent dispatch OK
"""

import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)


async def check_tier(task_class: str) -> str:
    """Query tier_registry for task_class. Returns 'A' or 'B'."""
    try:
        import asyncpg

        db_url = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        if not db_url:
            return "B"
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT tier FROM public.tier_registry WHERE task_class = $1",
                task_class,
            )
            return row["tier"] if row else "B"
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning("tier_registry query failed for %s: %s — defaulting to B", task_class, exc)
        return "B"


async def dispatch_to_clone(
    clone_callsign: str,
    task_brief: str,
    max_task_minutes: int = 30,
) -> None:
    """Write task brief to clone inbox for dispatch."""
    inbox_dir = Path(f"/tmp/telegram-relay-{clone_callsign}/inbox")
    inbox_dir.mkdir(parents=True, exist_ok=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    task_file = inbox_dir / f"{ts}_dispatch.json"
    task_file.write_text(
        json.dumps(
            {
                "type": "task_dispatch",
                "from": os.environ.get("CALLSIGN", "unknown"),
                "to": clone_callsign,
                "max_task_minutes": max_task_minutes,
                "brief": task_brief,
                "dispatched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    )
    logger.info("Dispatched task to %s: %s", clone_callsign, task_file)


async def escalate_to_tier_a(
    task_class: str,
    stall_evidence: str,
    reviewed_by: str,
) -> None:
    """Permanently escalate a task_class to Tier A after stall."""
    try:
        import asyncpg

        db_url = os.environ.get("DATABASE_URL", "").replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        if not db_url:
            return
        conn = await asyncpg.connect(db_url, statement_cache_size=0)
        try:
            await conn.execute(
                """INSERT INTO public.tier_registry
                   (task_class, tier, escalated_from_stall, stall_evidence_path, reviewed_by, last_reviewed_at)
                   VALUES ($1, 'A', true, $2, $3, NOW())
                   ON CONFLICT (task_class) DO UPDATE SET
                       tier = 'A',
                       escalated_from_stall = true,
                       stall_evidence_path = EXCLUDED.stall_evidence_path,
                       reviewed_by = EXCLUDED.reviewed_by,
                       last_reviewed_at = NOW(),
                       updated_at = NOW()""",
                task_class,
                stall_evidence,
                reviewed_by,
            )
            logger.info("Escalated %s to Tier A: %s", task_class, stall_evidence)
        finally:
            await conn.close()
    except Exception as exc:
        logger.error("Failed to escalate %s to Tier A: %s", task_class, exc)
