"""Stage 9 — SOCIAL: LinkedIn social intelligence.

Scrapes DM LinkedIn posts and company LinkedIn posts via Bright Data.
Facebook deferred to post-launch.

Pipeline F v2.1. Ratified: 2026-04-15.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.integrations.bright_data_client import BrightDataClient

logger = logging.getLogger(__name__)


async def run_stage9_social(
    bd: BrightDataClient,
    dm_linkedin_url: str | None,
    company_linkedin_url: str | None,
    dm_name: str | None = None,
    max_posts: int = 5,
    days: int = 30,
) -> dict:
    """Run social intelligence scraping for a prospect.

    Args:
        bd: Authenticated BrightDataClient.
        dm_linkedin_url: Verified DM LinkedIn URL (from Stage 8 L2).
        company_linkedin_url: Company LinkedIn URL (from Stage 2/4).
        dm_name: DM name for filtering authored posts.
        max_posts: Max posts to return per source.
        days: Days of posts to retrieve.

    Returns:
        {
            "dm_posts": list[dict],
            "dm_posts_count": int,
            "company_posts": list[dict],
            "company_posts_count": int,
            "_cost": float,
        }
    """
    dm_posts: list[dict] = []
    company_posts: list[dict] = []

    # DM LinkedIn posts (only if verified URL available)
    if dm_linkedin_url:
        try:
            raw_posts = await bd.scrape_linkedin_posts_90d(dm_linkedin_url, days=days)
            dm_posts = (raw_posts or [])[:max_posts]
            logger.info(
                "Stage 9 SOCIAL dm_posts: %d for %s",
                len(dm_posts),
                dm_linkedin_url[:40],
            )
        except Exception as exc:
            logger.warning("Stage 9 SOCIAL dm_posts failed: %s", exc)

    # Company LinkedIn posts (bundled in company profile scrape)
    if company_linkedin_url:
        try:
            results = await bd._scraper_request(
                "gd_l1vikfnt1wgvvqz95w",
                [{"url": company_linkedin_url}],
            )
            if results and len(results) > 0:
                company = results[0]
                raw_company_posts = company.get("updates") or company.get("posts") or []
                company_posts = raw_company_posts[:max_posts]
            logger.info(
                "Stage 9 SOCIAL company_posts: %d for %s",
                len(company_posts),
                company_linkedin_url[:40],
            )
        except Exception as exc:
            logger.warning("Stage 9 SOCIAL company_posts failed: %s", exc)

    return {
        "dm_posts": dm_posts,
        "dm_posts_count": len(dm_posts),
        "company_posts": company_posts,
        "company_posts_count": len(company_posts),
        "_cost": 0.027,  # ~$0.002 DM + $0.025 company
    }
