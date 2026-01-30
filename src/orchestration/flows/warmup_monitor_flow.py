"""
FILE: src/orchestration/flows/warmup_monitor_flow.py
PURPOSE: Daily check of WarmForge to mark warmed domains as AVAILABLE
PHASE: Resource Pool Management
TRIGGER: Daily cron at 6am AEST (19:00 UTC previous day)
DEPENDENCIES:
  - src/integrations/warmforge.py
  - src/models/resource_pool.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 7: Prefect for orchestration
"""

import logging
from datetime import datetime

from prefect import flow, get_run_logger, task
from prefect.runtime import flow_run
from sqlalchemy import select

from src.config.database import get_db_session
from src.integrations.warmforge import get_warmforge_client
from src.models.resource_pool import ResourcePool, ResourceStatus, ResourceType

logger = logging.getLogger(__name__)

# Minimum heat score to consider a domain fully warmed
WARMUP_THRESHOLD = 85


@task(name="get_warming_domains", retries=2, retry_delay_seconds=10)
async def get_warming_domains_task() -> list[dict]:
    """
    Get all email domains from resource_pool where status='warming'.

    Returns:
        List of dicts with id, resource_value (domain), provider_id
    """
    log = get_run_logger()

    async with get_db_session() as db:
        result = await db.execute(
            select(ResourcePool).where(
                ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN,
                ResourcePool.status == ResourceStatus.WARMING,
            )
        )
        resources = result.scalars().all()

        domains = [
            {
                "id": str(r.id),
                "domain": r.resource_value,
                "provider_id": r.provider_id,
                "warmup_started_at": r.warmup_started_at.isoformat() if r.warmup_started_at else None,
            }
            for r in resources
        ]

        log.info(f"Found {len(domains)} domains in warming status")
        return domains


@task(name="check_warmforge_status", retries=3, retry_delay_seconds=15)
async def check_warmforge_status_task(domain: str) -> dict:
    """
    Check WarmForge API for domain warmup status.

    Args:
        domain: Domain name to check

    Returns:
        Dict with warm, heat_score, mailbox_count, warmed_count
    """
    log = get_run_logger()

    try:
        client = get_warmforge_client()
        status = await client.get_domain_warmup_status(domain)

        log.info(
            f"WarmForge status for {domain}: "
            f"warm={status['warm']}, heat_score={status['heat_score']}, "
            f"mailboxes={status['warmed_count']}/{status['mailbox_count']}"
        )

        return status

    except Exception as e:
        log.error(f"Failed to check WarmForge for {domain}: {e}")
        return {
            "warm": False,
            "heat_score": 0,
            "mailbox_count": 0,
            "warmed_count": 0,
            "error": str(e),
        }


@task(name="update_domain_status", retries=2, retry_delay_seconds=5)
async def update_domain_status_task(
    resource_id: str,
    domain: str,
    warmforge_status: dict,
) -> dict:
    """
    Update resource_pool record if domain is fully warmed.

    Criteria: warm=True AND heatScore >= 85

    Args:
        resource_id: UUID of resource_pool record
        domain: Domain name
        warmforge_status: Status from WarmForge API

    Returns:
        Dict with updated, reason
    """
    log = get_run_logger()

    # Check if domain meets warmup criteria
    is_warm = warmforge_status.get("warm", False)
    heat_score = warmforge_status.get("heat_score", 0)

    if not is_warm:
        log.info(f"Domain {domain} not fully warmed yet (warm=False)")
        return {"updated": False, "reason": "not_warm"}

    if heat_score < WARMUP_THRESHOLD:
        log.info(f"Domain {domain} heat score {heat_score} below threshold {WARMUP_THRESHOLD}")
        return {"updated": False, "reason": f"heat_score_below_{WARMUP_THRESHOLD}"}

    # Domain is ready - update to available
    async with get_db_session() as db:
        from uuid import UUID

        result = await db.execute(
            select(ResourcePool).where(ResourcePool.id == UUID(resource_id))
        )
        resource = result.scalar_one_or_none()

        if not resource:
            log.error(f"Resource {resource_id} not found")
            return {"updated": False, "reason": "resource_not_found"}

        # Update status
        resource.status = ResourceStatus.AVAILABLE
        resource.reputation_score = heat_score
        resource.warmup_completed_at = datetime.utcnow()

        await db.commit()

        log.info(
            f"✅ Domain {domain} marked AVAILABLE "
            f"(heat_score={heat_score}, warmup_completed_at={resource.warmup_completed_at})"
        )

        return {
            "updated": True,
            "domain": domain,
            "heat_score": heat_score,
            "warmup_completed_at": resource.warmup_completed_at.isoformat(),
        }


