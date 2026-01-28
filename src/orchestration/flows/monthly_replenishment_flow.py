"""
FILE: src/orchestration/flows/monthly_replenishment_flow.py
PURPOSE: Monthly lead replenishment flow - sources new leads after credit reset
PHASE: Phase D - Item 17
TASK: TODO Item 17 (P2: Implement monthly replenishment flow)
DEPENDENCIES:
  - src/orchestration/flows/pool_population_flow.py
  - src/orchestration/flows/credit_reset_flow.py (trigger)
  - src/services/lead_allocator_service.py
  - src/config/tiers.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only
  - Spec: docs/architecture/flows/MONTHLY_LIFECYCLE.md
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.deployments import run_deployment
from sqlalchemy import and_, func, select

from src.config.tiers import get_leads_for_tier
from src.integrations.supabase import get_db_session
from src.models.base import CampaignStatus, LeadStatus
from src.models.campaign import Campaign
from src.models.client import Client
from src.models.lead import Lead
from src.services.lead_allocator_service import LeadAllocatorService

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="calculate_lead_gap", retries=2, retry_delay_seconds=5)
async def calculate_lead_gap_task(client_id: UUID) -> dict[str, Any]:
    """
    Calculate how many new leads to source.

    Gap = Tier Quota - Active Pipeline

    Active Pipeline includes:
    - Leads with status: NEW, ENRICHED, IN_SEQUENCE, REPLIED
    - Excludes: CONVERTED, NOT_INTERESTED, BOUNCED, UNSUBSCRIBED, ARCHIVED, COMPLETED

    Args:
        client_id: Client UUID

    Returns:
        Dict with gap calculation details
    """
    async with get_db_session() as db:
        # Get client tier
        client = await db.get(Client, client_id)
        if not client:
            raise ValueError(f"Client {client_id} not found")

        tier_name = client.tier.value if client.tier else "ignition"
        tier_quota = get_leads_for_tier(tier_name)

        # Count active pipeline - leads still in play
        # Note: LeadStatus enum has: NEW, ENRICHED, SCORED, IN_SEQUENCE, CONVERTED, UNSUBSCRIBED, BOUNCED
        # Active pipeline = leads not yet converted or removed
        active_statuses = [
            LeadStatus.NEW,
            LeadStatus.ENRICHED,
            LeadStatus.SCORED,
            LeadStatus.IN_SEQUENCE,
        ]
        # Excluded from pipeline count: CONVERTED (success), UNSUBSCRIBED, BOUNCED

        pipeline_count = await db.scalar(
            select(func.count(Lead.id))
            .where(
                and_(
                    Lead.client_id == client_id,
                    Lead.deleted_at.is_(None),
                    Lead.status.in_(active_statuses),
                )
            )
        ) or 0

        # Calculate gap (never negative)
        gap = max(0, tier_quota - pipeline_count)

        logger.info(
            f"Lead gap for {client.name}: "
            f"Quota={tier_quota}, Pipeline={pipeline_count}, Gap={gap}"
        )

        return {
            "client_id": str(client_id),
            "client_name": client.name,
            "tier": tier_name,
            "tier_quota": tier_quota,
            "active_pipeline": pipeline_count,
            "gap": gap,
        }


@task(name="get_active_campaigns", retries=2, retry_delay_seconds=5)
async def get_active_campaigns_task(client_id: UUID) -> list[dict[str, Any]]:
    """
    Get all ACTIVE campaigns for a client with their allocation percentages.

    Only ACTIVE campaigns receive new leads.
    DRAFT, PAUSED, and COMPLETED campaigns are excluded.

    Args:
        client_id: Client UUID

    Returns:
        List of active campaigns with allocation info
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(Campaign)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Campaign.status == CampaignStatus.ACTIVE,
                    Campaign.deleted_at.is_(None),
                )
            )
            .order_by(Campaign.created_at)
        )
        campaigns = result.scalars().all()

        if not campaigns:
            logger.warning(f"No active campaigns for client {client_id}")
            return []

        campaign_list = []
        total_allocation = 0

        for campaign in campaigns:
            pct = campaign.lead_allocation_pct or 0
            total_allocation += pct
            campaign_list.append({
                "id": str(campaign.id),
                "name": campaign.name,
                "lead_allocation_pct": pct,
            })

        # Normalize allocations if they don't sum to 100
        if total_allocation > 0 and total_allocation != 100:
            logger.info(
                f"Normalizing allocations: total={total_allocation}%, "
                f"adjusting to 100%"
            )
            for c in campaign_list:
                c["normalized_pct"] = (c["lead_allocation_pct"] / total_allocation) * 100
        else:
            for c in campaign_list:
                c["normalized_pct"] = c["lead_allocation_pct"]

        logger.info(
            f"Found {len(campaign_list)} active campaigns for client {client_id}"
        )

        return campaign_list


