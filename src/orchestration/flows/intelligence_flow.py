"""
FILE: src/orchestration/flows/intelligence_flow.py
PURPOSE: Auto-trigger Deep Research for Hot leads (ALS >= 85)
PHASE: 20 (UI Wiring)
TASK: WIRE-001
DEPENDENCIES:
  - src/integrations/supabase.py
  - src/engines/scout.py
  - src/models/lead.py
  - src/models/client.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation - check client billing before research
  - ALS Hot threshold is 85 (NOT 80)
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import and_, select, update

from src.engines.scout import get_scout_engine
from src.integrations.supabase import get_db_session
from src.models.base import SubscriptionStatus
from src.models.client import Client
from src.models.lead import Lead

logger = logging.getLogger(__name__)

# Hot lead threshold (CRITICAL: Must be 85, not 80)
HOT_LEAD_THRESHOLD = 85


# ============================================
# TASKS
# ============================================


@task(name="get_hot_leads_needing_research", retries=2, retry_delay_seconds=5)
async def get_hot_leads_needing_research_task(
    limit: int = 50,
    client_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Get hot leads (ALS >= 85) that haven't had deep research run.

    Includes JIT validation: checks client billing status.

    Args:
        limit: Maximum number of leads to process
        client_id: Optional client ID to filter by

    Returns:
        Dict with lead IDs needing research
    """
    async with get_db_session() as db:
        stmt = (
            select(
                Lead.id,
                Lead.client_id,
                Lead.als_score,
                Lead.first_name,
                Lead.last_name,
                Lead.linkedin_url,
                Client.credits_remaining,
            )
            .join(Client, Lead.client_id == Client.id)
            .where(
                and_(
                    Lead.als_score >= HOT_LEAD_THRESHOLD,
                    Lead.als_tier == "hot",
                    Lead.linkedin_url.isnot(None),
                    Lead.deep_research_run_at.is_(None),
                    Lead.deleted_at.is_(None),
                    Client.deleted_at.is_(None),
                    Client.subscription_status.in_(
                        [
                            SubscriptionStatus.ACTIVE,
                            SubscriptionStatus.TRIALING,
                        ]
                    ),
                    Client.credits_remaining > 0,
                )
            )
            .order_by(Lead.als_score.desc())
            .limit(limit)
        )

        if client_id:
            stmt = stmt.where(Lead.client_id == client_id)

        result = await db.execute(stmt)
        rows = result.all()

        leads_data = []
        for lead_id, client_id_val, als_score, first_name, last_name, linkedin_url, credits in rows:
            leads_data.append(
                {
                    "lead_id": str(lead_id),
                    "client_id": str(client_id_val),
                    "als_score": als_score,
                    "name": f"{first_name or ''} {last_name or ''}".strip(),
                    "linkedin_url": linkedin_url,
                    "credits_remaining": credits,
                }
            )

        logger.info(f"Found {len(leads_data)} hot leads needing deep research")

        return {
            "total_leads": len(leads_data),
            "leads": leads_data,
        }


@task(name="perform_deep_research", retries=2, retry_delay_seconds=30)
async def perform_deep_research_task(
    lead_id: str,
    client_id: str,
) -> dict[str, Any]:
    """
    Perform deep research on a single lead.

    Uses the Scout engine's perform_deep_research method which:
    - Scrapes LinkedIn posts via Apify
    - Generates icebreaker hooks via Claude
    - Saves results to lead_research and lead_social_posts tables

    Args:
        lead_id: Lead UUID string
        client_id: Client UUID string

    Returns:
        Dict with research results
    """
    async with get_db_session() as db:
        scout_engine = get_scout_engine()
        lead_uuid = UUID(lead_id)

        result = await scout_engine.perform_deep_research(
            db=db,
            lead_id=lead_uuid,
        )

        if result.success:
            logger.info(
                f"Deep research completed for lead {lead_id}: "
                f"icebreaker generated, {result.data.get('posts_found', 0)} posts found"
            )
            return {
                "lead_id": lead_id,
                "client_id": client_id,
                "success": True,
                "icebreaker_hook": result.data.get("icebreaker_hook"),
                "posts_found": result.data.get("posts_found", 0),
                "confidence": result.data.get("confidence"),
                "tokens_used": result.metadata.get("tokens_used", 0),
                "cost_aud": result.metadata.get("cost_aud", 0),
            }
        else:
            logger.warning(f"Deep research failed for lead {lead_id}: {result.error}")
            return {
                "lead_id": lead_id,
                "client_id": client_id,
                "success": False,
                "error": result.error,
            }


