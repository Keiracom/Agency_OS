"""
Contract: src/integrations/ads_transparency.py
Purpose: Google Ads Transparency Center check.
Directive: #290

IMPLEMENTATION STATUS: STUB
No public API exists. Stub returns None so pipeline degrades gracefully.
TODO (Sprint 6): implement via Playwright or Bright Data Ads dataset.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


async def check_google_ads(domain: str) -> dict | None:
    """
    Check if domain is running Google Ads. STUB — returns None always.
    Returns dict with keys: is_running_ads, ads_count, last_seen — OR None.
    """
    logger.debug("check_google_ads: stub (domain=%s)", domain)
    return None
