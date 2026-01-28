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

from src.agents.sdk_agents import (
    should_use_sdk_enrichment,
)
from src.agents.sdk_agents.email_agent import run_sdk_email
from src.agents.sdk_agents.enrichment_agent import run_sdk_enrichment
from src.agents.sdk_agents.voice_kb_agent import run_sdk_voice_kb
from src.agents.skills.research_skills import PersonalizationAnalysisSkill
from src.engines.scorer import get_scorer_engine
from src.engines.scout import get_scout_engine
from src.integrations.anthropic import get_anthropic_client
from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTIONS
# ============================================


async def get_client_intelligence_for_sdk(client_id: str) -> dict[str, Any] | None:
    """
    Fetch client intelligence data for SDK personalization.

    Args:
        client_id: Client UUID string

    Returns:
        Dict with proof points or None if not available
    """
    async with get_db_session() as db:
        query = text("""
            SELECT
                proof_metrics,
                proof_clients,
                proof_industries,
                common_pain_points,
                differentiators,
                website_testimonials,
                website_case_studies,
                g2_rating,
                g2_review_count,
                capterra_rating,
                capterra_review_count,
                trustpilot_rating,
                trustpilot_review_count,
                google_rating,
                google_review_count
            FROM client_intelligence
            WHERE client_id = :client_id
            AND deleted_at IS NULL
        """)

        result = await db.execute(query, {"client_id": client_id})
        row = result.fetchone()

        if not row:
            return None

        return {
            "proof_metrics": row.proof_metrics or [],
            "proof_clients": row.proof_clients or [],
            "proof_industries": row.proof_industries or [],
            "common_pain_points": row.common_pain_points or [],
            "differentiators": row.differentiators or [],
            "testimonials": row.website_testimonials or [],
            "case_studies": row.website_case_studies or [],
            "ratings": {
                "g2": {"rating": float(row.g2_rating) if row.g2_rating else None, "count": row.g2_review_count},
                "capterra": {"rating": float(row.capterra_rating) if row.capterra_rating else None, "count": row.capterra_review_count},
                "trustpilot": {"rating": float(row.trustpilot_rating) if row.trustpilot_rating else None, "count": row.trustpilot_review_count},
                "google": {"rating": float(row.google_rating) if row.google_rating else None, "count": row.google_review_count},
            },
        }


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


@task(name="sdk_enrich_hot_assignment", retries=2, retry_delay_seconds=10)
async def sdk_enrich_hot_assignment_task(
    assignment_id: str,
    lead_data: dict[str, Any],
    signals: list[str],
) -> dict[str, Any]:
    """
    Run SDK enrichment for a Hot lead assignment.

    This task performs deep web research using Claude SDK to find
    funding, hiring, news, and personalization opportunities.

    Args:
        assignment_id: Lead assignment UUID string
        lead_data: Lead info for SDK agent
        signals: Priority signals that triggered SDK

    Returns:
        Dict with SDK enrichment data
    """
    try:
        result = await run_sdk_enrichment(lead_data)

        if result.success and result.parsed_data:
            # Store SDK enrichment in assignment
            async with get_db_session() as db:
                import json
                update_query = text("""
                    UPDATE lead_assignments
                    SET
                        sdk_enrichment = :sdk_enrichment,
                        sdk_signals = :sdk_signals,
                        sdk_cost_aud = :sdk_cost,
                        sdk_enriched_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :assignment_id
                """)

                await db.execute(update_query, {
                    "assignment_id": assignment_id,
                    "sdk_enrichment": json.dumps(result.parsed_data),
                    "sdk_signals": signals,
                    "sdk_cost": result.cost_aud or 0,
                })
                await db.commit()

            logger.info(
                f"SDK enrichment complete for {assignment_id}: "
                f"signals={signals}, cost=${result.cost_aud:.2f}"
            )

            return {
                "success": True,
                "assignment_id": assignment_id,
                "sdk_enrichment": result.parsed_data,
                "sdk_cost_aud": result.cost_aud,
                "signals": signals,
            }
        else:
            logger.warning(f"SDK enrichment failed for {assignment_id}: {result.error}")
            return {
                "success": False,
                "assignment_id": assignment_id,
                "error": result.error,
            }
    except Exception as e:
        logger.exception(f"SDK enrichment error for {assignment_id}: {e}")
        return {
            "success": False,
            "assignment_id": assignment_id,
            "error": str(e),
        }


