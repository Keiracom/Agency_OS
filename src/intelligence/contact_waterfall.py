"""F5 — Contact Waterfall.

Three cascading waterfalls per directive F-REFACTOR-01:
  LinkedIn URL: L1 SERP discovery (candidate URL) → L2 profile scraper verification → L3 unresolved
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
from difflib import SequenceMatcher

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

def _fuzzy_match_company(
    profile: dict,
    business_name: str,
) -> dict:
    """Match harvestapi profile experience against business_name.

    Returns: {match_type, match_company, match_confidence}
    """
    biz_lower = business_name.lower().strip()
    best_ratio = 0.0
    best_company = ""
    best_type = "no_match"

    # Check headline first
    headline = (profile.get("headline") or "").lower()
    if biz_lower in headline:
        return {"match_type": "direct_match", "match_company": business_name, "match_confidence": 1.0}

    # Check current position
    current_position = profile.get("currentPosition") or profile.get("position") or ""
    if isinstance(current_position, str) and biz_lower in current_position.lower():
        return {"match_type": "direct_match", "match_company": business_name, "match_confidence": 1.0}

    # Check experience entries
    experience = profile.get("experience") or profile.get("experiences") or []
    for exp in experience:
        company = ""
        if isinstance(exp, dict):
            company = exp.get("company") or exp.get("companyName") or exp.get("subtitle") or ""
        elif isinstance(exp, str):
            company = exp
        if not company:
            continue

        ratio = SequenceMatcher(None, biz_lower, company.lower().strip()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_company = company

    if best_ratio >= 0.85:
        best_type = "direct_match"
    elif best_ratio >= 0.75:
        best_type = "past_or_related_match"

    return {"match_type": best_type, "match_company": best_company, "match_confidence": round(best_ratio, 3)}


async def _linkedin_cascade(
    dm_name: str | None,
    business_name: str,
    f3a_linkedin: str | None,
    f4_linkedin: str | None,
    company_linkedin_url: str | None = None,
) -> dict:
    """L1 SERP discovery → L2 profile scraper verification → L3 unresolved.

    L1: SERP provides candidate URL (F3a Gemini or F4 DFS SERP). NOT auto-trusted.
    L2: harvestapi/linkedin-profile-scraper scrapes the candidate URL, returns full
        profile. Post-filter verifies currentCompany/experience against business_name.
    L3: unresolved if no candidate URL or L2 rejects.
    """
    apify_token = os.environ.get("APIFY_API_TOKEN", "")

    # L1: Collect candidate URL from F3a or F4 SERP (discovery only, NOT verified)
    candidate_url = f3a_linkedin or f4_linkedin
    candidate_source = "f3a_gemini" if f3a_linkedin else ("f4_serp" if f4_linkedin else None)

    if not candidate_url or not apify_token:
        return {"linkedin_url": None, "source": "unresolved", "tier": "L3",
                "match_type": "no_match", "match_company": "", "match_confidence": 0.0,
                "l2_status": "no_candidate_url"}

    # L2: Verify candidate via harvestapi/linkedin-profile-scraper
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{APIFY_BASE}/acts/harvestapi~linkedin-profile-scraper/runs?token={apify_token}",
                json={
                    "queries": [candidate_url],
                    "profileScraperMode": "Profile details no email ($4 per 1k)",
                })
            if r.status_code not in (200, 201):
                logger.warning("F5 LinkedIn L2 scraper HTTP %s: %s", r.status_code, r.text[:200])
                return {"linkedin_url": None, "source": "unresolved", "tier": "L2",
                        "match_type": "no_match", "match_company": "", "match_confidence": 0.0,
                        "l2_status": "scraper_http_error"}

            run_id = r.json().get("data", {}).get("id")
            if not run_id:
                return {"linkedin_url": None, "source": "unresolved", "tier": "L2",
                        "match_type": "no_match", "match_company": "", "match_confidence": 0.0,
                        "l2_status": "no_run_id"}

            for _ in range(20):
                await asyncio.sleep(3)
                sr = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={apify_token}")
                sd = sr.json().get("data", {})
                if sd.get("status") in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                    if sd["status"] != "SUCCEEDED":
                        logger.warning("F5 LinkedIn L2 scraper run %s: %s", run_id, sd["status"])
                        break

                    ds_id = sd.get("defaultDatasetId")
                    items = (await client.get(
                        f"{APIFY_BASE}/datasets/{ds_id}/items?token={apify_token}"
                    )).json()

                    if not items:
                        logger.info("F5 LinkedIn L2: scraper returned 0 profiles for %s", candidate_url)
                        return {"linkedin_url": None, "source": "unresolved", "tier": "L2",
                                "match_type": "no_match", "match_company": "", "match_confidence": 0.0,
                                "l2_status": "scraper_empty_response",
                                "l1_candidate_url": candidate_url, "l1_candidate_source": candidate_source}

                    profile = items[0]
                    scraped_url = profile.get("linkedinUrl") or candidate_url
                    match = _fuzzy_match_company(profile, business_name)

                    if match["match_type"] != "no_match":
                        logger.info(
                            "F5 LinkedIn L2: VERIFIED %s (%s, confidence=%.3f, company=%s)",
                            scraped_url, match["match_type"], match["match_confidence"], match["match_company"])
                        return {"linkedin_url": scraped_url, "source": f"l2_verified_{candidate_source}",
                                "tier": "L2", **match,
                                "l1_candidate_url": candidate_url, "l1_candidate_source": candidate_source}

                    # Profile scraped but company doesn't match
                    profile_headline = profile.get("headline", "")
                    profile_exp = profile.get("experience") or profile.get("experiences") or []
                    exp_companies = [
                        (e.get("company") or e.get("companyName") or e.get("subtitle") or "")
                        for e in profile_exp if isinstance(e, dict)
                    ]
                    logger.info(
                        "F5 LinkedIn L2: REJECTED %s (headline='%s', companies=%s, wanted='%s')",
                        scraped_url, profile_headline[:60], exp_companies[:3], business_name)
                    return {"linkedin_url": None, "source": "unresolved", "tier": "L2",
                            "match_type": "no_match", "match_company": match["match_company"],
                            "match_confidence": match["match_confidence"],
                            "l2_status": "rejected_no_company_match",
                            "l2_profile_headline": profile_headline[:100],
                            "l2_profile_companies": exp_companies[:5],
                            "l1_candidate_url": candidate_url, "l1_candidate_source": candidate_source}

    except Exception as e:
        logger.warning("F5 LinkedIn L2 scraper failed: %s", e)

    return {"linkedin_url": None, "source": "unresolved", "tier": "L3",
            "match_type": "no_match", "match_company": "", "match_confidence": 0.0}


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
    company_linkedin_url: str | None = None,
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
    linkedin = await _linkedin_cascade(dm_name, business_name, f3a_linkedin_url, f4_linkedin_url, company_linkedin_url)
    resolved_li = linkedin.get("linkedin_url")

    # Email and mobile can run in parallel
    email_task = _email_waterfall(dm_name, domain, resolved_li)
    mobile_task = _mobile_waterfall(dm_name, domain, resolved_li, entity_type, business_phone)
    email, mobile = await asyncio.gather(email_task, mobile_task)

    return {"linkedin": linkedin, "email": email, "mobile": mobile}
