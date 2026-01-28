"""
FILE: src/orchestration/flows/campaign_evolution_flow.py
PURPOSE: Orchestrate campaign evolution agents to generate suggestions
PHASE: Phase D - Item 18
TASK: Implement campaign evolution agents
DEPENDENCIES:
  - src/agents/campaign_evolution/*.py (analyzers + orchestrator)
  - src/models/campaign_suggestion.py
  - src/orchestration/flows/pattern_learning_flow.py (trigger source)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 14: Soft deletes only
  - Spec: docs/architecture/flows/MONTHLY_LIFECYCLE.md

CRITICAL: This flow generates SUGGESTIONS that require client approval.
Suggestions are NEVER auto-applied to campaigns.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from prefect import flow, task
from sqlalchemy import and_, select

from src.agents.campaign_evolution import (
    generate_campaign_suggestions,
    run_how_analyzer,
    run_what_analyzer,
    run_who_analyzer,
)
from src.agents.campaign_evolution.campaign_orchestrator_agent import (
    validate_suggestion_for_storage,
)
from src.integrations.supabase import get_db_session
from src.models.base import CampaignStatus, SubscriptionStatus
from src.models.campaign import Campaign
from src.models.campaign_suggestion import (
    CampaignSuggestion,
    SuggestionStatus,
)
from src.models.client import Client

logger = logging.getLogger(__name__)


# ============================================
# CONFIGURATION
# ============================================

# Minimum requirements for campaign evolution
MIN_CONVERSIONS_FOR_EVOLUTION = 20
MIN_ACTIVE_MONTHS = 2
MIN_PATTERN_CONFIDENCE = 0.5

# Cost limits (AUD)
MAX_EVOLUTION_COST_PER_CLIENT = 5.00  # ~$1.25 per analyzer + orchestrator


# ============================================
# TASKS
# ============================================


@task(name="check_evolution_eligibility", retries=2, retry_delay_seconds=5)
async def check_evolution_eligibility_task(client_id: UUID) -> dict[str, Any]:
    """
    Check if a client is eligible for campaign evolution.

    Requirements:
    - Active subscription
    - At least 2 months of data
    - At least 20 conversions
    - Has valid CIS patterns

    Args:
        client_id: Client UUID

    Returns:
        Dict with eligibility status and details
    """
    async with get_db_session() as db:
        client = await db.get(Client, client_id)
        if not client:
            return {"eligible": False, "reason": "Client not found"}

        # Check subscription status
        if client.subscription_status not in [
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
        ]:
            return {
                "eligible": False,
                "reason": f"Subscription status: {client.subscription_status}",
            }

        # Check account age (need 2+ months of data)
        if client.created_at:
            account_age_days = (datetime.utcnow() - client.created_at).days
            if account_age_days < 60:
                return {
                    "eligible": False,
                    "reason": f"Account age: {account_age_days} days (need 60+)",
                }

        # Check for valid CIS patterns
        from src.models.conversion_patterns import ConversionPattern

        pattern_result = await db.execute(
            select(ConversionPattern)
            .where(
                and_(
                    ConversionPattern.client_id == client_id,
                    ConversionPattern.valid_until > datetime.utcnow(),
                    ConversionPattern.confidence >= MIN_PATTERN_CONFIDENCE,
                )
            )
        )
        patterns = pattern_result.scalars().all()

        # Get conversion count from pattern sample sizes (computed during pattern learning)
        conversion_count = max((p.sample_size or 0 for p in patterns), default=0)
        if conversion_count < MIN_CONVERSIONS_FOR_EVOLUTION:
            return {
                "eligible": False,
                "reason": f"Conversions: {conversion_count} (need {MIN_CONVERSIONS_FOR_EVOLUTION}+)",
            }

        pattern_types = {p.pattern_type for p in patterns}
        required_patterns = {"who", "what", "how"}
        missing_patterns = required_patterns - pattern_types

        if missing_patterns:
            return {
                "eligible": False,
                "reason": f"Missing patterns: {missing_patterns}",
            }

        return {
            "eligible": True,
            "client_id": str(client_id),
            "client_name": client.name,
            "tier": client.tier.value if client.tier else "ignition",
            "conversion_count": conversion_count,
            "pattern_count": len(patterns),
        }


@task(name="fetch_cis_patterns", retries=2, retry_delay_seconds=5)
async def fetch_cis_patterns_task(client_id: UUID) -> dict[str, dict[str, Any]]:
    """
    Fetch all valid CIS patterns for a client.

    Args:
        client_id: Client UUID

    Returns:
        Dict with pattern_type -> pattern_data
    """
    async with get_db_session() as db:
        from src.models.conversion_patterns import ConversionPattern

        result = await db.execute(
            select(ConversionPattern)
            .where(
                and_(
                    ConversionPattern.client_id == client_id,
                    ConversionPattern.valid_until > datetime.utcnow(),
                )
            )
        )
        patterns = result.scalars().all()

        pattern_dict = {}
        for p in patterns:
            pattern_dict[p.pattern_type] = {
                "patterns": p.patterns,
                "confidence": float(p.confidence),
                "sample_size": p.sample_size,
                "computed_at": p.computed_at.isoformat() if p.computed_at else None,
            }

        logger.info(
            f"Fetched {len(pattern_dict)} CIS patterns for client {client_id}: "
            f"{list(pattern_dict.keys())}"
        )

        return pattern_dict


@task(name="fetch_current_campaigns", retries=2, retry_delay_seconds=5)
async def fetch_current_campaigns_task(client_id: UUID) -> list[dict[str, Any]]:
    """
    Fetch current campaigns with performance metrics.

    Args:
        client_id: Client UUID

    Returns:
        List of campaign data dicts
    """
    async with get_db_session() as db:
        result = await db.execute(
            select(Campaign)
            .where(
                and_(
                    Campaign.client_id == client_id,
                    Campaign.deleted_at.is_(None),
                    Campaign.status.in_([
                        CampaignStatus.ACTIVE,
                        CampaignStatus.PAUSED,
                    ]),
                )
            )
            .order_by(Campaign.created_at.desc())
        )
        campaigns = result.scalars().all()

        campaign_data = []
        for c in campaigns:
            # Calculate metrics from campaign data
            lead_count = c.lead_count if hasattr(c, "lead_count") else 0
            reply_count = c.reply_count if hasattr(c, "reply_count") else 0
            conversion_count = c.conversion_count if hasattr(c, "conversion_count") else 0

            reply_rate = (reply_count / lead_count * 100) if lead_count > 0 else 0
            conversion_rate = (conversion_count / lead_count * 100) if lead_count > 0 else 0

            campaign_data.append({
                "id": str(c.id),
                "name": c.name,
                "status": c.status.value if c.status else "unknown",
                "lead_count": lead_count,
                "reply_rate": round(reply_rate, 2),
                "conversion_rate": round(conversion_rate, 2),
                "lead_allocation_pct": c.lead_allocation_pct or 0,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

        logger.info(f"Fetched {len(campaign_data)} campaigns for client {client_id}")
        return campaign_data


@task(name="fetch_client_context", retries=2, retry_delay_seconds=5)
async def fetch_client_context_task(client_id: UUID) -> dict[str, Any]:
    """
    Fetch client context for evolution analysis.

    Args:
        client_id: Client UUID

    Returns:
        Dict with client context
    """
    async with get_db_session() as db:
        client = await db.get(Client, client_id)
        if not client:
            return {}

        # Calculate active months
        active_months = 1
        if client.created_at:
            active_months = max(1, (datetime.utcnow() - client.created_at).days // 30)

        # Get tier config
        from src.config.tiers import get_leads_for_tier

        tier_name = client.tier.value if client.tier else "ignition"
        monthly_leads = get_leads_for_tier(tier_name)

        return {
            "client_id": str(client_id),
            "client_name": client.name,
            "tier": tier_name,
            "monthly_leads": monthly_leads,
            "active_months": active_months,
            "icp_industries": client.icp_industries or [],
            "icp_titles": client.icp_titles or [],
            "icp_locations": client.icp_locations or [],
        }


@task(name="run_analyzers", retries=1, retry_delay_seconds=30)
async def run_analyzers_task(
    patterns: dict[str, dict[str, Any]],
    campaigns: list[dict[str, Any]],
    client_context: dict[str, Any],
    client_id: UUID,
) -> dict[str, Any]:
    """
    Run WHO, WHAT, and HOW analyzers.

    Args:
        patterns: CIS patterns by type
        campaigns: Current campaign data
        client_context: Client context
        client_id: Client UUID

    Returns:
        Dict with analyzer outputs and costs
    """
    # Prepare current targeting from client context
    current_targeting = {
        "industries": client_context.get("icp_industries", []),
        "titles": client_context.get("icp_titles", []),
        "locations": client_context.get("icp_locations", []),
        "company_sizes": [],  # Not stored in client context currently
    }

    # Aggregate campaign metrics
    total_leads = sum(c.get("lead_count", 0) for c in campaigns)
    total_replies = sum(
        c.get("lead_count", 0) * c.get("reply_rate", 0) / 100
        for c in campaigns
    )
    campaign_metrics = {
        "leads_contacted": total_leads,
        "reply_rate": round(total_replies / total_leads * 100, 2) if total_leads > 0 else 0,
    }

    # Current content strategy (simplified - would need content table)
    current_content = {
        "templates": [],  # Would fetch from content table
    }

    # Current channel strategy (simplified)
    current_strategy = {
        "channel_allocation": {"email": 70, "linkedin": 20, "voice": 10},
    }

    results = {
        "who": None,
        "what": None,
        "how": None,
        "costs": {},
        "errors": [],
    }

    # Run WHO analyzer
    if "who" in patterns:
        try:
            who_result = await run_who_analyzer(
                who_patterns=patterns["who"]["patterns"],
                current_targeting=current_targeting,
                campaign_metrics=campaign_metrics,
                client_id=client_id,
            )
            if who_result.success and who_result.data:
                results["who"] = who_result.data.model_dump()
                results["costs"]["who"] = who_result.cost_aud
            else:
                results["errors"].append(f"WHO analyzer failed: {who_result.error}")
        except Exception as e:
            logger.error(f"WHO analyzer error: {e}")
            results["errors"].append(f"WHO analyzer error: {str(e)}")
    else:
        results["errors"].append("No WHO patterns available")

    # Run WHAT analyzer
    if "what" in patterns:
        try:
            what_result = await run_what_analyzer(
                what_patterns=patterns["what"]["patterns"],
                current_content=current_content,
                campaign_metrics=campaign_metrics,
                client_id=client_id,
            )
            if what_result.success and what_result.data:
                results["what"] = what_result.data.model_dump()
                results["costs"]["what"] = what_result.cost_aud
            else:
                results["errors"].append(f"WHAT analyzer failed: {what_result.error}")
        except Exception as e:
            logger.error(f"WHAT analyzer error: {e}")
            results["errors"].append(f"WHAT analyzer error: {str(e)}")
    else:
        results["errors"].append("No WHAT patterns available")

    # Run HOW analyzer
    if "how" in patterns:
        when_patterns = patterns.get("when", {}).get("patterns")
        try:
            how_result = await run_how_analyzer(
                how_patterns=patterns["how"]["patterns"],
                when_patterns=when_patterns,
                current_strategy=current_strategy,
                campaign_metrics=campaign_metrics,
                client_id=client_id,
            )
            if how_result.success and how_result.data:
                results["how"] = how_result.data.model_dump()
                results["costs"]["how"] = how_result.cost_aud
            else:
                results["errors"].append(f"HOW analyzer failed: {how_result.error}")
        except Exception as e:
            logger.error(f"HOW analyzer error: {e}")
            results["errors"].append(f"HOW analyzer error: {str(e)}")
    else:
        results["errors"].append("No HOW patterns available")

    total_cost = sum(results["costs"].values())
    logger.info(
        f"Analyzers complete for client {client_id}: "
        f"WHO={'OK' if results['who'] else 'FAIL'}, "
        f"WHAT={'OK' if results['what'] else 'FAIL'}, "
        f"HOW={'OK' if results['how'] else 'FAIL'}, "
        f"cost=${total_cost:.4f}"
    )

    return results


@task(name="run_orchestrator", retries=1, retry_delay_seconds=30)
async def run_orchestrator_task(
    analyzer_results: dict[str, Any],
    campaigns: list[dict[str, Any]],
    client_context: dict[str, Any],
    client_id: UUID,
) -> dict[str, Any] | None:
    """
    Run campaign orchestrator to generate suggestions.

    Args:
        analyzer_results: Output from run_analyzers_task
        campaigns: Current campaign data
        client_context: Client context
        client_id: Client UUID

    Returns:
        Orchestrator output or None if failed
    """
    # Need at least 2 successful analyzer outputs
    successful_analyzers = sum([
        1 if analyzer_results.get("who") else 0,
        1 if analyzer_results.get("what") else 0,
        1 if analyzer_results.get("how") else 0,
    ])

    if successful_analyzers < 2:
        logger.warning(
            f"Insufficient analyzer outputs ({successful_analyzers}/3) - skipping orchestrator"
        )
        return None

    # Use empty dict for missing analyzers
    who_analysis = analyzer_results.get("who") or {"summary": "No WHO analysis available", "confidence": 0}
    what_analysis = analyzer_results.get("what") or {"summary": "No WHAT analysis available", "confidence": 0}
    how_analysis = analyzer_results.get("how") or {"summary": "No HOW analysis available", "confidence": 0}

    result = await generate_campaign_suggestions(
        who_analysis=who_analysis,
        what_analysis=what_analysis,
        how_analysis=how_analysis,
        current_campaigns=campaigns,
        client_context=client_context,
        analyzer_costs=analyzer_results.get("costs", {}),
        client_id=client_id,
    )

    if result:
        logger.info(
            f"Orchestrator generated {len(result.get('suggestions', []))} suggestions "
            f"for client {client_id}"
        )
    else:
        logger.warning(f"Orchestrator failed for client {client_id}")

    return result


@task(name="store_suggestions", retries=2, retry_delay_seconds=5)
async def store_suggestions_task(
    orchestrator_output: dict[str, Any],
    client_id: UUID,
    patterns: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Store suggestions in the database.

    Args:
        orchestrator_output: Output from orchestrator
        client_id: Client UUID
        patterns: CIS patterns (for snapshot)

    Returns:
        Dict with storage results
    """
    suggestions = orchestrator_output.get("suggestions", [])
    if not suggestions:
        return {"stored": 0, "skipped": 0, "errors": []}

    stored = 0
    skipped = 0
    errors = []

    async with get_db_session() as db:
        for suggestion in suggestions:
            # Validate suggestion
            if not validate_suggestion_for_storage(suggestion):
                skipped += 1
                continue

            try:
                # Create suggestion record
                db_suggestion = CampaignSuggestion(
                    client_id=client_id,
                    campaign_id=None,  # Will be set when applied
                    suggestion_type=suggestion["suggestion_type"],
                    status=SuggestionStatus.PENDING.value,
                    title=suggestion["title"],
                    description=suggestion["description"],
                    rationale=suggestion.get("rationale", {}),
                    recommended_action=suggestion["recommended_action"],
                    confidence=suggestion["confidence"],
                    priority=suggestion["priority"],
                    pattern_types=suggestion.get("pattern_types", []),
                    pattern_snapshot={
                        pt: {
                            "confidence": p.get("confidence"),
                            "sample_size": p.get("sample_size"),
                            "computed_at": p.get("computed_at"),
                        }
                        for pt, p in patterns.items()
                    },
                    projected_improvement=suggestion.get("projected_improvement", {}),
                    expires_at=datetime.utcnow() + timedelta(days=14),
                )

                db.add(db_suggestion)
                stored += 1

            except Exception as e:
                logger.error(f"Failed to store suggestion '{suggestion.get('title')}': {e}")
                errors.append(str(e))

        await db.commit()

    logger.info(
        f"Stored {stored} suggestions for client {client_id} "
        f"(skipped: {skipped}, errors: {len(errors)})"
    )

    return {
        "stored": stored,
        "skipped": skipped,
        "errors": errors,
    }


