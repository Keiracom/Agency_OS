"""DFS Signal Bundle — Stage 4 — SIGNAL.

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
    from src.integrations.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)


async def build_signal_bundle(
    dfs: DFSLabsClient,
    domain: str,
    business_name: str | None = None,
    max_competitors: int = 10,
    max_keywords: int = 50,
) -> dict:
    """Assemble a DFS signal bundle for Pipeline F.

    Calls up to 10 DFS endpoints concurrently (~$0.0725/domain):
    - domain_rank_overview    ($0.010)
    - competitors_domain      ($0.011)
    - keywords_for_site       ($0.011)
    - domain_technologies     ($0.010)
    - maps_search_gmb         ($0.0035)
    - backlinks_summary       ($0.020)
    - brand_serp              ($0.002)
    - indexed_pages           ($0.002)
    - ads_search_by_domain    ($0.002)
    - google_ads_advertisers  ($0.006)

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
            "gmb": dict | None,
            "backlinks": dict,
            "brand_serp": dict,
            "indexed_pages": int,
            "ads_domain": dict | None,
            "ads_competitors": list[dict],
            "cost_usd": float,
        }
    """
    results = await asyncio.gather(
        dfs.domain_rank_overview(domain),
        dfs.competitors_domain(domain, limit=max_competitors),
        dfs.keywords_for_site(domain, limit=max_keywords),
        dfs.domain_technologies(domain),
        dfs.maps_search_gmb(business_name or domain),
        dfs.backlinks_summary(domain),
        dfs.brand_serp(business_name or domain),
        dfs.indexed_pages(domain),
        dfs.ads_search_by_domain(domain),
        dfs.google_ads_advertisers(keyword=domain),
        return_exceptions=True,
    )

    (
        rank_overview,
        competitors_raw,
        keywords_raw,
        tech_raw,
        gmb_raw,
        backlinks_raw,
        brand_serp_raw,
        indexed_raw,
        ads_domain_raw,
        ads_comp_raw,
    ) = results

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

    # GMB
    gmb: dict | None = None
    if isinstance(gmb_raw, dict):
        gmb = gmb_raw
    elif isinstance(gmb_raw, Exception):
        logger.warning("maps_search_gmb failed for %s: %s", domain, gmb_raw)

    # Backlinks
    backlinks: dict = {}
    if isinstance(backlinks_raw, dict):
        backlinks = backlinks_raw
    elif isinstance(backlinks_raw, Exception):
        logger.warning("backlinks_summary failed for %s: %s", domain, backlinks_raw)

    # Brand SERP
    brand_serp_data: dict = {}
    if isinstance(brand_serp_raw, dict):
        brand_serp_data = brand_serp_raw
    elif isinstance(brand_serp_raw, Exception):
        logger.warning("brand_serp failed for %s: %s", domain, brand_serp_raw)

    # Indexed pages
    indexed: int = 0
    if isinstance(indexed_raw, int):
        indexed = indexed_raw
    elif isinstance(indexed_raw, Exception):
        logger.warning("indexed_pages failed for %s: %s", domain, indexed_raw)

    # Ads by domain
    ads_domain: dict | None = None
    if isinstance(ads_domain_raw, dict):
        ads_domain = ads_domain_raw
    elif isinstance(ads_domain_raw, Exception):
        logger.warning("ads_search_by_domain failed for %s: %s", domain, ads_domain_raw)

    # Ads advertisers (competitors bidding)
    ads_competitors: list[dict] = []
    if isinstance(ads_comp_raw, list):
        ads_competitors = ads_comp_raw[:10]
    elif isinstance(ads_comp_raw, Exception):
        logger.warning("google_ads_advertisers failed for %s: %s", domain, ads_comp_raw)

    return {
        "domain": domain,
        "rank_overview": rank_overview_clean,
        "competitors": competitors_list,
        "keywords": keywords_list,
        "technologies": tech_list,
        "gmb": gmb,
        "backlinks": backlinks,
        "brand_serp": brand_serp_data,
        "indexed_pages": indexed,
        "ads_domain": ads_domain,
        "ads_competitors": ads_competitors,
        "cost_usd": round(dfs.total_cost_usd, 6),
    }
