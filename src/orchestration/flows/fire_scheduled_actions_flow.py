"""
Contract: src/orchestration/flows/fire_scheduled_actions_flow.py
Purpose: Fires scheduled outreach actions every 5 minutes (dry-run default)
Layer: orchestration
Imports: models, integrations, engines, services
Consumers: Prefect scheduler
"""

import logging
from datetime import UTC, datetime

from prefect import flow, task

logger = logging.getLogger(__name__)

# Feature flag — dry-run by default
# Set REAL_MODE_ENABLED = True via env var when ready for go-live
REAL_MODE_ENABLED = False


@task(retries=0)
async def get_due_actions(db):
    """Query outreach_actions WHERE status='scheduled' AND scheduled_at <= NOW()."""
    # Production query:
    # result = await db.execute(
    #     select(OutreachAction)
    #     .where(and_(
    #         OutreachAction.status == 'scheduled',
    #         OutreachAction.scheduled_at <= datetime.now(timezone.utc),
    #     ))
    #     .order_by(OutreachAction.scheduled_at)
    #     .limit(100)
    # )
    # return result.scalars().all()
    return []


@task(retries=0)
async def fire_action(action, rate_limit_manager, db):
    """Fire a single outreach action (or log in dry-run mode)."""
    # Re-check rate limits at fire time
    can_fire, reason = await rate_limit_manager.can_fire(
        client_id=str(action.cycle_id),  # Resolve to client_id in production
        channel=action.channel,
        target_date=datetime.now(UTC),
        db=db,
    )

    if not can_fire:
        action.status = "held"
        action.skipped_reason = reason
        logger.info(f"Action {action.id} HELD: {reason}")
        return

    # Check if prospect has replied/suppressed since scheduling
    # (production: check cycle_prospects.outreach_status)

    if REAL_MODE_ENABLED and not action.dry_run:
        # REAL MODE — call actual provider API
        # email.send(), linkedin.connect(), voice.call() fire here
        # NOT IMPLEMENTED in this directive — gated behind go-live
        logger.warning(f"REAL MODE not implemented — action {action.id} skipped")
        action.status = "skipped"
        action.skipped_reason = "real_mode_not_implemented"
    else:
        # DRY-RUN MODE — log what would fire
        logger.info(
            f"DRY-RUN: Would fire {action.channel} {action.action_type} "
            f"for prospect {action.prospect_id} at {action.scheduled_at}"
        )
        action.status = "fired"
        action.fired_at = datetime.now(UTC)
        action.dry_run = True
        action.result = {
            "dry_run": True,
            "would_fire": action.channel,
            "action_type": action.action_type,
            "logged_at": datetime.now(UTC).isoformat(),
        }


@flow(
    name="fire_scheduled_actions",
    description="Fires due outreach actions every 5 minutes (dry-run default)",
    log_prints=True,
)
async def fire_scheduled_actions_flow():
    """Main firing flow — runs every 5 minutes via Prefect schedule."""
    from src.services.rate_limit_manager import RateLimitManager

    logger.info("Firing engine: checking for due actions...")

    rate_limit_manager = RateLimitManager()

    # In production: get DB session from context or dependency injection
    db = None  # Placeholder

    actions = await get_due_actions(db)

    if not actions:
        logger.info("No due actions found")
        return {"fired": 0, "held": 0, "skipped": 0}

    fired = held = skipped = 0
    for action in actions:
        await fire_action(action, rate_limit_manager, db)
        if action.status == "fired":
            fired += 1
        elif action.status == "held":
            held += 1
        elif action.status == "skipped":
            skipped += 1

    logger.info(f"Firing engine complete: {fired} fired, {held} held, {skipped} skipped")
    return {"fired": fired, "held": held, "skipped": skipped}
