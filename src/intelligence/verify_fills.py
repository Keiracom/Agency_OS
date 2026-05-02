"""Stage 2 — VERIFY (Gap Fills).

ABN is now PRIMARY via DFS SERP (not Gemini). Gemini ABN is discarded entirely.
LinkedIn DM URL fill also uses DFS SERP with safe error handling.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.clients.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)

ABN_RE = re.compile(r"\b(\d{2}\s?\d{3}\s?\d{3}\s?\d{3})\b")
LINKEDIN_PERSON_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+/?", re.IGNORECASE
)
LINKEDIN_COMPANY_RE = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/company/[a-zA-Z0-9\-_%]+/?", re.IGNORECASE
)


def _parse_abn_from_snippets(serp_result: dict) -> str | None:
    """Extract ABN from DFS SERP result snippets targeting abr.business.gov.au."""
    items = []
    if isinstance(serp_result, dict):
        items = serp_result.get("items") or []
    for item in items:
        if not isinstance(item, dict):
            continue
        snippet = item.get("description") or item.get("snippet") or ""
        url = item.get("url") or ""
        # Prefer ABR result
        if "abr.business.gov.au" in url or "abn" in url.lower():
            m = ABN_RE.search(snippet)
            if m:
                return m.group(1).replace(" ", "")
    # Fallback: any snippet with ABN pattern
    for item in items:
        if not isinstance(item, dict):
            continue
        snippet = item.get("description") or item.get("snippet") or ""
        m = ABN_RE.search(snippet)
        if m:
            return m.group(1).replace(" ", "")
    return None


def _parse_linkedin_company_from_snippets(serp_result: dict) -> str | None:
    """Extract a LinkedIn /company/ URL from DFS SERP result."""
    items = []
    if isinstance(serp_result, dict):
        items = serp_result.get("items") or []
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        if LINKEDIN_COMPANY_RE.match(url):
            return url.rstrip("/") + "/"
        snippet = item.get("description") or item.get("snippet") or ""
        m = LINKEDIN_COMPANY_RE.search(url + " " + snippet)
        if m:
            return m.group(0).rstrip("/") + "/"
    return None


def _parse_linkedin_from_snippets(serp_result: dict) -> str | None:
    """Extract a LinkedIn /in/ URL from DFS SERP result snippets."""
    items = []
    if isinstance(serp_result, dict):
        items = serp_result.get("items") or []
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or ""
        if LINKEDIN_PERSON_RE.match(url):
            return url.rstrip("/")
        snippet = item.get("description") or item.get("snippet") or ""
        m = LINKEDIN_PERSON_RE.search(url + " " + snippet)
        if m:
            return m.group(0).rstrip("/")
    return None


async def fill_abn_via_serp(
    dfs: DFSLabsClient,
    business_name: str,
    suburb: str | None = None,
    state: str | None = None,
) -> str | None:
    """Stage 2 VERIFY: resolve ABN via DFS SERP query '{business_name} ABN'.

    This is now the PRIMARY (and only) ABN source. Gemini ABN is discarded.

    Returns: 11-digit ABN string (no spaces) or None.
    """
    if not business_name:
        return None
    from decimal import Decimal

    # Compound SERP strategy: try 3 query variants in priority order
    # Suburb/state come from Stage 3 IDENTIFY location output (passed via business_name enrichment)
    queries = []
    if suburb:
        queries.append(f'"{business_name}" "{suburb}" ABN')
    if state:
        queries.append(f'"{business_name}" "{state}" ABN')
    queries.append(f'"{business_name}" ABN site:abr.business.gov.au')
    queries.append(f"{business_name} ABN")

    for query in queries:
        try:
            result = await dfs._post(
                endpoint="/v3/serp/google/organic/live/advanced",
                payload=[
                    {
                        "keyword": query,
                        "location_name": "Australia",
                        "language_name": "English",
                        "depth": 5,
                    }
                ],
                cost_per_call=Decimal("0.002"),
                cost_attr="_cost_serp",
                swallow_no_data=True,
            )
            abn = _parse_abn_from_snippets(result)
            if abn:
                logger.info(
                    "ABN found via SERP for '%s' (query: %s): %s", business_name, query[:40], abn
                )
                return abn
        except Exception as exc:
            logger.warning("fill_abn_via_serp query '%s' failed: %s", query[:40], exc)

    logger.info("ABN not found via SERP for '%s' (all queries exhausted)", business_name)
    return None


async def fill_linkedin_via_serp(
    dfs: DFSLabsClient,
    dm_name: str,
    business_name: str,
) -> str | None:
    """Stage 2 VERIFY: resolve DM LinkedIn URL via DFS SERP query '{dm_name} {business_name} LinkedIn'.

    Returns: LinkedIn /in/ URL string or None.
    """
    if not dm_name:
        return None
    query = f"site:linkedin.com/in {dm_name} {business_name}"
    try:
        from decimal import Decimal

        result = await dfs._post(
            endpoint="/v3/serp/google/organic/live/advanced",
            payload=[
                {
                    "keyword": query,
                    "location_name": "Australia",
                    "language_name": "English",
                    "depth": 5,
                }
            ],
            cost_per_call=Decimal("0.002"),
            cost_attr="_cost_serp",
            swallow_no_data=True,
        )
        url = _parse_linkedin_from_snippets(result)
        if url:
            logger.info(
                "LinkedIn found via SERP for '%s' at '%s': %s",
                dm_name,
                business_name,
                url,
            )
        else:
            logger.info(
                "LinkedIn not found via SERP for '%s' at '%s'",
                dm_name,
                business_name,
            )
        return url
    except Exception as exc:
        logger.warning("fill_linkedin_via_serp failed for '%s': %s", dm_name, exc)
        return None


async def fill_company_linkedin_via_serp(
    dfs: DFSLabsClient,
    business_name: str,
) -> str | None:
    """Stage 2 VERIFY: resolve company LinkedIn URL via DFS SERP.

    Returns: LinkedIn /company/ URL string or None.
    """
    if not business_name:
        return None
    query = f'site:linkedin.com/company "{business_name}"'
    try:
        from decimal import Decimal

        result = await dfs._post(
            endpoint="/v3/serp/google/organic/live/advanced",
            payload=[
                {
                    "keyword": query,
                    "location_name": "Australia",
                    "language_name": "English",
                    "depth": 5,
                }
            ],
            cost_per_call=Decimal("0.002"),
            cost_attr="_cost_serp",
            swallow_no_data=True,
        )
        url = _parse_linkedin_company_from_snippets(result)
        if url:
            logger.info("Company LinkedIn found via SERP for '%s': %s", business_name, url)
        else:
            logger.info("Company LinkedIn not found via SERP for '%s'", business_name)
        return url
    except Exception as exc:
        logger.warning("fill_company_linkedin_via_serp failed for '%s': %s", business_name, exc)
        return None


async def run_verify_fills(
    dfs: DFSLabsClient,
    f3a_output: dict,
) -> dict:
    """Stage 2 VERIFY: run all gap fills and return a fills dict.

    Args:
        dfs: Authenticated DFSLabsClient.
        f3a_output: Parsed Stage 3 IDENTIFY output dict.
            NOTE: param name retained for caller compatibility (scripts use f3a_output= kwarg).

    Returns:
        {
            "abn": str | None,
            "dm_linkedin_url": str | None,
        }
    """
    business_name = f3a_output.get("business_name") or ""
    dm_candidate = f3a_output.get("dm_candidate") or {}
    dm_name = dm_candidate.get("name") or ""

    location = f3a_output.get("location") or {}
    suburb = location.get("suburb")
    state = location.get("state")
    abn, dm_linkedin, company_linkedin = await _gather_fills(
        dfs, business_name, dm_name, suburb, state
    )

    # FIX L4: _cost updated to 0.008 (4 SERP call variants now possible)
    # FIX M3: gmb_rating/gmb_reviews/gmb_category removed — always None, deferred by design
    return {
        "abn": abn,
        "abn_status": "verified_serp" if abn else "unresolved",
        "abn_source": "dfs_serp_abr" if abn else "unresolved",
        "dm_linkedin_url": dm_linkedin,
        "company_linkedin_url": company_linkedin,
        "_cost": 0.008,
    }


async def _gather_fills(
    dfs: DFSLabsClient,
    business_name: str,
    dm_name: str,
    suburb: str | None = None,
    state: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Run ABN, DM LinkedIn, and Company LinkedIn fills concurrently."""
    import asyncio

    abn_task = asyncio.create_task(fill_abn_via_serp(dfs, business_name, suburb, state))
    li_task = asyncio.create_task(fill_linkedin_via_serp(dfs, dm_name, business_name))
    company_li_task = asyncio.create_task(fill_company_linkedin_via_serp(dfs, business_name))
    abn = await abn_task
    li = await li_task
    company_li = await company_li_task
    return abn, li, company_li
