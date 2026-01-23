"""
FILE: src/orchestration/flows/recording_cleanup_flow.py
PURPOSE: Daily cleanup of voice recordings older than 90 days
PHASE: Voice Engine Compliance
TASK: TODO.md #14
DEPENDENCIES:
  - src/services/recording_cleanup_service.py
  - src/integrations/supabase.py
  - src/integrations/vapi.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only (marks recording deleted, preserves activity)

Blueprint requirement (VOICE.md):
- 0-90 days: Stored for QA and compliance
- 90 days: Auto-delete unless flagged
- Flagged: Kept for training/compliance review
"""

import logging
from typing import Any

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.integrations.supabase import get_db_session
from src.services.recording_cleanup_service import (
    RecordingCleanupService,
    RECORDING_RETENTION_DAYS,
)

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="cleanup_old_recordings", retries=2, retry_delay_seconds=60)
async def cleanup_old_recordings_task(
    retention_days: int = RECORDING_RETENTION_DAYS,
    batch_size: int = 100,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Delete voice recordings older than retention period.

    Args:
        retention_days: Days to retain recordings (default 90)
        batch_size: Maximum recordings to process per run
        dry_run: If True, identify but don't delete recordings

    Returns:
        Cleanup result dict
    """
    async with get_db_session() as db:
        service = RecordingCleanupService(db)
        result = await service.cleanup_old_recordings(
            retention_days=retention_days,
            batch_size=batch_size,
            dry_run=dry_run,
        )

        logger.info(
            f"Recording cleanup task complete: "
            f"checked={result['checked']}, deleted={result['deleted']}, "
            f"skipped_flagged={result['skipped_flagged']}, failed={result['failed']}"
        )

        return result


# ============================================
# FLOW
# ============================================


@flow(
    name="recording-cleanup",
    description="Daily cleanup of voice recordings older than 90 days for compliance",
    task_runner=ConcurrentTaskRunner(),
)
async def recording_cleanup_flow(
    retention_days: int = RECORDING_RETENTION_DAYS,
    batch_size: int = 100,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Daily flow to clean up old voice recordings.

    Runs daily at 3 AM AEST to delete recordings older than 90 days.
    Respects flagged_for_retention flag on activities.

    Args:
        retention_days: Days to retain recordings (default 90)
        batch_size: Maximum recordings to process per run
        dry_run: If True, identify but don't delete recordings

    Returns:
        Cleanup result dict with statistics
    """
    logger.info(
        f"Starting recording cleanup flow: "
        f"retention_days={retention_days}, batch_size={batch_size}, dry_run={dry_run}"
    )

    result = await cleanup_old_recordings_task(
        retention_days=retention_days,
        batch_size=batch_size,
        dry_run=dry_run,
    )

    # Log summary
    if result["deleted"] > 0:
        logger.info(
            f"Recording cleanup complete: {result['deleted']} recordings deleted, "
            f"{result['skipped_flagged']} flagged recordings preserved"
        )
    else:
        logger.info("Recording cleanup complete: no recordings to delete")

    return result


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Prefect flow for recording cleanup
# [x] Uses RecordingCleanupService
# [x] Configurable retention_days (default 90)
# [x] Configurable batch_size for large backlogs
# [x] dry_run mode for testing
# [x] Logging of cleanup statistics
# [x] Task retry on failure (2 retries, 60s delay)
# [x] All functions have type hints
# [x] All functions have docstrings