@task(name="source_leads_for_replenishment", retries=1, retry_delay_seconds=30)
async def source_leads_task(
    client_id: UUID,
    lead_count: int,
) -> dict[str, Any]:
    """
    Source new leads using pool_population_flow.

    Calls the existing pool population flow which uses the waterfall strategy:
    - Tier 1: Portfolio lookalikes
    - Tier 2: Portfolio industries
    - Tier 3: Generic ICP fallback

    Args:
        client_id: Client UUID
        lead_count: Number of leads to source

    Returns:
        Dict with sourcing results
    """
    if lead_count <= 0:
        return {
            "success": True,
            "leads_sourced": 0,
            "message": "No leads needed (gap is 0)",
        }

    logger.info(f"Sourcing {lead_count} leads for client {client_id}")

    try:
        # Call pool_population_flow via deployment
        # This sources leads and adds them to the pool
        # Deployment name format: <flow_name>/<deployment_name>
        result = await run_deployment(
            name="pool_population/pool-population-flow",
            parameters={
                "client_id": str(client_id),
                "limit": lead_count,
            },
            timeout=0,  # Don't wait - run async
        )

        logger.info(f"Pool population triggered for client {client_id}")

        return {
            "success": True,
            "leads_requested": lead_count,
            "flow_run_id": str(result.id) if result else None,
            "message": "Pool population flow triggered",
        }

    except Exception as e:
        logger.error(f"Failed to trigger pool population: {e}")
        return {
            "success": False,
            "leads_requested": lead_count,
            "error": str(e),
        }


@task(name="assign_leads_to_campaigns", retries=2, retry_delay_seconds=10)
async def assign_leads_to_campaigns_task(
    client_id: UUID,
    campaigns: list[dict[str, Any]],
    lead_count: int,
) -> dict[str, Any]:
    """
    Assign newly sourced leads to ACTIVE campaigns proportionally.

    Distributes leads based on each campaign's lead_allocation_pct.
    Uses LeadAllocatorService for the actual assignment.

    Args:
        client_id: Client UUID
        campaigns: List of active campaigns with allocation percentages
        lead_count: Total leads to distribute

    Returns:
        Dict with assignment results
    """
    if not campaigns:
        logger.warning(f"No active campaigns to assign leads for client {client_id}")
        return {
            "success": True,
            "leads_assigned": 0,
            "campaigns_updated": 0,
            "message": "No active campaigns - leads sourced but not assigned",
        }

    if lead_count <= 0:
        return {
            "success": True,
            "leads_assigned": 0,
            "campaigns_updated": 0,
            "message": "No leads to assign",
        }

    async with get_db_session() as db:
        allocator = LeadAllocatorService(db)

        # Get client ICP for matching
        client = await db.get(Client, client_id)
        icp_criteria = {
            "industries": client.icp_industries or [],
            "titles": client.icp_titles or [],
            "countries": client.icp_locations or ["Australia"],
        }

        assignments = []
        total_assigned = 0
        remaining_leads = lead_count

        for campaign in campaigns:
            # Calculate leads for this campaign based on allocation %
            pct = campaign.get("normalized_pct", 0)
            campaign_lead_count = int(lead_count * pct / 100)

            # Ensure at least 1 lead if there's any allocation
            if pct > 0 and campaign_lead_count == 0 and remaining_leads > 0:
                campaign_lead_count = 1

            # Don't exceed remaining
            campaign_lead_count = min(campaign_lead_count, remaining_leads)

            if campaign_lead_count <= 0:
                continue

            try:
                # Allocate leads to this campaign
                assigned = await allocator.allocate_leads(
                    client_id=client_id,
                    icp_criteria=icp_criteria,
                    count=campaign_lead_count,
                    campaign_id=UUID(campaign["id"]),
                )

                actual_assigned = len(assigned)
                total_assigned += actual_assigned
                remaining_leads -= actual_assigned

                assignments.append({
                    "campaign_id": campaign["id"],
                    "campaign_name": campaign["name"],
                    "requested": campaign_lead_count,
                    "assigned": actual_assigned,
                })

                logger.info(
                    f"Assigned {actual_assigned}/{campaign_lead_count} leads to "
                    f"campaign '{campaign['name']}'"
                )

            except Exception as e:
                logger.error(
                    f"Failed to assign leads to campaign {campaign['id']}: {e}"
                )
                assignments.append({
                    "campaign_id": campaign["id"],
                    "campaign_name": campaign["name"],
                    "requested": campaign_lead_count,
                    "assigned": 0,
                    "error": str(e),
                })

        return {
            "success": total_assigned > 0,
            "leads_assigned": total_assigned,
            "campaigns_updated": len([a for a in assignments if a.get("assigned", 0) > 0]),
            "assignments": assignments,
        }


