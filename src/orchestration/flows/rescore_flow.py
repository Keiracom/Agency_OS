"""
Contract: src/orchestration/flows/rescore_flow.py
Purpose: Monthly Prefect flow that re-scores pipeline_stage=-1 rejects and
         promotes qualifying leads back to stage 1 for re-enrichment.
Layer: 4 - orchestration
Imports: src.pipeline.rescore_engine, prefect_utils hooks
Consumers: Prefect scheduler (1st of month, 02:00 UTC)
"""

from __future__ import annotations

import logging
import os

import asyncpg
from prefect import flow, task

from src.pipeline.rescore_engine import RescoreEngine, RescoreResult
from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook

logger = logging.getLogger(__name__)


@task(name="run_rescore_engine", retries=2, retry_delay_seconds=30)
async def run_rescore_engine_task(
    vertical: str | None = None,
    batch_size: int = 500,
    dry_run: bool = False,
) -> dict:
    """Run the RescoreEngine and return serialisable result dict."""
    database_url = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(database_url)
    try:
        engine = RescoreEngine(conn)
        result: RescoreResult = await engine.run(
            vertical=vertical,
            batch_size=batch_size,
            dry_run=dry_run,
        )
    finally:
        await conn.close()

    return {
        "total_evaluated": result.total_evaluated,
        "promoted": result.promoted,
        "still_rejected": result.still_rejected,
        "skipped": result.skipped,
        "dry_run": result.dry_run,
        "vertical": result.vertical,
        "estimated_cost_usd": result.estimated_cost_usd,
    }


# Deployment schedule: cron="0 2 1 * *" (1st of month, 02:00 UTC)
# Configure via prefect.yaml deployment or Prefect UI
@flow(
    name="monthly-rescore-flow",
    description="Monthly re-score of pipeline_stage=-1 rejects against current signal configs",
    log_prints=True,
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def monthly_rescore_flow(
    vertical: str | None = None,
    batch_size: int = 500,
    dry_run: bool = False,
) -> dict:
    """
    Monthly re-scoring flow.

    Fetches all pipeline_stage=-1 rejects that haven't been re-scored
    in the last 30 days, re-evaluates them against current signal configs,
    and promotes qualifying leads back to stage 1 for re-enrichment.

    Args:
        vertical: Optional vertical slug to scope threshold loading.
                  None = use default threshold across all verticals.
        batch_size: Maximum rejects to evaluate per run (default 500).
        dry_run: If True, compute scores but write nothing to DB.

    Returns:
        Summary dict with promoted/rejected/skipped counts.
    """
    logger.info(
        f"Starting monthly rescore flow "
        f"(vertical={vertical}, batch_size={batch_size}, dry_run={dry_run})"
    )

    result = await run_rescore_engine_task(
        vertical=vertical,
        batch_size=batch_size,
        dry_run=dry_run,
    )

    logger.info(
        f"Monthly rescore complete — "
        f"evaluated={result['total_evaluated']}, "
        f"promoted={result['promoted']}, "
        f"still_rejected={result['still_rejected']}, "
        f"skipped={result['skipped']}, "
        f"dry_run={result['dry_run']}"
    )

    return result
