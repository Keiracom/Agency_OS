"""
Elliot Knowledge Decay Flow
===========================
Daily job to apply decay to unapplied knowledge and prune stale items.

Schedule: Run daily after the learning scrape (e.g., 7am UTC)
"""

import os
from datetime import datetime, timezone
from typing import Optional

from prefect import flow, task, get_run_logger
from supabase import create_client, Client

# ============================================
# Configuration
# ============================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# Decay settings
DECAY_AMOUNT = 0.1  # Reduce score by this much per day
PRUNE_THRESHOLD = 0.3  # Prune items below this score

# ============================================
# Supabase Client
# ============================================

def get_supabase() -> Client:
    """Get authenticated Supabase client."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ============================================
# Tasks
# ============================================

@task(retries=2, retry_delay_seconds=30)
async def apply_decay() -> dict:
    """
    Apply decay to all unapplied knowledge items.
    
    Returns:
        Dict with decayed_count, min_score_after, max_age_days
    """
    logger = get_run_logger()
    logger.info("Applying decay to unapplied knowledge...")
    
    supabase = get_supabase()
    
    try:
        result = supabase.rpc('decay_unused_knowledge').execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            decay_result = {
                "decayed_count": row['decayed_count'],
                "min_score_after": row['min_score_after'],
                "max_age_days": row['max_age_days']
            }
            logger.info(
                f"Decay applied: {decay_result['decayed_count']} items affected, "
                f"min score now {decay_result['min_score_after']:.2f}, "
                f"oldest item {decay_result['max_age_days']} days"
            )
            return decay_result
        
        logger.info("No items to decay")
        return {"decayed_count": 0, "min_score_after": 1.0, "max_age_days": 0}
    
    except Exception as e:
        logger.error(f"Decay failed: {e}")
        raise


@task(retries=2, retry_delay_seconds=30)
async def prune_stale(min_score: float = PRUNE_THRESHOLD) -> dict:
    """
    Prune knowledge items with decay score below threshold.
    
    Args:
        min_score: Minimum score to keep (default 0.3)
    
    Returns:
        Dict with pruned_count and pruned_ids
    """
    logger = get_run_logger()
    logger.info(f"Pruning knowledge with decay score < {min_score}...")
    
    supabase = get_supabase()
    
    try:
        result = supabase.rpc(
            'prune_stale_knowledge',
            {'min_score': min_score}
        ).execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            prune_result = {
                "pruned_count": row['pruned_count'],
                "pruned_ids": row['pruned_ids'] or []
            }
            
            if prune_result['pruned_count'] > 0:
                logger.warning(
                    f"Pruned {prune_result['pruned_count']} stale items "
                    f"(IDs: {', '.join(str(id)[:8] + '...' for id in prune_result['pruned_ids'][:5])})"
                )
            else:
                logger.info("No items below threshold to prune")
            
            return prune_result
        
        return {"pruned_count": 0, "pruned_ids": []}
    
    except Exception as e:
        logger.error(f"Prune failed: {e}")
        raise


@task
async def get_decay_stats() -> dict:
    """
    Get current knowledge decay statistics for logging.
    
    Returns:
        Dict with stats about the knowledge base
    """
    logger = get_run_logger()
    
    supabase = get_supabase()
    
    try:
        result = supabase.rpc('get_session_learning_stats', {'hours_back': 24}).execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            stats = {
                "total_knowledge": row['total_knowledge'],
                "applied_count": row['applied_count'],
                "unapplied_count": row['unapplied_count'],
                "avg_decay_score": row['avg_decay_score'],
                "at_risk_count": row['at_risk_count']
            }
            
            logger.info(
                f"Knowledge stats: {stats['total_knowledge']} total, "
                f"{stats['applied_count']} applied, {stats['unapplied_count']} pending, "
                f"{stats['at_risk_count']} at risk"
            )
            return stats
        
        return {}
    
    except Exception as e:
        logger.warning(f"Failed to get stats: {e}")
        return {}


@task
async def update_decay_run_stats(decay_result: dict, prune_result: dict):
    """
    Store the decay run results in session state for tracking.
    """
    logger = get_run_logger()
    
    supabase = get_supabase()
    
    try:
        run_stats = {
            "last_decay_run": datetime.now(timezone.utc).isoformat(),
            "last_decayed_count": decay_result.get('decayed_count', 0),
            "last_pruned_count": prune_result.get('pruned_count', 0),
            "min_score_after_decay": decay_result.get('min_score_after', 0)
        }
        
        # Get existing stats
        existing = supabase.table('elliot_session_state') \
            .select('value') \
            .eq('key', 'elliot:learning_stats') \
            .single() \
            .execute()
        
        if existing.data:
            current_stats = existing.data.get('value', {})
            current_stats.update(run_stats)
            
            supabase.table('elliot_session_state').upsert({
                'key': 'elliot:learning_stats',
                'value': current_stats
            }).execute()
            
            logger.info("Updated learning stats with decay run info")
        
    except Exception as e:
        logger.warning(f"Failed to update decay stats: {e}")


# ============================================
# Main Flow
# ============================================

@flow(
    name="knowledge_decay",
    description="Apply decay to unapplied knowledge and prune stale items",
    retries=1,
    retry_delay_seconds=300,
    log_prints=True
)
async def knowledge_decay(
    prune_threshold: float = PRUNE_THRESHOLD,
    skip_prune: bool = False
):
    """
    Main flow: Apply decay and optionally prune stale knowledge.
    
    Args:
        prune_threshold: Minimum decay score to keep (default 0.3)
        skip_prune: If True, only apply decay without pruning
    """
    logger = get_run_logger()
    logger.info("Starting knowledge decay flow...")
    
    # Get pre-decay stats
    pre_stats = await get_decay_stats()
    
    # Apply decay
    decay_result = await apply_decay()
    
    # Prune stale items (unless skipped)
    prune_result = {"pruned_count": 0, "pruned_ids": []}
    if not skip_prune:
        prune_result = await prune_stale(prune_threshold)
    
    # Update stats
    await update_decay_run_stats(decay_result, prune_result)
    
    # Get post-decay stats
    post_stats = await get_decay_stats()
    
    # Summary
    summary = {
        "decay": {
            "items_affected": decay_result['decayed_count'],
            "min_score_after": decay_result['min_score_after'],
            "oldest_item_days": decay_result['max_age_days']
        },
        "prune": {
            "items_removed": prune_result['pruned_count'],
            "threshold": prune_threshold
        },
        "stats_before": pre_stats,
        "stats_after": post_stats
    }
    
    logger.info(f"Knowledge decay complete: {summary}")
    
    return summary


# ============================================
# Deployment Helper
# ============================================

if __name__ == "__main__":
    import asyncio
    asyncio.run(knowledge_decay())
