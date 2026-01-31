"""
FILE: src/orchestration/flows/persona_buffer_flow.py
PURPOSE: Event-driven persona+domain replenishment triggered by Stripe signup webhook
PHASE: Resource Pool Management
TRIGGER: Stripe webhook after client signup (maintains 40% buffer)
DEPENDENCIES:
  - src/config/database.py
  - src/models/resource_pool.py
  - src/services/persona_service.py
  - src/services/domain_provisioning_service.py
RULES APPLIED:
  - Rule 11: Session passed as argument
  - Rule 7: Prefect for orchestration
  - Rule 20: Webhook-first architecture
"""

import logging
from datetime import datetime
from math import ceil

from prefect import flow, get_run_logger, task
from prefect.runtime import flow_run
from sqlalchemy import func, select

from src.config.database import get_db_session
from src.models.resource_pool import ResourcePool, ResourceStatus, ResourceType
from src.services.persona_service import generate_persona
from src.services.domain_provisioning_service import provision_persona_with_domains

logger = logging.getLogger(__name__)

# Buffer configuration
BUFFER_RATIO = 0.40  # Maintain 40% buffer of warmed persona+domain sets
MIN_HEAT_SCORE = 85  # Minimum reputation score for domain to be considered ready


@task(name="calculate_buffer_shortfall", retries=2, retry_delay_seconds=10)
async def calculate_buffer_shortfall_task() -> dict:
    """
    Calculate if buffer replenishment is needed.

    Compares allocated domains against available + warming to determine shortfall.

    Returns:
        Dict with allocated, available, warming, required_buffer, shortfall
    """
    log = get_run_logger()

    async with get_db_session() as db:
        # Count allocated domains (assigned to clients)
        allocated = (
            await db.scalar(
                select(func.count(ResourcePool.id))
                .where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
                .where(ResourcePool.status == ResourceStatus.ASSIGNED)
                .where(ResourcePool.deleted_at.is_(None))
            )
            or 0
        )

        # Count available domains (warmed, ready to assign)
        available = (
            await db.scalar(
                select(func.count(ResourcePool.id))
                .where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
                .where(ResourcePool.status == ResourceStatus.AVAILABLE)
                .where(ResourcePool.reputation_score >= MIN_HEAT_SCORE)
                .where(ResourcePool.deleted_at.is_(None))
            )
            or 0
        )

        # Count warming (in progress)
        warming = (
            await db.scalar(
                select(func.count(ResourcePool.id))
                .where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
                .where(ResourcePool.status == ResourceStatus.WARMING)
                .where(ResourcePool.deleted_at.is_(None))
            )
            or 0
        )

        required_buffer = ceil(allocated * BUFFER_RATIO)
        shortfall = max(0, required_buffer - available - warming)

        log.info(
            f"Buffer status: allocated={allocated}, available={available}, "
            f"warming={warming}, required={required_buffer}, shortfall={shortfall}"
        )

        return {
            "allocated": allocated,
            "available": available,
            "warming": warming,
            "required_buffer": required_buffer,
            "shortfall": shortfall,
        }


@task(name="provision_persona_set", retries=1, retry_delay_seconds=30)
async def provision_persona_set_task() -> dict:
    """
    Generate one persona + provision domains.

    Creates a new persona and provisions associated domains for warmup.

    Returns:
        Dict with success, persona_id, domains provisioned
    """
    log = get_run_logger()

    async with get_db_session() as db:
        try:
            # Generate persona
            persona = await generate_persona(db)
            log.info(f"Generated persona: {persona.id}")

            # Provision domains
            result = await provision_persona_with_domains(db, persona)

            await db.commit()

            log.info(
                f"✅ Provisioned persona set: persona_id={persona.id}, "
                f"result={result}"
            )
            return result

        except Exception as e:
            log.error(f"Failed to provision persona set: {e}")
            await db.rollback()
            raise


