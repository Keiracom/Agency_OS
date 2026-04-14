"""DFS Signal Bundle — F2 stage.

Assembles a multi-endpoint DFS signal bundle for a prospect domain.
Each endpoint returns a dict with an "items" key (not a bare list).
This module extracts the list correctly before slicing.

BUG FIX: competitors_domain() and keywords_for_site() both return
{"items": [...]} — a dict, not a list. Previous code attempted to
slice the dict directly, causing TypeError. Fixed: always extract
result.get("items", []) before slicing.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.clients.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)


async def build_signal_bundle(
    dfs: DFSLabsClient,
    domain: str,
    max_competitors: int = 10,
    max_keywords: int = 50,
) -> dict:
    """Assemble a DFS signal bundle for Pipeline F.

    Calls up to 4 DFS endpoints concurrently:
    - domain_rank_overview  ($0.010)
    - competitors_domain    ($0.011)
    - keywords_for_site     ($0.011)
    - domain_technologies   ($0.010)

    Returns a normalised dict safe for JSON serialisation and Gemini injection.

    Args:
        dfs: Authenticated DFSLabsClient instance.
        domain: Prospect domain (no scheme, e.g. "example.com.au").
        max_competitors: Slice cap on competitor list (default 10).
        max_keywords: Slice cap on keyword list (default 50).

    Returns:
        {
            "domain": str,
            "rank_overview": dict | None,
            "competitors": list[dict],   # sliced to max_competitors
            "keywords": list[dict],      # sliced to max_keywords
            "technologies": list[str],
            "cost_usd": float,
        }
    """
    results = await asyncio.gather(
        dfs.domain_rank_overview(domain),
        dfs.competitors_domain(domain, limit=max_competitors),
        dfs.keywords_for_site(domain, limit=max_keywords),
        dfs.domain_technologies(domain),
        return_exceptions=True,
    )

    rank_overview, competitors_raw, keywords_raw, tech_raw = results

    # rank_overview returns dict | None directly
    rank_overview_clean: dict | None = None
    if isinstance(rank_overview, dict):
        rank_overview_clean = rank_overview
    elif isinstance(rank_overview, Exception):
        logger.warning("domain_rank_overview failed for %s: %s", domain, rank_overview)

    # competitors_domain returns {"items": [...]} — extract list, then slice
    competitors_list: list[dict] = []
    if isinstance(competitors_raw, dict):
        raw_items = competitors_raw.get("items") or []
        competitors_list = raw_items[:max_competitors]
    elif isinstance(competitors_raw, Exception):
        logger.warning("competitors_domain failed for %s: %s", domain, competitors_raw)

    # keywords_for_site returns {"items": [...]} — extract list, then slice
    keywords_list: list[dict] = []
    if isinstance(keywords_raw, dict):
        raw_items = keywords_raw.get("items") or []
        keywords_list = raw_items[:max_keywords]
    elif isinstance(keywords_raw, Exception):
        logger.warning("keywords_for_site failed for %s: %s", domain, keywords_raw)

    # domain_technologies returns {"tech_stack": [...], ...} or None
    tech_list: list[str] = []
    if isinstance(tech_raw, dict):
        tech_list = tech_raw.get("tech_stack") or []
    elif isinstance(tech_raw, Exception):
        logger.warning("domain_technologies failed for %s: %s", domain, tech_raw)

    return {
        "domain": domain,
        "rank_overview": rank_overview_clean,
        "competitors": competitors_list,
        "keywords": keywords_list,
        "technologies": tech_list,
        "cost_usd": round(dfs.total_cost_usd, 6),
    }
