"""
FILE: src/integrations/clay.py
PURPOSE: Clay API integration for premium fallback enrichment
PHASE: 3 (Integrations)
TASK: INT-005
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - Clay is Tier 2 fallback (max 15% of batch)
"""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class ClayClient:
    """
    Clay API client for premium enrichment fallback.

    Clay is the Tier 2 enrichment source, used when Apollo + Apify
    fail to provide sufficient data. Limited to 15% of batch.
    """

    BASE_URL = "https://api.clay.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.clay_api_key
        if not self.api_key:
            raise IntegrationError(
                service="clay",
                message="Clay API key is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,  # Clay can be slow
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                service="clay",
                status_code=e.response.status_code,
                response=e.response.text,
                message=f"Clay API error: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="clay",
                message=f"Clay request failed: {str(e)}",
            )

    async def enrich_person(
        self,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
    ) -> dict[str, Any]:
        """
        Enrich a person using Clay's data sources.

        Args:
            email: Email address
            linkedin_url: LinkedIn profile URL
            first_name: First name
            last_name: Last name
            company: Company name

        Returns:
            Enriched person data
        """
        data = {
            "email": email,
            "linkedin_url": linkedin_url,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
        }
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        result = await self._request("POST", "/enrich/person", data)

        if not result.get("person"):
            return {"found": False, "confidence": 0.0}

        return self._transform_person(result["person"])

    async def enrich_company(self, domain: str) -> dict[str, Any]:
        """
        Enrich a company using Clay's data sources.

        Args:
            domain: Company domain

        Returns:
            Enriched company data
        """
        result = await self._request(
            "POST",
            "/enrich/company",
            {"domain": domain},
        )

        if not result.get("company"):
            return {"found": False, "confidence": 0.0}

        return self._transform_company(result["company"])

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> dict[str, Any]:
        """
        Find email address for a person.

        Args:
            first_name: First name
            last_name: Last name
            domain: Company domain

        Returns:
            Email finding result
        """
        result = await self._request(
            "POST",
            "/find/email",
            {
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain,
            },
        )

        return {
            "found": bool(result.get("email")),
            "email": result.get("email"),
            "confidence": result.get("confidence", 0.0),
            "verification_status": result.get("verification_status"),
        }

    async def waterfall_enrich(
        self,
        leads: list[dict[str, Any]],
        max_percentage: float = 0.15,
    ) -> list[dict[str, Any]]:
        """
        Enrich leads using Clay waterfall (max 15% of batch).

        This is the fallback enrichment path when Apollo + Apify
        don't provide sufficient data.

        Args:
            leads: List of leads to enrich
            max_percentage: Maximum percentage of leads to send to Clay

        Returns:
            Enriched leads
        """
        max_leads = int(len(leads) * max_percentage)
        leads_to_enrich = leads[:max_leads]

        results = []
        for lead in leads_to_enrich:
            try:
                enriched = await self.enrich_person(
                    email=lead.get("email"),
                    linkedin_url=lead.get("linkedin_url"),
                    first_name=lead.get("first_name"),
                    last_name=lead.get("last_name"),
                    company=lead.get("company"),
                )
                results.append({**lead, **enriched})
            except Exception:
                results.append({**lead, "found": False, "source": "clay_failed"})

        return results

    def _transform_person(self, person: dict) -> dict[str, Any]:
        """Transform Clay person response to standard format."""
        return {
            "found": True,
            "confidence": person.get("confidence", 0.85),
            "source": "clay",
            # Person data
            "email": person.get("email"),
            "email_verified": person.get("email_verified"),
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "title": person.get("title"),
            "linkedin_url": person.get("linkedin_url"),
            "phone": person.get("phone"),
            "seniority": person.get("seniority"),
            # Company data
            "company": person.get("company_name"),
            "domain": person.get("company_domain"),
            "organization_industry": person.get("company_industry"),
            "organization_employee_count": person.get("company_size"),
            "organization_country": person.get("company_country"),
        }

    def _transform_company(self, company: dict) -> dict[str, Any]:
        """Transform Clay company response to standard format."""
        return {
            "found": True,
            "confidence": 0.90,
            "source": "clay",
            "name": company.get("name"),
            "domain": company.get("domain"),
            "industry": company.get("industry"),
            "employee_count": company.get("employee_count"),
            "country": company.get("country"),
            "founded_year": company.get("founded_year"),
            "description": company.get("description"),
            "technologies": company.get("technologies", []),
        }


# Singleton instance
_clay_client: ClayClient | None = None


def get_clay_client() -> ClayClient:
    """Get or create Clay client instance."""
    global _clay_client
    if _clay_client is None:
        _clay_client = ClayClient()
    return _clay_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Retry logic with tenacity
# [x] Person enrichment
# [x] Company enrichment
# [x] Email finder
# [x] Waterfall enrich with 15% limit
# [x] Standard response format
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
