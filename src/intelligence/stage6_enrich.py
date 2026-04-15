"""Stage 6 — ENRICH: Premium DFS endpoint enrichment.

Only fires for prospects with Stage 5 composite score >= 60.
Adds historical rank trajectory data for trend analysis.

google_jobs_advertisers REMOVED — 0/5 data return rate for AU SMBs (audit 2026-04-15).

Pipeline F v2.1. Ratified: 2026-04-15.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.clients.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)

ENRICH_SCORE_GATE = 60


async def run_stage6_enrich(
    dfs: DFSLabsClient,
    domain: str,
    composite_score: int,
) -> dict:
    """Run premium enrichment if prospect meets score gate.

    Args:
        dfs: Authenticated DFSLabsClient.
        domain: Prospect domain.
        composite_score: Stage 5 composite score (0-100).

    Returns:
        {
            "enriched": bool,
            "historical_rank": list[dict] | None,
            "months_available": int,
            "_cost": float,
        }
    """
    if composite_score < ENRICH_SCORE_GATE:
        return {"enriched": False, "historical_rank": None, "months_available": 0, "_cost": 0.0}

    cost_before = dfs.total_cost_usd
    try:
        result = await dfs.historical_rank_overview(domain)
        historical = None
        months = 0
        if isinstance(result, dict):
            items = result.get("items") or []
            historical = items
            months = len(items)
        elif isinstance(result, list):
            historical = result
            months = len(result)

        logger.info("Stage 6 ENRICH %s: %d months of historical data", domain, months)
        return {
            "enriched": True,
            "historical_rank": historical,
            "months_available": months,
            "_cost": dfs.total_cost_usd - cost_before,
        }
    except Exception as exc:
        logger.warning("Stage 6 ENRICH %s failed: %s", domain, exc)
        return {
            "enriched": False,
            "historical_rank": None,
            "months_available": 0,
            "_cost": dfs.total_cost_usd - cost_before,
        }
