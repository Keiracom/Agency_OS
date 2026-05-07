"""
Contract: src/pipeline/social_enrichment.py
Purpose: LinkedIn company page + DM profile scraping via existing BrightDataLinkedInClient.
         Feeds into classify_intent (company data) and refine_evidence (DM activity).
Layer: 4 - orchestration
Imports: src.integrations.bright_data_linkedin_client
Directive: #300-FIX Issues 13-14

Stage 9:  scrape_linkedin_company — run on intent-passed domains with company LinkedIn URL
Stage 10: scrape_linkedin_dm      — run on DM-found domains with dm_linkedin_url

Both functions:
  - GLOBAL_SEM_BRIGHTDATA = asyncio.Semaphore(15)  (shared module-level)
  - Short-circuit (return None) if URL is null
  - Return None gracefully on any failure
  - Log cost per call ($0.00075)
  - Results stored in BU under linkedin_company (jsonb) and linkedin_dm_profile (jsonb)
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from src.integrations.bright_data_linkedin_client import COST_PER_RECORD_USD, BrightDataLinkedInClient

logger = logging.getLogger(__name__)

GLOBAL_SEM_BRIGHTDATA = asyncio.Semaphore(15)

_COST = Decimal(str(COST_PER_RECORD_USD))


def _activity_level(recent_post_count: int | None) -> str:
    """Classify posting activity from recent post count."""
    if recent_post_count is None:
        return "unknown"
    if recent_post_count >= 8:
        return "active"
    if recent_post_count >= 2:
        return "moderate"
    return "lurker"


async def scrape_linkedin_company(
    company_url: str,
    domain: str,
) -> dict | None:
    """
    Scrape a LinkedIn company page via BrightDataLinkedInClient.

    Args:
        company_url: Full LinkedIn company URL.
                     e.g. "https://www.linkedin.com/company/smile-solutions"
        domain: Business domain (for logging only).

    Returns dict with keys:
        employee_count, follower_count,
        recent_posts (list of last 3 dicts with date + text),
        last_post_date, job_postings (count),
        specialties (list), description, cost_usd

    Returns None on null URL, API failure, or empty response.
    Cost: $0.00075/call.
    Semaphore: GLOBAL_SEM_BRIGHTDATA (15 concurrent).
    """
    if not company_url:
        return None

    async with GLOBAL_SEM_BRIGHTDATA:
        try:
            bd = BrightDataLinkedInClient()
            records = await bd._scraper_request(
                dataset_id="gd_l1vikfnt1wgvvqz95w",
                inputs=[{"url": company_url}],
            )
            if not records:
                logger.info("scrape_linkedin_company empty response domain=%s", domain)
                return None

            r = records[0]

            # Extract recent posts (last 3)
            raw_posts = r.get("posts") or r.get("recent_posts") or []
            if isinstance(raw_posts, list):
                recent_posts = [
                    {
                        "date": p.get("date") or p.get("published_at"),
                        "text": (p.get("text") or p.get("content") or "")[:300],
                    }
                    for p in raw_posts[:3]
                ]
            else:
                recent_posts = []

            last_post_date = recent_posts[0].get("date") if recent_posts else None
            post_count = len(raw_posts) if isinstance(raw_posts, list) else None

            result = {
                "employee_count": r.get("employee_count") or r.get("company_size"),
                "follower_count": r.get("followers") or r.get("follower_count"),
                "recent_posts": recent_posts,
                "last_post_date": last_post_date,
                "job_postings": r.get("job_openings") or r.get("jobs_count") or 0,
                "specialties": r.get("specialties") or [],
                "description": (r.get("description") or r.get("about") or "")[:500],
                "activity_level": _activity_level(post_count),
                "cost_usd": str(_COST),
            }

            logger.info(
                "scrape_linkedin_company domain=%s followers=%s employees=%s cost=%.5f",
                domain,
                result["follower_count"],
                result["employee_count"],
                COST_PER_RECORD_USD,
            )
            return result

        except Exception as exc:
            logger.warning("scrape_linkedin_company failed domain=%s: %s", domain, exc)
            return None


async def scrape_linkedin_dm(
    profile_url: str,
    domain: str,
) -> dict | None:
    """
    Scrape a LinkedIn person profile via BrightDataLinkedInClient.

    Args:
        profile_url: Full LinkedIn profile URL.
                     e.g. "https://au.linkedin.com/in/tammy-stevenson-75609b254"
        domain: Business domain (for logging only).

    Returns dict with keys:
        headline, summary,
        recent_posts (list of last 3 dicts with date + text),
        career_history (list of current + previous roles),
        skills (list), connections_count, activity_level

    Returns None on null URL, API failure, or empty response.
    Cost: $0.00075/call.
    Semaphore: GLOBAL_SEM_BRIGHTDATA (15 concurrent).
    """
    if not profile_url:
        return None

    async with GLOBAL_SEM_BRIGHTDATA:
        try:
            bd = BrightDataLinkedInClient()
            # Use profile dataset ID
            records = await bd._scraper_request(
                dataset_id="gd_l1viktl72bvl7bjuj0",
                inputs=[{"url": profile_url}],
            )
            if not records:
                logger.info("scrape_linkedin_dm empty response domain=%s", domain)
                return None

            r = records[0]

            # Recent posts (last 3)
            raw_posts = r.get("posts") or r.get("recent_posts") or []
            if isinstance(raw_posts, list):
                recent_posts = [
                    {
                        "date": p.get("date") or p.get("published_at"),
                        "text": (p.get("text") or p.get("content") or "")[:300],
                    }
                    for p in raw_posts[:3]
                ]
            else:
                recent_posts = []

            post_count = len(raw_posts) if isinstance(raw_posts, list) else None

            # Career history: current + previous
            experience = r.get("experience") or r.get("work_history") or []
            career_history = [
                {
                    "company": e.get("company") or e.get("company_name"),
                    "title": e.get("title") or e.get("position"),
                    "start": e.get("start_date") or e.get("start"),
                    "end": e.get("end_date") or e.get("end"),
                    "current": not bool(e.get("end_date") or e.get("end")),
                }
                for e in (experience[:5] if isinstance(experience, list) else [])
            ]

            # BD profile response uses "activity" (list of liked/shared posts)
            raw_activity = r.get("activity") or []
            post_count = len(raw_activity) if isinstance(raw_activity, list) else None
            recent_posts_from_activity = [
                {
                    "date": None,  # activity items don't expose date
                    "text": (p.get("title") or "")[:300],
                    "interaction": p.get("interaction", ""),
                }
                for p in (raw_activity[:3] if isinstance(raw_activity, list) else [])
            ]

            result = {
                "headline": (r.get("headline") or r.get("occupation") or r.get("title") or ""),
                "summary": (r.get("summary") or r.get("about") or "")[:500],
                "recent_posts": recent_posts if recent_posts else recent_posts_from_activity,
                "career_history": career_history,
                "skills": (r.get("skills") or [])[:20],
                "connections_count": r.get("connections") or r.get("connection_count"),
                "location": r.get("city") or r.get("location"),
                "activity_level": _activity_level(post_count),
                "cost_usd": str(_COST),
            }

            logger.info(
                "scrape_linkedin_dm domain=%s profile=%s activity=%s cost=%.5f",
                domain,
                profile_url,
                result["activity_level"],
                COST_PER_RECORD_USD,
            )
            return result

        except Exception as exc:
            logger.warning("scrape_linkedin_dm failed domain=%s: %s", domain, exc)
            return None