@flow(name="process_single_domain", log_prints=True)
async def process_single_domain_flow(domain_record: dict) -> dict:
    """
    Process a single domain: check WarmForge and update if ready.

    Args:
        domain_record: Dict with id, domain, provider_id

    Returns:
        Processing result
    """
    log = get_run_logger()
    domain = domain_record["domain"]
    resource_id = domain_record["id"]

    log.info(f"Processing domain: {domain}")

    # Check WarmForge status
    warmforge_status = await check_warmforge_status_task(domain)

    # Skip if there was an error
    if warmforge_status.get("error"):
        return {
            "domain": domain,
            "status": "error",
            "error": warmforge_status["error"],
        }

    # Update if criteria met
    update_result = await update_domain_status_task(
        resource_id=resource_id,
        domain=domain,
        warmforge_status=warmforge_status,
    )

    return {
        "domain": domain,
        "status": "updated" if update_result["updated"] else "still_warming",
        "heat_score": warmforge_status["heat_score"],
        "warmed_mailboxes": f"{warmforge_status['warmed_count']}/{warmforge_status['mailbox_count']}",
        "reason": update_result.get("reason"),
    }


@flow(name="warmup_monitor", log_prints=True)
async def warmup_monitor_flow() -> dict:
    """
    Check WarmForge for completed warmups, update resource_pool.

    Steps:
    1. Get all resources from resource_pool where status='warming'
    2. For each, call WarmForge API to get current status
    3. If warm=True AND heatScore >= 85:
       - Update status to 'available'
       - Set reputation_score = heatScore
       - Set warmup_completed_at = now()

    Returns:
        Summary with count updated.
    """
    log = get_run_logger()
    run_id = flow_run.id if flow_run else "manual"

    log.info(f"Starting warmup monitor flow (run_id={run_id})")

    # Get all warming domains
    warming_domains = await get_warming_domains_task()

    if not warming_domains:
        log.info("No domains currently in warming status")
        return {
            "status": "complete",
            "domains_checked": 0,
            "domains_updated": 0,
            "message": "No warming domains found",
        }

    # Process each domain
    results = []
    updated_count = 0
    error_count = 0
    still_warming_count = 0

    for domain_record in warming_domains:
        try:
            result = await process_single_domain_flow(domain_record)
            results.append(result)

            if result["status"] == "updated":
                updated_count += 1
            elif result["status"] == "error":
                error_count += 1
            else:
                still_warming_count += 1

        except Exception as e:
            log.error(f"Error processing domain {domain_record['domain']}: {e}")
            results.append({
                "domain": domain_record["domain"],
                "status": "error",
                "error": str(e),
            })
            error_count += 1

    log.info(
        f"Warmup monitor complete: "
        f"{updated_count} updated, {still_warming_count} still warming, {error_count} errors"
    )

    return {
        "status": "complete",
        "domains_checked": len(warming_domains),
        "domains_updated": updated_count,
        "domains_still_warming": still_warming_count,
        "domains_error": error_count,
        "results": results,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Uses Prefect @flow and @task decorators
# [x] Tasks have retries configured
# [x] Session managed via get_db_session context manager
# [x] Checks WarmForge API for warmup status
# [x] Warmup threshold of 85 heat score
# [x] Updates status to 'available' when criteria met
# [x] Sets reputation_score from heatScore
# [x] Sets warmup_completed_at to now()
# [x] Error handling and logging
# [x] Summary return with counts
