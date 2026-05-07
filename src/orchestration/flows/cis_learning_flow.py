"""
CIS Learning Engine Flow
Directive #147: Weekly weight adjustment based on outcomes

ARCHITECTURE:
1. Query outcomes since last run
2. Threshold check (>= 20 MEETING_BOOKED)
3. Claude analysis via sdk_brain
4. Apply deltas with ±5 cap
5. Log all changes to cis_adjustment_log

PROPRIETARY: Weights never in code, only in ceo:propensity_weights_v3

This is the moat. The CIS Learning Engine makes Agency OS smarter over time
by analyzing what outreach patterns lead to booked meetings and adjusting
propensity weights accordingly.

Contract: src/orchestration/flows/cis_learning_flow.py
Purpose: CIS Learning Engine weekly weight optimization
Layer: 4 - orchestration
Imports: services, integrations
Consumers: Prefect scheduler
"""

import json
import os

from prefect import flow, get_run_logger, task

from src.integrations.supabase import get_db_session
from src.prefect_utils.completion_hook import on_completion_hook
from src.prefect_utils.hooks import on_failure_hook
from src.services.cis_outcome_service import (
    count_meeting_booked_outcomes,
    get_outcomes_since_last_run,
    get_propensity_weights,
    log_cis_run_complete,
    log_cis_run_start,
    log_weight_adjustment,
    save_propensity_weights,
)

CEO_MEMORY_WEIGHTS_KEY = "ceo:propensity_weights_v3"
MIN_OUTCOMES_THRESHOLD = int(os.environ.get("CIS_MIN_OUTCOMES_THRESHOLD", "20"))
MAX_DELTA_PER_RUN = 5


@task(name="cis-query-outcomes")
async def query_outcomes(customer_id: str | None = None) -> list[dict]:
    """
    Query outcomes for CIS analysis.

    Fetches all outcomes since last CIS run with signals_active data.
    """
    async with get_db_session() as db:
        return await get_outcomes_since_last_run(db, customer_id)


@task(name="cis-check-threshold")
async def check_threshold(customer_id: str | None = None) -> tuple[bool, int]:
    """
    Check if we have enough MEETING_BOOKED outcomes.

    Requires >= 20 meeting_booked outcomes for statistical significance.
    """
    async with get_db_session() as db:
        count = await count_meeting_booked_outcomes(db, customer_id)
        return count >= MIN_OUTCOMES_THRESHOLD, count


@task(name="cis-get-weights")
async def get_current_weights() -> dict:
    """
    Fetch current weights from ceo_memory.

    Weights are stored at ceo:propensity_weights_v3 in Supabase.
    """
    async with get_db_session() as db:
        return await get_propensity_weights(db)


@task(name="cis-claude-analysis")
async def analyze_with_claude(
    outcomes: list[dict],
    weights: dict,
) -> dict:
    """
    Run Claude analysis on outcomes.

    Calls SiegeSDKIntelligence.analyze_cis_outcomes() which uses
    Claude Sonnet 4 with a $2 AUD cost cap.
    """
    raise NotImplementedError("dead path: sdk_brain removed in PR-A #593")


