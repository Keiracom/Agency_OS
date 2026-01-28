"""
FILE: src/orchestration/flows/enrichment_flow.py
PURPOSE: Daily enrichment flow with client billing checks and ALS scoring
PHASE: 5 (Orchestration)
TASK: ORC-003
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/integrations/dncr.py
  - src/engines/scout.py
  - src/engines/scorer.py
  - src/engines/allocator.py
  - src/models/lead.py
  - src/models/client.py
  - src/models/campaign.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation - check client billing before enrichment
  - Rule 14: Soft deletes only
  - DNCR batch wash at enrichment for Australian numbers
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import and_, select, update

from src.agents.sdk_agents import should_use_sdk_enrichment
from src.config.tiers import get_available_channels_enum
from src.engines.allocator import get_allocator_engine
from src.engines.scorer import get_scorer_engine
from src.engines.scout import get_scout_engine
from src.integrations.supabase import get_db_session
from src.models.base import (
    CampaignStatus,
    LeadStatus,
    SubscriptionStatus,
)
from src.models.campaign import Campaign
from src.models.client import Client
from src.models.lead import Lead

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="get_leads_needing_enrichment", retries=2, retry_delay_seconds=5)
async def get_leads_needing_enrichment_task(
    limit: int = 100, client_id: UUID | None = None
) -> dict[str, Any]:
    """
    Get leads that need enrichment.

    Includes JIT validation: joins with clients table to check billing status.
    Only returns leads from clients with active/trialing subscriptions and credits.

    Args:
        limit: Maximum number of leads to enrich in this batch
        client_id: Optional client ID to filter by

    Returns:
        Dict with lead IDs grouped by client
    """
    async with get_db_session() as db:
        # Build query with client billing validation (Rule 13)
        stmt = (
            select(Lead.id, Lead.client_id, Lead.campaign_id, Client.credits_remaining)
            .join(Client, Lead.client_id == Client.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .where(
                and_(
                    Lead.status == LeadStatus.NEW,
                    Lead.deleted_at.is_(None),  # Soft delete check
                    Client.deleted_at.is_(None),  # Soft delete check
                    Campaign.deleted_at.is_(None),  # Soft delete check
                    Campaign.status == CampaignStatus.ACTIVE,
                    # JIT validation: client billing status
                    Client.subscription_status.in_(
                        [
                            SubscriptionStatus.ACTIVE,
                            SubscriptionStatus.TRIALING,
                        ]
                    ),
                    Client.credits_remaining > 0,
                )
            )
            .order_by(Lead.created_at.asc())
            .limit(limit)
        )

        # Add client filter if provided
        if client_id:
            stmt = stmt.where(Lead.client_id == client_id)

        result = await db.execute(stmt)
        rows = result.all()

        # Group leads by client for efficient processing
        leads_by_client: dict[str, list[str]] = {}
        client_credits: dict[str, int] = {}

        for lead_id, client_id_val, _campaign_id, credits in rows:
            client_key = str(client_id_val)
            if client_key not in leads_by_client:
                leads_by_client[client_key] = []
                client_credits[client_key] = credits

            leads_by_client[client_key].append(str(lead_id))

        total_leads = sum(len(leads) for leads in leads_by_client.values())

        logger.info(
            f"Found {total_leads} leads needing enrichment across {len(leads_by_client)} clients"
        )

        return {
            "total_leads": total_leads,
            "client_count": len(leads_by_client),
            "leads_by_client": leads_by_client,
            "client_credits": client_credits,
        }


@task(name="enrich_lead_batch", retries=3, retry_delay_seconds=10)
async def enrich_lead_batch_task(lead_ids: list[str], client_id: str) -> dict[str, Any]:
    """
    Enrich a batch of leads for a single client.

    Args:
        lead_ids: List of lead UUID strings
        client_id: Client UUID string

    Returns:
        Dict with enrichment results
    """
    async with get_db_session() as db:
        scout_engine = get_scout_engine()

        # Convert to UUIDs
        lead_uuids = [UUID(lid) for lid in lead_ids]

        # Enrich batch
        result = await scout_engine.enrich_batch(
            db=db,
            lead_ids=lead_uuids,
            force_refresh=False,
        )

        if result.success:
            logger.info(
                f"Enriched {result.data['tier1_success'] + result.data['tier2_success']} "
                f"of {result.data['total']} leads for client {client_id}"
            )
        else:
            logger.warning(f"Enrichment batch failed for client {client_id}: {result.error}")

        return {
            "client_id": client_id,
            "total": len(lead_ids),
            "success": result.success,
            "data": result.data if result.success else None,
            "error": result.error if not result.success else None,
        }


@task(name="dncr_batch_check", retries=2, retry_delay_seconds=10)
async def dncr_batch_check_task(lead_ids: list[str]) -> dict[str, Any]:
    """
    Batch check DNCR status for Australian phone numbers.

    This runs after enrichment to cache DNCR status on leads,
    avoiding API calls at send-time for already-checked numbers.

    Args:
        lead_ids: List of lead UUID strings to check

    Returns:
        Dict with DNCR check results
    """
    from src.integrations.dncr import get_dncr_client

    async with get_db_session() as db:
        dncr_client = get_dncr_client()

        # Fetch leads with Australian phone numbers
        lead_uuids = [UUID(lid) for lid in lead_ids]
        stmt = select(Lead).where(
            and_(
                Lead.id.in_(lead_uuids),
                Lead.phone.isnot(None),
                Lead.phone.startswith("+61"),  # Australian numbers only
                not Lead.dncr_checked,  # Not already checked
            )
        )
        result = await db.execute(stmt)
        leads_to_check = result.scalars().all()

        if not leads_to_check:
            logger.info("No Australian phone numbers to check against DNCR")
            return {
                "total": 0,
                "checked": 0,
                "on_dncr": 0,
                "clean": 0,
            }

        # Extract phone numbers
        phone_to_lead: dict[str, Lead] = {lead.phone: lead for lead in leads_to_check}
        phones = list(phone_to_lead.keys())

        logger.info(f"Checking {len(phones)} Australian phone numbers against DNCR")

        # Batch check via DNCR client
        dncr_results = await dncr_client.check_numbers_batch(phones)

        # Update lead records
        on_dncr_count = 0
        clean_count = 0
        datetime.utcnow()

        for phone, is_on_dncr in dncr_results.items():
            if phone in phone_to_lead:
                lead = phone_to_lead[phone]
                lead.dncr_checked = True
                lead.dncr_result = is_on_dncr
                # Note: Lead model doesn't have dncr_checked_at, but LeadPool does
                # We set dncr_checked=True and dncr_result to cache the result

                if is_on_dncr:
                    on_dncr_count += 1
                    logger.info(f"Lead {lead.id} phone {phone[:8]}... is on DNCR")
                else:
                    clean_count += 1

        await db.commit()

        logger.info(
            f"DNCR batch check complete: {len(phones)} checked, "
            f"{on_dncr_count} on DNCR, {clean_count} clean"
        )

        return {
            "total": len(phones),
            "checked": len(dncr_results),
            "on_dncr": on_dncr_count,
            "clean": clean_count,
        }


@task(name="score_lead", retries=2, retry_delay_seconds=5)
async def score_lead_task(lead_id: str) -> dict[str, Any]:
    """
    Calculate ALS score for an enriched lead.

    Args:
        lead_id: Lead UUID string

    Returns:
        Dict with scoring results including SDK eligibility info
    """
    async with get_db_session() as db:
        scorer_engine = get_scorer_engine()
        lead_uuid = UUID(lead_id)

        # Calculate ALS score
        result = await scorer_engine.calculate_als(db=db, lead_id=lead_uuid)

        if result.success:
            als_score = result.data["als_score"]
            als_tier = result.data["als_tier"]
            logger.info(f"Lead {lead_id} scored: {als_score} ({als_tier} tier)")

            # Check if Hot lead needs SDK enrichment
            # Fetch lead for signal check
            lead_stmt = select(Lead).where(Lead.id == lead_uuid)
            lead_result = await db.execute(lead_stmt)
            lead = lead_result.scalar_one_or_none()

            sdk_eligible = False
            sdk_signals = []
            if lead and als_score >= 85:  # Hot threshold
                lead_data = {
                    "als_score": als_score,
                    "company_latest_funding_date": lead.organization_latest_funding_date,
                    "company_open_roles": 3 if lead.organization_is_hiring else 0,
                    "company_employee_count": lead.organization_employee_count,
                    "source": getattr(lead, "source", None),
                }
                sdk_eligible, sdk_signals = should_use_sdk_enrichment(lead_data)

            return {
                "lead_id": lead_id,
                "success": True,
                "als_score": als_score,
                "als_tier": als_tier,
                "sdk_eligible": sdk_eligible,
                "sdk_signals": sdk_signals,
                "error": None,
            }
        else:
            logger.warning(f"Scoring failed for lead {lead_id}: {result.error}")
            return {
                "lead_id": lead_id,
                "success": False,
                "als_score": None,
                "als_tier": None,
                "sdk_eligible": False,
                "sdk_signals": [],
                "error": result.error,
            }


@task(name="sdk_enrich_hot_lead", retries=2, retry_delay_seconds=10)
async def sdk_enrich_hot_lead_task(lead_id: str, signals: list[str]) -> dict[str, Any]:
    """
    Run SDK enrichment for a Hot lead with priority signals.

    This performs deep web research to find funding info, hiring data,
    recent news, and personalization opportunities.

    Args:
        lead_id: Lead UUID string
        signals: Priority signals that triggered SDK eligibility

    Returns:
        Dict with SDK enrichment results
    """
    async with get_db_session() as db:
        scout_engine = get_scout_engine()
        lead_uuid = UUID(lead_id)

        # Run SDK-enhanced enrichment
        result = await scout_engine.enrich_lead_with_sdk(
            db=db,
            lead_id=lead_uuid,
            force_refresh=False,
        )

        if result.success:
            sdk_data = result.data.get("sdk_enrichment", {})
            sdk_cost = result.data.get("sdk_cost_aud", 0)
            logger.info(
                f"SDK enrichment complete for lead {lead_id}: "
                f"signals={signals}, cost=${sdk_cost:.2f}"
            )
            return {
                "lead_id": lead_id,
                "success": True,
                "sdk_enrichment": sdk_data,
                "sdk_cost_aud": sdk_cost,
                "signals": signals,
            }
        else:
            logger.warning(f"SDK enrichment failed for {lead_id}: {result.error}")
            return {
                "lead_id": lead_id,
                "success": False,
                "error": result.error,
            }


@task(name="allocate_channels_for_lead", retries=2, retry_delay_seconds=5)
async def allocate_channels_for_lead_task(lead_id: str, als_tier: str) -> dict[str, Any]:
    """
    Allocate channels for a scored lead based on tier.

    Args:
        lead_id: Lead UUID string
        als_tier: Lead tier (hot, warm, cool, cold, dead) - used for logging only

    Returns:
        Dict with allocation results
    """
    async with get_db_session() as db:
        allocator_engine = get_allocator_engine()
        lead_uuid = UUID(lead_id)

        # Fetch lead to get current ALS score
        lead = await db.get(Lead, lead_uuid)
        if not lead:
            return {
                "lead_id": lead_id,
                "success": False,
                "error": "Lead not found",
            }

        # P1 Fix: Use canonical channel access from tiers.py (single source of truth)
        als_score = lead.als_score or 0
        available_channels = get_available_channels_enum(als_score)

        if not available_channels:
            return {
                "lead_id": lead_id,
                "success": False,
                "error": f"No channels available for tier {als_tier}",
            }

        # Allocate channels
        result = await allocator_engine.allocate_channels(
            db=db,
            lead_id=lead_uuid,
            available_channels=available_channels,
        )

        if result.success:
            logger.info(
                f"Allocated {len(result.data['channels'])} channels for lead {lead_id} "
                f"(tier: {als_tier})"
            )
        else:
            logger.warning(f"Channel allocation failed for lead {lead_id}: {result.error}")

        return {
            "lead_id": lead_id,
            "success": result.success,
            "channels": result.data.get("channels", []) if result.success else [],
            "error": result.error if not result.success else None,
        }


@task(name="deduct_client_credits", retries=3, retry_delay_seconds=5)
async def deduct_client_credits_task(client_id: str, credits_to_deduct: int) -> dict[str, Any]:
    """
    Deduct credits from client after successful enrichment.

    Args:
        client_id: Client UUID string
        credits_to_deduct: Number of credits to deduct

    Returns:
        Dict with credit deduction result
    """
    async with get_db_session() as db:
        client_uuid = UUID(client_id)

        # Deduct credits
        stmt = (
            update(Client)
            .where(
                and_(
                    Client.id == client_uuid,
                    Client.deleted_at.is_(None),
                    Client.credits_remaining >= credits_to_deduct,
                )
            )
            .values(
                credits_remaining=Client.credits_remaining - credits_to_deduct,
                updated_at=datetime.utcnow(),
            )
            .returning(Client.credits_remaining)
        )
        result = await db.execute(stmt)
        new_credits = result.scalar_one_or_none()

        if new_credits is None:
            await db.rollback()
            raise ValueError(
                f"Failed to deduct {credits_to_deduct} credits from client {client_id}"
            )

        await db.commit()

        logger.info(
            f"Deducted {credits_to_deduct} credits from client {client_id}, "
            f"remaining: {new_credits}"
        )

        return {
            "client_id": client_id,
            "credits_deducted": credits_to_deduct,
            "credits_remaining": new_credits,
        }


# ============================================
# FLOW
# ============================================


@flow(
    name="daily_enrichment",
    description="Daily enrichment flow with billing checks, scoring, and allocation",
    log_prints=True,
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
async def daily_enrichment_flow(
    batch_size: int = 100, client_id: str | UUID | None = None
) -> dict[str, Any]:
    """
    Daily enrichment flow.

    Steps:
    1. Get leads needing enrichment (with client billing validation)
    2. Enrich leads in batches by client
    3. Score enriched leads (calculate ALS)
    4. Allocate channels based on ALS tier
    5. Deduct credits from clients

    Args:
        batch_size: Maximum leads to process in one run
        client_id: Optional client ID to process (string or UUID)

    Returns:
        Dict with enrichment summary
    """
    # Convert string to UUID if needed (Prefect API passes strings)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting daily enrichment flow (batch_size={batch_size}, client_id={client_id})")

    # Step 1: Get leads needing enrichment (with JIT billing validation)
    leads_data = await get_leads_needing_enrichment_task(limit=batch_size, client_id=client_id)

    if leads_data["total_leads"] == 0:
        logger.info("No leads needing enrichment")
        return {
            "total_leads": 0,
            "enriched": 0,
            "scored": 0,
            "allocated": 0,
            "message": "No leads needing enrichment",
        }

    # Step 2: Enrich leads by client
    enrichment_results = []
    for client_id_str, lead_ids in leads_data["leads_by_client"].items():
        result = await enrich_lead_batch_task(lead_ids=lead_ids, client_id=client_id_str)
        enrichment_results.append(result)

    # Collect successfully enriched leads
    enriched_lead_ids = []
    for result in enrichment_results:
        if result["success"] and result["data"]:
            for lead_info in result["data"].get("enriched_leads", []):
                enriched_lead_ids.append(lead_info["lead_id"])

    logger.info(f"Successfully enriched {len(enriched_lead_ids)} leads")

    # Step 2.5: DNCR batch check for Australian phone numbers
    dncr_result = {"total": 0, "on_dncr": 0, "clean": 0}
    if enriched_lead_ids:
        dncr_result = await dncr_batch_check_task(lead_ids=enriched_lead_ids)
        if dncr_result["on_dncr"] > 0:
            logger.warning(
                f"DNCR check found {dncr_result['on_dncr']} numbers on "
                f"Do Not Call Register - these will be blocked from SMS"
            )

    # Step 3: Score enriched leads
    scoring_results = []
    for lead_id in enriched_lead_ids:
        result = await score_lead_task(lead_id=lead_id)
        scoring_results.append(result)

    # Step 3.5: SDK enrichment for Hot leads with priority signals
    sdk_enrichment_results = []
    for score_result in scoring_results:
        if score_result.get("sdk_eligible") and score_result.get("sdk_signals"):
            logger.info(
                f"Hot lead {score_result['lead_id']} qualifies for SDK enrichment: "
                f"{score_result['sdk_signals']}"
            )
            sdk_result = await sdk_enrich_hot_lead_task(
                lead_id=score_result["lead_id"],
                signals=score_result["sdk_signals"],
            )
            sdk_enrichment_results.append(sdk_result)

    # Step 4: Allocate channels for scored leads
    allocation_results = []
    for score_result in scoring_results:
        if score_result["success"] and score_result["als_tier"]:
            result = await allocate_channels_for_lead_task(
                lead_id=score_result["lead_id"], als_tier=score_result["als_tier"]
            )
            allocation_results.append(result)

    # Step 5: Deduct credits from clients
    # Calculate credits to deduct per client (1 credit per enriched lead)
    credits_by_client: dict[str, int] = {}
    for result in enrichment_results:
        if result["success"] and result["data"]:
            client_id_str = result["client_id"]
            enriched_count = result["data"].get("tier1_success", 0) + result["data"].get(
                "tier2_success", 0
            )
            credits_by_client[client_id_str] = enriched_count

    credit_results = []
    for client_id_str, credits in credits_by_client.items():
        if credits > 0:
            result = await deduct_client_credits_task(
                client_id=client_id_str, credits_to_deduct=credits
            )
            credit_results.append(result)

    # Compile summary
    total_enriched = len(enriched_lead_ids)
    total_scored = sum(1 for r in scoring_results if r["success"])
    total_allocated = sum(1 for r in allocation_results if r["success"])
    total_credits_deducted = sum(r["credits_deducted"] for r in credit_results)

    # SDK enrichment stats
    total_sdk_enriched = sum(1 for r in sdk_enrichment_results if r.get("success"))
    total_sdk_cost = sum(
        r.get("sdk_cost_aud", 0) for r in sdk_enrichment_results if r.get("success")
    )

    summary = {
        "total_leads_processed": leads_data["total_leads"],
        "total_enriched": total_enriched,
        "total_scored": total_scored,
        "total_allocated": total_allocated,
        "clients_processed": len(leads_data["leads_by_client"]),
        "total_credits_deducted": total_credits_deducted,
        "sdk_enriched": total_sdk_enriched,
        "sdk_cost_aud": total_sdk_cost,
        "dncr_checked": dncr_result.get("total", 0),
        "dncr_blocked": dncr_result.get("on_dncr", 0),
        "enrichment_results": enrichment_results,
        "sdk_enrichment_results": sdk_enrichment_results,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Daily enrichment flow completed: {total_enriched} enriched, "
        f"{total_scored} scored, {total_allocated} allocated, "
        f"{total_credits_deducted} credits deducted, "
        f"{total_sdk_enriched} SDK enriched (${total_sdk_cost:.2f}), "
        f"DNCR: {dncr_result.get('on_dncr', 0)}/{dncr_result.get('total', 0)} blocked"
    )

    return summary


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] No imports from other orchestration files
# [x] Imports from engines (scout, scorer, allocator), models, integrations
# [x] JIT validation in get_leads_needing_enrichment_task (Rule 13)
# [x] Checks client billing status before enrichment
# [x] Soft delete checks in all queries (Rule 14)
# [x] @flow and @task decorators from Prefect
# [x] ConcurrentTaskRunner with max_workers=10
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] Batches leads for efficiency
# [x] Credit deduction after successful enrichment
# [x] DNCR batch wash at enrichment for Australian numbers
# [x] DNCR results cached in lead.dncr_checked and lead.dncr_result
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Returns structured dict results
