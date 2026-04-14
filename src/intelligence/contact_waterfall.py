"""F5 — Contact Waterfall.

Three cascading waterfalls per directive F-REFACTOR-01:
  LinkedIn URL: L1 F3a/F4 → L2 harvestapi → L3 BD Web Unlocker → L4 unresolved
  Email: L1 ContactOut → L2 Hunter → L3 pattern+ZeroBounce → L4 harvestapi → L5 unresolved
  Mobile: L0 sole-trader inference → L1 ContactOut → L2 harvestapi → L3 BD → L4 unresolved

DM social: apimaestro/linkedin-posts-search-scraper-no-cookies
  Author filter: only posts where author matches DM identity.

Leadmagic EXCLUDED (0% AU mobile, 7% AU email per ratified memory).

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

import httpx

from src.common.phone_classifier import classify_au_phone

logger = logging.getLogger(__name__)

CONTACTOUT_ENRICH_URL = "https://api.contactout.com/v1/people/enrich"
HUNTER_EMAIL_FINDER_URL = "https://api.hunter.io/v2/email-finder"
ZEROBOUNCE_VALIDATE_URL = "https://api.zerobounce.net/v2/validate"
APIFY_BASE = "https://api.apify.com/v2"


# ── Author filter for DM posts ─────────────────────────────────────────────

def _author_matches_dm(
    post_author: dict,
    dm_name: str | None,
    dm_linkedin_url: str | None,
) -> bool:
    """Return True if post author matches DM candidate (URL or name)."""
    if not post_author:
        return False
    if dm_linkedin_url:
        author_url = post_author.get("profile_url") or post_author.get("linkedin_url") or ""
        if author_url and dm_linkedin_url.rstrip("/") in author_url.rstrip("/"):
            return True
    if dm_name:
        author_name = post_author.get("name") or post_author.get("display_name") or ""
        if author_name and dm_name.lower() in author_name.lower():
            return True
    return False


def filter_dm_posts(posts: list[dict], dm_name: str | None, dm_linkedin_url: str | None) -> list[dict]:
    """Filter to authored-by-DM only (not engaged/reshared)."""
    return [p for p in (posts or []) if _author_matches_dm(p.get("author") or {}, dm_name, dm_linkedin_url)]


# ── LinkedIn URL cascade ───────────────────────────────────────────────────

async def _linkedin_cascade(
    dm_name: str | None,
    business_name: str,
    f3a_linkedin: str | None,
    f4_linkedin: str | None,
) -> dict:
    """L1 F3a/F4 → L2 harvestapi → L3 BD Web Unlocker → L4 unresolved."""
    apify_token = os.environ.get("APIFY_API_TOKEN", "")

    # L1: from F3a or F4
    if f3a_linkedin:
        return {"linkedin_url": f3a_linkedin, "source": "f3a_gemini", "tier": "L1"}
    if f4_linkedin:
        return {"linkedin_url": f4_linkedin, "source": "f4_serp", "tier": "L1"}

    # L2: harvestapi/linkedin-profile-search-by-name (no cookies)
    if apify_token and dm_name:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(
                    f"{APIFY_BASE}/acts/harvestapi~linkedin-profile-search-by-name/runs?token={apify_token}",
                    json={"name": dm_name, "company": business_name, "maxResults": 3})
                if r.status_code in (200, 201):
                    run_id = r.json().get("data", {}).get("id")
                    if run_id:
                        for _ in range(15):
                            await asyncio.sleep(3)
                            sr = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={apify_token}")
                            sd = sr.json().get("data", {})
                            if sd.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                                if sd["status"] == "SUCCEEDED":
                                    ds_id = sd.get("defaultDatasetId")
                                    items = (await client.get(f"{APIFY_BASE}/datasets/{ds_id}/items?token={apify_token}")).json()
                                    for item in items[:3]:
                                        url = item.get("profileUrl") or item.get("profile_url") or item.get("url")
                                        if url and "linkedin.com/in/" in url:
                                            return {"linkedin_url": url, "source": "apify_harvestapi", "tier": "L2"}
                                break
        except Exception as e:
            logger.warning("F5 LinkedIn L2 harvestapi failed: %s", e)

    # L3: BD Web Unlocker — skip for now (complex, L2 covers most cases)
    # L4: unresolved
    return {"linkedin_url": None, "source": "unresolved", "tier": "L4"}


# ── Email waterfall ────────────────────────────────────────────────────────

async def _email_waterfall(
    dm_name: str | None,
    domain: str,
    linkedin_url: str | None,
) -> dict:
    """L1 ContactOut → L2 Hunter → L3 pattern+ZeroBounce → L4 harvestapi → L5 unresolved."""
    co_key = os.environ.get("CONTACTOUT_API_KEY", "")
    hunter_key = os.environ.get("HUNTER_API_KEY", "")
    zb_key = os.environ.get("ZEROBOUNCE_API_KEY", "")

    first = (dm_name or "").split()[0] if dm_name else ""
    last = " ".join((dm_name or "").split()[1:]) if dm_name and len((dm_name or "").split()) > 1 else ""

    # L1: ContactOut /v1/people/enrich (by LinkedIn URL)
    if linkedin_url and co_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(CONTACTOUT_ENRICH_URL,
                    headers={"authorization": "basic", "token": co_key},
                    json={"linkedin_url": linkedin_url})
                if r.status_code == 200:
                    profile = r.json().get("profile") or r.json().get("person") or r.json()
                    emails = profile.get("emails") or profile.get("work_emails") or []
                    if emails:
                        email = emails[0] if isinstance(emails[0], str) else emails[0].get("email", "")
                        if email:
                            return {"email": email, "source": "contactout", "tier": "L1", "verified": True}
        except Exception as e:
            logger.warning("F5 Email L1 ContactOut failed: %s", e)

    # L2: Hunter domain + first/last name
    if hunter_key and first and domain:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(HUNTER_EMAIL_FINDER_URL,
                    params={"domain": domain, "first_name": first, "last_name": last, "api_key": hunter_key})
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    email = data.get("email")
                    conf = data.get("confidence", 0)
                    if email and conf >= 70:
                        return {"email": email, "source": "hunter", "tier": "L2", "confidence": conf}
        except Exception as e:
            logger.warning("F5 Email L2 Hunter failed: %s", e)

    # L3: Pattern guess + ZeroBounce verify
    if zb_key and first and domain:
        patterns = [
            f"{first.lower()}.{last.lower()}@{domain}" if last else f"{first.lower()}@{domain}",
            f"{first.lower()[0]}{last.lower()}@{domain}" if last else None,
            f"{first.lower()}@{domain}",
        ]
        for pattern in [p for p in patterns if p]:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(ZEROBOUNCE_VALIDATE_URL,
                        params={"api_key": zb_key, "email": pattern})
                    if r.status_code == 200 and r.json().get("status") == "valid":
                        return {"email": pattern, "source": "pattern_zerobounce", "tier": "L3", "verified": True}
            except Exception as e:
                logger.debug("F5 Email L3 ZeroBounce failed for %s: %s", pattern, e)

    # L4: harvestapi Full+email mode — skip (Apify actor may not support email)
    # L5: unresolved
    return {"email": None, "source": "unresolved", "tier": "L5"}


# ── Mobile waterfall ───────────────────────────────────────────────────────

async def _mobile_waterfall(
    dm_name: str | None,
    domain: str,
    linkedin_url: str | None,
    entity_type: str | None,
    business_phone: str | None,
) -> dict:
    """L0 sole-trader inference → L1 ContactOut → L2 harvestapi → L3 BD → L4 unresolved."""
    co_key = os.environ.get("CONTACTOUT_API_KEY", "")

    # L0: Sole-trader business-phone inference
    if business_phone and entity_type and "sole trader" in entity_type.lower():
        classified = classify_au_phone(business_phone)
        if classified["phone_type"] == "mobile":
            return {"mobile": classified["normalized_e164"], "source": "sole_trader_inference",
                    "tier": "L0", **classified}

    # L1: ContactOut (bundled with enrich — check for phone)
    if linkedin_url and co_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(CONTACTOUT_ENRICH_URL,
                    headers={"authorization": "basic", "token": co_key},
                    json={"linkedin_url": linkedin_url, "include": ["phone"]})
                if r.status_code == 200:
                    profile = r.json().get("profile") or r.json()
                    phones = profile.get("phones") or profile.get("phone_numbers") or []
                    for phone in phones:
                        p = phone if isinstance(phone, str) else phone.get("number", "")
                        if p:
                            classified = classify_au_phone(p)
                            if classified["phone_type"] == "mobile":
                                return {"mobile": classified["normalized_e164"], "source": "contactout",
                                        "tier": "L1", **classified}
        except Exception as e:
            logger.warning("F5 Mobile L1 ContactOut failed: %s", e)

    # L2-L3: harvestapi / BD Web Unlocker — skip (complex, low AU mobile rate)
    # L4: unresolved
    return {"mobile": None, "source": "unresolved", "tier": "L4"}


# ── DM social (LinkedIn posts) ─────────────────────────────────────────────

async def fetch_dm_posts(
    dm_linkedin_url: str | None,
    dm_name: str | None,
    max_posts: int = 10,
) -> list[dict]:
    """Fetch DM LinkedIn posts via apimaestro, filter to authored only."""
    apify_token = os.environ.get("APIFY_API_TOKEN", "")
    if not dm_linkedin_url or not apify_token:
        return []

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"{APIFY_BASE}/acts/apimaestro~linkedin-posts-search-scraper-no-cookies/runs?token={apify_token}",
                json={"profileUrl": dm_linkedin_url, "maxPosts": max_posts})
            if r.status_code not in (200, 201):
                return []
            run_id = r.json().get("data", {}).get("id")
            if not run_id:
                return []
            for _ in range(20):
                await asyncio.sleep(3)
                sr = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={apify_token}")
                sd = sr.json().get("data", {})
                if sd.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    if sd["status"] == "SUCCEEDED":
                        ds_id = sd.get("defaultDatasetId")
                        items = (await client.get(f"{APIFY_BASE}/datasets/{ds_id}/items?token={apify_token}")).json()
                        return filter_dm_posts(items, dm_name, dm_linkedin_url)
                    return []
    except Exception as e:
        logger.warning("F5 fetch_dm_posts failed: %s", e)
    return []


# ── Main entry point ───────────────────────────────────────────────────────

async def run_contact_waterfall(
    dm_name: str | None,
    dm_title: str | None,
    business_name: str,
    domain: str,
    f3a_linkedin_url: str | None = None,
    f4_linkedin_url: str | None = None,
    entity_type: str | None = None,
    business_phone: str | None = None,
) -> dict:
    """Run all three contact waterfalls.

    Returns: {
        "linkedin": {linkedin_url, source, tier},
        "email": {email, source, tier, verified?},
        "mobile": {mobile, source, tier, phone_type?},
    }
    """
    # LinkedIn first (email/mobile may need the URL)
    linkedin = await _linkedin_cascade(dm_name, business_name, f3a_linkedin_url, f4_linkedin_url)
    resolved_li = linkedin.get("linkedin_url")

    # Email and mobile can run in parallel
    email_task = _email_waterfall(dm_name, domain, resolved_li)
    mobile_task = _mobile_waterfall(dm_name, domain, resolved_li, entity_type, business_phone)
    email, mobile = await asyncio.gather(email_task, mobile_task)

    return {"linkedin": linkedin, "email": email, "mobile": mobile}
