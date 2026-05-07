"""
Contract: src/integrations/ads_transparency.py
Purpose: Google Ads activity check via DFS Ads Search endpoint.
Layer: integration
Directive: #291

Replaces the stub from #290 with a real implementation using the DFS
/v3/serp/google/ads_search/live/advanced endpoint (validated in spike:
3/10 AU dental SMBs detected, $0.002/call, status 40102 = no ads).
Cost: $0.002/domain.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.integrations.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)


async def check_google_ads(domain: str, dfs_client: DFSLabsClient | None = None) -> dict | None:
    """
    Check if a domain is running Google Ads via DFS Ads Search.

    Args:
        domain: Business domain to check.
        dfs_client: Optional DFSLabsClient instance. If None, returns None (graceful stub).

    Returns:
        dict with keys: is_running_ads (bool), ad_count (int), formats (list),
        first_shown (str|None), last_shown (str|None)
        OR None if dfs_client not available.
    """
    if dfs_client is None:
        logger.debug("check_google_ads: no dfs_client provided, skipping (domain=%s)", domain)
        return None
    try:
        return await dfs_client.ads_search_by_domain(domain)
    except Exception as exc:
        logger.warning("check_google_ads failed for %s: %s", domain, exc)
        return None
