"""F5 — Contact Waterfall.

Resolves email and mobile for a decision-maker via ContactOut primary waterfall.
Includes DM post author filter: only returns posts where author matches DM identity.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _author_matches_dm(
    post_author: dict,
    dm_name: str | None,
    dm_linkedin_url: str | None,
) -> bool:
    """Return True if a post's author matches the DM candidate.

    Matches on LinkedIn profile URL (exact) or display name (case-insensitive).
    """
    if not post_author:
        return False

    # LinkedIn URL match (most reliable)
    if dm_linkedin_url:
        author_url = post_author.get("profile_url") or post_author.get("linkedin_url") or ""
        if author_url and dm_linkedin_url.rstrip("/") in author_url.rstrip("/"):
            return True

    # Name match (fallback)
    if dm_name:
        author_name = post_author.get("name") or post_author.get("display_name") or ""
        if author_name and dm_name.lower() in author_name.lower():
            return True

    return False


def _filter_dm_posts(
    posts: list[dict],
    dm_name: str | None,
    dm_linkedin_url: str | None,
) -> list[dict]:
    """Filter post list to only those authored by the DM candidate."""
    if not posts:
        return []
    return [
        p for p in posts
        if _author_matches_dm(p.get("author") or {}, dm_name, dm_linkedin_url)
    ]


async def _fetch_dm_posts(
    unipile_client: Any,
    dm_linkedin_url: str,
    dm_name: str | None,
    limit: int = 5,
) -> list[dict]:
    """Fetch recent LinkedIn posts for a DM and filter to authored-by-DM only.

    Args:
        unipile_client: Unipile client with get_profile / list_posts capability.
        dm_linkedin_url: DM LinkedIn /in/ URL.
        dm_name: DM display name (used as fallback filter).
        limit: Max posts to return after filtering.

    Returns:
        Filtered list of post dicts (may be empty).
    """
    try:
        profile = await unipile_client.get_profile(dm_linkedin_url)
        raw_posts = profile.get("posts") or []
    except Exception as exc:
        logger.warning("_fetch_dm_posts: get_profile failed for %s: %s", dm_linkedin_url, exc)
        return []

    filtered = _filter_dm_posts(raw_posts, dm_name, dm_linkedin_url)
    return filtered[:limit]


async def run_contact_waterfall(
    leadmagic_client: Any,
    dm_linkedin_url: str | None,
    dm_name: str | None,
    domain: str,
) -> dict:
    """F5 contact waterfall: resolve email and mobile for a DM.

    Tier order:
    1. Leadmagic email by domain + name
    2. Leadmagic mobile by LinkedIn URL (if available)

    Args:
        leadmagic_client: Leadmagic client instance.
        dm_linkedin_url: DM LinkedIn URL (optional).
        dm_name: DM full name.
        domain: Prospect domain.

    Returns:
        {
            "email": str | None,
            "email_source": str | None,
            "mobile": str | None,
            "mobile_source": str | None,
        }
    """
    email = email_source = mobile = mobile_source = None

    # T3: Leadmagic email discovery
    if dm_name and domain:
        try:
            result = await leadmagic_client.find_email(
                full_name=dm_name,
                domain=domain,
            )
            if result and result.get("email"):
                email = result["email"]
                email_source = "leadmagic_email"
        except Exception as exc:
            logger.warning(
                "run_contact_waterfall: Leadmagic email failed for %s@%s: %s",
                dm_name, domain, exc,
            )

    # T5: Leadmagic mobile
    if dm_linkedin_url:
        try:
            result = await leadmagic_client.find_mobile(
                linkedin_url=dm_linkedin_url,
            )
            if result and result.get("mobile"):
                mobile = result["mobile"]
                mobile_source = "leadmagic_mobile"
        except Exception as exc:
            logger.warning(
                "run_contact_waterfall: Leadmagic mobile failed for %s: %s",
                dm_linkedin_url, exc,
            )

    return {
        "email": email,
        "email_source": email_source,
        "mobile": mobile,
        "mobile_source": mobile_source,
    }