# ============================================
# FLOW
# ============================================


@flow(
    name="campaign_evolution",
    description="Generate campaign optimization suggestions from CIS patterns",
    retries=1,
    retry_delay_seconds=60,
)
async def campaign_evolution_flow(
    client_id: str | UUID,
    force: bool = False,
) -> dict[str, Any]:
    """
    Campaign evolution flow - generates suggestions from CIS patterns.

    This flow:
    1. Checks eligibility (conversions, patterns, subscription)
    2. Fetches CIS patterns and campaign data
    3. Runs WHO, WHAT, HOW analyzers in sequence
    4. Runs orchestrator to generate suggestions
    5. Stores suggestions for client review

    CRITICAL: Suggestions require client approval. They are NEVER auto-applied.

    Args:
        client_id: Client UUID
        force: Skip eligibility check (for testing)

    Returns:
        Dict with flow results
    """
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting campaign evolution for client {client_id}")

    # Step 1: Check eligibility
    if not force:
        eligibility = await check_evolution_eligibility_task(client_id)
        if not eligibility.get("eligible"):
            logger.info(
                f"Client {client_id} not eligible for evolution: "
                f"{eligibility.get('reason')}"
            )
            return {
                "success": False,
                "client_id": str(client_id),
                "reason": eligibility.get("reason"),
                "suggestions_generated": 0,
            }
    else:
        eligibility = {"eligible": True, "forced": True}

    # Step 2: Fetch data
    patterns = await fetch_cis_patterns_task(client_id)
    campaigns = await fetch_current_campaigns_task(client_id)
    client_context = await fetch_client_context_task(client_id)

    # Step 3: Run analyzers
    analyzer_results = await run_analyzers_task(
        patterns=patterns,
        campaigns=campaigns,
        client_context=client_context,
        client_id=client_id,
    )

    # Step 4: Run orchestrator
    orchestrator_output = await run_orchestrator_task(
        analyzer_results=analyzer_results,
        campaigns=campaigns,
        client_context=client_context,
        client_id=client_id,
    )

    if not orchestrator_output:
        return {
            "success": False,
            "client_id": str(client_id),
            "reason": "Orchestrator failed",
            "analyzer_errors": analyzer_results.get("errors", []),
            "suggestions_generated": 0,
        }

    # Step 5: Store suggestions
    storage_result = await store_suggestions_task(
        orchestrator_output=orchestrator_output,
        client_id=client_id,
        patterns=patterns,
    )

    return {
        "success": True,
        "client_id": str(client_id),
        "client_name": client_context.get("client_name"),
        "suggestions_generated": storage_result["stored"],
        "suggestions_skipped": storage_result["skipped"],
        "executive_summary": orchestrator_output.get("executive_summary"),
        "campaign_health_score": orchestrator_output.get("campaign_health_score"),
        "total_cost_aud": orchestrator_output.get("total_analysis_cost_aud", 0),
        "completed_at": datetime.utcnow().isoformat(),
    }


