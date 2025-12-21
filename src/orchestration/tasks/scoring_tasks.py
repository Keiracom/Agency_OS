"""
FILE: src/orchestration/tasks/scoring_tasks.py
PURPOSE: Prefect tasks for lead scoring via Scorer engine
PHASE: 5 (Orchestration)
TASK: ORC-007
DEPENDENCIES:
  - src/engines/scorer.py
  - src/models/lead.py
  - src/integrations/supabase.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: Import hierarchy (no other tasks)
  - Rule 14: Soft deletes only
"""

import logging
from typing import Any
from uuid import UUID

from prefect import task
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.scorer import ScorerEngine
from src.exceptions import ValidationError
from src.integrations.supabase import get_db_session
from src.models.base import LeadStatus
from src.models.lead import Lead

logger = logging.getLogger(__name__)


@task(
    name="score_lead",
    description="Score single lead via Scorer engine",
    retries=2,
    retry_delay_seconds=[30, 120],  # 30s, 2min
    tags=["scoring", "als"],
)
async def score_lead_task(
    lead_id: UUID,
) -> dict[str, Any]:
    """
    Score a single lead using ALS (Agency Lead Score) formula.

    Calculates 5-component score:
    - Data Quality (20 points)
    - Authority (25 points)
    - Company Fit (25 points)
    - Timing (15 points)
    - Risk (15 points, deductions)

    Args:
        lead_id: Lead UUID to score

    Returns:
        Scoring result with:
            - success: bool
            - lead_id: UUID
            - als_score: int (0-100)
            - als_tier: str (Hot/Warm/Cool/Cold/Dead)
            - components: dict with breakdown

    Raises:
        ValidationError: If lead not found
    """
    async with get_db_session() as db:
        # Fetch lead (check soft delete)
        stmt = select(Lead).where(
            and_(
                Lead.id == lead_id,
                Lead.deleted_at.is_(None),
            )
        )
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValidationError(
                message=f"Lead {lead_id} not found or deleted",
                field="lead_id",
            )

        # Ensure lead is enriched
        if lead.status == LeadStatus.NEW:
            raise ValidationError(
                message=f"Lead {lead_id} must be enriched before scoring",
                field="lead_status",
            )

        # === SCORING ===
        logger.info(f"Scoring lead {lead_id}")

        scorer = ScorerEngine()
        score_result = await scorer.score(db=db, lead_id=lead_id)

        if not score_result.success:
            raise ValidationError(
                message=f"Scoring failed: {score_result.error}",
                field="scoring",
            )

        logger.info(
            f"Successfully scored lead {lead_id}: "
            f"ALS {score_result.data['als_score']} ({score_result.data['als_tier']})"
        )

        return {
            "success": True,
            "lead_id": str(lead_id),
            "als_score": score_result.data["als_score"],
            "als_tier": score_result.data["als_tier"],
            "components": {
                "data_quality": score_result.data.get("als_data_quality", 0),
                "authority": score_result.data.get("als_authority", 0),
                "company_fit": score_result.data.get("als_company_fit", 0),
                "timing": score_result.data.get("als_timing", 0),
                "risk": score_result.data.get("als_risk", 0),
            },
        }


@task(
    name="score_batch",
    description="Score batch of leads",
    retries=2,
    retry_delay_seconds=[60, 300],  # 1min, 5min
    tags=["scoring", "batch"],
)
async def score_batch_task(
    lead_ids: list[UUID],
) -> dict[str, Any]:
    """
    Score a batch of leads.

    Args:
        lead_ids: List of lead UUIDs to score

    Returns:
        Batch result with:
            - total: int
            - successful: int
            - failed: int
            - tier_distribution: dict[str, int]
            - results: list[dict]
    """
    results = []
    successful = 0
    failed = 0
    tier_counts: dict[str, int] = {
        "Hot": 0,
        "Warm": 0,
        "Cool": 0,
        "Cold": 0,
        "Dead": 0,
    }

    for lead_id in lead_ids:
        try:
            result = await score_lead_task(lead_id)
            results.append(result)

            # Count tier distribution
            tier = result.get("als_tier", "Dead")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

            successful += 1

        except Exception as e:
            logger.error(f"Failed to score lead {lead_id}: {e}")
            results.append({
                "success": False,
                "lead_id": str(lead_id),
                "error": str(e),
            })
            failed += 1

    logger.info(
        f"Scored {successful}/{len(lead_ids)} leads. "
        f"Distribution: {tier_counts}"
    )

    return {
        "total": len(lead_ids),
        "successful": successful,
        "failed": failed,
        "tier_distribution": tier_counts,
        "results": results,
    }


@task(
    name="get_tier_distribution",
    description="Get ALS tier distribution for campaign",
    retries=1,
    retry_delay_seconds=30,
    tags=["scoring", "analytics"],
)
async def get_tier_distribution_task(
    campaign_id: UUID | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Get ALS tier distribution for a campaign or client.

    Args:
        campaign_id: Optional campaign UUID (filters to campaign)
        client_id: Optional client UUID (filters to client)

    Returns:
        Tier distribution with:
            - total_leads: int
            - tier_counts: dict[str, int]
            - tier_percentages: dict[str, float]
            - average_score: float

    Raises:
        ValidationError: If neither campaign_id nor client_id provided
    """
    if not campaign_id and not client_id:
        raise ValidationError(
            message="Either campaign_id or client_id must be provided",
            field="filters",
        )

    async with get_db_session() as db:
        # Build query
        stmt = select(
            Lead.als_tier,
            func.count(Lead.id).label("count"),
            func.avg(Lead.als_score).label("avg_score"),
        ).where(Lead.deleted_at.is_(None))

        # Apply filters
        if campaign_id:
            stmt = stmt.where(Lead.campaign_id == campaign_id)
        if client_id:
            stmt = stmt.where(Lead.client_id == client_id)

        # Group by tier
        stmt = stmt.group_by(Lead.als_tier)

        result = await db.execute(stmt)
        rows = result.all()

        # Build response
        total_leads = sum(row.count for row in rows)
        tier_counts = {row.als_tier or "Unscored": row.count for row in rows}
        tier_percentages = {
            tier: (count / total_leads * 100) if total_leads > 0 else 0
            for tier, count in tier_counts.items()
        }

        # Calculate average score
        avg_score_stmt = select(func.avg(Lead.als_score)).where(
            Lead.deleted_at.is_(None)
        )
        if campaign_id:
            avg_score_stmt = avg_score_stmt.where(Lead.campaign_id == campaign_id)
        if client_id:
            avg_score_stmt = avg_score_stmt.where(Lead.client_id == client_id)

        avg_result = await db.execute(avg_score_stmt)
        average_score = avg_result.scalar() or 0.0

        logger.info(
            f"Tier distribution for "
            f"{'campaign ' + str(campaign_id) if campaign_id else 'client ' + str(client_id)}: "
            f"{tier_counts}"
        )

        return {
            "total_leads": total_leads,
            "tier_counts": tier_counts,
            "tier_percentages": tier_percentages,
            "average_score": float(average_score),
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session obtained via get_db_session()
# [x] No imports from other tasks (only engines)
# [x] Soft delete check in queries (deleted_at IS NULL)
# [x] All tasks use @task decorator with retries
# [x] Proper logging
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] ALS scoring via Scorer engine
# [x] Tier distribution analytics
