"""
Contract: src/integrations/contactout_client.py
Purpose: ContactOut API integration for contact enrichment via LinkedIn URL
Layer: 2 - integrations
Endpoint: POST /v1/people/enrich (canonical — NOT /v1/people/linkedin)
Auth: authorization: basic + token: <API_KEY> headers
"""
import logging
import os
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

CONTACTOUT_API_URL = "https://api.contactout.com/v1/people/enrich"


@dataclass
class ContactOutResult:
    """Enrichment result from ContactOut."""

    linkedin_url: str
    full_name: str = ""
    headline: str = ""

    # Emails (all returned — nothing discarded)
    all_emails: list[str] = field(default_factory=list)
    work_emails: list[str] = field(default_factory=list)
    personal_emails: list[str] = field(default_factory=list)
    email_verification: dict = field(default_factory=dict)  # {email: status}

    # Selected best email (after freshness logic)
    best_work_email: str = ""
    best_email_confidence: str = ""  # "current_match", "stale", "personal_only", "none"

    # Phones
    all_phones: list[str] = field(default_factory=list)
    best_phone: str = ""  # Preferred AU mobile

    # Company (from ContactOut profile)
    company_name: str = ""
    company_domain: str = ""
    company_linkedin_url: str = ""
    company_industry: str = ""
    company_size: str = ""

    # Metadata
    found: bool = False
    raw_response: dict = field(default_factory=dict)


class ContactOutClient:
    """ContactOut enrichment client using /v1/people/enrich."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CONTACTOUT_API_KEY", "")
        if not self.api_key:
            logger.warning("No CONTACTOUT_API_KEY configured")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def enrich_by_linkedin(self, linkedin_url: str) -> ContactOutResult:
        """Enrich a prospect by LinkedIn URL. Returns full result with freshness logic applied."""
        result = ContactOutResult(linkedin_url=linkedin_url)

        if not self.is_configured:
            logger.warning("ContactOut not configured — skipping")
            return result

        headers = {
            "authorization": "basic",
            "token": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    CONTACTOUT_API_URL,
                    headers=headers,
                    json={
                        "linkedin_url": linkedin_url,
                        "include": ["work_email", "personal_email", "phone"],
                    },
                )

            if resp.status_code == 404:
                logger.info(f"ContactOut: profile not found for {linkedin_url}")
                return result

            if resp.status_code != 200:
                logger.warning(
                    f"ContactOut: HTTP {resp.status_code} for {linkedin_url}: {resp.text[:200]}"
                )
                return result

            data = resp.json()
            profile = data.get("profile", {})
            result.found = True
            result.raw_response = data

            # Parse profile
            result.full_name = profile.get("full_name", "")
            result.headline = profile.get("headline", "")

            # Parse emails
            result.all_emails = profile.get("email", [])
            result.work_emails = profile.get("work_email", [])
            result.personal_emails = profile.get("personal_email", [])
            result.email_verification = profile.get("work_email_status", {})

            # Parse phones
            result.all_phones = profile.get("phone", [])

            # Parse company
            company = profile.get("company", {})
            if isinstance(company, dict):
                result.company_name = company.get("name", "")
                result.company_domain = company.get("domain", "") or company.get(
                    "email_domain", ""
                )
                result.company_linkedin_url = company.get("url", "")
                result.company_industry = company.get("industry", "")
                result.company_size = company.get("size", "")

            # Apply freshness selection logic
            self._select_best_email(result)
            self._select_best_phone(result)

            return result

        except httpx.TimeoutException:
            logger.warning(f"ContactOut: timeout for {linkedin_url}")
            return result
        except Exception as e:
            logger.error(f"ContactOut: error for {linkedin_url}: {e}")
            return result

    def _select_best_email(self, result: ContactOutResult) -> None:
        """Freshness selection: prefer email whose domain matches current company."""
        company_domain = result.company_domain.lower().strip()

        if not company_domain:
            # No company domain to match against
            if result.work_emails:
                result.best_work_email = result.work_emails[0]
                result.best_email_confidence = "no_company_domain"
            elif result.all_emails:
                result.best_work_email = result.all_emails[0]
                result.best_email_confidence = "personal_only"
            else:
                result.best_email_confidence = "none"
            return

        # Check work_emails first for domain match
        for email in result.work_emails:
            if "@" in email and email.split("@")[1].lower() == company_domain:
                result.best_work_email = email
                result.best_email_confidence = "current_match"
                return

        # Check all emails for domain match
        for email in result.all_emails:
            if "@" in email and email.split("@")[1].lower() == company_domain:
                result.best_work_email = email
                result.best_email_confidence = "current_match"
                return

        # No domain match — flag as stale
        if result.work_emails:
            result.best_work_email = result.work_emails[0]
            result.best_email_confidence = "stale"
        elif result.all_emails:
            result.best_work_email = result.all_emails[0]
            result.best_email_confidence = "stale"
        else:
            result.best_email_confidence = "none"

    def _select_best_phone(self, result: ContactOutResult) -> None:
        """Prefer AU mobile (+61 4xx) over other formats."""
        for phone in result.all_phones:
            cleaned = phone.replace(" ", "").replace("-", "")
            # AU mobile: +614xxxxxxxx
            if cleaned.startswith("+614") and len(cleaned) >= 12:
                result.best_phone = phone
                return
            # AU any: +61
            if cleaned.startswith("+61"):
                result.best_phone = phone
                return
        # Fallback: first phone
        if result.all_phones:
            result.best_phone = result.all_phones[0]


def get_contactout_client() -> ContactOutClient:
    """Factory function for ContactOutClient."""
    return ContactOutClient()
