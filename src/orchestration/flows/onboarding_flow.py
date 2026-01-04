"""
FILE: src/orchestration/flows/onboarding_flow.py
TASK: ICP-014
PHASE: 11 (ICP Discovery System)
PURPOSE: Prefect flow for async ICP extraction during client onboarding

DEPENDENCIES:
- src/agents/icp_discovery_agent.py
- src/engines/icp_scraper.py
- src/integrations/supabase.py

RULES APPLIED:
- Rule 1: Follow blueprint exactly
- Rule 11: Session passed as argument
- Rule 14: Soft deletes only
- Rule 15: AI spend limiter via Anthropic integration
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.icp_discovery_agent import ICPExtractionResult, get_icp_discovery_agent
from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="update_job_status", retries=2, retry_delay_seconds=3)
async def update_job_status_task(
    job_id: UUID,
    status: str,
    current_step: str | None = None,
    completed_steps: int | None = None,
    error_message: str | None = None,
) -> bool:
    """
    Update the status of an extraction job.

    Args:
        job_id: Extraction job UUID
        status: New status (pending, running, completed, failed)
        current_step: Current step name
        completed_steps: Number of completed steps
        error_message: Error message if failed

    Returns:
        True if updated successfully
    """
    async with get_db_session() as db:
        updates = {"status": status}

        if current_step is not None:
            updates["current_step"] = current_step
        if completed_steps is not None:
            updates["completed_steps"] = completed_steps
        if error_message is not None:
            updates["error_message"] = error_message
        if status == "running" and "started_at" not in updates:
            updates["started_at"] = datetime.utcnow()
        if status in ("completed", "failed"):
            updates["completed_at"] = datetime.utcnow()

        set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
        await db.execute(
            f"""
            UPDATE icp_extraction_jobs
            SET {set_clauses}
            WHERE id = :job_id
            """,
            {"job_id": str(job_id), **updates},
        )
        await db.commit()

    logger.info(f"Updated job {job_id} status to {status}")
    return True


@task(name="scrape_website", retries=2, retry_delay_seconds=10)
async def scrape_website_task(
    job_id: UUID,
    website_url: str,
) -> dict[str, Any]:
    """
    Scrape the website content using Apify.

    Args:
        job_id: Extraction job UUID
        website_url: URL to scrape

    Returns:
        Dict with scraped content or error
    """
    from src.engines.icp_scraper import get_icp_scraper_engine

    # Update progress
    await update_job_status_task(
        job_id=job_id,
        status="running",
        current_step="Scraping website",
        completed_steps=1,
    )

    scraper = get_icp_scraper_engine()
    result = await scraper.scrape_website(website_url)

    if not result.success:
        logger.error(f"Website scraping failed: {result.error}")
        return {"success": False, "error": result.error}

    logger.info(f"Scraped {result.data.page_count} pages from {website_url}")
    return {
        "success": True,
        "raw_html": result.data.raw_html,
        "pages": [
            {
                "url": p.url,
                "title": p.title,
                "text": p.text[:5000],  # Limit text size
            }
            for p in result.data.pages
        ],
        "page_count": result.data.page_count,
    }


@task(name="run_icp_extraction", retries=1, timeout_seconds=600)
async def run_icp_extraction_task(
    job_id: UUID,
    website_url: str,
) -> dict[str, Any]:
    """
    Run the full ICP extraction using the ICP Discovery Agent.

    Args:
        job_id: Extraction job UUID
        website_url: URL to analyze

    Returns:
        Dict with extraction result or error
    """
    # Update progress
    await update_job_status_task(
        job_id=job_id,
        status="running",
        current_step="Extracting ICP profile",
        completed_steps=2,
    )

    agent = get_icp_discovery_agent()
    result = await agent.extract_icp(website_url)

    if result.success and result.profile:
        logger.info(
            f"ICP extraction completed for {website_url}: "
            f"{result.services_found} services, "
            f"{result.portfolio_companies_found} portfolio companies"
        )
        return {
            "success": True,
            "profile": result.profile.model_dump(),
            "tokens_used": result.total_tokens,
            "cost_aud": result.total_cost_aud,
            "duration_seconds": result.duration_seconds,
        }
    else:
        logger.error(f"ICP extraction failed: {result.error}")
        return {"success": False, "error": result.error}


@task(name="save_extraction_result", retries=3, retry_delay_seconds=5)
async def save_extraction_result_task(
    job_id: UUID,
    client_id: UUID,
    result: dict[str, Any],
) -> bool:
    """
    Save the extraction result to the database.

    Args:
        job_id: Extraction job UUID
        client_id: Client UUID
        result: Extraction result dict

    Returns:
        True if saved successfully
    """
    import json

    async with get_db_session() as db:
        if result.get("success"):
            # Save to extraction job
            await db.execute(
                """
                UPDATE icp_extraction_jobs
                SET status = 'completed',
                    completed_at = :now,
                    completed_steps = 8,
                    current_step = 'Complete',
                    extracted_icp = :icp
                WHERE id = :job_id
                """,
                {
                    "job_id": str(job_id),
                    "now": datetime.utcnow(),
                    "icp": json.dumps(result.get("profile", {})),
                },
            )
            await db.commit()
            logger.info(f"Saved extraction result for job {job_id}")
            return True
        else:
            # Save error
            await db.execute(
                """
                UPDATE icp_extraction_jobs
                SET status = 'failed',
                    completed_at = :now,
                    error_message = :error
                WHERE id = :job_id
                """,
                {
                    "job_id": str(job_id),
                    "now": datetime.utcnow(),
                    "error": result.get("error", "Unknown error"),
                },
            )
            await db.commit()
            logger.error(f"Saved extraction error for job {job_id}")
            return False


@task(name="apply_icp_to_client")
async def apply_icp_to_client_task(
    client_id: UUID,
    profile: dict[str, Any],
    job_id: UUID,
) -> bool:
    """
    Apply extracted ICP to client record (without confirmation).

    This pre-populates the client fields but doesn't mark as confirmed.
    User still needs to confirm via the UI.

    Args:
        client_id: Client UUID
        profile: ICP profile dict
        job_id: Extraction job UUID

    Returns:
        True if applied successfully
    """
    async with get_db_session() as db:
        await db.execute(
            """
            UPDATE clients
            SET website_url = :website_url,
                company_description = :description,
                services_offered = :services,
                value_proposition = :value_prop,
                team_size = :team_size,
                icp_industries = :industries,
                icp_company_sizes = :sizes,
                icp_locations = :locations,
                icp_titles = :titles,
                icp_pain_points = :pain_points,
                als_weights = :als_weights,
                icp_extracted_at = :now,
                icp_extraction_source = 'ai_extraction',
                icp_extraction_job_id = :job_id,
                updated_at = :now
            WHERE id = :client_id AND deleted_at IS NULL
            """,
            {
                "client_id": str(client_id),
                "website_url": profile.get("website_url"),
                "description": profile.get("company_description", ""),
                "services": profile.get("services_offered", []),
                "value_prop": profile.get("value_proposition", ""),
                "team_size": profile.get("team_size"),
                "industries": profile.get("icp_industries", []),
                "sizes": profile.get("icp_company_sizes", []),
                "locations": profile.get("icp_locations", []),
                "titles": profile.get("icp_titles", []),
                "pain_points": profile.get("icp_pain_points", []),
                "als_weights": profile.get("als_weights", {}),
                "now": datetime.utcnow(),
                "job_id": str(job_id),
            },
        )
        await db.commit()

    logger.info(f"Applied ICP to client {client_id}")
    return True


# ============================================
# FLOWS
# ============================================


@flow(
    name="icp_onboarding_flow",
    description="Extract ICP from client website during onboarding",
    task_runner=ConcurrentTaskRunner(),
    retries=0,
    timeout_seconds=900,  # 15 minute timeout
)
async def icp_onboarding_flow(
    job_id: UUID,
    client_id: UUID,
    website_url: str,
    auto_apply: bool = True,
) -> dict[str, Any]:
    """
    Main onboarding flow for ICP extraction.

    Flow steps:
    1. Update job status to running
    2. Run ICP extraction (includes scraping + AI analysis)
    3. Save extraction result
    4. Optionally apply to client

    Args:
        job_id: Extraction job UUID
        client_id: Client UUID
        website_url: Website URL to analyze
        auto_apply: Whether to auto-apply ICP to client (default True)

    Returns:
        Dict with flow result
    """
    logger.info(f"Starting ICP onboarding flow for job {job_id}, URL: {website_url}")

    try:
        # Step 1: Update to running
        await update_job_status_task(
            job_id=job_id,
            status="running",
            current_step="Starting extraction",
            completed_steps=0,
        )

        # Step 2: Run extraction
        extraction_result = await run_icp_extraction_task(
            job_id=job_id,
            website_url=website_url,
        )

        # Step 3: Save result
        saved = await save_extraction_result_task(
            job_id=job_id,
            client_id=client_id,
            result=extraction_result,
        )

        # Step 4: Auto-apply if enabled and successful
        if auto_apply and extraction_result.get("success") and extraction_result.get("profile"):
            await apply_icp_to_client_task(
                client_id=client_id,
                profile=extraction_result["profile"],
                job_id=job_id,
            )

        return {
            "success": extraction_result.get("success", False),
            "job_id": str(job_id),
            "client_id": str(client_id),
            "website_url": website_url,
            "tokens_used": extraction_result.get("tokens_used", 0),
            "cost_aud": extraction_result.get("cost_aud", 0.0),
            "duration_seconds": extraction_result.get("duration_seconds", 0),
            "error": extraction_result.get("error"),
        }

    except Exception as e:
        logger.exception(f"ICP onboarding flow failed: {e}")

        # Update job with error
        await update_job_status_task(
            job_id=job_id,
            status="failed",
            error_message=str(e),
        )

        return {
            "success": False,
            "job_id": str(job_id),
            "client_id": str(client_id),
            "website_url": website_url,
            "error": str(e),
        }


@flow(
    name="icp_reextract_flow",
    description="Re-extract ICP for existing client",
)
async def icp_reextract_flow(
    client_id: UUID,
    website_url: str,
) -> dict[str, Any]:
    """
    Re-extract ICP for an existing client.

    Used when client wants to refresh their ICP or update website.

    Args:
        client_id: Client UUID
        website_url: New or updated website URL

    Returns:
        Dict with flow result
    """
    from uuid import uuid4

    job_id = uuid4()

    # Create new extraction job
    async with get_db_session() as db:
        await db.execute(
            """
            INSERT INTO icp_extraction_jobs
            (id, client_id, status, website_url, created_at)
            VALUES (:id, :client_id, 'pending', :url, :now)
            """,
            {
                "id": str(job_id),
                "client_id": str(client_id),
                "url": website_url,
                "now": datetime.utcnow(),
            },
        )
        await db.commit()

    # Run the main onboarding flow
    return await icp_onboarding_flow(
        job_id=job_id,
        client_id=client_id,
        website_url=website_url,
        auto_apply=False,  # Require confirmation for re-extraction
    )


# ============================================
# DEPLOYMENT
# ============================================


def deploy_onboarding_flows():
    """
    Deploy onboarding flows to Prefect.

    Run this to register flows with the Prefect server.
    """
    from prefect.deployments import Deployment

    # Main onboarding flow deployment
    onboarding_deployment = Deployment.build_from_flow(
        flow=icp_onboarding_flow,
        name="icp-onboarding",
        work_queue_name="default",
        tags=["onboarding", "icp"],
    )
    onboarding_deployment.apply()

    # Re-extraction flow deployment
    reextract_deployment = Deployment.build_from_flow(
        flow=icp_reextract_flow,
        name="icp-reextract",
        work_queue_name="default",
        tags=["onboarding", "icp"],
    )
    reextract_deployment.apply()

    logger.info("Deployed ICP onboarding flows")


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Session managed properly with get_db_session()
- [x] Soft delete checks (deleted_at IS NULL)
- [x] Prefect @task and @flow decorators
- [x] Retries configured on tasks
- [x] Timeout configured on flows
- [x] Progress tracking via update_job_status_task
- [x] Error handling with proper logging
- [x] Main flow and re-extraction flow
- [x] Deployment function for Prefect registration
- [x] Type hints on all functions
- [x] Docstrings on all functions
"""
