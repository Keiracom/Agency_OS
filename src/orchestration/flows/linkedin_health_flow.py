"""
FILE: src/orchestration/flows/linkedin_health_flow.py
PURPOSE: Daily LinkedIn seat health and warmup management
PHASE: Phase D (Code Fixes)
TASK: Item 14 - Implement LinkedIn seat warmup service
DEPENDENCIES:
  - src/services/linkedin_warmup_service.py
  - src/services/linkedin_health_service.py
  - src/integrations/supabase.py
  - src/models/linkedin_seat.py
  - src/models/linkedin_connection.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only
  - Prefect 3.x patterns

Daily tasks:
1. Process warmup completions (WARMUP → ACTIVE at day 12)
2. Update health metrics (accept rates, pending counts)
3. Apply health-based limit reductions
4. Mark stale connections as ignored (14-day timeout)
5. Withdraw stale connection requests (30-day timeout)
6. Detect potentially restricted seats

Schedule: Daily at 6 AM AEST
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.integrations.supabase import get_db_session
from src.services.linkedin_health_service import linkedin_health_service
from src.services.linkedin_warmup_service import linkedin_warmup_service

logger = logging.getLogger(__name__)


@task(name="process_linkedin_warmups", retries=2, retry_delay_seconds=10)
async def process_warmups_task(client_id: str | None = None) -> dict[str, Any]:
    """
    Process all seats in warmup status.

    Transitions seats from WARMUP to ACTIVE when they reach day 12+.

    Args:
        client_id: Optional client filter (string UUID)

    Returns:
        Dict with warmup processing results
    """
    async with get_db_session() as db:
        client_uuid = UUID(client_id) if client_id else None
        result = await linkedin_warmup_service.process_all_warmups(db, client_uuid)

        if result["completed"] > 0:
            logger.info(
                f"Warmup completions: {result['completed']} seats "
                f"transitioned to ACTIVE"
            )

        return result


@task(name="update_linkedin_health", retries=2, retry_delay_seconds=10)
async def update_health_task(client_id: str | None = None) -> dict[str, Any]:
    """
    Update health metrics for all active LinkedIn seats.

    Calculates accept rates, applies limit reductions for unhealthy seats.

    Args:
        client_id: Optional client filter (string UUID)

    Returns:
        Dict with health update results
    """
    async with get_db_session() as db:
        client_uuid = UUID(client_id) if client_id else None
        result = await linkedin_health_service.update_all_seats_health(db, client_uuid)

        if result["critical"] > 0:
            logger.warning(
                f"CRITICAL: {result['critical']} LinkedIn seats have "
                f"critically low accept rates (<20%)"
            )

        if result["warning"] > 0:
            logger.info(
                f"Warning: {result['warning']} LinkedIn seats have "
                f"below-target accept rates (<30%)"
            )

        return result


@task(name="mark_stale_linkedin_connections", retries=2, retry_delay_seconds=5)
async def mark_stale_connections_task(days: int = 14) -> dict[str, Any]:
    """
    Mark pending connections older than threshold as ignored.

    Per spec: 14 days pending → mark as ignored.

    Args:
        days: Days threshold (default 14)

    Returns:
        Dict with update count
    """
    async with get_db_session() as db:
        result = await linkedin_health_service.mark_stale_connections_ignored(db, days)

        if result["updated_count"] > 0:
            logger.info(
                f"Marked {result['updated_count']} stale LinkedIn "
                f"connections as ignored (>{days} days)"
            )

        return result


@task(name="withdraw_stale_linkedin_connections", retries=2, retry_delay_seconds=10)
async def withdraw_stale_connections_task(days: int = 30) -> dict[str, Any]:
    """
    Withdraw pending connections older than threshold via Unipile API.

    Per spec: 30 days pending -> withdraw request.
    Withdrawing frees up connection request slots on LinkedIn.

    Args:
        days: Days threshold for withdrawal (default 30)

    Returns:
        Dict with withdrawal summary
    """
    async with get_db_session() as db:
        result = await linkedin_health_service.withdraw_stale_requests(db, days=days)

        if result["withdrawn"] > 0:
            logger.info(
                f"Withdrew {result['withdrawn']} stale LinkedIn "
                f"connections (>{days} days)"
            )

        if result["failed"] > 0:
            logger.warning(
                f"Failed to withdraw {result['failed']} stale "
                f"LinkedIn connections"
            )

        return result


@task(name="detect_linkedin_restrictions", retries=2, retry_delay_seconds=5)
async def detect_restrictions_task() -> dict[str, Any]:
    """
    Detect seats that may be restricted.

    Safety check for seats with no activity despite having quota.

    Returns:
        Dict with suspicious seats
    """
    async with get_db_session() as db:
        suspicious = await linkedin_health_service.detect_restrictions(db)

        if suspicious:
            logger.warning(
                f"Detected {len(suspicious)} potentially restricted "
                f"LinkedIn seats - manual review recommended"
            )

        return {
            "suspicious_count": len(suspicious),
            "seats": suspicious,
        }


@flow(
    name="linkedin_daily_health",
    description="Daily LinkedIn seat health and warmup management",
    log_prints=True,
    task_runner=ConcurrentTaskRunner(max_workers=4),
)
async def linkedin_daily_health_flow(
    client_id: str | None = None,
    stale_days: int = 14,
    withdrawal_days: int = 30,
) -> dict[str, Any]:
    """
    Daily LinkedIn health management flow.

    Steps:
    1. Process warmup completions (WARMUP -> ACTIVE)
    2. Update health metrics (accept rates, limits)
    3. Mark stale connections as ignored (14 days)
    4. Withdraw stale connection requests (30 days)
    5. Detect potentially restricted seats

    Args:
        client_id: Optional client ID to process (string UUID)
        stale_days: Days threshold for marking ignored (default 14)
        withdrawal_days: Days threshold for withdrawal (default 30)

    Returns:
        Dict with comprehensive health summary
    """
    logger.info(
        f"Starting LinkedIn daily health flow "
        f"(client_id={client_id}, stale_days={stale_days}, withdrawal_days={withdrawal_days})"
    )

    # Step 1: Process warmup completions
    warmup_result = await process_warmups_task(client_id=client_id)

    # Step 2: Update health metrics
    health_result = await update_health_task(client_id=client_id)

    # Step 3: Mark stale connections as ignored (14 days)
    stale_result = await mark_stale_connections_task(days=stale_days)

    # Step 4: Withdraw stale connection requests (30 days)
    withdrawal_result = await withdraw_stale_connections_task(days=withdrawal_days)

    # Step 5: Detect restrictions
    restriction_result = await detect_restrictions_task()

    # Compile summary
    summary = {
        "warmup": {
            "total": warmup_result["total"],
            "completed": warmup_result["completed"],
            "continuing": warmup_result["continuing"],
        },
        "health": {
            "total": health_result["total"],
            "healthy": health_result["healthy"],
            "warning": health_result["warning"],
            "critical": health_result["critical"],
        },
        "stale_connections": {
            "marked_ignored": stale_result["updated_count"],
            "withdrawn": withdrawal_result["withdrawn"],
            "withdrawal_failed": withdrawal_result["failed"],
            "total_stale": withdrawal_result["total_stale"],
        },
        "restrictions": {
            "suspicious_count": restriction_result["suspicious_count"],
        },
        "completed_at": datetime.utcnow().isoformat(),
    }

    # Overall status
    if health_result["critical"] > 0 or restriction_result["suspicious_count"] > 0:
        summary["overall_status"] = "attention_required"
    elif health_result["warning"] > 0 or withdrawal_result["failed"] > 0:
        summary["overall_status"] = "warning"
    else:
        summary["overall_status"] = "healthy"

    logger.info(
        f"LinkedIn daily health complete: "
        f"{warmup_result['completed']} warmups completed, "
        f"{health_result['healthy']}/{health_result['total']} healthy, "
        f"{stale_result['updated_count']} stale marked ignored, "
        f"{withdrawal_result['withdrawn']} stale withdrawn, "
        f"{restriction_result['suspicious_count']} suspicious"
    )

    return summary


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] No imports from other orchestration files
# [x] Imports from services, integrations, models only
# [x] @flow and @task decorators from Prefect
# [x] ConcurrentTaskRunner for parallel processing
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] Process warmup completions
# [x] Update health metrics
# [x] Mark stale connections (14 days -> ignored)
# [x] Withdraw stale connections (30 days -> withdrawn via Unipile API)
# [x] Detect restrictions
# [x] Overall status summary
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Returns structured dict results
