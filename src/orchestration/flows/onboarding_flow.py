"""
FILE: src/orchestration/flows/onboarding_flow.py
TASK: ICP-014
PHASE: 11 (ICP Discovery System)
PURPOSE: Prefect flow for async ICP extraction during client onboarding

DEPENDENCIES:
- src/agents/icp_discovery_agent.py
- src/agents/sdk_agents/icp_agent.py (SDK enhancement)
- src/engines/icp_scraper.py
- src/integrations/supabase.py

RULES APPLIED:
- Rule 1: Follow blueprint exactly
- Rule 11: Session passed as argument
- Rule 14: Soft deletes only
- Rule 15: AI spend limiter via Anthropic integration
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import text

from src.agents.icp_discovery_agent import get_icp_discovery_agent
from src.config.settings import get_settings
from src.engines.client_intelligence import (
    ScrapeConfig,
    get_client_intelligence_engine,
)
from src.integrations.supabase import get_db_session
from src.models.resource_pool import ResourceType
from src.services.resource_assignment_service import (
    assign_resources_to_client,
    check_buffer_and_alert,
)

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


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

        set_clauses = ", ".join([f"{k} = :{k}" for k in updates])
        await db.execute(
            text(f"""
            UPDATE icp_extraction_jobs
            SET {set_clauses}
            WHERE id = :job_id
            """),
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


@task(name="enhance_icp_with_sdk", retries=1, timeout_seconds=300)
async def enhance_icp_with_sdk_task(
    job_id: UUID,
    client_id: UUID,
    website_url: str,
    basic_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Enhance ICP extraction using Claude Agent SDK.

    This task takes the basic ICP result and uses the SDK Agent to:
    - Research additional context via web search
    - Build more detailed pain points and buying signals
    - Self-review and refine the ICP

    Args:
        job_id: Extraction job UUID
        client_id: Client UUID
        website_url: Website URL being analyzed
        basic_result: Result from basic ICP extraction

    Returns:
        Enhanced ICP result dict or original if SDK disabled/fails
    """
    settings = get_settings()

    # Check if SDK is enabled
    if not settings.sdk_brain_enabled:
        logger.info("SDK Brain disabled, returning basic ICP result")
        return basic_result

    # Only enhance if basic extraction succeeded
    if not basic_result.get("success"):
        logger.info("Basic extraction failed, skipping SDK enhancement")
        return basic_result

    try:
        # Update progress
        await update_job_status_task(
            job_id=job_id,
            status="running",
            current_step="Enhancing ICP with AI research",
            completed_steps=5,
        )

        # Import SDK components
        from src.agents.sdk_agents.icp_agent import extract_icp

        # Prepare website content from basic result profile
        profile = basic_result.get("profile", {})
        website_content = profile.get("company_description", "")

        # Add services and other scraped data
        if profile.get("services_offered"):
            website_content += "\n\nServices: " + ", ".join(profile.get("services_offered", []))
        if profile.get("value_proposition"):
            website_content += "\n\nValue Proposition: " + profile.get("value_proposition", "")

        # Extract portfolio companies if available
        portfolio_companies = []
        # Note: basic result may not have portfolio data, SDK will research

        # Get client name from database
        async with get_db_session() as db:
            result_row = await db.execute(
                text("SELECT company_name FROM clients WHERE id = :client_id"),
                {"client_id": str(client_id)},
            )
            row = result_row.fetchone()
            client_name = row[0] if row else "Unknown Agency"

        # Run SDK ICP extraction
        logger.info(f"Running SDK ICP enhancement for {client_name}")
        sdk_result = await extract_icp(
            client_name=client_name,
            website_url=website_url,
            website_content=website_content,
            portfolio_companies=portfolio_companies,
            social_links=profile.get("social_links", {}),
            existing_icp=profile,  # Pass basic ICP for refinement
            client_id=client_id,
        )

        if sdk_result.success and sdk_result.data:
            logger.info(
                f"SDK ICP enhancement completed: "
                f"confidence={sdk_result.data.confidence_score:.2f}, "
                f"cost=${sdk_result.cost_aud:.4f}"
            )

            # Merge SDK result into the profile
            enhanced_profile = basic_result.get("profile", {}).copy()

            # Update with SDK-enhanced fields
            sdk_data = sdk_result.data
            enhanced_profile["icp_industries"] = [ind.name for ind in sdk_data.target_industries]
            enhanced_profile["icp_titles"] = [title.title for title in sdk_data.target_titles]
            enhanced_profile["icp_pain_points"] = [pp.pain_point for pp in sdk_data.pain_points]
            enhanced_profile["icp_company_sizes"] = [
                f"{sdk_data.company_size_range.min_employees}-{sdk_data.company_size_range.max_employees}"
            ]
            enhanced_profile["icp_locations"] = sdk_data.target_locations
            enhanced_profile["services_offered"] = sdk_data.services_offered
            enhanced_profile["value_proposition"] = ", ".join(sdk_data.agency_strengths)

            # Add SDK-specific metadata
            enhanced_profile["sdk_confidence_score"] = sdk_data.confidence_score
            enhanced_profile["sdk_data_gaps"] = sdk_data.data_gaps
            enhanced_profile["sdk_buying_signals"] = [
                {"signal": bs.signal, "urgency": bs.urgency} for bs in sdk_data.buying_signals
            ]
            enhanced_profile["sdk_sources_used"] = sdk_data.sources_used

            return {
                "success": True,
                "profile": enhanced_profile,
                "tokens_used": basic_result.get("tokens_used", 0)
                + (sdk_result.input_tokens + sdk_result.output_tokens),
                "cost_aud": basic_result.get("cost_aud", 0.0) + sdk_result.cost_aud,
                "duration_seconds": basic_result.get("duration_seconds", 0),
                "sdk_enhanced": True,
                "sdk_confidence": sdk_data.confidence_score,
            }
        else:
            logger.warning(f"SDK ICP enhancement failed: {sdk_result.error}")
            # Return original result if SDK fails
            return basic_result

    except Exception as e:
        logger.exception(f"SDK ICP enhancement error: {e}")
        # Return original result on error
        return basic_result


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
                text("""
                UPDATE icp_extraction_jobs
                SET status = 'completed',
                    completed_at = :now,
                    completed_steps = 8,
                    current_step = 'Complete',
                    extracted_icp = :icp
                WHERE id = :job_id
                """),
                {
                    "job_id": str(job_id),
                    "now": datetime.utcnow(),
                    "icp": json.dumps(result.get("profile", {}), cls=DateTimeEncoder),
                },
            )
            await db.commit()
            logger.info(f"Saved extraction result for job {job_id}")
            return True
        else:
            # Save error
            await db.execute(
                text("""
                UPDATE icp_extraction_jobs
                SET status = 'failed',
                    completed_at = :now,
                    error_message = :error
                WHERE id = :job_id
                """),
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
        # TEXT[] columns need Python lists - asyncpg handles list -> PostgreSQL array
        # JSONB columns (als_weights only) need JSON string with CAST
        await db.execute(
            text("""
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
                als_weights = CAST(:als_weights AS jsonb),
                icp_extracted_at = :now,
                icp_extraction_source = 'ai_extraction',
                icp_extraction_job_id = :job_id,
                updated_at = :now
            WHERE id = :client_id AND deleted_at IS NULL
            """),
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
                "als_weights": json.dumps(profile.get("als_weights", {})),
                "now": datetime.utcnow(),
                "job_id": str(job_id),
            },
        )
        await db.commit()

    logger.info(f"Applied ICP to client {client_id}")
    return True


