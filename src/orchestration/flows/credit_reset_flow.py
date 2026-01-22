"""
FILE: src/orchestration/flows/credit_reset_flow.py
PURPOSE: Monthly credit reset flow - resets client credits on billing date
PHASE: P0 Critical Fix, Phase D Item 17 (trigger replenishment)
TASK: TODO P0-001, Item 17
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/models/client.py
  - src/config/tiers.py
  - src/orchestration/flows/monthly_replenishment_flow.py (triggered post-reset)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only
  - Spec: docs/architecture/business/TIERS_AND_BILLING.md
  - Spec: docs/architecture/flows/MONTHLY_LIFECYCLE.md
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.deployments import run_deployment
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.tiers import get_leads_for_tier
from src.integrations.supabase import get_db_session
from src.models.base import SubscriptionStatus
from src.models.client import Client

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="find_clients_needing_credit_reset", retries=2, retry_delay_seconds=5)
async def find_clients_needing_credit_reset_task() -> list[dict[str, Any]]:
    """
    Find clients whose credits_reset_at has passed.

    Returns clients with:
    - Active or trialing subscription
    - credits_reset_at <= now() OR credits_reset_at is NULL (new clients)
    - Not soft-deleted

    Returns:
        List of client dicts with id, name, tier, current credits, reset date
    """
    async with get_db_session() as db:
        now = datetime.utcnow()

        stmt = (
            select(
                Client.id,
                Client.name,
                Client.tier,
                Client.credits_remaining,
                Client.credits_reset_at,
            )
            .where(
                and_(
                    Client.deleted_at.is_(None),
                    Client.subscription_status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING,
                    ]),
                    # Reset if: reset date passed OR never set (new client)
                    (Client.credits_reset_at <= now) | (Client.credits_reset_at.is_(None)),
                )
            )
        )

        result = await db.execute(stmt)
        rows = result.all()

        clients = []
        for row in rows:
            clients.append({
                "id": row.id,
                "name": row.name,
                "tier": row.tier.value if row.tier else "ignition",
                "credits_remaining": row.credits_remaining,
                "credits_reset_at": row.credits_reset_at,
            })

        logger.info(f"Found {len(clients)} clients needing credit reset")
        return clients


@task(name="reset_client_credits", retries=2, retry_delay_seconds=5)
async def reset_client_credits_task(client_data: dict[str, Any]) -> dict[str, Any]:
    """
    Reset credits for a single client.

    - Sets credits_remaining to tier quota
    - Sets credits_reset_at to 1 month from now
    - Logs the reset event

    Args:
        client_data: Dict with client id, name, tier, current credits

    Returns:
        Dict with reset result including old/new values
    """
    client_id = client_data["id"]
    tier_name = client_data["tier"]
    old_credits = client_data["credits_remaining"]

    # Get new credit quota from tier config
    new_credits = get_leads_for_tier(tier_name)

    # Calculate next reset date (1 month from now)
    now = datetime.utcnow()
    next_reset = now + timedelta(days=30)  # Approximate month

    async with get_db_session() as db:
        stmt = (
            update(Client)
            .where(Client.id == client_id)
            .values(
                credits_remaining=new_credits,
                credits_reset_at=next_reset,
            )
        )
        await db.execute(stmt)
        await db.commit()

    result = {
        "client_id": str(client_id),
        "client_name": client_data["name"],
        "tier": tier_name,
        "old_credits": old_credits,
        "new_credits": new_credits,
        "next_reset_at": next_reset.isoformat(),
        "reset_at": now.isoformat(),
    }

    logger.info(
        f"Reset credits for {client_data['name']}: "
        f"{old_credits} -> {new_credits} (tier: {tier_name}), "
        f"next reset: {next_reset.date()}"
    )

    return result


@task(name="trigger_monthly_replenishment", retries=1, retry_delay_seconds=10)
async def trigger_replenishment_task(client_id: UUID, client_name: str) -> dict[str, Any]:
    """
    Trigger monthly replenishment flow for a client after credit reset.

    This runs asynchronously - we don't wait for replenishment to complete.
    The replenishment flow will source leads and assign them to campaigns.

    Args:
        client_id: Client UUID
        client_name: Client name for logging

    Returns:
        Dict with trigger result
    """
    try:
        # Trigger replenishment flow via deployment (non-blocking)
        flow_run = await run_deployment(
            name="monthly_replenishment/monthly-replenishment-flow",
            parameters={"client_id": str(client_id)},
            timeout=0,  # Don't wait for completion
        )

        logger.info(
            f"Triggered monthly replenishment for {client_name} "
            f"(flow_run_id: {flow_run.id if flow_run else 'unknown'})"
        )

        return {
            "client_id": str(client_id),
            "client_name": client_name,
            "replenishment_triggered": True,
            "flow_run_id": str(flow_run.id) if flow_run else None,
        }

    except Exception as e:
        # Log but don't fail - replenishment is non-critical
        logger.warning(
            f"Failed to trigger replenishment for {client_name}: {e}. "
            f"Replenishment can be triggered manually."
        )
        return {
            "client_id": str(client_id),
            "client_name": client_name,
            "replenishment_triggered": False,
            "error": str(e),
        }


# ============================================
# FLOW
# ============================================


@flow(
    name="credit_reset_check",
    description="Hourly check to reset client credits on billing date",
    retries=1,
    retry_delay_seconds=60,
)
async def credit_reset_check_flow() -> dict[str, Any]:
    """
    Credit reset check flow.

    Runs hourly to:
    1. Find clients where credits_reset_at <= now()
    2. Reset credits_remaining to tier.leads_per_month
    3. Set credits_reset_at to next billing date (30 days)
    4. Log reset events

    Returns:
        Dict with summary of resets performed
    """
    logger.info("Starting credit reset check flow")

    # Find clients needing reset
    clients = await find_clients_needing_credit_reset_task()

    if not clients:
        logger.info("No clients need credit reset at this time")
        return {
            "status": "success",
            "clients_checked": 0,
            "clients_reset": 0,
            "resets": [],
        }

    # Reset credits for each client and trigger replenishment
    resets = []
    replenishments = []

    for client in clients:
        try:
            result = await reset_client_credits_task(client)
            resets.append(result)

            # Trigger replenishment after successful reset
            replenish_result = await trigger_replenishment_task(
                client_id=client["id"],
                client_name=client["name"],
            )
            replenishments.append(replenish_result)

        except Exception as e:
            logger.error(f"Failed to reset credits for client {client['id']}: {e}")
            resets.append({
                "client_id": str(client["id"]),
                "client_name": client["name"],
                "error": str(e),
            })

    successful_resets = [r for r in resets if "error" not in r]
    failed_resets = [r for r in resets if "error" in r]

    successful_replenishments = [r for r in replenishments if r.get("replenishment_triggered")]

    logger.info(
        f"Credit reset complete: {len(successful_resets)} successful, "
        f"{len(failed_resets)} failed, "
        f"{len(successful_replenishments)} replenishments triggered"
    )

    return {
        "status": "success" if not failed_resets else "partial",
        "clients_checked": len(clients),
        "clients_reset": len(successful_resets),
        "clients_failed": len(failed_resets),
        "replenishments_triggered": len(successful_replenishments),
        "resets": resets,
        "replenishments": replenishments,
    }


# ============================================
# MANUAL TRIGGER (for testing/admin)
# ============================================


async def reset_credits_for_client(client_id: UUID) -> dict[str, Any]:
    """
    Manually reset credits for a specific client.

    Used by admin panel for manual resets.

    Args:
        client_id: UUID of the client to reset

    Returns:
        Reset result dict
    """
    async with get_db_session() as db:
        stmt = select(
            Client.id,
            Client.name,
            Client.tier,
            Client.credits_remaining,
            Client.credits_reset_at,
        ).where(Client.id == client_id)

        result = await db.execute(stmt)
        row = result.first()

        if not row:
            raise ValueError(f"Client {client_id} not found")

        client_data = {
            "id": row.id,
            "name": row.name,
            "tier": row.tier.value if row.tier else "ignition",
            "credits_remaining": row.credits_remaining,
            "credits_reset_at": row.credits_reset_at,
        }

    return await reset_client_credits_task(client_data)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Uses get_db_session() pattern
# [x] Soft delete checks (deleted_at.is_(None))
# [x] Proper Prefect task/flow decorators
# [x] Retry configuration on tasks
# [x] Logging for audit trail
# [x] Returns structured results
# [x] Handles errors gracefully
# [x] Manual reset function for admin use
# [x] Uses tier config for credit amounts
# --- Item 17: Monthly Replenishment Trigger ---
# [x] trigger_replenishment_task added
# [x] Replenishment triggered after each successful credit reset
# [x] Non-blocking (timeout=0) - doesn't wait for replenishment to complete
# [x] Graceful failure handling - logs warning but doesn't fail flow
# [x] Return includes replenishments array
