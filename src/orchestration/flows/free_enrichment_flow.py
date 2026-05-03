"""Free-mode enrichment flow — Stage 0/1 trigger fix.

Directive: BU Closed-Loop Engine — Substep 3 (paired with bu_closed_loop_flow).
Purpose:    Catch BU rows that pool_population inserts without setting
            pipeline_stage (default = 0 / NULL) and run them through
            FreeEnrichment.run(). 5,022 production rows are stuck at
            pipeline_stage=0 because the existing FreeEnrichment cursor
            requires pipeline_stage >= 1.

Posture:    paused=false acceptable — Stage 1 is AUD 0 (local DNS, httpx
            scraping, local abn_registry lookups, optional Spider fallback
            which is gated off when SPIDER_API_KEY is unset).
Schedule:   Hourly safety-net.

Two-phase logic:
  1. PROMOTE — UPDATE business_universe SET pipeline_stage = 1
     WHERE pipeline_stage IS NULL OR pipeline_stage = 0
       AND domain IS NOT NULL.
     Brings stage-0 rows into the existing FreeEnrichment cursor's reach.
  2. ENRICH — Invoke FreeEnrichment.run(limit) which uses the cursor
     (pipeline_stage >= 1 AND free_enrichment_completed_at IS NULL ...)
     and writes website_*, dns_*, abn_*, free_enrichment_completed_at,
     and the stage_metrics.stage_completed_at.free_enrichment marker
     introduced in BU Closed-Loop S1.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import asyncpg
from prefect import flow, task
from prefect.cache_policies import NO_CACHE

from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

logger = logging.getLogger(__name__)


async def _init_jsonb_codec(conn):
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def _open_pool() -> asyncpg.pool.Pool:
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.create_pool(
        db_url,
        min_size=2,
        max_size=4,
        statement_cache_size=0,
        init=_init_jsonb_codec,
    )


# gap #11 — domain backfill from gmb_domain to unblock promote_stage_0_rows
@task(name="free-enrichment-backfill-domain", retries=1, cache_policy=NO_CACHE)
async def backfill_domain_from_gmb(pool: asyncpg.pool.Pool) -> int:
    """Backfill domain from gmb_domain for BU rows that have gmb_domain set
    but domain NULL. pool_population_flow sets gmb_domain but not domain, so
    promote_stage_0_rows (which gates on domain IS NOT NULL) silently skips
    those rows. Running this first unlocks ~5022 stuck rows.

    Idempotent — WHERE filter ensures rows already backfilled are not touched.
    Returns the number of rows updated."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE business_universe
                  SET domain = gmb_domain,
                      updated_at = NOW()
                WHERE domain IS NULL
                  AND gmb_domain IS NOT NULL"""
        )
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0


@task(name="free-enrichment-promote-stage-0", retries=1, cache_policy=NO_CACHE)
async def promote_stage_0_rows(pool: asyncpg.pool.Pool) -> int:
    """Promote BU rows whose pipeline_stage is NULL or 0 to pipeline_stage=1
    so they enter the FreeEnrichment cursor on the next pass. Returns the
    number of rows promoted."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE business_universe
                  SET pipeline_stage = 1, updated_at = NOW()
                WHERE (pipeline_stage IS NULL OR pipeline_stage = 0)
                  AND domain IS NOT NULL"""
        )
    # asyncpg returns "UPDATE N"; pull the integer suffix.
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0


@task(name="free-enrichment-run", retries=0, cache_policy=NO_CACHE)
async def run_free_enrichment(limit: int) -> dict[str, Any]:
    """Invoke FreeEnrichment.run(limit). Imported lazily so unit tests can
    stub the module surface without paying its httpx / dns dependency cost."""
    from src.pipeline.free_enrichment import FreeEnrichment

    engine = FreeEnrichment()
    return await engine.run(limit=limit)


@flow(
    name="free-enrichment-flow",
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def free_enrichment_flow(
    limit: int = 500,
    promote_stage_0: bool = True,
) -> dict[str, Any]:
    """Stage 0/1 trigger fix — promotes stage-0 BU rows then runs
    FreeEnrichment over the resulting backlog.

    Parameters
    ----------
    limit:           Max rows for FreeEnrichment.run() per invocation.
    promote_stage_0: If True (default), bump pipeline_stage NULL/0 to 1
                     before enrichment runs. Disable for read-only audits.
    """
    run_start = datetime.now(UTC).isoformat()
    pool = await _open_pool()

    summary: dict[str, Any] = {
        "run_start_ts": run_start,
        "limit": limit,
        "promote_stage_0": promote_stage_0,
        "backfilled": 0,
        "promoted": 0,
        "enrichment": {},
    }

    try:
        # gap #11 — backfill domain from gmb_domain before promote gate runs
        backfilled = await backfill_domain_from_gmb(pool)
        summary["backfilled"] = backfilled
        logger.info("free_enrichment_flow: backfilled domain for %d rows from gmb_domain", backfilled)

        if promote_stage_0:
            promoted = await promote_stage_0_rows(pool)
            summary["promoted"] = promoted
            logger.info("free_enrichment_flow: promoted %d stage-0/NULL rows to stage 1", promoted)
        else:
            logger.info("free_enrichment_flow: promote_stage_0=False — skipping promote step")

        enrichment_stats = await run_free_enrichment(limit)
        summary["enrichment"] = enrichment_stats
    finally:
        await pool.close()

    logger.info("free_enrichment_flow complete: %s", json.dumps(summary, default=str))
    return summary