@task(name="assign_client_resources", retries=2, retry_delay_seconds=5)
async def assign_client_resources_task(
    client_id: UUID,
    tier: str,
) -> dict[str, Any]:
    """
    Assign resources from pool to a new client based on tier.

    Called during onboarding after payment confirmation.
    Per RESOURCE_POOL.md spec.

    Args:
        client_id: Client UUID
        tier: Pricing tier ('ignition', 'velocity', 'dominance')

    Returns:
        Dict with assignment result including resource IDs
    """
    logger.info(f"Assigning resources to client {client_id} (tier: {tier})")

    try:
        async with get_db_session() as db:
            # Assign resources from pool
            assigned = await assign_resources_to_client(db, client_id, tier)

            # Check buffer status after assignment
            buffer_status = {}
            for resource_type in [ResourceType.EMAIL_DOMAIN, ResourceType.PHONE_NUMBER]:
                status = await check_buffer_and_alert(db, resource_type)
                buffer_status[resource_type.value] = status

            # Log any buffer warnings
            for rt, status in buffer_status.items():
                if status.get("status") in ("warning", "critical"):
                    logger.warning(
                        f"Resource pool buffer {status.get('status')}: "
                        f"{rt} - {status.get('message')}"
                    )

            return {
                "success": True,
                "client_id": str(client_id),
                "tier": tier,
                "assigned": {k: [str(v) for v in ids] for k, ids in assigned.items()},
                "total_resources": sum(len(ids) for ids in assigned.values()),
                "buffer_status": buffer_status,
            }

    except Exception as e:
        logger.exception(f"Resource assignment failed for client {client_id}: {e}")
        return {
            "success": False,
            "client_id": str(client_id),
            "tier": tier,
            "error": str(e),
        }


