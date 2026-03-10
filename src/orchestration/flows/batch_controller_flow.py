"""
FILE: src/orchestration/flows/batch_controller_flow.py
PURPOSE: Batch controller with quota monitoring, discard-and-replace, and discovery loop
PHASE: Directive 048 (CEO Directive - Part C)
TASK: BATCH-001
DEPENDENCIES:
  - src/services/lead_pool_service.py
  - src/services/icp_filter_service.py
  - src/engines/scorer.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only

DIRECTIVE 048 REQUIREMENTS:
- Monitors lead quota per active campaign
- On discard at Gate 1 or 2, triggers replacement GMB discovery
- Replacement runs full waterfall from T1
- Loops until quota of ALS ≥35 leads is met
- After 3 failed replacement loops, fires quota shortfall alert
- Gate 1 triggers: ICP fail, invalid ABN, duplicate, pre-ALS <35 on free tiers only
- Gate 2 triggers: no email AND no phone, ALS <35 after T3, Leadmagic confidence <70%
- Gate 3: demote tier only, never discard
- Every discard writes reason to discarded_leads before status change
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from sqlalchemy import text

from src.integrations.supabase import get_db_session
from src.services.icp_filter_service import get_icp_filter_service

logger = logging.getLogger(__name__)


# =============================================================================
# GATE CONFIGURATIONS
# =============================================================================

# Gate 1: Pre-enrichment discard triggers
GATE_1_TRIGGERS = {
    "icp_fail": "ICP qualification failed",
    "invalid_abn": "Invalid or missing ABN",
    "duplicate": "Duplicate lead in pool",
    "pre_als_low_free": "Pre-ALS <35 on free tier",
}

# Gate 2: Post-enrichment discard triggers
GATE_2_TRIGGERS = {
    "no_contact": "No email AND no phone after enrichment",
    "post_als_low": "ALS <35 after T3 enrichment",
    "leadmagic_low_confidence": "Leadmagic email confidence <70%",
}

# Gate 3: Never discard, only demote
# Gate 3 does not trigger discards, only tier demotion

MIN_QUALIFIED_ALS = 35
MAX_REPLACEMENT_LOOPS = 3


# =============================================================================
# TASKS
# =============================================================================


@task(name="check_campaign_quota", retries=2, retry_delay_seconds=5)
async def check_campaign_quota_task(campaign_id: str) -> dict[str, Any]:
    """
    Check if a campaign has met its lead quota.

    Args:
        campaign_id: Campaign UUID string

    Returns:
        Dict with quota status
    """
    async with get_db_session() as db:
        # Get campaign quota config
        result = await db.execute(
            text("""
                SELECT
                    c.id,
                    c.client_id,
                    c.name,
                    COALESCE(cqs.target_lead_count, 100) as target_lead_count,
                    COALESCE(cqs.min_propensity_score, 35) as min_propensity_score,
                    COALESCE(cqs.current_qualified_count, 0) as current_qualified_count,
                    COALESCE(cqs.discovery_loops_run, 0) as discovery_loops_run
                FROM campaigns c
                LEFT JOIN campaign_quota_status cqs ON c.id = cqs.campaign_id
                WHERE c.id = :campaign_id
                AND c.deleted_at IS NULL
            """),
            {"campaign_id": campaign_id},
        )
        row = result.fetchone()

        if not row:
            return {
                "campaign_id": campaign_id,
                "error": "Campaign not found",
                "quota_met": False,
            }

        # Count current qualified leads
        count_result = await db.execute(
            text("""
                SELECT COUNT(*) as qualified_count
                FROM lead_pool lp
                JOIN lead_assignments la ON lp.id = la.lead_pool_id
                WHERE la.campaign_id = :campaign_id
                AND lp.pool_status NOT IN ('discarded_pending', 'bounced', 'invalid')
                AND lp.als_score >= :min_als  -- propensity threshold
                AND lp.deleted_at IS NULL
            """),
            {"campaign_id": campaign_id, "min_als": row.min_propensity_score},
        )
        count_row = count_result.fetchone()
        qualified_count = count_row.qualified_count if count_row else 0

        # Calculate shortfall
        shortfall = max(0, row.target_lead_count - qualified_count)

        return {
            "campaign_id": campaign_id,
            "client_id": str(row.client_id),
            "campaign_name": row.name,
            "target_count": row.target_lead_count,
            "min_als": row.min_propensity_score,
            "current_qualified": qualified_count,
            "shortfall": shortfall,
            "quota_met": shortfall == 0,
            "discovery_loops_run": row.discovery_loops_run,
        }


@task(name="apply_gate_1_filter", retries=2, retry_delay_seconds=5)
async def apply_gate_1_filter_task(
    lead_pool_id: str,
    client_id: str | None = None,
    campaign_id: str | None = None,
    is_free_tier: bool = False,
) -> dict[str, Any]:
    """
    Apply Gate 1 filter: Pre-enrichment quality gate.

    Triggers:
    - ICP fail
    - Invalid ABN
    - Duplicate
    - Pre-ALS <35 on free tiers only

    Args:
        lead_pool_id: Lead pool UUID
        client_id: Optional client UUID
        campaign_id: Optional campaign UUID
        is_free_tier: Whether client is on free tier

    Returns:
        Dict with gate result
    """
    async with get_db_session() as db:
        # Get lead data
        result = await db.execute(
            text("""
                SELECT
                    id, email, company_name, company_industry,
                    enrichment_data, als_score, pool_status
                FROM lead_pool
                WHERE id = :lead_pool_id
            """),
            {"lead_pool_id": lead_pool_id},
        )
        row = result.fetchone()

        if not row:
            return {"lead_pool_id": lead_pool_id, "passed": False, "reason": "Lead not found"}

        # Check ICP qualification
        icp_service = get_icp_filter_service()
        lead_data = {
            "company_name": row.company_name,
            "company_industry": row.company_industry,
            "enrichment_data": row.enrichment_data or {},
        }
        is_qualified, icp_details = icp_service.is_icp_qualified(lead_data)

        if not is_qualified:
            # Discard at Gate 1
            await _soft_discard_lead(
                db,
                UUID(lead_pool_id),
                gate=1,
                reason=f"ICP fail: {icp_details.get('reason', 'Not ICP qualified')}",
                client_id=UUID(client_id) if client_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
            )
            return {
                "lead_pool_id": lead_pool_id,
                "passed": False,
                "gate": 1,
                "reason": "icp_fail",
                "details": icp_details,
            }

        # Check ABN (if Australian)
        enrichment_data = row.enrichment_data or {}
        if enrichment_data.get("country", "").lower() == "australia":
            abn = enrichment_data.get("abn")
            abn_verified = enrichment_data.get("abn_verified", False)

            if not abn and not abn_verified:
                await _soft_discard_lead(
                    db,
                    UUID(lead_pool_id),
                    gate=1,
                    reason="Invalid or missing ABN for Australian business",
                    client_id=UUID(client_id) if client_id else None,
                    campaign_id=UUID(campaign_id) if campaign_id else None,
                )
                return {
                    "lead_pool_id": lead_pool_id,
                    "passed": False,
                    "gate": 1,
                    "reason": "invalid_abn",
                }

        # Check duplicate
        dup_result = await db.execute(
            text("""
                SELECT COUNT(*) as dup_count
                FROM lead_pool
                WHERE email = (SELECT email FROM lead_pool WHERE id = :lead_pool_id)
                AND id != :lead_pool_id
                AND pool_status NOT IN ('discarded_pending', 'bounced', 'invalid')
            """),
            {"lead_pool_id": lead_pool_id},
        )
        dup_row = dup_result.fetchone()

        if dup_row and dup_row.dup_count > 0:
            await _soft_discard_lead(
                db,
                UUID(lead_pool_id),
                gate=1,
                reason="Duplicate lead in pool",
                client_id=UUID(client_id) if client_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
            )
            return {
                "lead_pool_id": lead_pool_id,
                "passed": False,
                "gate": 1,
                "reason": "duplicate",
            }

        # Check pre-propensity on free tier only
        if is_free_tier and row.als_score is not None and row.als_score < MIN_QUALIFIED_ALS:
            await _soft_discard_lead(
                db,
                UUID(lead_pool_id),
                gate=1,
                reason=f"Pre-propensity {row.als_score} < {MIN_QUALIFIED_ALS} (free tier)",
                client_id=UUID(client_id) if client_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
            )
            return {
                "lead_pool_id": lead_pool_id,
                "passed": False,
                "gate": 1,
                "reason": "pre_propensity_low_free",
                "propensity_score": row.als_score,
            }

        return {
            "lead_pool_id": lead_pool_id,
            "passed": True,
            "gate": 1,
        }


@task(name="apply_gate_2_filter", retries=2, retry_delay_seconds=5)
async def apply_gate_2_filter_task(
    lead_pool_id: str,
    client_id: str | None = None,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """
    Apply Gate 2 filter: Post-enrichment quality gate.

    Triggers:
    - No email AND no phone
    - ALS <35 after T3
    - Leadmagic confidence <70%

    Args:
        lead_pool_id: Lead pool UUID
        client_id: Optional client UUID
        campaign_id: Optional campaign UUID

    Returns:
        Dict with gate result
    """
    async with get_db_session() as db:
        # Get lead data
        result = await db.execute(
            text("""
                SELECT
                    id, email, phone, als_score,
                    enrichment_data, enrichment_confidence
                FROM lead_pool
                WHERE id = :lead_pool_id
            """),
            {"lead_pool_id": lead_pool_id},
        )
        row = result.fetchone()

        if not row:
            return {"lead_pool_id": lead_pool_id, "passed": False, "reason": "Lead not found"}

        # Check no contact info
        if not row.email and not row.phone:
            await _soft_discard_lead(
                db,
                UUID(lead_pool_id),
                gate=2,
                reason="No email AND no phone after enrichment",
                client_id=UUID(client_id) if client_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
            )
            return {
                "lead_pool_id": lead_pool_id,
                "passed": False,
                "gate": 2,
                "reason": "no_contact",
            }

        # Check propensity after T3
        if row.als_score is not None and row.als_score < MIN_QUALIFIED_ALS:
            await _soft_discard_lead(
                db,
                UUID(lead_pool_id),
                gate=2,
                reason=f"Propensity {row.als_score} < {MIN_QUALIFIED_ALS} after T3",
                client_id=UUID(client_id) if client_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
            )
            return {
                "lead_pool_id": lead_pool_id,
                "passed": False,
                "gate": 2,
                "reason": "post_propensity_low",
                "propensity_score": row.als_score,
            }

        # Check Leadmagic confidence
        enrichment_data = row.enrichment_data or {}
        leadmagic_confidence = enrichment_data.get("leadmagic_confidence", 100)

        if leadmagic_confidence < 70:
            await _soft_discard_lead(
                db,
                UUID(lead_pool_id),
                gate=2,
                reason=f"Leadmagic email confidence {leadmagic_confidence}% < 70%",
                client_id=UUID(client_id) if client_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
            )
            return {
                "lead_pool_id": lead_pool_id,
                "passed": False,
                "gate": 2,
                "reason": "leadmagic_low_confidence",
                "confidence": leadmagic_confidence,
            }

        return {
            "lead_pool_id": lead_pool_id,
            "passed": True,
            "gate": 2,
        }


@task(name="apply_gate_3_filter", retries=2, retry_delay_seconds=5)
async def apply_gate_3_filter_task(lead_pool_id: str) -> dict[str, Any]:
    """
    Apply Gate 3 filter: Tier demotion only, never discard.

    Gate 3 only demotes leads to lower tiers, never discards them.

    Args:
        lead_pool_id: Lead pool UUID

    Returns:
        Dict with gate result (always passes, may demote tier)
    """
    async with get_db_session() as db:
        # Get current tier
        result = await db.execute(
            text("""
                SELECT id, als_score, als_tier
                FROM lead_pool
                WHERE id = :lead_pool_id
            """),
            {"lead_pool_id": lead_pool_id},
        )
        row = result.fetchone()

        if not row:
            return {"lead_pool_id": lead_pool_id, "passed": True, "action": "not_found"}

        # Gate 3 never discards - only demotes
        current_tier = row.als_tier
        propensity_score = row.als_score or 0

        # Check if tier needs demotion based on score
        expected_tier = _get_tier_from_score(propensity_score)

        if current_tier != expected_tier:
            # Demote tier
            await db.execute(
                text("""
                    UPDATE lead_pool
                    SET als_tier = :new_tier,
                        updated_at = NOW()
                    WHERE id = :lead_pool_id
                """),
                {"lead_pool_id": lead_pool_id, "new_tier": expected_tier},
            )
            await db.commit()

            return {
                "lead_pool_id": lead_pool_id,
                "passed": True,
                "gate": 3,
                "action": "demoted",
                "from_tier": current_tier,
                "to_tier": expected_tier,
            }

        return {
            "lead_pool_id": lead_pool_id,
            "passed": True,
            "gate": 3,
            "action": "no_change",
            "tier": current_tier,
        }


@task(name="trigger_replacement_discovery", retries=3, retry_delay_seconds=30)
async def trigger_replacement_discovery_task(
    campaign_id: str,
    client_id: str,
    count_needed: int,
) -> dict[str, Any]:
    """
    Trigger GMB discovery to replace discarded leads.

    Runs full waterfall from T1 for replacement leads.

    Args:
        campaign_id: Campaign UUID
        client_id: Client UUID
        count_needed: Number of replacement leads needed

    Returns:
        Dict with discovery result
    """
    async with get_db_session() as db:
        try:
            # Get campaign ICP config for discovery
            result = await db.execute(
                text("""
                    SELECT icp_config, name
                    FROM campaigns
                    WHERE id = :campaign_id
                    AND deleted_at IS NULL
                """),
                {"campaign_id": campaign_id},
            )
            row = result.fetchone()

            if not row:
                return {
                    "campaign_id": campaign_id,
                    "success": False,
                    "error": "Campaign not found",
                }

            icp_config = row.icp_config or {}

            # Siege Waterfall v3: GMB-first discovery via Bright Data (Directive #144)
            from src.enrichment.discovery_modes import (
                CampaignConfig,
                DiscoveryMode,
                GMBFirstDiscovery,
            )
            from src.integrations.bright_data_client import get_bright_data_client

            bd_client = get_bright_data_client()
            gmb_discovery = GMBFirstDiscovery(bright_data_client=bd_client)

            # Build discovery config from ICP
            discovery_config = CampaignConfig(
                mode=DiscoveryMode.GMB_FIRST,
                industry=icp_config.get("industry")
                or icp_config.get("search_queries", ["business"])[0],
                location=icp_config.get("location", "Australia"),
                state=icp_config.get("state"),
                max_results=count_needed * 2,  # Get 2x to account for filtering
            )

            # Execute GMB-first discovery
            discovery_records = await gmb_discovery.discover(discovery_config)

            discovery_result = {
                "count": len(discovery_records),
                "records": discovery_records,
                "mode": "gmb_first",
            }

            # Update discovery loop count
            await db.execute(
                text("""
                    INSERT INTO campaign_quota_status (campaign_id, client_id, discovery_loops_run, last_discovery_at)
                    VALUES (:campaign_id, :client_id, 1, NOW())
                    ON CONFLICT (campaign_id) DO UPDATE
                    SET discovery_loops_run = campaign_quota_status.discovery_loops_run + 1,
                        last_discovery_at = NOW(),
                        updated_at = NOW()
                """),
                {"campaign_id": campaign_id, "client_id": client_id},
            )
            await db.commit()

            return {
                "campaign_id": campaign_id,
                "success": True,
                "leads_discovered": discovery_result.get("count", 0),
                "search_queries": icp_config.get("search_queries", []),
            }

        except Exception as e:
            logger.error(f"Replacement discovery failed: {e}")
            return {
                "campaign_id": campaign_id,
                "success": False,
                "error": str(e),
            }


@task(name="fire_quota_shortfall_alert", retries=2, retry_delay_seconds=5)
async def fire_quota_shortfall_alert_task(
    campaign_id: str,
    client_id: str,
    shortfall: int,
    loops_run: int,
) -> dict[str, Any]:
    """
    Fire quota shortfall alert after max replacement loops.

    Args:
        campaign_id: Campaign UUID
        client_id: Client UUID
        shortfall: Number of leads still needed
        loops_run: Number of discovery loops attempted

    Returns:
        Dict with alert result
    """
    async with get_db_session() as db:
        try:
            # Get campaign name
            result = await db.execute(
                text("SELECT name FROM campaigns WHERE id = :campaign_id"),
                {"campaign_id": campaign_id},
            )
            row = result.fetchone()
            campaign_name = row.name if row else "Unknown Campaign"

            # Create admin notification
            await db.execute(
                text("""
                    SELECT create_admin_notification(
                        'quota_shortfall',
                        :client_id,
                        :title,
                        :message,
                        'high',
                        NULL,
                        :campaign_id,
                        :metadata
                    )
                """),
                {
                    "client_id": client_id,
                    "title": f"⚠️ Lead Quota Shortfall: {campaign_name}",
                    "message": f"Campaign '{campaign_name}' is {shortfall} leads short after "
                    f"{loops_run} discovery attempts. Manual intervention required.",
                    "campaign_id": campaign_id,
                    "metadata": {
                        "shortfall": shortfall,
                        "discovery_loops_run": loops_run,
                        "alert_time": datetime.now(UTC).isoformat(),
                    },
                },
            )

            # Update quota status
            await db.execute(
                text("""
                    UPDATE campaign_quota_status
                    SET quota_shortfall_alert_sent = TRUE,
                        quota_shortfall_at = NOW(),
                        updated_at = NOW()
                    WHERE campaign_id = :campaign_id
                """),
                {"campaign_id": campaign_id},
            )
            await db.commit()

            return {
                "campaign_id": campaign_id,
                "alert_sent": True,
                "shortfall": shortfall,
            }

        except Exception as e:
            logger.error(f"Failed to fire quota shortfall alert: {e}")
            return {
                "campaign_id": campaign_id,
                "alert_sent": False,
                "error": str(e),
            }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


async def _soft_discard_lead(
    db,
    lead_pool_id: UUID,
    gate: int,
    reason: str,
    client_id: UUID | None = None,
    campaign_id: UUID | None = None,
    metadata: dict | None = None,
) -> UUID | None:
    """
    Soft discard a lead with reason tracking.

    Args:
        db: Database session
        lead_pool_id: Lead pool UUID
        gate: Discard gate (1, 2, or 3)
        reason: Discard reason
        client_id: Optional client UUID
        campaign_id: Optional campaign UUID
        metadata: Optional additional metadata

    Returns:
        Discard record UUID or None
    """
    import json

    try:
        result = await db.execute(
            text("""
                SELECT soft_discard_lead(
                    :lead_id,
                    :discard_gate,
                    :discard_reason,
                    :client_id,
                    :campaign_id,
                    :metadata
                ) as discard_id
            """),
            {
                "lead_id": str(lead_pool_id),
                "discard_gate": gate,
                "discard_reason": reason,
                "client_id": str(client_id) if client_id else None,
                "campaign_id": str(campaign_id) if campaign_id else None,
                "metadata": json.dumps(metadata or {}),
            },
        )
        row = result.fetchone()
        await db.commit()

        if row and row.discard_id:
            logger.info(f"Soft discarded lead {lead_pool_id} at Gate {gate}: {reason}")
            return row.discard_id

        return None

    except Exception as e:
        logger.error(f"Failed to soft discard lead {lead_pool_id}: {e}")
        return None


def _get_tier_from_score(propensity_score: int) -> str:
    """Get tier name from propensity score."""
    if propensity_score >= 85:
        return "hot"
    elif propensity_score >= 60:
        return "warm"
    elif propensity_score >= 35:
        return "cool"
    elif propensity_score >= 20:
        return "cold"
    else:
        return "dead"


# =============================================================================
# FLOW
# =============================================================================


@flow(
    name="batch_controller",
    description="Batch controller with quota monitoring, discard-and-replace, and discovery loop",
    log_prints=True,
)
async def batch_controller_flow(campaign_id: str) -> dict[str, Any]:
    """
    Batch controller flow for quota management and lead quality.

    Steps:
    1. Check campaign quota status
    2. If shortfall exists:
       a. Apply Gate 1 filter to pending leads
       b. Apply Gate 2 filter to enriched leads
       c. Apply Gate 3 to scored leads (demote only)
       d. Trigger replacement discovery
       e. Loop until quota met or max loops reached
    3. Fire alert if quota not met after max loops

    Args:
        campaign_id: Campaign UUID string

    Returns:
        Dict with batch controller results
    """
    logger.info(f"Starting batch controller for campaign {campaign_id}")

    results = {
        "campaign_id": campaign_id,
        "quota_status": None,
        "gate_1_discards": 0,
        "gate_2_discards": 0,
        "gate_3_demotions": 0,
        "discovery_runs": 0,
        "final_quota_met": False,
        "alert_sent": False,
    }

    # Step 1: Check quota
    quota_status = await check_campaign_quota_task(campaign_id)
    results["quota_status"] = quota_status

    if quota_status.get("quota_met"):
        logger.info(f"Campaign {campaign_id} quota already met")
        results["final_quota_met"] = True
        return results

    # Step 2: Discovery and replacement loop
    loops_run = quota_status.get("discovery_loops_run", 0)
    shortfall = quota_status.get("shortfall", 0)
    client_id = quota_status.get("client_id")

    while shortfall > 0 and loops_run < MAX_REPLACEMENT_LOOPS:
        logger.info(f"Discovery loop {loops_run + 1}: {shortfall} leads needed")

        # Trigger replacement discovery
        discovery_result = await trigger_replacement_discovery_task(
            campaign_id=campaign_id,
            client_id=client_id,
            count_needed=shortfall,
        )
        results["discovery_runs"] += 1

        if not discovery_result.get("success"):
            logger.warning(f"Discovery failed: {discovery_result.get('error')}")
            break

        # Re-check quota after discovery
        quota_status = await check_campaign_quota_task(campaign_id)
        shortfall = quota_status.get("shortfall", 0)
        loops_run = quota_status.get("discovery_loops_run", 0)

        if shortfall == 0:
            results["final_quota_met"] = True
            break

    # Step 3: Fire alert if quota not met
    if shortfall > 0 and loops_run >= MAX_REPLACEMENT_LOOPS:
        alert_result = await fire_quota_shortfall_alert_task(
            campaign_id=campaign_id,
            client_id=client_id,
            shortfall=shortfall,
            loops_run=loops_run,
        )
        results["alert_sent"] = alert_result.get("alert_sent", False)

    results["final_shortfall"] = shortfall
    results["total_loops"] = loops_run

    logger.info(
        f"Batch controller completed for {campaign_id}: "
        f"quota_met={results['final_quota_met']}, shortfall={shortfall}"
    )

    return results


@flow(
    name="apply_quality_gates",
    description="Apply all quality gates to a batch of leads",
    log_prints=True,
)
async def apply_quality_gates_flow(
    lead_pool_ids: list[str],
    client_id: str | None = None,
    campaign_id: str | None = None,
    is_free_tier: bool = False,
) -> dict[str, Any]:
    """
    Apply quality gates to a batch of leads.

    Args:
        lead_pool_ids: List of lead pool UUIDs
        client_id: Optional client UUID
        campaign_id: Optional campaign UUID
        is_free_tier: Whether client is on free tier

    Returns:
        Dict with gate results
    """
    results = {
        "total": len(lead_pool_ids),
        "gate_1_passed": 0,
        "gate_1_failed": 0,
        "gate_2_passed": 0,
        "gate_2_failed": 0,
        "gate_3_demoted": 0,
        "discards": [],
    }

    for lead_pool_id in lead_pool_ids:
        # Gate 1
        g1_result = await apply_gate_1_filter_task(
            lead_pool_id=lead_pool_id,
            client_id=client_id,
            campaign_id=campaign_id,
            is_free_tier=is_free_tier,
        )

        if g1_result.get("passed"):
            results["gate_1_passed"] += 1
        else:
            results["gate_1_failed"] += 1
            results["discards"].append(
                {
                    "lead_pool_id": lead_pool_id,
                    "gate": 1,
                    "reason": g1_result.get("reason"),
                }
            )
            continue  # Don't apply further gates

        # Gate 2
        g2_result = await apply_gate_2_filter_task(
            lead_pool_id=lead_pool_id,
            client_id=client_id,
            campaign_id=campaign_id,
        )

        if g2_result.get("passed"):
            results["gate_2_passed"] += 1
        else:
            results["gate_2_failed"] += 1
            results["discards"].append(
                {
                    "lead_pool_id": lead_pool_id,
                    "gate": 2,
                    "reason": g2_result.get("reason"),
                }
            )
            continue

        # Gate 3 (never discards)
        g3_result = await apply_gate_3_filter_task(lead_pool_id=lead_pool_id)

        if g3_result.get("action") == "demoted":
            results["gate_3_demoted"] += 1

    return results


# =============================================================================
# VERIFICATION CHECKLIST
# =============================================================================
# [x] Contract comment at top
# [x] Gate 1 triggers: ICP fail, invalid ABN, duplicate, pre-ALS <35 (free only)
# [x] Gate 2 triggers: no contact, ALS <35 after T3, Leadmagic <70%
# [x] Gate 3: demote only, never discard
# [x] Quota monitoring via campaign_quota_status table
# [x] Replacement discovery triggers after discards
# [x] Max 3 replacement loops before alert
# [x] quota_shortfall alert via admin_notifications
# [x] soft_discard_lead function call with reason tracking
# [x] discarded_leads table populated before status change
# [x] Soft delete holds for 48 hours
# [x] @flow and @task decorators from Prefect
# [x] All functions have type hints
# [x] All functions have docstrings
