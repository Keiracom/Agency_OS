"""Stage 2 — VERIFY: SERP-based candidate discovery.

5 parallel DFS SERP calls per domain to gather candidate data before Gemini.
Gemini uses these as starting points, not restrictions.

Pipeline F v2.1. Ratified: 2026-04-15.
"""

from __future__ import annotations

import asyncio
import logging
import re
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.clients.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)

ABN_RE = re.compile(r"\b(\d{2}\s?\d{3}\s?\d{3}\s?\d{3})\b")
LINKEDIN_COMPANY_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/company/[a-zA-Z0-9\-_%]+/?", re.IGNORECASE
)
FACEBOOK_PAGE_RE = re.compile(r"https?://(?:www\.)?facebook\.com/[a-zA-Z0-9.\-_]+/?", re.IGNORECASE)


def _extract_business_name(serp_result: dict) -> str | None:
    """Extract business name from SERP title of first organic result."""
    items = serp_result.get("items") or []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        if title and len(title) > 2:
            # Clean common suffixes
            for suffix in [" - Home", " | Home", " - Official", " | Official"]:
                if title.endswith(suffix):
                    title = title[: -len(suffix)]
            return title.strip()
    return None


def _extract_abn(serp_result: dict) -> str | None:
    """Extract ABN from SERP snippets, preferring ABR results."""
    items = serp_result.get("items") or []
    # Prefer ABR
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        snippet = item.get("description") or item.get("snippet") or ""
        if "abr.business.gov.au" in url or "abn" in url.lower():
            m = ABN_RE.search(snippet)
            if m:
                return m.group(1).replace(" ", "")
    # Fallback any snippet
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        snippet = item.get("description") or item.get("snippet") or ""
        m = ABN_RE.search(snippet)
        if m:
            return m.group(1).replace(" ", "")
    return None


def _extract_company_linkedin(serp_result: dict) -> str | None:
    """Extract LinkedIn company URL from SERP results."""
    items = serp_result.get("items") or []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        if LINKEDIN_COMPANY_RE.match(url):
            return url.rstrip("/") + "/"
    return None


def _extract_facebook_url(serp_result: dict) -> str | None:
    """Extract Facebook page URL from SERP results."""
    items = serp_result.get("items") or []
    for item in items[:3]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        if FACEBOOK_PAGE_RE.match(url) and "facebook.com/share" not in url:
            return url.rstrip("/") + "/"
    return None


def _extract_dm_candidate(serp_result: dict) -> str | None:
    """Extract owner/director/founder name from SERP snippets."""
    items = serp_result.get("items") or []
    # Look for names in titles and snippets mentioning owner/director/founder
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        # LinkedIn /in/ URLs often have the name in the title
        url = item.get("url") or ""
        if "linkedin.com/in/" in url and " - " in title:
            name = title.split(" - ")[0].strip()
            if name and len(name.split()) >= 2:
                return name
    return None


async def run_serp_verify(
    dfs: "DFSLabsClient",  # noqa: UP037
    domain: str,
) -> dict:
    """Run 5 SERP queries in parallel to gather candidate data for a domain.

    Returns:
        {
            "serp_business_name": str | None,
            "serp_abn": str | None,
            "serp_company_linkedin": str | None,
            "serp_dm_candidate": str | None,
            "serp_facebook_url": str | None,
            "f_status": "success" | "partial",
            "_errors": list[str],
            "_cost": float,
        }
    """
    clean_domain = domain.removeprefix("www.")
    cost_before = dfs.total_cost_usd
    errors: list[str] = []

    async def _serp(keyword: str) -> dict:
        try:
            return await dfs._post(
                endpoint="/v3/serp/google/organic/live/advanced",
                payload=[
                    {
                        "keyword": keyword,
                        "location_name": "Australia",
                        "language_name": "English",
                        "depth": 10,
                    }
                ],
                cost_per_call=Decimal("0.002"),
                cost_attr="_cost_serp",
                swallow_no_data=True,
            )
        except Exception as exc:
            error_msg = str(exc)[:80]
            errors.append(error_msg)
            logger.warning("SERP query '%s' failed: %s", keyword[:40], error_msg)
            return {}

    # Extract business name first for Facebook query
    q_biz = await _serp(f'"{clean_domain}"')
    biz_name = _extract_business_name(q_biz)

    q_abn, q_li, q_dm, q_fb = await asyncio.gather(
        _serp(f'"{clean_domain}" ABN'),
        _serp(f'"{clean_domain}" site:linkedin.com/company'),
        _serp(f'"{clean_domain}" owner OR director OR founder'),
        _serp(
            f'"{biz_name}" site:facebook.com' if biz_name else f'"{clean_domain}" site:facebook.com'
        ),
    )

    # Determine if any queries failed (non-empty results vs errors)
    any_errors = bool(errors)
    f_status = "partial" if any_errors else "success"

    result = {
        "serp_business_name": biz_name,
        "serp_abn": _extract_abn(q_abn),
        "serp_company_linkedin": _extract_company_linkedin(q_li),
        "serp_dm_candidate": _extract_dm_candidate(q_dm),
        "serp_facebook_url": _extract_facebook_url(q_fb),
        "f_status": f_status,
        "_errors": errors,
        "_cost": dfs.total_cost_usd - cost_before,
    }
    logger.info(
        "Stage 2 VERIFY %s: biz=%s abn=%s li=%s dm=%s fb=%s (f_status=%s)",
        domain,
        result["serp_business_name"][:30] if result["serp_business_name"] else "null",
        result["serp_abn"] or "null",
        bool(result["serp_company_linkedin"]),
        result["serp_dm_candidate"] or "null",
        bool(result["serp_facebook_url"]),
        f_status,
    )
    return result
