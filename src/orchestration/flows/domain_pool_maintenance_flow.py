"""
Contract: src/orchestration/flows/domain_pool_maintenance_flow.py
Purpose: Daily maintenance of the Salesforge burner domain pool
Layer: 4 - orchestration
Imports: models, integrations, services
Consumers: Prefect scheduler

Schedule: Daily at 3am AEST (17:00 UTC previous day)

Tasks:
1. check_pool_size_task       — count ready domains, flag replenishment need
2. generate_candidates_task   — generate new names if pool below target
3. sync_warmup_status_task    — advance warming/dns_configuring domains
4. process_quarantine_task    — release expired quarantine domains
"""

import logging
from datetime import UTC, datetime
from typing import Any

from prefect import flow, get_run_logger, task

from src.config.database import get_db_session
from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook
from src.services.domain_pool_manager import DomainPoolManager

logger = logging.getLogger(__name__)


@task(name="check_pool_size", retries=2, retry_delay_seconds=10)
async def check_pool_size_task() -> dict[str, Any]:
    """Count domains by status and determine replenishment need."""
    log = get_run_logger()
    async with get_db_session() as db:
        manager = DomainPoolManager(db)
        counts = await manager.pool_size()
    log.info(f"Pool status: {counts}")
    return counts


@task(name="generate_domain_candidates", retries=1)
async def generate_candidates_task(count: int) -> list[dict]:
    """Generate candidate domain names from approved naming patterns."""
    log = get_run_logger()
    if count <= 0:
        log.info("Pool is at target — no candidates needed")
        return []

    async with get_db_session() as db:
        manager = DomainPoolManager(db)
        candidates = await manager.generate_candidates(count=count)

    log.info(f"Generated {len(candidates)} domain name candidates")
    return candidates


@task(name="sync_warmup_status", retries=2, retry_delay_seconds=30)
async def sync_warmup_status_task() -> list[dict[str, Any]]:
    """Sync warmup state for all warming/dns_configuring domains."""
    log = get_run_logger()
    async with get_db_session() as db:
        manager = DomainPoolManager(db)
        updates = await manager.sync_warmup_status()
        await db.commit()
    log.info(f"Warmup sync completed — {len(updates)} domains processed")
    return updates


@task(name="process_quarantine_expiry", retries=2, retry_delay_seconds=10)
async def process_quarantine_task() -> list[str]:
    """Release domains from quarantine if their quarantine_until has passed."""
    log = get_run_logger()
    async with get_db_session() as db:
        manager = DomainPoolManager(db)
        released = await manager.process_quarantine()
        await db.commit()
    log.info(f"Quarantine expiry: {len(released)} domains returned to ready pool")
    return released


@flow(
    name="domain_pool_maintenance",
    description="Daily replenishment and maintenance of Salesforge burner domain pool",
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def domain_pool_maintenance_flow() -> dict[str, Any]:
    """
    Daily maintenance flow for the burner domain pool.

    Schedule: 3am AEST (17:00 UTC).

    1. Check pool size — how many ready domains exist
    2. Generate candidates if below POOL_TARGET_SIZE
    3. Sync warmup status for in-progress domains
    4. Process quarantine expiry
    """
    log = get_run_logger()
    started_at = datetime.now(UTC)
    log.info(f"domain_pool_maintenance_flow started at {started_at.isoformat()}")

    # Step 1: Pool size check
    pool_counts = await check_pool_size_task()
    needs = pool_counts.get("_needs_replenishment", 0)

    # Step 2: Generate candidates if needed (does not auto-purchase — Dave approves)
    candidates = await generate_candidates_task(count=needs)

    # Step 3: Sync warmup status
    warmup_updates = await sync_warmup_status_task()

    # Step 4: Process quarantine expiry
    quarantine_released = await process_quarantine_task()

    result = {
        "run_at": started_at.isoformat(),
        "pool_counts": pool_counts,
        "candidates_generated": len(candidates),
        "warmup_synced": len(warmup_updates),
        "quarantine_released": len(quarantine_released),
        "candidates": candidates,
    }

    log.info(
        f"domain_pool_maintenance complete — "
        f"ready={pool_counts.get('_ready', 0)}, "
        f"candidates={len(candidates)}, "
        f"released_from_quarantine={len(quarantine_released)}"
    )
    return result