# ============================================
# FLOW
# ============================================


@flow(
    name="monthly_replenishment",
    description="Post-credit-reset lead replenishment flow",
    retries=1,
    retry_delay_seconds=60,
)
async def monthly_replenishment_flow(
    client_id: str | UUID,
    force_full: bool = False,
) -> dict[str, Any]:
    """
    Monthly lead replenishment flow.

    Triggered after credit reset to source new leads for the month.

    Steps:
    1. Calculate lead gap (Tier Quota - Active Pipeline)
    2. Source leads using pool_population_flow
    3. Assign leads to ACTIVE campaigns proportionally

    Args:
        client_id: Client UUID (string or UUID)
        force_full: If True, source full tier quota regardless of pipeline

    Returns:
        Dict with replenishment summary
    """
    # Convert string to UUID if needed
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting monthly replenishment for client {client_id}")

    # Step 1: Calculate lead gap
    gap_result = await calculate_lead_gap_task(client_id)

    # Determine how many leads to source
    if force_full:
        leads_to_source = gap_result["tier_quota"]
        logger.info(f"Force full mode: sourcing full quota of {leads_to_source}")
    else:
        leads_to_source = gap_result["gap"]

    # Early exit if pipeline is full
    if leads_to_source <= 0:
        logger.info(
            f"Pipeline full for {gap_result['client_name']} - "
            f"no replenishment needed"
        )
        return {
            "success": True,
            "client_id": str(client_id),
            "client_name": gap_result["client_name"],
            "leads_sourced": 0,
            "leads_assigned": 0,
            "reason": "Pipeline full - no leads needed",
            "gap_calculation": gap_result,
            "completed_at": datetime.utcnow().isoformat(),
        }

    # Step 2: Get active campaigns
    campaigns = await get_active_campaigns_task(client_id)

    # Step 3: Source leads
    source_result = await source_leads_task(client_id, leads_to_source)

    # Step 4: Assign to campaigns (if we have active campaigns)
    if campaigns and source_result.get("success"):
        assign_result = await assign_leads_to_campaigns_task(
            client_id=client_id,
            campaigns=campaigns,
            lead_count=leads_to_source,
        )
    else:
        assign_result = {
            "success": True,
            "leads_assigned": 0,
            "campaigns_updated": 0,
            "message": "No active campaigns" if not campaigns else "Sourcing failed",
        }

    # Compile summary
    summary = {
        "success": source_result.get("success", False),
        "client_id": str(client_id),
        "client_name": gap_result["client_name"],
        "tier": gap_result["tier"],
        "gap_calculation": gap_result,
        "leads_requested": leads_to_source,
        "source_result": source_result,
        "assign_result": assign_result,
        "active_campaigns": len(campaigns),
        "completed_at": datetime.utcnow().isoformat(),
    }

    if source_result.get("success"):
        logger.info(
            f"Monthly replenishment complete for {gap_result['client_name']}: "
            f"requested={leads_to_source}, "
            f"campaigns={len(campaigns)}"
        )
    else:
        logger.warning(
            f"Monthly replenishment issues for {gap_result['client_name']}: "
            f"{source_result.get('error', 'unknown error')}"
        )

    return summary


# ============================================
# MANUAL TRIGGER (for admin/testing)
# ============================================


async def trigger_replenishment_for_client(
    client_id: UUID,
    force_full: bool = False,
) -> dict[str, Any]:
    """
    Manually trigger replenishment for a specific client.

    Used by admin panel for manual replenishment.

    Args:
        client_id: UUID of the client
        force_full: If True, source full tier quota

    Returns:
        Replenishment result dict
    """
    return await monthly_replenishment_flow(
        client_id=client_id,
        force_full=force_full,
    )


async def trigger_replenishment_batch(
    client_ids: list[UUID],
    force_full: bool = False,
) -> list[dict[str, Any]]:
    """
    Trigger replenishment for multiple clients.

    Args:
        client_ids: List of client UUIDs
        force_full: If True, source full tier quota for all

    Returns:
        List of replenishment results
    """
    results = []
    for client_id in client_ids:
        try:
            result = await monthly_replenishment_flow(
                client_id=client_id,
                force_full=force_full,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Replenishment failed for client {client_id}: {e}")
            results.append({
                "client_id": str(client_id),
                "success": False,
                "error": str(e),
            })

    return results


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
# [x] Manual trigger functions for admin use
# [x] Uses tier config for lead quotas
# [x] Gap calculation: Tier Quota - Active Pipeline
# [x] Only ACTIVE campaigns receive leads
# [x] Proportional assignment by lead_allocation_pct
# [x] Early exit if pipeline is full
# [x] Integrates with pool_population_flow
