"""F4 — Verification Gap Fills.

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
    r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_%]+/?", re.IGNORECASE
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
    dfs: "DFSLabsClient",
    business_name: str,
) -> str | None:
    """F4: resolve ABN via DFS SERP query '{business_name} ABN'.

    This is now the PRIMARY (and only) ABN source. Gemini ABN is discarded.

    Returns: 11-digit ABN string (no spaces) or None.
    """
    if not business_name:
        return None
    query = f"{business_name} ABN"
    try:
        result = await dfs.brand_serp(query)
        abn = _parse_abn_from_snippets(result)
        if abn:
            logger.info("ABN found via SERP for '%s': %s", business_name, abn)
        else:
            logger.info("ABN not found via SERP for '%s'", business_name)
        return abn
    except Exception as exc:
        logger.warning("fill_abn_via_serp failed for '%s': %s", business_name, exc)
        return None


async def fill_linkedin_via_serp(
    dfs: "DFSLabsClient",
    dm_name: str,
    business_name: str,
) -> str | None:
    """F4: resolve DM LinkedIn URL via DFS SERP query '{dm_name} {business_name} LinkedIn'.

    Returns: LinkedIn /in/ URL string or None.
    """
    if not dm_name:
        return None
    query = f"{dm_name} {business_name} LinkedIn"
    try:
        result = await dfs.brand_serp(query)
        url = _parse_linkedin_from_snippets(result)
        if url:
            logger.info(
                "LinkedIn found via SERP for '%s' at '%s': %s",
                dm_name, business_name, url,
            )
        else:
            logger.info(
                "LinkedIn not found via SERP for '%s' at '%s'",
                dm_name, business_name,
            )
        return url
    except Exception as exc:
        logger.warning(
            "fill_linkedin_via_serp failed for '%s': %s", dm_name, exc
        )
        return None


async def run_verify_fills(
    dfs: "DFSLabsClient",
    f3a_output: dict,
) -> dict:
    """Run all F4 gap fills and return a fills dict.

    Args:
        dfs: Authenticated DFSLabsClient.
        f3a_output: Parsed F3a output dict.

    Returns:
        {
            "abn": str | None,
            "dm_linkedin_url": str | None,
        }
    """
    business_name = f3a_output.get("business_name") or ""
    dm_candidate = f3a_output.get("dm_candidate") or {}
    dm_name = dm_candidate.get("name") or ""

    abn, dm_linkedin = await _gather_fills(dfs, business_name, dm_name)

    return {
        "abn": abn,
        "dm_linkedin_url": dm_linkedin,
    }


async def _gather_fills(
    dfs: "DFSLabsClient",
    business_name: str,
    dm_name: str,
) -> tuple[str | None, str | None]:
    """Run ABN and LinkedIn fills concurrently."""
    import asyncio

    abn_task = asyncio.create_task(fill_abn_via_serp(dfs, business_name))
    li_task = asyncio.create_task(
        fill_linkedin_via_serp(dfs, dm_name, business_name)
    )
    abn = await abn_task
    li = await li_task
    return abn, li