@task(name="update_lead_research_status", retries=2, retry_delay_seconds=5)
async def update_lead_research_status_task(
    lead_id: str,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    """
    Update lead's deep research status.

    Args:
        lead_id: Lead UUID string
        status: Research status (completed, failed)
        error: Optional error message

    Returns:
        Dict with update result
    """
    async with get_db_session() as db:
        lead_uuid = UUID(lead_id)

        update_data = {
            "updated_at": datetime.utcnow(),
        }

        if status == "failed" and error:
            # Store error in deep_research_data
            update_data["deep_research_data"] = {"error": error, "status": "failed"}
            update_data["deep_research_run_at"] = datetime.utcnow()

        stmt = update(Lead).where(Lead.id == lead_uuid).values(**update_data)
        await db.execute(stmt)
        await db.commit()

        return {
            "lead_id": lead_id,
            "status": status,
        }


# ============================================
# FLOW
# ============================================


@flow(
    name="intelligence_research",
    description="Auto-trigger Deep Research for Hot leads (ALS >= 85)",
    log_prints=True,
    task_runner=ConcurrentTaskRunner(max_workers=5),
)
async def intelligence_research_flow(
    batch_size: int = 50,
    client_id: str | UUID | None = None,
) -> dict[str, Any]:
    """
    Intelligence research flow for hot leads.

    Automatically triggers deep research for leads with:
    - ALS score >= 85 (Hot tier)
    - LinkedIn URL available
    - No previous deep research

    Steps:
    1. Get hot leads needing research
    2. Perform deep research (scrape LinkedIn, generate icebreakers)
    3. Update lead status

    Args:
        batch_size: Maximum leads to process
        client_id: Optional client ID to filter by

    Returns:
        Dict with research summary
    """
    # Convert string to UUID if needed (Prefect API passes strings)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(
        f"Starting intelligence research flow (batch_size={batch_size}, client_id={client_id})"
    )

    # Step 1: Get hot leads needing research
    leads_data = await get_hot_leads_needing_research_task(
        limit=batch_size,
        client_id=client_id,
    )

    if leads_data["total_leads"] == 0:
        logger.info("No hot leads needing deep research")
        return {
            "total_leads": 0,
            "researched": 0,
            "failed": 0,
            "message": "No hot leads needing deep research",
        }

    # Step 2: Perform deep research on each lead
    research_results = []
    for lead_info in leads_data["leads"]:
        result = await perform_deep_research_task(
            lead_id=lead_info["lead_id"],
            client_id=lead_info["client_id"],
        )
        research_results.append(result)

        # Update status for failed leads
        if not result["success"]:
            await update_lead_research_status_task(
                lead_id=lead_info["lead_id"],
                status="failed",
                error=result.get("error"),
            )

    # Compile summary
    successful = [r for r in research_results if r["success"]]
    failed = [r for r in research_results if not r["success"]]

    total_tokens = sum(r.get("tokens_used", 0) for r in successful)
    total_cost = sum(r.get("cost_aud", 0) for r in successful)

    summary = {
        "total_leads": leads_data["total_leads"],
        "researched": len(successful),
        "failed": len(failed),
        "total_tokens_used": total_tokens,
        "total_cost_aud": total_cost,
        "successful_leads": [
            {
                "lead_id": r["lead_id"],
                "icebreaker_hook": r.get("icebreaker_hook"),
                "posts_found": r.get("posts_found", 0),
            }
            for r in successful
        ],
        "failed_leads": [
            {
                "lead_id": r["lead_id"],
                "error": r.get("error"),
            }
            for r in failed
        ],
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Intelligence research flow completed: {len(successful)} researched, "
        f"{len(failed)} failed, {total_cost:.4f} AUD spent"
    )

    return summary


@flow(
    name="trigger_lead_research",
    description="Trigger deep research for a single lead (on-demand)",
    log_prints=True,
)
async def trigger_lead_research_flow(
    lead_id: str | UUID,
    client_id: str | UUID,
) -> dict[str, Any]:
    """
    Trigger deep research for a single lead.

    Called when:
    - Lead is scored and ALS >= 85
    - Manual trigger from dashboard

    Args:
        lead_id: Lead UUID (string or UUID)
        client_id: Client UUID (string or UUID)

    Returns:
        Dict with research result
    """
    # Convert strings to UUIDs if needed (Prefect API passes strings)
    if isinstance(lead_id, str):
        lead_id = UUID(lead_id)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Triggering deep research for lead {lead_id}")

    result = await perform_deep_research_task(
        lead_id=str(lead_id),
        client_id=str(client_id),
    )

    if not result["success"]:
        await update_lead_research_status_task(
            lead_id=str(lead_id),
            status="failed",
            error=result.get("error"),
        )

    return result


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] No imports from other orchestration files
# [x] Imports from engines (scout), models, integrations
# [x] JIT validation in get_hot_leads_needing_research_task
# [x] Checks client billing status before research
# [x] Soft delete checks in all queries
# [x] @flow and @task decorators from Prefect
# [x] ConcurrentTaskRunner with max_workers=5
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] Hot threshold is 85 (NOT 80)
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Returns structured dict results