@task(name="scrape_client_intelligence", retries=1, timeout_seconds=600)
async def scrape_client_intelligence_task(
    job_id: UUID,
    client_id: UUID,
    config: ScrapeConfig | None = None,
) -> dict[str, Any]:
    """
    Scrape client intelligence data for SDK personalization.

    Scrapes:
    - Website (case studies, testimonials, services)
    - LinkedIn company page
    - Twitter/X, Facebook, Instagram profiles
    - Review platforms (Trustpilot, G2, Capterra, Google)

    Then uses AI to extract proof points for SDK agents.

    Args:
        job_id: Extraction job UUID
        client_id: Client UUID
        config: Optional scrape configuration

    Returns:
        Dict with scrape result summary
    """
    # Update progress
    await update_job_status_task(
        job_id=job_id,
        status="running",
        current_step="Scraping client intelligence",
        completed_steps=6,
    )

    try:
        engine = get_client_intelligence_engine()

        async with get_db_session() as db:
            # Run the full scrape
            result = await engine.scrape_client(
                db=db,
                client_id=client_id,
                config=config,
            )

            if result.success:
                # Save to database
                intel = await engine.save_to_database(
                    db=db,
                    client_id=client_id,
                    result=result,
                )

                logger.info(
                    f"Client intelligence scrape completed for {client_id}: "
                    f"{len(result.sources_scraped)} sources, ${result.total_cost_aud:.2f}"
                )

                return {
                    "success": True,
                    "sources_scraped": result.sources_scraped,
                    "total_cost_aud": float(result.total_cost_aud),
                    "errors": result.errors,
                    "intelligence_id": str(intel.id),
                }
            else:
                logger.warning(f"Client intelligence scrape failed: {result.errors}")
                return {
                    "success": False,
                    "sources_scraped": result.sources_scraped,
                    "errors": result.errors,
                }

    except Exception as e:
        logger.exception(f"Client intelligence scrape error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


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
    job_id: str | UUID,
    client_id: str | UUID,
    website_url: str,
    auto_apply: bool = True,
) -> dict[str, Any]:
    """
    Main onboarding flow for ICP extraction.

    Flow steps:
    1. Update job status to running
    2. Run basic ICP extraction (scraping + AI analysis)
    3. Enhance with SDK Agent (if enabled - adds research, pain points, buying signals)
    4. Save extraction result
    5. Optionally apply to client

    Args:
        job_id: Extraction job UUID (string or UUID)
        client_id: Client UUID (string or UUID)
        website_url: Website URL to analyze
        auto_apply: Whether to auto-apply ICP to client (default True)

    Returns:
        Dict with flow result
    """
    # Convert strings to UUIDs if needed (Prefect API passes strings)
    if isinstance(job_id, str):
        job_id = UUID(job_id)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting ICP onboarding flow for job {job_id}, URL: {website_url}")

    try:
        # Step 1: Update to running
        await update_job_status_task(
            job_id=job_id,
            status="running",
            current_step="Starting extraction",
            completed_steps=0,
        )

        # Step 2: Run basic extraction
        extraction_result = await run_icp_extraction_task(
            job_id=job_id,
            website_url=website_url,
        )

        # Step 3: Enhance with SDK (if enabled and basic succeeded)
        extraction_result = await enhance_icp_with_sdk_task(
            job_id=job_id,
            client_id=client_id,
            website_url=website_url,
            basic_result=extraction_result,
        )

        # Step 4: Save result
        await save_extraction_result_task(
            job_id=job_id,
            client_id=client_id,
            result=extraction_result,
        )

        # Step 5: Auto-apply if enabled and successful
        if auto_apply and extraction_result.get("success") and extraction_result.get("profile"):
            await apply_icp_to_client_task(
                client_id=client_id,
                profile=extraction_result["profile"],
                job_id=job_id,
            )

        # Step 6: Scrape client intelligence for SDK personalization
        intel_result = await scrape_client_intelligence_task(
            job_id=job_id,
            client_id=client_id,
        )

        return {
            "success": extraction_result.get("success", False),
            "job_id": str(job_id),
            "client_id": str(client_id),
            "website_url": website_url,
            "tokens_used": extraction_result.get("tokens_used", 0),
            "cost_aud": extraction_result.get("cost_aud", 0.0)
            + intel_result.get("total_cost_aud", 0.0),
            "duration_seconds": extraction_result.get("duration_seconds", 0),
            "sdk_enhanced": extraction_result.get("sdk_enhanced", False),
            "sdk_confidence": extraction_result.get("sdk_confidence"),
            "intel_sources_scraped": intel_result.get("sources_scraped", []),
            "intel_cost_aud": intel_result.get("total_cost_aud", 0.0),
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
    client_id: str | UUID,
    website_url: str,
) -> dict[str, Any]:
    """
    Re-extract ICP for an existing client.

    Used when client wants to refresh their ICP or update website.

    Args:
        client_id: Client UUID (string or UUID)
        website_url: New or updated website URL

    Returns:
        Dict with flow result
    """
    from uuid import uuid4

    # Convert strings to UUIDs if needed (Prefect API passes strings)
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    job_id = uuid4()

    # Create new extraction job
    async with get_db_session() as db:
        await db.execute(
            text("""
            INSERT INTO icp_extraction_jobs
            (id, client_id, status, website_url, created_at)
            VALUES (:id, :client_id, 'pending', :url, :now)
            """),
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


@flow(
    name="resource_assignment_flow",
    description="Assign resources from pool to client based on tier",
    retries=1,
    timeout_seconds=60,
)
async def resource_assignment_flow(
    client_id: str | UUID,
    tier: str,
) -> dict[str, Any]:
    """
    Standalone flow for resource assignment.

    Can be triggered by:
    - Stripe payment confirmed webhook
    - Admin manual trigger
    - Onboarding completion

    Per RESOURCE_POOL.md: Allocation trigger is **Payment confirmed** (Stripe webhook)

    Args:
        client_id: Client UUID (string or UUID)
        tier: Pricing tier ('ignition', 'velocity', 'dominance')

    Returns:
        Dict with assignment result
    """
    # Convert string to UUID if needed
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    logger.info(f"Starting resource assignment flow for client {client_id} (tier: {tier})")

    result = await assign_client_resources_task(
        client_id=client_id,
        tier=tier,
    )

    if result.get("success"):
        logger.info(
            f"Resource assignment completed for client {client_id}: "
            f"{result.get('total_resources')} resources assigned"
        )
    else:
        logger.error(f"Resource assignment failed for client {client_id}: {result.get('error')}")

    return result


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

    # Resource assignment flow deployment
    resource_deployment = Deployment.build_from_flow(
        flow=resource_assignment_flow,
        name="resource-assignment",
        work_queue_name="default",
        tags=["onboarding", "resources"],
    )
    resource_deployment.apply()

    logger.info("Deployed ICP onboarding and resource assignment flows")


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
- [x] Resource assignment task (assign_client_resources_task)
- [x] Resource assignment flow (resource_assignment_flow)
- [x] Deployment function for Prefect registration (includes resource assignment)
- [x] Type hints on all functions
- [x] Docstrings on all functions
"""