@task(name="cis-apply-deltas")
async def apply_weight_deltas(
    current_weights: dict,
    adjustments: dict,
    outcome_sample_size: int,
    run_id: str,
) -> dict:
    """
    Apply deltas to weights with ±5 cap.
    Log all changes to cis_adjustment_log.

    This task:
    1. Iterates through proposed adjustments
    2. Skips low confidence (<0.7) adjustments
    3. Caps deltas at ±5 per signal
    4. Logs every adjustment (applied or skipped) for audit
    5. Returns updated weights dict
    """
    logger = get_run_logger()
    updated_weights = json.loads(json.dumps(current_weights))  # Deep copy

    async with get_db_session() as db:
        for signal_name, adjustment in adjustments.items():
            delta = adjustment.get("delta", 0)
            confidence = adjustment.get("confidence", 0)
            reasoning = adjustment.get("reasoning", "")

            # Determine if this is a positive or negative signal
            is_negative = signal_name in current_weights.get("negative", {})
            weight_section = "negative" if is_negative else "weights"

            # Get current weight
            weight_before = current_weights.get(weight_section, {}).get(signal_name, 0)

            # Skip low confidence adjustments
            if confidence < 0.7:
                await log_weight_adjustment(
                    db=db,
                    customer_id=None,  # Global weights
                    signal_name=signal_name,
                    weight_before=weight_before,
                    delta_applied=0,
                    weight_after=weight_before,
                    confidence_score=confidence,
                    outcome_sample_size=outcome_sample_size,
                    skipped=True,
                    skip_reason=f"Confidence {confidence:.2f} < 0.7 threshold",
                    run_id=run_id,
                )
                logger.info(
                    f"Skipped {signal_name}: confidence {confidence:.2f} < 0.7 "
                    f"(reasoning: {reasoning})"
                )
                continue

            # Cap delta at ±5
            capped_delta = max(-MAX_DELTA_PER_RUN, min(MAX_DELTA_PER_RUN, delta))
            if capped_delta != delta:
                logger.info(f"Capped {signal_name} delta: {delta} → {capped_delta}")

            # Calculate new weight
            weight_after = weight_before + capped_delta

            # Update weights dict
            if weight_section not in updated_weights:
                updated_weights[weight_section] = {}
            updated_weights[weight_section][signal_name] = weight_after

            # Log the adjustment
            await log_weight_adjustment(
                db=db,
                customer_id=None,
                signal_name=signal_name,
                weight_before=weight_before,
                delta_applied=capped_delta,
                weight_after=weight_after,
                confidence_score=confidence,
                outcome_sample_size=outcome_sample_size,
                skipped=False,
                skip_reason=None,
                run_id=run_id,
            )

            logger.info(
                f"✓ Adjusted {signal_name}: {weight_before} + {capped_delta} = {weight_after} "
                f"(confidence: {confidence:.2f}, reasoning: {reasoning})"
            )

    return updated_weights


@task(name="cis-save-weights")
async def save_updated_weights(weights: dict) -> bool:
    """
    Write updated weights back to ceo_memory.

    Performs upsert to ceo:propensity_weights_v3 in Supabase.
    """
    async with get_db_session() as db:
        result = await save_propensity_weights(db, weights)
        return result.get("success", False)


@task(name="cis-log-run-start")
async def start_cis_run(
    run_type: str = "weekly",
    customer_id: str | None = None,
) -> str:
    """Log the start of a CIS run."""
    async with get_db_session() as db:
        return await log_cis_run_start(db, run_type, customer_id)


@task(name="cis-log-run-complete")
async def complete_cis_run(
    run_id: str,
    status: str,
    outcomes_analyzed: int = 0,
    adjustments_applied: int = 0,
    summary: str = "",
) -> bool:
    """Log the completion of a CIS run."""
    async with get_db_session() as db:
        result = await log_cis_run_complete(
            db, run_id, status, outcomes_analyzed, adjustments_applied, summary
        )
        return result.get("success", False)


