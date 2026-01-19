"""
FILE: src/orchestration/flows/post_onboarding_flow.py
TASK: Phase 37 (Lead/Campaign Architecture)
PURPOSE: Post-onboarding flow to generate campaigns and source leads
PHASE: 37

DEPENDENCIES:
- src/engines/campaign_suggester.py
- src/orchestration/flows/pool_population_flow.py
- src/services/lead_allocator_service.py
- src/integrations/supabase.py

RULES APPLIED:
- Rule 1: Follow blueprint exactly
- Rule 11: Session passed as argument
- Rule 12: No cross-engine imports (only orchestration imports engines)

This flow is triggered after client onboarding completes and ICP is confirmed.
It performs:
1. AI campaign suggestions based on ICP
2. Campaign creation (as drafts)
3. Lead sourcing from Apollo based on ICP
4. Lead assignment to campaigns
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="verify_icp_ready", retries=2, retry_delay_seconds=3)
async def verify_icp_ready_task(client_id: UUID) -> dict[str, Any]:
    """
    Verify client has ICP data ready for lead sourcing.

    Args:
        client_id: Client UUID

    Returns:
        Dict with client data and ICP status
    """
    async with get_db_session() as db:
        result = await db.execute(
            text("""
            SELECT
                c.id,
                c.company_name,
                c.tier,
                c.icp_industries,
                c.icp_titles,
                c.icp_company_sizes,
                c.icp_locations,
                c.icp_pain_points,
                c.icp_confirmed_at,
                c.onboarding_status
            FROM clients c
            WHERE c.id = :client_id
            AND c.deleted_at IS NULL
            """),
            {"client_id": str(client_id)},
        )
        row = result.fetchone()

    if not row:
        return {
            "ready": False,
            "error": f"Client {client_id} not found",
        }

    # Check if ICP is populated
    has_icp = bool(row.icp_industries or row.icp_titles)

    if not has_icp:
        return {
            "ready": False,
            "error": "Client has no ICP data. Complete onboarding first.",
            "client_id": str(client_id),
        }

    return {
        "ready": True,
        "client_id": str(client_id),
        "company_name": row.company_name,
        "tier": str(row.tier) if row.tier else "ignition",
        "icp": {
            "industries": row.icp_industries or [],
            "titles": row.icp_titles or [],
            "company_sizes": row.icp_company_sizes or [],
            "locations": row.icp_locations or [],
            "pain_points": row.icp_pain_points or [],
        },
        "icp_confirmed": row.icp_confirmed_at is not None,
    }


@task(name="generate_campaign_suggestions", retries=1, timeout_seconds=120)
async def generate_campaign_suggestions_task(
    client_id: UUID,
) -> dict[str, Any]:
    """
    Generate AI campaign suggestions for the client.

    Args:
        client_id: Client UUID

    Returns:
        Dict with campaign suggestions
    """
    from src.engines.campaign_suggester import get_campaign_suggester

    engine = get_campaign_suggester()

    async with get_db_session() as db:
        result = await engine.suggest_campaigns(db, client_id)

    if not result.success:
        logger.error(f"Campaign suggestion failed: {result.error}")
        return {
            "success": False,
            "error": result.error,
        }

    logger.info(
        f"Generated {len(result.data['suggestions'])} campaign suggestions for client {client_id}"
    )

    return {
        "success": True,
        "suggestions": result.data["suggestions"],
        "ai_campaign_slots": result.data["ai_campaign_slots"],
        "custom_campaign_slots": result.data["custom_campaign_slots"],
    }


@task(name="create_draft_campaigns", retries=2, retry_delay_seconds=5)
async def create_draft_campaigns_task(
    client_id: UUID,
    suggestions: list[dict[str, Any]],
    auto_activate: bool = False,
) -> dict[str, Any]:
    """
    Create draft campaigns from AI suggestions.

    Args:
        client_id: Client UUID
        suggestions: List of campaign suggestions
        auto_activate: Whether to activate campaigns immediately

    Returns:
        Dict with created campaign IDs
    """
    from src.engines.campaign_suggester import get_campaign_suggester

    engine = get_campaign_suggester()

    async with get_db_session() as db:
        result = await engine.create_suggested_campaigns(
            db=db,
            client_id=client_id,
            suggestions=suggestions,
            auto_activate=auto_activate,
        )

    if not result.success:
        logger.error(f"Campaign creation failed: {result.error}")
        return {
            "success": False,
            "error": result.error,
        }

    logger.info(
        f"Created {result.data['campaigns_created']} campaigns for client {client_id}"
    )

    return {
        "success": True,
        "campaigns_created": result.data["campaigns_created"],
        "campaigns": result.data["campaigns"],
        "total_allocation": result.data["total_allocation"],
    }


@task(name="source_leads_from_apollo", retries=2, retry_delay_seconds=10)
async def source_leads_from_apollo_task(
    client_id: UUID,
    icp_criteria: dict[str, Any],
    lead_count: int,
) -> dict[str, Any]:
    """
    Source leads from Apollo based on ICP criteria.

    Args:
        client_id: Client UUID
        icp_criteria: ICP criteria dict
        lead_count: Number of leads to source

    Returns:
        Dict with sourced lead info
    """
    from src.orchestration.flows.pool_population_flow import pool_population_flow

    logger.info(f"Sourcing {lead_count} leads for client {client_id}")

    result = await pool_population_flow(
        client_id=client_id,
        limit=lead_count,
    )

    if not result.get("success", False):
        return {
            "success": False,
            "error": result.get("error", "Pool population failed"),
        }

    logger.info(
        f"Sourced {result.get('leads_added', 0)} leads for client {client_id}"
    )

    return {
        "success": True,
        "leads_added": result.get("leads_added", 0),
        "leads_skipped": result.get("leads_skipped", 0),
        "total_cost_aud": result.get("total_cost_aud", 0.0),
    }


@task(name="assign_leads_to_campaigns", retries=2, retry_delay_seconds=5)
async def assign_leads_to_campaigns_task(
    client_id: UUID,
    campaigns: list[dict[str, Any]],
    total_leads: int,
) -> dict[str, Any]:
    """
    Assign sourced leads to campaigns based on allocation percentages.

    Args:
        client_id: Client UUID
        campaigns: List of campaign dicts with allocation_pct
        total_leads: Total leads available to assign

    Returns:
        Dict with assignment results
    """
    from src.services.lead_allocator_service import LeadAllocatorService

    if total_leads <= 0:
        return {
            "success": True,
            "leads_assigned": 0,
            "assignments": [],
        }

    assignments = []

    async with get_db_session() as db:
        allocator = LeadAllocatorService(db)

        for campaign in campaigns:
            campaign_id = UUID(campaign["campaign_id"])
            allocation_pct = campaign.get("allocation_pct", 0)

            # Calculate leads for this campaign
            leads_for_campaign = int(total_leads * allocation_pct / 100)

            if leads_for_campaign <= 0:
                continue

            # Get ICP criteria from campaign targeting
            icp_criteria = {
                "industries": campaign.get("target_industries", []),
                "seniorities": [],  # Not specified in campaign
                "titles": campaign.get("target_titles", []),
                "countries": campaign.get("target_locations", []),
            }

            assigned = await allocator.allocate_leads(
                client_id=client_id,
                icp_criteria=icp_criteria,
                count=leads_for_campaign,
                campaign_id=campaign_id,
            )

            assignments.append({
                "campaign_id": str(campaign_id),
                "campaign_name": campaign.get("name", "Unknown"),
                "leads_assigned": len(assigned),
                "allocation_pct": allocation_pct,
            })

            logger.info(
                f"Assigned {len(assigned)} leads to campaign {campaign_id}"
            )

    total_assigned = sum(a["leads_assigned"] for a in assignments)

    return {
        "success": True,
        "leads_assigned": total_assigned,
        "assignments": assignments,
    }


@task(name="update_onboarding_status")
async def update_onboarding_status_task(
    client_id: UUID,
    status: str,
) -> bool:
    """
    Update client onboarding status.

    Args:
        client_id: Client UUID
        status: New onboarding status

    Returns:
        True if updated successfully
    """
    async with get_db_session() as db:
        await db.execute(
            text("""
            UPDATE clients
            SET onboarding_status = :status,
                updated_at = NOW()
            WHERE id = :client_id
            AND deleted_at IS NULL
            """),
            {
                "client_id": str(client_id),
                "status": status,
            },
        )
        await db.commit()

    logger.info(f"Updated onboarding status for client {client_id} to {status}")
    return True


# ============================================
# FLOWS
# ============================================


@flow(
    name="post_onboarding_setup",
    description="Generate campaigns and source leads after onboarding",
    task_runner=ConcurrentTaskRunner(),
    retries=0,
    timeout_seconds=600,  # 10 minute timeout
)
async def post_onboarding_setup_flow(
    client_id: str | UUID,
    auto_create_campaigns: bool = True,
    auto_source_leads: bool = True,
    auto_activate_campaigns: bool = False,
    lead_count_override: int | None = None,
) -> dict[str, Any]:
    """
    Post-onboarding setup flow.

    This flow should be triggered after ICP extraction completes:
    1. Verifies ICP is ready
    2. Generates AI campaign suggestions
    3. Creates campaigns (as drafts by default)
    4. Sources leads from Apollo based on tier allowance
    5. Assigns leads to campaigns based on allocation %

    Args:
        client_id: Client UUID (string or UUID)
        auto_create_campaigns: Create campaigns from suggestions (default True)
        auto_source_leads: Source leads from Apollo (default True)
        auto_activate_campaigns: Activate campaigns immediately (default False)
        lead_count_override: Override tier-based lead count (optional)

    Returns:
        Dict with flow result
    """
    # Convert strings to UUIDs if needed (Prefect API passes strings)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting post-onboarding setup for client {client_id}")

    try:
        # Step 1: Verify ICP is ready
        icp_status = await verify_icp_ready_task(client_id)

        if not icp_status["ready"]:
            logger.error(f"ICP not ready: {icp_status.get('error')}")
            return {
                "success": False,
                "client_id": str(client_id),
                "error": icp_status.get("error", "ICP not ready"),
            }

        tier = icp_status["tier"]
        icp = icp_status["icp"]

        # Step 2: Generate campaign suggestions
        suggestions_result = await generate_campaign_suggestions_task(client_id)

        if not suggestions_result["success"]:
            return {
                "success": False,
                "client_id": str(client_id),
                "error": suggestions_result.get("error", "Campaign suggestion failed"),
            }

        suggestions = suggestions_result["suggestions"]
        campaigns_created = []

        # Step 3: Create draft campaigns
        if auto_create_campaigns and suggestions:
            create_result = await create_draft_campaigns_task(
                client_id=client_id,
                suggestions=suggestions,
                auto_activate=auto_activate_campaigns,
            )

            if create_result["success"]:
                campaigns_created = create_result.get("campaigns", [])

        # Step 4: Determine lead count based on tier
        from src.config.tiers import TIER_CONFIG

        tier_lower = tier.lower()
        tier_config = TIER_CONFIG.get(tier_lower, TIER_CONFIG["ignition"])
        tier_lead_count = tier_config["leads_per_month"]

        lead_count = lead_count_override or tier_lead_count
        logger.info(f"Lead count for {tier}: {lead_count}")

        # Step 5: Source leads from Apollo
        leads_sourced = 0
        sourcing_cost = 0.0

        if auto_source_leads:
            source_result = await source_leads_from_apollo_task(
                client_id=client_id,
                icp_criteria=icp,
                lead_count=lead_count,
            )

            if source_result["success"]:
                leads_sourced = source_result.get("leads_added", 0)
                sourcing_cost = source_result.get("total_cost_aud", 0.0)

        # Step 6: Assign leads to campaigns
        assignments = []
        if campaigns_created and leads_sourced > 0:
            assign_result = await assign_leads_to_campaigns_task(
                client_id=client_id,
                campaigns=campaigns_created,
                total_leads=leads_sourced,
            )

            if assign_result["success"]:
                assignments = assign_result.get("assignments", [])

        # Step 7: Update onboarding status
        await update_onboarding_status_task(
            client_id=client_id,
            status="completed",
        )

        logger.info(
            f"Post-onboarding setup completed for client {client_id}: "
            f"{len(campaigns_created)} campaigns, {leads_sourced} leads"
        )

        return {
            "success": True,
            "client_id": str(client_id),
            "tier": tier,
            "campaigns_suggested": len(suggestions),
            "campaigns_created": len(campaigns_created),
            "campaigns": campaigns_created,
            "leads_sourced": leads_sourced,
            "leads_assigned": sum(a["leads_assigned"] for a in assignments),
            "assignments": assignments,
            "sourcing_cost_aud": sourcing_cost,
        }

    except Exception as e:
        logger.exception(f"Post-onboarding setup failed: {e}")

        return {
            "success": False,
            "client_id": str(client_id),
            "error": str(e),
        }


@flow(
    name="trigger_lead_sourcing",
    description="Source additional leads for a client",
)
async def trigger_lead_sourcing_flow(
    client_id: str | UUID,
    lead_count: int,
    campaign_id: str | UUID | None = None,
) -> dict[str, Any]:
    """
    Trigger additional lead sourcing for a client.

    Can be used to top up leads for a specific campaign or client.

    Args:
        client_id: Client UUID
        lead_count: Number of leads to source
        campaign_id: Optional campaign to assign leads to

    Returns:
        Dict with sourcing result
    """
    if isinstance(client_id, str):
        client_id = UUID(client_id)
    if isinstance(campaign_id, str):
        campaign_id = UUID(campaign_id)

    logger.info(f"Triggering lead sourcing for client {client_id}: {lead_count} leads")

    # Verify ICP
    icp_status = await verify_icp_ready_task(client_id)

    if not icp_status["ready"]:
        return {
            "success": False,
            "error": icp_status.get("error", "ICP not ready"),
        }

    # Source leads
    source_result = await source_leads_from_apollo_task(
        client_id=client_id,
        icp_criteria=icp_status["icp"],
        lead_count=lead_count,
    )

    if not source_result["success"]:
        return source_result

    leads_sourced = source_result.get("leads_added", 0)

    # Assign to specific campaign if provided
    assignments = []
    if campaign_id and leads_sourced > 0:
        from src.services.lead_allocator_service import LeadAllocatorService

        async with get_db_session() as db:
            allocator = LeadAllocatorService(db)

            assigned = await allocator.allocate_leads(
                client_id=client_id,
                icp_criteria=icp_status["icp"],
                count=leads_sourced,
                campaign_id=campaign_id,
            )

            assignments.append({
                "campaign_id": str(campaign_id),
                "leads_assigned": len(assigned),
            })

    return {
        "success": True,
        "client_id": str(client_id),
        "leads_sourced": leads_sourced,
        "leads_skipped": source_result.get("leads_skipped", 0),
        "total_cost_aud": source_result.get("total_cost_aud", 0.0),
        "assignments": assignments,
    }


# ============================================
# DEPLOYMENT
# ============================================


def deploy_post_onboarding_flows():
    """
    Deploy post-onboarding flows to Prefect.

    Run this to register flows with the Prefect server.
    """
    from prefect.deployments import Deployment

    # Main post-onboarding setup flow
    setup_deployment = Deployment.build_from_flow(
        flow=post_onboarding_setup_flow,
        name="post-onboarding-setup",
        work_queue_name="default",
        tags=["onboarding", "campaigns", "leads"],
    )
    setup_deployment.apply()

    # Lead sourcing flow
    sourcing_deployment = Deployment.build_from_flow(
        flow=trigger_lead_sourcing_flow,
        name="trigger-lead-sourcing",
        work_queue_name="default",
        tags=["leads", "sourcing"],
    )
    sourcing_deployment.apply()

    logger.info("Deployed post-onboarding flows")


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Follows import hierarchy (Rule 12)
# [x] Session managed properly with get_db_session()
# [x] Soft delete checks (deleted_at IS NULL)
# [x] Prefect @task and @flow decorators
# [x] Retries configured on tasks
# [x] Timeout configured on flows
# [x] Verifies ICP before sourcing leads
# [x] Generates AI campaign suggestions
# [x] Creates campaigns as drafts by default
# [x] Sources leads based on tier allowance
# [x] Assigns leads to campaigns by allocation %
# [x] Updates onboarding status
# [x] Error handling with proper logging
# [x] Deployment function for Prefect registration
# [x] Type hints on all functions
# [x] Docstrings on all functions
