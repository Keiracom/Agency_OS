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
) -> dict[str, Any] | None:
    """
    Call ContactOut for email + mobile in one shot.

    Returns a dict with canonical keys consumed by email_waterfall and
    mobile_waterfall, or None if ContactOut is not configured, the URL is
    missing, or the profile was not found.

    Cost: 1 ContactOut credit per call (only billed on found=True).

    Freshness logic (applied inside ContactOutClient):
      - best_email_confidence == "current_match": email domain matches current company
      - "stale": email found but domain mismatch (e.g. ex-employer) — still included,
        flagged so downstream can decide whether to use it or fall through
      - "none": no email at all
    """
    if not linkedin_url:
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

    result = await client.enrich_by_linkedin(linkedin_url)
    if not result.found:
        logger.debug("contactout_enricher: profile not found for %s", linkedin_url)
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