@flow(
    name="batch_campaign_evolution",
    description="Run campaign evolution for all eligible clients",
)
async def batch_campaign_evolution_flow() -> dict[str, Any]:
    """
    Run campaign evolution for all eligible clients.

    Typically triggered after weekly pattern learning.

    Returns:
        Dict with batch results
    """
    logger.info("Starting batch campaign evolution")

    async with get_db_session() as db:
        # Get all active clients
        result = await db.execute(
            select(Client.id)
            .where(
                and_(
                    Client.subscription_status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING,
                    ]),
                    Client.deleted_at.is_(None),
                )
            )
        )
        client_ids = [row[0] for row in result.fetchall()]

    results = []
    successful = 0
    failed = 0

    for client_id in client_ids:
        try:
            result = await campaign_evolution_flow(client_id=client_id)
            results.append(result)
            if result.get("success"):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Campaign evolution failed for client {client_id}: {e}")
            failed += 1
            results.append({
                "client_id": str(client_id),
                "success": False,
                "error": str(e),
            })

    total_suggestions = sum(r.get("suggestions_generated", 0) for r in results)

    logger.info(
        f"Batch campaign evolution complete: "
        f"{successful} successful, {failed} failed, "
        f"{total_suggestions} total suggestions generated"
    )

    return {
        "clients_processed": len(client_ids),
        "successful": successful,
        "failed": failed,
        "total_suggestions": total_suggestions,
        "results": results,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] CRITICAL: Suggestions require client approval
# [x] Eligibility check (conversions, patterns, subscription)
# [x] Fetch CIS patterns
# [x] Fetch campaign data
# [x] Run WHO, WHAT, HOW analyzers
# [x] Run orchestrator
# [x] Store suggestions with expiration
# [x] Pattern snapshot for audit trail
# [x] Batch flow for all clients
# [x] Cost tracking
# [x] Comprehensive logging
# [x] Error handling
# [x] Retry configuration on tasks