@task(name="sdk_generate_email_for_assignment", retries=2, retry_delay_seconds=10)
async def sdk_generate_email_for_assignment_task(
    assignment_id: str,
    client_id: str,
    lead_data: dict[str, Any],
    sdk_enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate SDK-powered email for a Hot lead assignment.

    Args:
        assignment_id: Lead assignment UUID string
        client_id: Client UUID string (for fetching client intelligence)
        lead_data: Lead info
        sdk_enrichment: Optional SDK enrichment data

    Returns:
        Dict with generated email
    """
    try:
        # Fetch client intelligence for proof points
        client_intelligence = await get_client_intelligence_for_sdk(client_id)

        result = await run_sdk_email(
            lead_data=lead_data,
            enrichment_data=sdk_enrichment,
            client_intelligence=client_intelligence,
        )

        if result.success and result.parsed_data:
            # Store SDK email in assignment
            async with get_db_session() as db:
                import json
                update_query = text("""
                    UPDATE lead_assignments
                    SET
                        sdk_email_content = :sdk_email,
                        updated_at = NOW()
                    WHERE id = :assignment_id
                """)

                await db.execute(update_query, {
                    "assignment_id": assignment_id,
                    "sdk_email": json.dumps(result.parsed_data),
                })
                await db.commit()

            logger.info(f"SDK email generated for {assignment_id}")

            return {
                "success": True,
                "assignment_id": assignment_id,
                "subject": result.parsed_data.get("subject"),
                "body": result.parsed_data.get("body"),
                "sdk_cost_aud": result.cost_aud,
            }
        else:
            logger.warning(f"SDK email generation failed for {assignment_id}: {result.error}")
            return {
                "success": False,
                "assignment_id": assignment_id,
                "error": result.error,
            }
    except Exception as e:
        logger.exception(f"SDK email error for {assignment_id}: {e}")
        return {
            "success": False,
            "assignment_id": assignment_id,
            "error": str(e),
        }


@task(name="sdk_generate_voice_kb_for_assignment", retries=2, retry_delay_seconds=10)
async def sdk_generate_voice_kb_for_assignment_task(
    assignment_id: str,
    client_id: str,
    lead_data: dict[str, Any],
    sdk_enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate SDK-powered voice knowledge base for a Hot lead assignment.

    Args:
        assignment_id: Lead assignment UUID string
        client_id: Client UUID string (for fetching client intelligence)
        lead_data: Lead info
        sdk_enrichment: Optional SDK enrichment data

    Returns:
        Dict with voice KB
    """
    try:
        # Fetch client intelligence for proof points
        client_intelligence = await get_client_intelligence_for_sdk(client_id)

        result = await run_sdk_voice_kb(
            lead_data=lead_data,
            enrichment_data=sdk_enrichment,
            client_intelligence=client_intelligence,
        )

        if result.success and result.parsed_data:
            # Store SDK voice KB in assignment
            async with get_db_session() as db:
                import json
                update_query = text("""
                    UPDATE lead_assignments
                    SET
                        sdk_voice_kb = :sdk_voice_kb,
                        updated_at = NOW()
                    WHERE id = :assignment_id
                """)

                await db.execute(update_query, {
                    "assignment_id": assignment_id,
                    "sdk_voice_kb": json.dumps(result.parsed_data),
                })
                await db.commit()

            logger.info(f"SDK voice KB generated for {assignment_id}")

            return {
                "success": True,
                "assignment_id": assignment_id,
                "voice_kb": result.parsed_data,
                "sdk_cost_aud": result.cost_aud,
            }
        else:
            logger.warning(f"SDK voice KB failed for {assignment_id}: {result.error}")
            return {
                "success": False,
                "assignment_id": assignment_id,
                "error": result.error,
            }
    except Exception as e:
        logger.exception(f"SDK voice KB error for {assignment_id}: {e}")
        return {
            "success": False,
            "assignment_id": assignment_id,
            "error": str(e),
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

    # Stage 5: SDK processing for Hot leads (ALS 85+)
    sdk_enrichment_result = None
    sdk_email_result = None
    sdk_voice_kb_result = None
    total_sdk_cost = 0.0

    if scoring_result.get("success") and scoring_result.get("als_score", 0) >= 85:
        als_score = scoring_result["als_score"]
        logger.info(f"Hot lead detected (ALS {als_score}), starting SDK processing")

        # Build lead_data for SDK agents
        lead_data = {
            "first_name": assignment_data.get("first_name", ""),
            "last_name": assignment_data.get("last_name", ""),
            "title": assignment_data.get("title", ""),
            "company_name": assignment_data.get("company_name", ""),
            "company_domain": assignment_data.get("company_domain", ""),
            "company_industry": assignment_data.get("company_industry", ""),
            "linkedin_url": assignment_data.get("linkedin_url", ""),
            "als_score": als_score,
        }

        # Check if SDK enrichment should run (Hot + signals)
        sdk_eligible, sdk_signals = should_use_sdk_enrichment({
            "als_score": als_score,
            "company_employee_count": assignment_data.get("company_employee_count"),
        })

        if sdk_eligible and sdk_signals:
            # Stage 5a: SDK deep enrichment (for Hot leads with signals)
            sdk_enrichment_result = await sdk_enrich_hot_assignment_task(
                assignment_id=assignment_id,
                lead_data=lead_data,
                signals=sdk_signals,
            )
            if sdk_enrichment_result.get("success"):
                total_sdk_cost += sdk_enrichment_result.get("sdk_cost_aud", 0)

        # Stage 5b: SDK email generation (for ALL Hot leads)
        sdk_enrichment_data = sdk_enrichment_result.get("sdk_enrichment") if sdk_enrichment_result and sdk_enrichment_result.get("success") else None
        sdk_email_result = await sdk_generate_email_for_assignment_task(
            assignment_id=assignment_id,
            client_id=assignment_data["client_id"],
            lead_data=lead_data,
            sdk_enrichment=sdk_enrichment_data,
        )
        if sdk_email_result.get("success"):
            total_sdk_cost += sdk_email_result.get("sdk_cost_aud", 0)

        # Stage 5c: SDK voice KB generation (for ALL Hot leads)
        sdk_voice_kb_result = await sdk_generate_voice_kb_for_assignment_task(
            assignment_id=assignment_id,
            client_id=assignment_data["client_id"],
            lead_data=lead_data,
            sdk_enrichment=sdk_enrichment_data,
        )
        if sdk_voice_kb_result.get("success"):
            total_sdk_cost += sdk_voice_kb_result.get("sdk_cost_aud", 0)

        logger.info(
            f"SDK processing complete for Hot lead {assignment_id}: "
            f"enrichment={sdk_enrichment_result.get('success') if sdk_enrichment_result else 'skipped'}, "
            f"email={sdk_email_result.get('success')}, "
            f"voice_kb={sdk_voice_kb_result.get('success')}, "
            f"total_cost=${total_sdk_cost:.2f}"
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
        # SDK results
        "sdk_enriched": sdk_enrichment_result.get("success") if sdk_enrichment_result else False,
        "sdk_email_generated": sdk_email_result.get("success") if sdk_email_result else False,
        "sdk_voice_kb_generated": sdk_voice_kb_result.get("success") if sdk_voice_kb_result else False,
        "sdk_total_cost_aud": total_sdk_cost,
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(
        f"Enrichment complete for {summary['lead_name']}: "
        f"ALS {summary['als_score']} ({summary['als_tier']}), "
        f"best channel: {summary['best_channel']}"
        f"{f', SDK cost: ${total_sdk_cost:.2f}' if total_sdk_cost > 0 else ''}"
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