@flow(name="persona_buffer_replenishment", log_prints=True)
async def persona_buffer_flow() -> dict:
    """
    Check buffer and provision if below 40%.

    Triggered by Stripe webhook after client signup.
    Maintains buffer of warmed persona+domain sets for instant client onboarding.

    Steps:
    1. Calculate current buffer status (allocated vs available+warming)
    2. Determine shortfall based on 40% buffer ratio
    3. Provision new persona sets to fill shortfall

    Returns:
        Summary with buffer status and provisioning results
    """
    log = get_run_logger()
    run_id = flow_run.id if flow_run else "manual"

    log.info(f"Starting persona buffer check (run_id={run_id})")

    # Calculate shortfall
    buffer_status = await calculate_buffer_shortfall_task()
    shortfall = buffer_status["shortfall"]

    if shortfall <= 0:
        log.info(
            f"Buffer healthy: {buffer_status['available']} available, "
            f"{buffer_status['warming']} warming"
        )
        return {
            "success": True,
            "action": "none",
            "buffer_status": buffer_status,
            "message": "Buffer is healthy, no provisioning needed",
        }

    log.info(f"Buffer shortfall: {shortfall} persona sets needed")

    # Provision shortfall
    provisioned = 0
    errors = []

    for i in range(shortfall):
        try:
            result = await provision_persona_set_task()
            if result.get("success"):
                provisioned += 1
                log.info(f"Provisioned persona set {i + 1}/{shortfall}")
        except Exception as e:
            log.error(f"Failed to provision persona set {i + 1}: {e}")
            errors.append(str(e))

    log.info(
        f"Persona buffer provisioning complete: "
        f"{provisioned}/{shortfall} provisioned, {len(errors)} errors"
    )

    return {
        "success": provisioned > 0,
        "action": "provisioned",
        "requested": shortfall,
        "provisioned": provisioned,
        "errors": errors if errors else None,
        "buffer_status": buffer_status,
        "completed_at": datetime.utcnow().isoformat(),
    }


async def get_buffer_status() -> dict:
    """
    Get current buffer status without triggering provisioning.

    Admin helper for dashboard/monitoring.

    Returns:
        Dict with allocated, available, warming, required_buffer, shortfall
    """
    async with get_db_session() as db:
        allocated = (
            await db.scalar(
                select(func.count(ResourcePool.id))
                .where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
                .where(ResourcePool.status == ResourceStatus.ASSIGNED)
                .where(ResourcePool.deleted_at.is_(None))
            )
            or 0
        )

        available = (
            await db.scalar(
                select(func.count(ResourcePool.id))
                .where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
                .where(ResourcePool.status == ResourceStatus.AVAILABLE)
                .where(ResourcePool.reputation_score >= MIN_HEAT_SCORE)
                .where(ResourcePool.deleted_at.is_(None))
            )
            or 0
        )

        warming = (
            await db.scalar(
                select(func.count(ResourcePool.id))
                .where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
                .where(ResourcePool.status == ResourceStatus.WARMING)
                .where(ResourcePool.deleted_at.is_(None))
            )
            or 0
        )

        required_buffer = ceil(allocated * BUFFER_RATIO)
        shortfall = max(0, required_buffer - available - warming)

        return {
            "allocated": allocated,
            "available": available,
            "warming": warming,
            "required_buffer": required_buffer,
            "shortfall": shortfall,
            "buffer_ratio": BUFFER_RATIO,
            "min_heat_score": MIN_HEAT_SCORE,
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Uses Prefect @flow and @task decorators
# [x] Tasks have retries configured
# [x] Session managed via get_db_session context manager
# [x] 40% buffer ratio constant
# [x] Minimum heat score of 85
# [x] Counts allocated, available, and warming domains
# [x] Provisions persona + domains to fill shortfall
# [x] Error handling with rollback
# [x] Admin helper for status check
# [x] Summary return with counts
