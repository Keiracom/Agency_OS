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
5. Promotion of lead_pool rows to leads table (Directive #184 Fix 1)

Directive #184 Changes:
- Fix 1: Added promote_pool_leads_to_leads_task — promotes validated lead_pool
  rows to the leads table after assignment so they appear on the dashboard.
- Fix 2: Added bypass_gates param — allows domain-only onboarding without
  LinkedIn/CRM connected. Gates become warnings, not hard blocks.
- Fix 3: Added demo_mode param — skips real discovery, injects Brisbane
  construction fixture leads instead. Zero real API credits burned per demo.
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import text

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
                c.name,
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
        "company_name": row.name,
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

    logger.info(f"Created {result.data['campaigns_created']} campaigns for client {client_id}")

    return {
        "success": True,
        "campaigns_created": result.data["campaigns_created"],
        "campaigns": result.data["campaigns"],
        "total_allocation": result.data["total_allocation"],
    }


@task(name="source_leads", retries=2, retry_delay_seconds=10)
async def source_leads_task(
    client_id: UUID,
    icp_criteria: dict[str, Any],
    lead_count: int,
) -> dict[str, Any]:
    """
    Source leads based on ICP criteria.

    NOTE: Apollo integration removed (CEO Directive #003).
    Uses pool_population_flow which relies on Siege Waterfall.

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

    logger.info(f"Sourced {result.get('leads_added', 0)} leads for client {client_id}")

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

            assignments.append(
                {
                    "campaign_id": str(campaign_id),
                    "campaign_name": campaign.get("name", "Unknown"),
                    "leads_assigned": len(assigned),
                    "allocation_pct": allocation_pct,
                }
            )

            logger.info(f"Assigned {len(assigned)} leads to campaign {campaign_id}")

    total_assigned = sum(a["leads_assigned"] for a in assignments)

    return {
        "success": True,
        "leads_assigned": total_assigned,
        "assignments": assignments,
    }


@task(name="promote_pool_leads_to_leads", retries=2, retry_delay_seconds=5)
async def promote_pool_leads_to_leads_task(client_id: UUID) -> dict[str, Any]:
    """
    Promote validated lead_pool rows to the leads table for dashboard visibility.

    Directive #184 Fix 1: The onboarding pipeline writes leads to lead_pool but
    the dashboard reads from leads. This task bridges the gap by copying assigned
    pool rows into leads with the correct column mapping.

    Column mapping (lead_pool → leads):
      company_name       → company
      company_domain     → domain
      company_industry   → organization_industry
      company_employee_count → organization_employee_count
      company_country    → organization_country
      company_website    → organization_website
      company_linkedin_url → organization_linkedin_url
      company_founded_year → organization_founded_year
      company_is_hiring  → organization_is_hiring
      seniority          → seniority_level
      id                 → lead_pool_id (back-reference)

    ALS defaults: als_score=0, als_tier='cold', status='new'
    Duplicate safety: ON CONFLICT ON CONSTRAINT unique_lead_per_client DO NOTHING

    Args:
        client_id: Client UUID

    Returns:
        Dict with promoted count and any errors
    """
    promoted = 0
    errors = []

    async with get_db_session() as db:
        # Fetch assigned pool leads for this client that have a campaign assigned
        result = await db.execute(
            text("""
            SELECT
                lp.id,
                lp.client_id,
                lp.campaign_id,
                lp.email,
                lp.first_name,
                lp.last_name,
                lp.title,
                lp.phone,
                lp.linkedin_url,
                lp.seniority,
                lp.personal_email,
                lp.timezone,
                lp.city,
                lp.state,
                lp.country,
                lp.company_name,
                lp.company_domain,
                lp.company_website,
                lp.company_linkedin_url,
                lp.company_industry,
                lp.company_employee_count,
                lp.company_country,
                lp.company_founded_year,
                lp.company_is_hiring,
                lp.enrichment_source,
                lp.enrichment_confidence
            FROM lead_pool lp
            WHERE lp.client_id = :client_id
            AND lp.campaign_id IS NOT NULL
            AND lp.pool_status NOT IN ('bounced', 'unsubscribed', 'invalid')
            AND lp.email IS NOT NULL
            """),
            {"client_id": str(client_id)},
        )
        pool_leads = result.fetchall()

        if not pool_leads:
            logger.info(f"No pool leads to promote for client {client_id}")
            return {"success": True, "promoted": 0, "skipped": 0}

        logger.info(f"Promoting {len(pool_leads)} pool leads to leads table for client {client_id}")

        skipped = 0
        for lead in pool_leads:
            try:
                insert_result = await db.execute(
                    text("""
                    INSERT INTO leads (
                        id,
                        client_id,
                        campaign_id,
                        email,
                        first_name,
                        last_name,
                        title,
                        phone,
                        linkedin_url,
                        seniority_level,
                        personal_email,
                        timezone,
                        company,
                        domain,
                        organization_website,
                        organization_linkedin_url,
                        organization_industry,
                        organization_employee_count,
                        organization_country,
                        organization_founded_year,
                        organization_is_hiring,
                        enrichment_source,
                        enrichment_confidence,
                        lead_pool_id,
                        als_score,
                        als_tier,
                        status,
                        created_at,
                        updated_at
                    ) VALUES (
                        gen_random_uuid(),
                        :client_id,
                        :campaign_id,
                        :email,
                        :first_name,
                        :last_name,
                        :title,
                        :phone,
                        :linkedin_url,
                        :seniority_level,
                        :personal_email,
                        :timezone,
                        :company,
                        :domain,
                        :organization_website,
                        :organization_linkedin_url,
                        :organization_industry,
                        :organization_employee_count,
                        :organization_country,
                        :organization_founded_year,
                        :organization_is_hiring,
                        :enrichment_source,
                        :enrichment_confidence,
                        :lead_pool_id,
                        0,
                        'cold',
                        'new',
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT ON CONSTRAINT unique_lead_per_client DO NOTHING
                    """),
                    {
                        "client_id": str(lead.client_id),
                        "campaign_id": str(lead.campaign_id),
                        "email": lead.email,
                        "first_name": lead.first_name,
                        "last_name": lead.last_name,
                        "title": lead.title,
                        "phone": lead.phone,
                        "linkedin_url": lead.linkedin_url,
                        "seniority_level": lead.seniority,
                        "personal_email": lead.personal_email,
                        "timezone": lead.timezone,
                        "company": lead.company_name,
                        "domain": lead.company_domain,
                        "organization_website": lead.company_website,
                        "organization_linkedin_url": lead.company_linkedin_url,
                        "organization_industry": lead.company_industry,
                        "organization_employee_count": lead.company_employee_count,
                        "organization_country": lead.company_country,
                        "organization_founded_year": lead.company_founded_year,
                        "organization_is_hiring": lead.company_is_hiring,
                        "enrichment_source": lead.enrichment_source,
                        "enrichment_confidence": lead.enrichment_confidence,
                        "lead_pool_id": str(lead.id),
                    },
                )
                rows_affected = insert_result.rowcount
                if rows_affected > 0:
                    promoted += 1
                else:
                    skipped += 1  # ON CONFLICT DO NOTHING — already exists
            except Exception as e:
                logger.warning(f"Failed to promote pool lead {lead.id} ({lead.email}): {e}")
                errors.append({"pool_lead_id": str(lead.id), "error": str(e)})

        await db.commit()

    logger.info(
        f"Promotion complete for client {client_id}: "
        f"{promoted} promoted, {skipped} skipped (duplicate), {len(errors)} errors"
    )

    return {
        "success": True,
        "promoted": promoted,
        "skipped": skipped,
        "errors": errors,
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
# DEMO MODE HELPER (Directive #184 Fix 3)
# ============================================


async def inject_demo_leads(client_id: UUID, campaign_id: UUID) -> int:
    """
    Inject demo fixture leads into lead_pool for demo mode.

    Reads from src/fixtures/demo_leads.json and inserts records
    into lead_pool with client_id + campaign_id set and
    pool_status = 'assigned'. Skips existing emails via
    ON CONFLICT DO NOTHING.

    Args:
        client_id: Client UUID
        campaign_id: Campaign UUID to assign demo leads to

    Returns:
        Number of leads injected
    """
    fixtures_path = Path(__file__).parent.parent.parent / "fixtures" / "demo_leads.json"
    if not fixtures_path.exists():
        logger.error(f"Demo leads fixture not found at {fixtures_path}")
        return 0

    with open(fixtures_path) as f:
        demo_leads = json.load(f)

    injected = 0
    async with get_db_session() as db:
        for lead in demo_leads:
            try:
                result = await db.execute(
                    text("""
                    INSERT INTO lead_pool (
                        id, client_id, campaign_id,
                        email, first_name, last_name, title,
                        company_name, company_domain, company_website,
                        company_industry, company_employee_count,
                        company_country, company_city,
                        pool_status,
                        enrichment_source,
                        created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :client_id, :campaign_id,
                        :email, :first_name, :last_name, :title,
                        :company_name, :company_domain, :company_website,
                        :company_industry, :company_employee_count,
                        :company_country, :company_city,
                        'assigned',
                        'demo_fixture',
                        NOW(), NOW()
                    )
                    ON CONFLICT (email) DO NOTHING
                    """),
                    {
                        "client_id": str(client_id),
                        "campaign_id": str(campaign_id),
                        "email": lead.get("email"),
                        "first_name": lead.get("first_name"),
                        "last_name": lead.get("last_name"),
                        "title": lead.get("title"),
                        "company_name": lead.get("company"),
                        "company_domain": lead.get("domain"),
                        "company_website": lead.get("company_website"),
                        "company_industry": lead.get("organization_industry"),
                        "company_employee_count": lead.get("organization_employee_count"),
                        "company_country": lead.get("organization_country"),
                        "company_city": lead.get("city"),
                    },
                )
                if result.rowcount > 0:
                    injected += 1
            except Exception as e:
                logger.warning(f"Failed to inject demo lead {lead.get('email')}: {e}")

        await db.commit()

    logger.info(f"Injected {injected} demo leads for client {client_id}, campaign {campaign_id}")
    return injected


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
    bypass_gates: bool = False,
    demo_mode: bool = False,
) -> dict[str, Any]:
    """
    Post-onboarding setup flow.

    MANDATORY GATES (Architecture Decision):
    - LinkedIn connection required (can be bypassed with bypass_gates=True)
    - CRM connection required (can be bypassed with bypass_gates=True)

    This flow should be triggered after ICP extraction completes:
    1. Optionally verifies LinkedIn and CRM gates (bypass_gates skips this)
    2. Verifies ICP is ready
    3. Generates AI campaign suggestions
    4. Creates campaigns (as drafts by default)
    5. Sources leads based on tier allowance (or injects demo fixture if demo_mode)
    6. Assigns leads to campaigns based on allocation %
    7. Promotes assigned lead_pool rows to leads table (Directive #184 Fix 1)

    Args:
        client_id: Client UUID (string or UUID)
        auto_create_campaigns: Create campaigns from suggestions (default True)
        auto_source_leads: Source leads (default True)
        auto_activate_campaigns: Activate campaigns immediately (default False)
        lead_count_override: Override tier-based lead count (optional)
        bypass_gates: Skip LinkedIn/CRM gate enforcement (Directive #184 Fix 2)
        demo_mode: Use fixture leads instead of real discovery (Directive #184 Fix 3)

    Returns:
        Dict with flow result

    Raises:
        LinkedInConnectionRequired: If LinkedIn is not connected (unless bypass_gates=True)
        CRMConnectionRequired: If CRM is not connected (unless bypass_gates=True)
    """
    from src.services.onboarding_gate_service import (
        CRMConnectionRequired,
        LinkedInConnectionRequired,
        enforce_onboarding_gates,
    )

    # Convert strings to UUIDs if needed (Prefect API passes strings)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    # Demo mode implies bypass_gates (no real integrations needed)
    if demo_mode:
        bypass_gates = True

    logger.info(
        f"Starting post-onboarding setup for client {client_id} "
        f"[bypass_gates={bypass_gates}, demo_mode={demo_mode}]"
    )

    try:
        # Step 0: GATE CHECK — LinkedIn and CRM connections
        # Directive #184 Fix 2: bypass_gates=True skips hard enforcement
        async with get_db_session() as db:
            if bypass_gates:
                logger.warning(
                    f"[post_onboarding] Gates bypassed for client {client_id} — "
                    f"domain-only mode (connect LinkedIn/CRM for better results)"
                )
            else:
                try:
                    await enforce_onboarding_gates(db, client_id)
                    logger.info(f"Onboarding gates passed for client {client_id}")
                except LinkedInConnectionRequired as e:
                    logger.error(f"Post-onboarding blocked: {e.message}")
                    return {
                        "success": False,
                        "client_id": str(client_id),
                        "error": e.message,
                        "error_code": "LINKEDIN_CONNECTION_REQUIRED",
                        "gate": "linkedin",
                    }
                except CRMConnectionRequired as e:
                    logger.error(f"Post-onboarding blocked: {e.message}")
                    return {
                        "success": False,
                        "client_id": str(client_id),
                        "error": e.message,
                        "error_code": "CRM_CONNECTION_REQUIRED",
                        "gate": "crm",
                    }

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

        # Step 5: Source leads
        # Directive #184 Fix 3: demo_mode injects fixture leads, skips real discovery
        leads_sourced = 0
        sourcing_cost = 0.0
        demo_leads_injected = 0

        if demo_mode and campaigns_created:
            # Inject demo fixture leads directly into lead_pool for each campaign
            logger.info(f"[demo_mode] Injecting fixture leads for client {client_id}")
            for campaign in campaigns_created:
                campaign_id = UUID(campaign["campaign_id"])
                injected = await inject_demo_leads(client_id, campaign_id)
                demo_leads_injected += injected
            leads_sourced = demo_leads_injected
            logger.info(f"[demo_mode] Injected {demo_leads_injected} fixture leads total")
        elif auto_source_leads:
            source_result = await source_leads_task(
                client_id=client_id,
                icp_criteria=icp,
                lead_count=lead_count,
            )

            if source_result["success"]:
                leads_sourced = source_result.get("leads_added", 0)
                sourcing_cost = source_result.get("total_cost_aud", 0.0)

        # Step 6: Assign leads to campaigns (skip in demo_mode — already assigned in inject)
        assignments = []
        if not demo_mode and campaigns_created and leads_sourced > 0:
            assign_result = await assign_leads_to_campaigns_task(
                client_id=client_id,
                campaigns=campaigns_created,
                total_leads=leads_sourced,
            )

            if assign_result["success"]:
                assignments = assign_result.get("assignments", [])

        # Step 7: Promote lead_pool → leads (Directive #184 Fix 1)
        # Run regardless of demo_mode — pool leads need to be in leads table for dashboard
        promotion_result = await promote_pool_leads_to_leads_task(client_id=client_id)
        leads_promoted = promotion_result.get("promoted", 0)

        if promotion_result.get("errors"):
            logger.warning(
                f"Promotion had {len(promotion_result['errors'])} errors for client {client_id}"
            )

        # Step 8: Update onboarding status
        await update_onboarding_status_task(
            client_id=client_id,
            status="completed",
        )

        logger.info(
            f"Post-onboarding setup completed for client {client_id}: "
            f"{len(campaigns_created)} campaigns, {leads_sourced} leads sourced, "
            f"{leads_promoted} promoted to dashboard"
        )

        return {
            "success": True,
            "client_id": str(client_id),
            "tier": tier,
            "campaigns_suggested": len(suggestions),
            "campaigns_created": len(campaigns_created),
            "campaigns": campaigns_created,
            "leads_sourced": leads_sourced,
            "leads_assigned": sum(a["leads_assigned"] for a in assignments) if assignments else leads_sourced,
            "leads_promoted": leads_promoted,
            "assignments": assignments,
            "sourcing_cost_aud": sourcing_cost,
            "demo_mode": demo_mode,
            "bypass_gates": bypass_gates,
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
    source_result = await source_leads_task(
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

            assignments.append(
                {
                    "campaign_id": str(campaign_id),
                    "leads_assigned": len(assigned),
                }
            )

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
# [x] Promotes lead_pool → leads (Directive #184 Fix 1)
# [x] bypass_gates param (Directive #184 Fix 2)
# [x] demo_mode param (Directive #184 Fix 3)
# [x] Updates onboarding status
# [x] Error handling with proper logging
# [x] Deployment function for Prefect registration
# [x] Type hints on all functions
# [x] Docstrings on all functions
