"""
FILE: src/orchestration/flows/lead_enrichment_flow.py
PURPOSE: Enrich assigned leads with LinkedIn data and Claude analysis
PHASE: 24A+ (Enhanced Lead Enrichment)
TASK: ENRICH-002
DEPENDENCIES:
  - src/engines/scout.py
  - src/engines/scorer.py
  - src/agents/skills/research_skills.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 13: JIT validation before enrichment

ENRICHMENT WATERFALL:
  Stage 1: Apollo data (already in pool from population)
  Stage 2: Apify LinkedIn person scrape (profile + posts)
  Stage 3: Apify LinkedIn company scrape (profile + posts)
  Stage 4: Claude analysis (pain points, personalization, hooks)
  Stage 5: ALS scoring with enhanced signals
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import text

from src.agents.skills.research_skills import PersonalizationAnalysisSkill
from src.engines.scorer import get_scorer_engine
from src.engines.scout import get_scout_engine
from src.integrations.anthropic import get_anthropic_client
from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# ============================================
# TASKS
# ============================================


@task(name="get_assignment_for_enrichment", retries=2, retry_delay_seconds=5)
async def get_assignment_for_enrichment_task(
    assignment_id: str,
) -> dict[str, Any]:
    """
    Get assignment data needed for enrichment.

    Args:
        assignment_id: Lead assignment UUID string

    Returns:
        Dict with assignment and pool lead data
    """
    async with get_db_session() as db:
        query = text("""
            SELECT
                la.id as assignment_id,
                la.client_id,
                la.campaign_id,
                la.enrichment_status,
                lp.id as lead_pool_id,
                lp.email,
                lp.first_name,
                lp.last_name,
                lp.title,
                lp.linkedin_url,
                lp.company_name,
                lp.company_domain,
                lp.company_linkedin_url,
                lp.company_industry,
                c.website as agency_website,
                c.description as agency_description
            FROM lead_assignments la
            JOIN lead_pool lp ON la.lead_pool_id = lp.id
            JOIN clients c ON la.client_id = c.id
            WHERE la.id = :assignment_id
            AND la.status = 'active'
        """)

        result = await db.execute(query, {"assignment_id": assignment_id})
        row = result.fetchone()

        if not row:
            raise ValueError(f"Assignment {assignment_id} not found or not active")

        return {
            "assignment_id": str(row.assignment_id),
            "client_id": str(row.client_id),
            "campaign_id": str(row.campaign_id) if row.campaign_id else None,
            "enrichment_status": row.enrichment_status,
            "lead_pool_id": str(row.lead_pool_id),
            "email": row.email,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "title": row.title,
            "linkedin_url": row.linkedin_url,
            "company_name": row.company_name,
            "company_domain": row.company_domain,
            "company_linkedin_url": row.company_linkedin_url,
            "company_industry": row.company_industry,
            "agency_website": row.agency_website,
            "agency_description": row.agency_description,
        }


@task(name="scrape_linkedin_data", retries=2, retry_delay_seconds=10)
async def scrape_linkedin_data_task(
    assignment_id: str,
    linkedin_person_url: str | None,
    linkedin_company_url: str | None,
) -> dict[str, Any]:
    """
    Scrape LinkedIn data for person and company.

    Args:
        assignment_id: Lead assignment UUID
        linkedin_person_url: Person's LinkedIn URL
        linkedin_company_url: Company's LinkedIn URL

    Returns:
        Dict with person and company LinkedIn data
    """
    async with get_db_session() as db:
        scout = get_scout_engine()

        result = await scout.enrich_linkedin_for_assignment(
            db=db,
            assignment_id=UUID(assignment_id),
            linkedin_person_url=linkedin_person_url,
            linkedin_company_url=linkedin_company_url,
        )

        if result.success:
            logger.info(
                f"LinkedIn scrape complete for {assignment_id}: "
                f"{result.data['person_posts_found']} person posts, "
                f"{result.data['company_posts_found']} company posts"
            )
            return {
                "success": True,
                "person_data": result.data.get("person_data"),
                "company_data": result.data.get("company_data"),
            }
        else:
            logger.warning(f"LinkedIn scrape failed for {assignment_id}: {result.error}")
            return {
                "success": False,
                "error": result.error,
            }


@task(name="analyze_for_personalization", retries=2, retry_delay_seconds=10)
async def analyze_for_personalization_task(
    assignment_id: str,
    lead_data: dict[str, Any],
    person_linkedin: dict[str, Any] | None,
    company_linkedin: dict[str, Any] | None,
    agency_services: str,
) -> dict[str, Any]:
    """
    Run Claude analysis to generate personalization data.

    Args:
        assignment_id: Lead assignment UUID
        lead_data: Basic lead info
        person_linkedin: Person LinkedIn data
        company_linkedin: Company LinkedIn data
        agency_services: Agency's service description

    Returns:
        Dict with pain points, personalization angles, and hooks
    """
    anthropic = get_anthropic_client()
    skill = PersonalizationAnalysisSkill()

    # Build skill input
    skill_input = skill.Input(
        first_name=lead_data.get("first_name", ""),
        last_name=lead_data.get("last_name", ""),
        title=lead_data.get("title", ""),
        company_name=lead_data.get("company_name", ""),
        industry=lead_data.get("company_industry", ""),
        person_headline=person_linkedin.get("headline", "") if person_linkedin else "",
        person_about=person_linkedin.get("about", "") if person_linkedin else "",
        person_posts=person_linkedin.get("posts", []) if person_linkedin else [],
        company_description=company_linkedin.get("description", "") if company_linkedin else "",
        company_specialties=company_linkedin.get("specialties", []) if company_linkedin else [],
        company_posts=company_linkedin.get("posts", []) if company_linkedin else [],
        agency_services=agency_services,
    )

    result = await skill.run(skill_input, anthropic)

    if result.success:
        output = result.data
        logger.info(
            f"Personalization analysis complete for {assignment_id}: "
            f"{len(output.pain_points)} pain points, "
            f"best channel: {output.best_channel}"
        )

        # Update assignment with personalization data
        async with get_db_session() as db:
            import json
            update_query = text("""
                UPDATE lead_assignments
                SET
                    personalization_data = :personalization_data,
                    pain_points = :pain_points,
                    icebreaker_hooks = :icebreaker_hooks,
                    best_channel = :best_channel,
                    personalization_confidence = :confidence,
                    personalization_analyzed_at = NOW(),
                    enrichment_status = 'analysis_complete',
                    updated_at = NOW()
                WHERE id = :assignment_id
            """)

            await db.execute(update_query, {
                "assignment_id": assignment_id,
                "personalization_data": json.dumps({
                    "pain_points": output.pain_points,
                    "personalization_angles": output.personalization_angles,
                    "topics_to_avoid": output.topics_to_avoid,
                    "common_ground": output.common_ground,
                    "best_timing": output.best_timing,
                }),
                "pain_points": output.pain_points,
                "icebreaker_hooks": json.dumps(output.icebreaker_hooks),
                "best_channel": output.best_channel,
                "confidence": output.confidence,
            })
            await db.commit()

        return {
            "success": True,
            "pain_points": output.pain_points,
            "personalization_angles": output.personalization_angles,
            "icebreaker_hooks": output.icebreaker_hooks,
            "best_channel": output.best_channel,
            "confidence": output.confidence,
            "tokens_used": result.tokens_used,
            "cost_aud": result.cost_aud,
        }
    else:
        logger.warning(f"Personalization analysis failed for {assignment_id}: {result.error}")
        return {
            "success": False,
            "error": result.error,
        }


@task(name="score_enriched_lead", retries=2, retry_delay_seconds=5)
async def score_enriched_lead_task(
    assignment_id: str,
    lead_pool_id: str,
    target_industries: list[str] | None = None,
) -> dict[str, Any]:
    """
    Calculate ALS score for an enriched lead.

    Args:
        assignment_id: Lead assignment UUID
        lead_pool_id: Lead pool UUID
        target_industries: Target industries for scoring

    Returns:
        Dict with ALS score and tier
    """
    async with get_db_session() as db:
        scorer = get_scorer_engine()

        # Phase 24A+: Pass assignment_id for LinkedIn boost calculation
        result = await scorer.score_pool_lead(
            db=db,
            lead_pool_id=UUID(lead_pool_id),
            target_industries=target_industries,
            assignment_id=UUID(assignment_id),
        )

        if result.success:
            # Update assignment with score
            update_query = text("""
                UPDATE lead_assignments
                SET
                    als_score = :als_score,
                    als_tier = :als_tier,
                    als_components = :als_components,
                    scored_at = NOW(),
                    enrichment_status = 'completed',
                    enrichment_completed_at = NOW(),
                    updated_at = NOW()
                WHERE id = :assignment_id
            """)

            import json
            await db.execute(update_query, {
                "assignment_id": assignment_id,
                "als_score": result.data["als_score"],
                "als_tier": result.data["als_tier"],
                "als_components": json.dumps(result.data.get("als_components", {})),
            })
            await db.commit()

            linkedin_boost = result.data.get("linkedin_boost", 0)
            logger.info(
                f"Scored assignment {assignment_id}: "
                f"{result.data['als_score']} ({result.data['als_tier']} tier)"
                f"{f', LinkedIn boost +{linkedin_boost}' if linkedin_boost else ''}"
            )

            return {
                "success": True,
                "als_score": result.data["als_score"],
                "als_tier": result.data["als_tier"],
                "linkedin_boost": linkedin_boost,
                "linkedin_signals": result.data.get("linkedin_signals", []),
            }
        else:
            logger.warning(f"Scoring failed for {assignment_id}: {result.error}")
            return {
                "success": False,
                "error": result.error,
            }


# ============================================
# MAIN FLOW
# ============================================


@flow(
    name="lead_enrichment",
    description="Enrich assigned lead with LinkedIn data and Claude analysis",
    task_runner=ConcurrentTaskRunner(max_workers=5),
    retries=1,
    retry_delay_seconds=30,
)
async def lead_enrichment_flow(
    assignment_id: str,
) -> dict[str, Any]:
    """
    Full enrichment waterfall for an assigned lead.

    Stages:
    1. Get assignment data
    2. Scrape LinkedIn (person + company)
    3. Claude analysis (pain points, hooks)
    4. ALS scoring

    Args:
        assignment_id: Lead assignment UUID string

    Returns:
        Dict with enrichment summary
    """
    logger.info(f"Starting enrichment for assignment {assignment_id}")

    # Stage 1: Get assignment data
    assignment_data = await get_assignment_for_enrichment_task(
        assignment_id=assignment_id
    )

    # Update status to in_progress
    async with get_db_session() as db:
        await db.execute(
            text("""
                UPDATE lead_assignments
                SET enrichment_status = 'in_progress',
                    enrichment_started_at = NOW(),
                    updated_at = NOW()
                WHERE id = :assignment_id
            """),
            {"assignment_id": assignment_id}
        )
        await db.commit()

    # Stage 2: Scrape LinkedIn data
    linkedin_result = await scrape_linkedin_data_task(
        assignment_id=assignment_id,
        linkedin_person_url=assignment_data.get("linkedin_url"),
        linkedin_company_url=assignment_data.get("company_linkedin_url"),
    )

    # Stage 3: Claude analysis
    analysis_result = await analyze_for_personalization_task(
        assignment_id=assignment_id,
        lead_data=assignment_data,
        person_linkedin=linkedin_result.get("person_data") if linkedin_result.get("success") else None,
        company_linkedin=linkedin_result.get("company_data") if linkedin_result.get("success") else None,
        agency_services=assignment_data.get("agency_description", ""),
    )

    # Stage 4: ALS scoring
    scoring_result = await score_enriched_lead_task(
        assignment_id=assignment_id,
        lead_pool_id=assignment_data["lead_pool_id"],
        target_industries=[assignment_data.get("company_industry")] if assignment_data.get("company_industry") else None,
    )

    # Compile summary
    summary = {
        "assignment_id": assignment_id,
        "lead_name": f"{assignment_data.get('first_name', '')} {assignment_data.get('last_name', '')}".strip(),
        "company": assignment_data.get("company_name"),
        "linkedin_scraped": linkedin_result.get("success", False),
        "person_posts_found": linkedin_result.get("person_data", {}).get("posts_count", 0) if linkedin_result.get("success") else 0,
        "company_posts_found": linkedin_result.get("company_data", {}).get("posts_count", 0) if linkedin_result.get("success") else 0,
        "analysis_complete": analysis_result.get("success", False),
        "pain_points_found": len(analysis_result.get("pain_points", [])) if analysis_result.get("success") else 0,
        "best_channel": analysis_result.get("best_channel") if analysis_result.get("success") else None,
        "als_score": scoring_result.get("als_score") if scoring_result.get("success") else None,
        "als_tier": scoring_result.get("als_tier") if scoring_result.get("success") else None,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Enrichment complete for {summary['lead_name']}: "
        f"ALS {summary['als_score']} ({summary['als_tier']}), "
        f"best channel: {summary['best_channel']}"
    )

    return summary


@flow(
    name="batch_lead_enrichment",
    description="Enrich multiple assigned leads",
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
async def batch_lead_enrichment_flow(
    assignment_ids: list[str],
) -> dict[str, Any]:
    """
    Enrich a batch of assigned leads.

    Args:
        assignment_ids: List of assignment UUID strings

    Returns:
        Dict with batch summary
    """
    logger.info(f"Starting batch enrichment for {len(assignment_ids)} assignments")

    results = []
    for assignment_id in assignment_ids:
        try:
            result = await lead_enrichment_flow(assignment_id=assignment_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Enrichment failed for {assignment_id}: {e}")
            results.append({
                "assignment_id": assignment_id,
                "success": False,
                "error": str(e),
            })

    # Compile batch summary
    successful = [r for r in results if r.get("als_score") is not None]
    failed = [r for r in results if r.get("als_score") is None]

    tier_distribution = {}
    for r in successful:
        tier = r.get("als_tier", "unknown")
        tier_distribution[tier] = tier_distribution.get(tier, 0) + 1

    summary = {
        "total": len(assignment_ids),
        "successful": len(successful),
        "failed": len(failed),
        "tier_distribution": tier_distribution,
        "average_score": sum(r.get("als_score", 0) for r in successful) / len(successful) if successful else 0,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Batch enrichment complete: {summary['successful']}/{summary['total']} successful, "
        f"avg score: {summary['average_score']:.1f}"
    )

    return summary


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] No hardcoded credentials
# [x] Session passed via get_db_session() context manager
# [x] Uses ScoutEngine for LinkedIn scraping
# [x] Uses PersonalizationAnalysisSkill for Claude analysis
# [x] Uses ScorerEngine for ALS scoring
# [x] Updates lead_assignments with enrichment data
# [x] @flow and @task decorators from Prefect
# [x] Proper error handling with retries
# [x] Logging throughout
# [x] All functions have type hints
# [x] All functions have docstrings