@flow(
    name="cis-learning-engine",
    log_prints=True,
    on_completion=[on_completion_hook],
    on_failure=[on_failure_hook],
)
async def cis_learning_flow(
    customer_id: str | None = None,
    run_type: str = "weekly",
):
    """
    CIS Learning Engine — Weekly weight adjustment.

    Directive #147: Makes Agency OS smarter over time.
    This is the moat.

    The flow:
    1. Checks threshold (need >= 20 MEETING_BOOKED outcomes)
    2. Queries all outcomes since last run
    3. Fetches current propensity weights from ceo_memory
    4. Calls Claude Sonnet 4 to analyze patterns
    5. Applies weight deltas (capped at ±5 per signal)
    6. Saves updated weights back to ceo_memory
    7. Logs everything to cis_adjustment_log for audit

    Args:
        customer_id: Optional customer filter (None = global weights)
        run_type: Type of run (weekly, manual, triggered)

    Returns:
        Dict with status, outcomes_analyzed, adjustments_applied, summary
    """
    logger = get_run_logger()
    logger.info("🧠 CIS Learning Engine starting...")
    logger.info(f"   Run type: {run_type}")
    logger.info(f"   Customer filter: {customer_id or 'global'}")

    # Start run logging
    run_id = await start_cis_run(run_type, customer_id)
    logger.info(f"   Run ID: {run_id}")

    # Step 1: Check threshold
    has_enough, count = await check_threshold(customer_id)

    if not has_enough:
        logger.info(f"⏸️  CIS_PENDING — insufficient data ({count} < {MIN_OUTCOMES_THRESHOLD})")

        await complete_cis_run(
            run_id=run_id,
            status="pending",
            outcomes_analyzed=0,
            adjustments_applied=0,
            summary=f"Insufficient data: {count} meeting_booked outcomes (need {MIN_OUTCOMES_THRESHOLD})",
        )

        return {
            "status": "pending",
            "reason": "insufficient_data",
            "count": count,
            "threshold": MIN_OUTCOMES_THRESHOLD,
            "run_id": run_id,
        }

    logger.info(f"✓ Threshold met: {count} MEETING_BOOKED outcomes")

    # Step 2: Query outcomes
    outcomes = await query_outcomes(customer_id)
    logger.info(f"✓ Queried {len(outcomes)} total outcomes for analysis")

    if not outcomes:
        logger.warning("⚠️  No outcomes returned from query")
        await complete_cis_run(
            run_id=run_id,
            status="failed",
            summary="No outcomes returned from query",
        )
        return {
            "status": "failed",
            "reason": "no_outcomes",
            "run_id": run_id,
        }

    # Step 3: Get current weights
    current_weights = await get_current_weights()
    logger.info(
        f"✓ Loaded current weights: {len(current_weights.get('weights', {}))} positive, "
        f"{len(current_weights.get('negative', {}))} negative signals"
    )

    # Step 4: Claude analysis
    logger.info("🔍 Running Claude analysis...")
    try:
        analysis = await analyze_with_claude(outcomes, current_weights)
    except Exception as e:
        logger.error(f"❌ Claude analysis failed: {e}")
        await complete_cis_run(
            run_id=run_id,
            status="failed",
            outcomes_analyzed=len(outcomes),
            summary=f"Claude analysis failed: {str(e)}",
        )
        return {
            "status": "failed",
            "reason": "analysis_failed",
            "error": str(e),
            "run_id": run_id,
        }

    adjustments = analysis.get("adjustments", {})
    summary = analysis.get("analysis_summary", "")

    logger.info(f"✓ Analysis complete: {len(adjustments)} adjustments proposed")
    logger.info(f"   Summary: {summary}")

    # Step 5: Apply deltas
    adjustments_applied = 0
    if adjustments:
        updated_weights = await apply_weight_deltas(
            current_weights=current_weights,
            adjustments=adjustments,
            outcome_sample_size=len(outcomes),
            run_id=run_id,
        )

        # Count applied adjustments (those that passed confidence threshold)
        adjustments_applied = sum(
            1 for adj in adjustments.values() if adj.get("confidence", 0) >= 0.7
        )

        # Step 6: Save updated weights
        if adjustments_applied > 0:
            save_success = await save_updated_weights(updated_weights)
            if save_success:
                logger.info("✓ Weights updated in ceo_memory")
            else:
                logger.error("❌ Failed to save updated weights")
                await complete_cis_run(
                    run_id=run_id,
                    status="failed",
                    outcomes_analyzed=len(outcomes),
                    adjustments_applied=adjustments_applied,
                    summary=f"Failed to save weights. {summary}",
                )
                return {
                    "status": "failed",
                    "reason": "save_failed",
                    "run_id": run_id,
                }
        else:
            logger.info("ℹ️  No adjustments passed confidence threshold")
    else:
        logger.info("ℹ️  No adjustments proposed")

    # Complete run logging
    await complete_cis_run(
        run_id=run_id,
        status="complete",
        outcomes_analyzed=len(outcomes),
        adjustments_applied=adjustments_applied,
        summary=summary,
    )

    logger.info("🎉 CIS Learning Engine complete!")
    logger.info(f"   Outcomes analyzed: {len(outcomes)}")
    logger.info(f"   Adjustments applied: {adjustments_applied}")

    return {
        "status": "complete",
        "outcomes_analyzed": len(outcomes),
        "meeting_booked_count": analysis.get("meeting_booked_count", count),
        "adjustments_proposed": len(adjustments),
        "adjustments_applied": adjustments_applied,
        "summary": summary,
        "run_id": run_id,
    }


# =========================================================================
# MANUAL TRIGGER HELPER
# =========================================================================


async def run_cis_manually(customer_id: str | None = None):
    """
    Helper function to trigger CIS manually.

    Usage:
        import asyncio
        from src.orchestration.flows.cis_learning_flow import run_cis_manually
        asyncio.run(run_cis_manually())
    """
    return await cis_learning_flow(customer_id=customer_id, run_type="manual")


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_cis_manually())
