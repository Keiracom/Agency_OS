"""
Contract: src/pipeline/contactout_enricher.py
Purpose: ContactOut DM enrichment helper for pipeline v7.
         Calls ContactOut ONCE per DM (by LinkedIn URL) and returns structured
         result consumed by both email_waterfall and mobile_waterfall.
Layer: 3 - pipeline
Directive: #317

ContactOut /v1/people/enrich returns BOTH email + mobile in a single API call.
We call it once, cache the result, and feed it into both waterfalls — avoiding
a second credit consumption.

Usage:
    result = await enrich_dm_via_contactout(dm_linkedin_url)
    # Pass result to discover_email(..., contactout_result=result)
    # Pass result to run_mobile_waterfall(..., contactout_result=result)
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def enrich_dm_via_contactout(
    linkedin_url: str | None,
    dm_name: str | None = None,
    company_name: str | None = None,
    dm_title: str | None = None,
) -> dict[str, Any] | None:
    """
    Call ContactOut for email + mobile in one shot.

    Two paths (GOV-8: maximum extraction per call):
      1. If linkedin_url provided: enrich directly via /v1/people/enrich
      2. If no linkedin_url but dm_name + company_name: search first via
         /v1/people/search (personal search, uses SEARCH credits), get LinkedIn
         URL, then enrich. Two-step pattern captures full profile.

    Returns a dict with canonical keys consumed by email_waterfall and
    mobile_waterfall, or None if ContactOut is not configured or profile not found.

    Cost: 1 SEARCH credit per search + 1 SEARCH credit per enrich (only billed on found=True).
    """
    if not linkedin_url and not (dm_name and company_name):
        return None

    try:
        from src.integrations.contactout_client import ContactOutClient
    except ImportError:
        logger.warning("contactout_enricher: ContactOutClient not importable")
        return None

    client = ContactOutClient()
    if not client.is_configured:
        logger.debug("contactout_enricher: not configured — skipping")
        return None

    # Step 1: If no LinkedIn URL, search by name + company first
    resolved_url = linkedin_url
    search_result = None
    if not resolved_url and dm_name and company_name:
        search_result = await client.search_by_name(
            dm_name=dm_name,
            company_name=company_name,
            title=dm_title or "Owner",
        )
        if search_result and search_result.found and search_result.linkedin_url:
            resolved_url = search_result.linkedin_url
            logger.info(
                "contactout_enricher: search found LinkedIn for %s → %s",
                dm_name, resolved_url,
            )
        else:
            logger.debug("contactout_enricher: search found no match for %s at %s", dm_name, company_name)
            return None

    if not resolved_url:
        return None

    # Step 2: Enrich by LinkedIn URL
    result = await client.enrich_by_linkedin(resolved_url)
    if not result.found:
        logger.debug("contactout_enricher: profile not found for %s", resolved_url)
        # Even if enrich fails, return search data if available (GOV-8: don't discard)
        if search_result and search_result.found:
            return {
                "email": None, "email_confidence": "none",
                "all_emails": [], "work_emails": [], "personal_emails": [],
                "phone": None, "all_phones": [],
                "full_name": search_result.full_name,
                "headline": search_result.headline,
                "company_name": search_result.company_name,
                "company_domain": search_result.company_domain,
                "company_linkedin_url": "",
                "linkedin_url_from_search": resolved_url,
                "raw": search_result.raw_response,
            }
        return None

    return {
        # Email
        "email": result.best_work_email or None,
        "email_confidence": result.best_email_confidence,  # "current_match" | "stale" | "none" | ...
        "all_emails": result.all_emails,
        "work_emails": result.work_emails,
        "personal_emails": result.personal_emails,
        # Mobile
        "phone": result.best_phone or None,
        "all_phones": result.all_phones,
        # Identity / company (enriches ProspectCard)
        "full_name": result.full_name,
        "headline": result.headline,
        "company_name": result.company_name,
        "company_domain": result.company_domain,
        "company_linkedin_url": result.company_linkedin_url,
        # Raw for storage (nothing discarded — architecture principle)
        "raw": result.raw_response,
    }
