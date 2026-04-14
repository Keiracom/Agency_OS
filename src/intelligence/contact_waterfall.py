"""F5 — Contact waterfalls: LinkedIn URL, email, mobile.

Three cascading waterfalls for DM contact resolution.

LinkedIn URL  tiers: L1 F3 Gemini → L2 Apify harvestapi → L4 unresolved
Email         tiers: L1 ContactOut → L2 Hunter → L3 Pattern+ZeroBounce → L5 unresolved
Mobile        tiers: L0 Sole-trader inference → L1 ContactOut → L4 unresolved

Ratified: 2026-04-14. Pipeline F architecture.
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

from src.common.phone_classifier import classify_au_phone

logger = logging.getLogger(__name__)

CONTACTOUT_URL = "https://api.contactout.com/v1/people/enrich"


class ContactWaterfall:
    """F5 stage: three contact waterfalls for DM resolution."""

    def __init__(self) -> None:
        self._co_key = os.environ.get("CONTACTOUT_API_KEY", "")
        self._hunter_key = os.environ.get("HUNTER_API_KEY", "")
        self._zb_key = os.environ.get("ZEROBOUNCE_API_KEY", "")
        self._apify_token = os.environ.get("APIFY_API_TOKEN", "")
        self._stats: dict = {"linkedin": {}, "email": {}, "mobile": {}}

    async def resolve(
        self,
        dm_name: str,
        dm_title: str | None,
        business_name: str,
        domain: str,
        linkedin_url: str | None = None,
        entity_type: str | None = None,
        business_phone: str | None = None,
    ) -> dict:
        """
        Run all three contact waterfalls in parallel.

        Returns merged contact dict:
        {
          "linkedin": {"linkedin_url": str|None, "source": str, "tier": str},
          "email":    {"email": str|None, "source": str, "tier": str, ...},
          "mobile":   {"mobile": str|None, "source": str, "tier": str, ...},
        }
        """
        linkedin, email, mobile = await asyncio.gather(
            self._linkedin_cascade(dm_name, business_name, linkedin_url),
            self._email_waterfall(dm_name, domain, linkedin_url),
            self._mobile_waterfall(dm_name, domain, linkedin_url, entity_type, business_phone),
        )
        # Re-run email/mobile with resolved LinkedIn URL if L2+ found one
        resolved_li = linkedin.get("linkedin_url")
        if resolved_li and resolved_li != linkedin_url:
            email, mobile = await asyncio.gather(
                self._email_waterfall(dm_name, domain, resolved_li),
                self._mobile_waterfall(dm_name, domain, resolved_li, entity_type, business_phone),
            )
        return {"linkedin": linkedin, "email": email, "mobile": mobile}

    # ------------------------------------------------------------------
    # LinkedIn waterfall
    # ------------------------------------------------------------------

    async def _linkedin_cascade(
        self,
        dm_name: str,
        business_name: str,
        f3_url: str | None,
    ) -> dict:
        """L1 F3 Gemini → L2 Apify harvestapi → L4 unresolved."""
        # L1: F3 already found a URL
        if f3_url:
            return {"linkedin_url": f3_url, "source": "f3_gemini", "tier": "L1"}

        # L2: Apify harvestapi/linkedin-profile-search-by-name
        if self._apify_token and dm_name:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    run_resp = await client.post(
                        f"https://api.apify.com/v2/acts/harvestapi~linkedin-profile-search-by-name/runs"
                        f"?token={self._apify_token}",
                        json={"name": dm_name, "company": business_name, "maxResults": 3},
                    )
                    if run_resp.status_code in (200, 201):
                        run_id = run_resp.json().get("data", {}).get("id")
                        if run_id:
                            url = await self._poll_apify_run(client, run_id)
                            if url:
                                return {"linkedin_url": url, "source": "apify_harvestapi", "tier": "L2"}
            except Exception as exc:
                logger.warning("F5 LinkedIn L2 Apify failed for %s: %s", dm_name, exc)

        # L3: Bright Data Web Unlocker — skipped (complex auth setup, not yet configured)
        # TODO: implement L3 when BD Web Unlocker credentials are available

        # L4: Unresolved
        return {"linkedin_url": None, "source": "unresolved", "tier": "L4"}

    async def _poll_apify_run(
        self,
        client: httpx.AsyncClient,
        run_id: str,
        max_polls: int = 10,
        poll_interval: float = 3.0,
    ) -> str | None:
        """Poll Apify run until SUCCEEDED/terminal. Returns first LinkedIn URL or None."""
        for _ in range(max_polls):
            await asyncio.sleep(poll_interval)
            try:
                sr = await client.get(
                    f"https://api.apify.com/v2/actor-runs/{run_id}?token={self._apify_token}"
                )
                run_data = sr.json().get("data", {})
                status = run_data.get("status", "")
                if status == "SUCCEEDED":
                    ds_id = run_data.get("defaultDatasetId")
                    if ds_id:
                        items_resp = await client.get(
                            f"https://api.apify.com/v2/datasets/{ds_id}/items?token={self._apify_token}"
                        )
                        for item in items_resp.json()[:3]:
                            url = (
                                item.get("profileUrl")
                                or item.get("profile_url")
                                or item.get("url")
                            )
                            if url and "linkedin.com" in url:
                                return url
                    return None
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    logger.warning("F5 Apify run %s ended with status %s", run_id, status)
                    return None
            except Exception as exc:
                logger.warning("F5 Apify poll error for run %s: %s", run_id, exc)
                return None
        return None

    # ------------------------------------------------------------------
    # Email waterfall
    # ------------------------------------------------------------------

    async def _email_waterfall(
        self,
        dm_name: str,
        domain: str,
        linkedin_url: str | None,
    ) -> dict:
        """L1 ContactOut → L2 Hunter → L3 Pattern+ZeroBounce → L5 unresolved."""
        parts = dm_name.split() if dm_name else []
        first_name = parts[0] if parts else ""
        last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # L1: ContactOut by LinkedIn URL
        if linkedin_url and self._co_key:
            result = await self._contactout_email(linkedin_url)
            if result:
                return result

        # L2: Hunter email-finder
        if self._hunter_key and first_name and domain:
            result = await self._hunter_email(first_name, last_name, domain)
            if result:
                return result

        # L3: Pattern guess + ZeroBounce verify
        if self._zb_key and first_name and domain:
            result = await self._pattern_zerobounce(first_name, last_name, domain)
            if result:
                return result

        # L4/L5: Unresolved
        return {"email": None, "source": "unresolved", "tier": "L5"}

    async def _contactout_email(self, linkedin_url: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    CONTACTOUT_URL,
                    headers={"authorization": "basic", "token": self._co_key},
                    json={"linkedin_url": linkedin_url},
                )
                if r.status_code == 200:
                    data = r.json()
                    profile = data.get("profile") or data.get("person") or data
                    emails = profile.get("emails") or profile.get("work_emails") or []
                    if emails:
                        email = emails[0] if isinstance(emails[0], str) else emails[0].get("email", "")
                        if email:
                            return {"email": email, "source": "contactout", "tier": "L1", "verified": True}
        except Exception as exc:
            logger.warning("F5 Email L1 ContactOut failed: %s", exc)
        return None

    async def _hunter_email(self, first_name: str, last_name: str, domain: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    "https://api.hunter.io/v2/email-finder",
                    params={
                        "domain": domain,
                        "first_name": first_name,
                        "last_name": last_name,
                        "api_key": self._hunter_key,
                    },
                )
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    email = data.get("email")
                    confidence = data.get("confidence", 0)
                    if email and confidence >= 70:
                        return {"email": email, "source": "hunter", "tier": "L2", "confidence": confidence}
        except Exception as exc:
            logger.warning("F5 Email L2 Hunter failed: %s", exc)
        return None

    async def _pattern_zerobounce(
        self, first_name: str, last_name: str, domain: str
    ) -> dict | None:
        first = first_name.lower()
        last = last_name.lower()
        patterns = [
            f"{first}.{last}@{domain}",
            f"{first[0]}{last}@{domain}",
            f"{first}@{domain}",
        ]
        for pattern in patterns:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(
                        "https://api.zerobounce.net/v2/validate",
                        params={"api_key": self._zb_key, "email": pattern},
                    )
                    if r.status_code == 200 and r.json().get("status") == "valid":
                        return {
                            "email": pattern,
                            "source": "pattern_zerobounce",
                            "tier": "L3",
                            "verified": True,
                        }
            except Exception:
                pass
        return None

    # ------------------------------------------------------------------
    # Mobile waterfall
    # ------------------------------------------------------------------

    async def _mobile_waterfall(
        self,
        dm_name: str,
        domain: str,
        linkedin_url: str | None,
        entity_type: str | None,
        business_phone: str | None,
    ) -> dict:
        """L0 sole-trader inference → L1 ContactOut → L4 unresolved."""
        # L0: Sole-trader — if the business phone IS a mobile, infer it's the DM's
        if business_phone and entity_type in ("Individual/Sole Trader", None):
            try:
                classified = classify_au_phone(business_phone)
                if classified["phone_type"] == "mobile":
                    return {
                        "mobile": classified["normalized_e164"],
                        "source": "sole_trader_inference",
                        "tier": "L0",
                        "phone_type": "mobile",
                        "sms_ok": True,
                        "voice_ai_ok": True,
                    }
            except Exception as exc:
                logger.warning("F5 Mobile L0 classify failed: %s", exc)

        # L1: ContactOut by LinkedIn URL
        if linkedin_url and self._co_key:
            result = await self._contactout_mobile(linkedin_url)
            if result:
                return result

        # L2-L3: Bright Data / Prospeo mobile — not yet configured
        # TODO: add L2 BD mobile lookup once credentials available

        # L4: Unresolved
        return {"mobile": None, "source": "unresolved", "tier": "L4"}

    async def _contactout_mobile(self, linkedin_url: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    CONTACTOUT_URL,
                    headers={"authorization": "basic", "token": self._co_key},
                    json={"linkedin_url": linkedin_url, "include": ["phone"]},
                )
                if r.status_code == 200:
                    profile = r.json().get("profile") or r.json()
                    phones = profile.get("phones") or profile.get("phone_numbers") or []
                    for phone in phones:
                        raw = phone if isinstance(phone, str) else phone.get("number", "")
                        if raw:
                            classified = classify_au_phone(raw)
                            if classified["phone_type"] == "mobile":
                                return {
                                    "mobile": classified["normalized_e164"],
                                    "source": "contactout",
                                    "tier": "L1",
                                    **classified,
                                }
        except Exception as exc:
            logger.warning("F5 Mobile L1 ContactOut failed: %s", exc)
        return None
