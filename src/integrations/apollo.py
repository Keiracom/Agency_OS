"""
FILE: src/integrations/apollo.py
PURPOSE: Apollo.io API integration for primary enrichment
PHASE: 3 (Integrations), updated Phase 24A (Lead Pool)
TASK: INT-003, POOL-004
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70

PHASE 24A CHANGES:
  - Updated _transform_person to capture ALL 50+ Apollo fields
  - Added _transform_person_for_pool for lead_pool table compatibility
  - Added email_status capture (CRITICAL for bounce prevention)
  - Added timezone inference from location
"""

from typing import Any

import httpx
import sentry_sdk
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ValidationError


class ApolloClient:
    """
    Apollo.io API client for lead enrichment.

    Apollo is the primary enrichment source (Tier 1) in the
    enrichment waterfall.
    """

    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.apollo_api_key
        if not self.api_key:
            raise IntegrationError(
                service="apollo",
                message="Apollo API key is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    "X-Api-Key": self.api_key,  # Apollo now requires API key in header
                },
                timeout=30.0,
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

        # Add API key to data
        request_data = data or {}
        request_data["api_key"] = self.api_key

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=request_data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            sentry_sdk.set_context("apollo_request", {
                "endpoint": endpoint,
                "method": method,
                "status_code": e.response.status_code,
            })
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="apollo",
                status_code=e.response.status_code,
                response=e.response.text,
                message=f"Apollo API error: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            sentry_sdk.set_context("apollo_request", {
                "endpoint": endpoint,
                "method": method,
            })
            sentry_sdk.capture_exception(e)
            raise IntegrationError(
                service="apollo",
                message=f"Apollo request failed: {str(e)}",
            )

    async def enrich_person(
        self,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """
        Enrich a person by email, LinkedIn URL, or name + domain.

        Args:
            email: Email address to look up
            linkedin_url: LinkedIn profile URL
            first_name: First name (used with domain)
            last_name: Last name (used with domain)
            domain: Company domain (used with name)

        Returns:
            Enriched person data

        Raises:
            ValidationError: If no valid lookup parameters provided
            APIError: If Apollo API returns an error
        """
        if not any([email, linkedin_url, (first_name and last_name and domain)]):
            raise ValidationError(
                message="Must provide email, LinkedIn URL, or name + domain",
            )

        data = {}
        if email:
            data["email"] = email
        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if domain:
            data["domain"] = domain

        result = await self._request("POST", "/people/match", data)

        if not result.get("person"):
            return {"found": False, "confidence": 0.0}

        person = result["person"]
        return self._transform_person(person)

    async def enrich_company(self, domain: str) -> dict[str, Any]:
        """
        Enrich a company by domain.

        Args:
            domain: Company domain to look up

        Returns:
            Enriched company data
        """
        result = await self._request(
            "POST",
            "/organizations/enrich",
            {"domain": domain},
        )

        if not result.get("organization"):
            return {"found": False, "confidence": 0.0}

        org = result["organization"]
        return self._transform_company(org)

    async def search_organizations(
        self,
        company_name: str,
        locations: list[str] | None = None,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Search for organizations by name.

        Args:
            company_name: Company name to search for
            locations: Optional location filters (e.g., ["Australia"])
            limit: Maximum results to return

        Returns:
            List of matching organizations
        """
        data: dict[str, Any] = {
            "q_organization_name": company_name,
            "per_page": min(limit, 10),
            "page": 1,
        }

        # Add location filters if provided
        if locations:
            data["organization_locations"] = locations

        try:
            result = await self._request(
                "POST",
                "/mixed_companies/search",
                data,
            )

            organizations = result.get("organizations", [])
            if not organizations:
                return []

            return [self._transform_company(org) for org in organizations[:limit]]
        except Exception as e:
            # Log but don't fail - search may not be available on all plans
            import logging
            logging.warning(f"Apollo organization search failed for {company_name}: {e}")
            return []

    async def search_people(
        self,
        domain: str,
        titles: list[str] | None = None,
        seniorities: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for people at a company.

        Args:
            domain: Company domain
            titles: Filter by job titles
            seniorities: Filter by seniority levels
            limit: Maximum results to return

        Returns:
            List of matching people
        """
        data = {
            "q_organization_domains": domain,
            "per_page": min(limit, 100),
        }

        if titles:
            data["person_titles"] = titles
        if seniorities:
            data["person_seniorities"] = seniorities

        result = await self._request("POST", "/mixed_people/api_search", data)

        people = result.get("people", [])
        return [self._transform_person(p) for p in people]

    async def search_people_for_pool(
        self,
        domain: str | None = None,
        titles: list[str] | None = None,
        seniorities: list[str] | None = None,
        industries: list[str] | None = None,
        employee_min: int | None = None,
        employee_max: int | None = None,
        countries: list[str] | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """
        Search for people with full pool-compatible data.

        This method is designed for populating the lead_pool with
        maximum data capture. Returns all 50+ fields.

        NOTE: Apollo API changed in 2025 - search now returns preview data only.
        We use /mixed_people/api_search to find candidates, then /people/match
        to get full contact details for each person.

        Args:
            domain: Company domain filter
            titles: Filter by job titles (e.g., ["CEO", "Founder"])
            seniorities: Filter by seniority (e.g., ["c_suite", "vp"])
            industries: Filter by industry (e.g., ["marketing", "advertising"])
            employee_min: Minimum employee count
            employee_max: Maximum employee count
            countries: Filter by country (e.g., ["Australia"])
            limit: Maximum results (up to 100)

        Returns:
            List of people with full pool-compatible data
        """
        import asyncio

        data: dict[str, Any] = {
            "per_page": min(limit, 100),
        }

        if domain:
            data["q_organization_domains"] = domain
        if titles:
            data["person_titles"] = titles
        if seniorities:
            data["person_seniorities"] = seniorities
        if industries:
            # Use q_organization_keyword_tags for text-based industry filtering
            # (organization_industry_tag_ids requires numeric Apollo IDs)
            data["q_organization_keyword_tags"] = industries
        if employee_min and employee_max:
            data["organization_num_employees_ranges"] = [
                f"{employee_min},{employee_max}"
            ]
        if countries:
            data["person_locations"] = countries

        # Step 1: Search for people (returns preview data only)
        search_result = await self._request("POST", "/mixed_people/api_search", data)
        preview_people = search_result.get("people", [])

        if not preview_people:
            return []

        # Step 2: Enrich each person to get full data
        # Apollo /people/match requires name + org or email or linkedin
        import logging
        logger = logging.getLogger(__name__)

        enriched_people = []
        logger.info(f"[Apollo] Found {len(preview_people)} preview people, enriching...")

        for preview in preview_people:
            try:
                # Skip people without emails in Apollo's database
                if not preview.get("has_email"):
                    logger.debug(f"[Apollo] Skipping {preview.get('first_name')} - no email in Apollo")
                    continue

                # Extract person ID from preview - this is the key for email retrieval
                person_id = preview.get("id")
                first_name = preview.get("first_name")
                org_name = (preview.get("organization") or {}).get("name")

                if person_id:
                    # Use /people/match with ID to get full data including email
                    # IMPORTANT: Matching by ID returns email, matching by name doesn't
                    match_result = await self._request(
                        "POST",
                        "/people/match",
                        {
                            "id": person_id,
                        },
                    )

                    person = match_result.get("person")
                    if person:
                        enriched = self._transform_person_for_pool(person)
                        email = enriched.get("email")
                        if email:  # Only include if we got an email
                            enriched_people.append(enriched)
                            logger.info(f"[Apollo] Enriched: {first_name} at {org_name} -> {email}")
                        else:
                            logger.debug(f"[Apollo] No email for: {first_name} at {org_name}")
                    else:
                        logger.debug(f"[Apollo] No match for ID: {person_id}")
                else:
                    logger.debug(f"[Apollo] No ID for: {first_name} at {org_name}")

                # Rate limit: avoid hitting Apollo too fast
                await asyncio.sleep(0.2)

            except Exception as e:
                logger.warning(f"[Apollo] Error enriching person: {e}")
                continue

        logger.info(f"[Apollo] Enrichment complete: {len(enriched_people)} with emails")
        return enriched_people

    async def enrich_person_for_pool(
        self,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """
        Enrich a person and return full pool-compatible data.

        This is the preferred enrichment method for leads going into
        the lead_pool. Captures all 50+ Apollo fields.

        Args:
            email: Email address to look up
            linkedin_url: LinkedIn profile URL
            first_name: First name (used with domain)
            last_name: Last name (used with domain)
            domain: Company domain (used with name)

        Returns:
            Enriched person data in lead_pool format
        """
        if not any([email, linkedin_url, (first_name and last_name and domain)]):
            raise ValidationError(
                message="Must provide email, LinkedIn URL, or name + domain",
            )

        data = {}
        if email:
            data["email"] = email
        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        if domain:
            data["domain"] = domain

        result = await self._request("POST", "/people/match", data)

        if not result.get("person"):
            return {"found": False, "confidence": 0.0}

        person = result["person"]
        return self._transform_person_for_pool(person)

    def _transform_person(self, person: dict) -> dict[str, Any]:
        """Transform Apollo person response to standard format (legacy compatibility)."""
        org = person.get("organization", {}) or {}

        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(person)

        # Extract phone
        phone = None
        if person.get("phone_numbers"):
            phone = person["phone_numbers"][0].get("sanitized_number")

        # Extract personal email
        personal_email = None
        if person.get("personal_emails"):
            personal_email = person["personal_emails"][0]

        # Extract employment start date
        employment_start_date = None
        if person.get("employment_history"):
            employment_start_date = person["employment_history"][0].get("start_date")

        return {
            "found": True,
            "confidence": confidence,
            "source": "apollo",
            # Person data
            "email": person.get("email"),
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "title": person.get("title"),
            "linkedin_url": person.get("linkedin_url"),
            "phone": phone,
            "personal_email": personal_email,
            "seniority": person.get("seniority"),
            "employment_start_date": employment_start_date,
            # Company data
            "company": org.get("name"),
            "domain": org.get("primary_domain"),
            "organization_industry": org.get("industry"),
            "organization_employee_count": org.get("estimated_num_employees"),
            "organization_country": org.get("country"),
            "organization_founded_year": org.get("founded_year"),
            "organization_is_hiring": org.get("is_hiring"),
            "organization_latest_funding_date": org.get("latest_funding_date"),
            "organization_website": org.get("website_url"),
            "organization_linkedin_url": org.get("linkedin_url"),
        }

    def _transform_person_for_pool(self, person: dict) -> dict[str, Any]:
        """
        Transform Apollo person response to lead_pool table format.

        Captures ALL 50+ fields from Apollo for maximum CIS learning.
        This is the preferred method for new leads going into the pool.
        """
        org = person.get("organization", {}) or {}

        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(person)

        # Extract phone (prefer mobile/direct)
        phone = None
        if person.get("phone_numbers"):
            for pn in person["phone_numbers"]:
                if pn.get("type") in ("mobile", "direct"):
                    phone = pn.get("sanitized_number")
                    break
            if not phone and person["phone_numbers"]:
                phone = person["phone_numbers"][0].get("sanitized_number")

        # Extract personal email
        personal_email = None
        if person.get("personal_emails"):
            personal_email = person["personal_emails"][0]

        # Extract full employment history
        employment_history = []
        current_role_start_date = None
        for job in person.get("employment_history", []):
            employment_history.append({
                "company": job.get("organization_name"),
                "title": job.get("title"),
                "start_date": job.get("start_date"),
                "end_date": job.get("end_date"),
                "is_current": job.get("current", False),
            })
            if job.get("current") and not current_role_start_date:
                current_role_start_date = job.get("start_date")

        # Infer timezone from country (basic mapping)
        timezone = self._infer_timezone(
            person.get("country"),
            person.get("state"),
            person.get("city")
        )

        return {
            # ===== META =====
            "found": True,
            "confidence": confidence,
            "enrichment_source": "apollo",

            # ===== IDENTIFIERS =====
            "apollo_id": person.get("id"),
            "email": person.get("email"),
            "email_status": person.get("email_status", "unknown"),  # CRITICAL
            "linkedin_url": person.get("linkedin_url"),

            # ===== PERSON DATA =====
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "title": person.get("title"),
            "seniority": person.get("seniority"),
            "linkedin_headline": person.get("headline"),
            "photo_url": person.get("photo_url"),
            "twitter_url": person.get("twitter_url"),
            "phone": phone,
            "personal_email": personal_email,

            # Person Location
            "city": person.get("city"),
            "state": person.get("state"),
            "country": person.get("country"),
            "timezone": timezone,

            # Departments
            "departments": person.get("departments", []),

            # Employment History
            "employment_history": employment_history if employment_history else None,
            "current_role_start_date": current_role_start_date,

            # ===== ORGANISATION DATA =====
            "company_name": org.get("name"),
            "company_domain": org.get("primary_domain"),
            "company_website": org.get("website_url"),
            "company_linkedin_url": org.get("linkedin_url"),
            "company_description": org.get("short_description"),
            "company_logo_url": org.get("logo_url"),

            # Company Firmographics
            "company_industry": org.get("industry"),
            "company_sub_industry": org.get("sub_industry"),
            "company_employee_count": org.get("estimated_num_employees"),
            "company_revenue": org.get("revenue"),
            "company_revenue_range": org.get("revenue_range"),
            "company_founded_year": org.get("founded_year"),
            "company_country": org.get("country"),
            "company_city": org.get("city"),
            "company_state": org.get("state"),
            "company_postal_code": org.get("postal_code"),

            # Company Signals
            "company_is_hiring": org.get("is_hiring"),
            "company_latest_funding_stage": org.get("latest_funding_stage"),
            "company_latest_funding_date": org.get("latest_funding_date"),
            "company_total_funding": org.get("total_funding"),
            "company_technologies": org.get("technologies", []),
            "company_keywords": org.get("keywords", []),

            # Raw data for reference
            "enrichment_data": {
                "apollo_person_id": person.get("id"),
                "apollo_org_id": org.get("id"),
                "raw_seniorities": person.get("seniorities", []),
                "raw_departments": person.get("departments", []),
            },
        }

    def _infer_timezone(
        self,
        country: str | None,
        state: str | None,
        city: str | None
    ) -> str | None:
        """
        Infer timezone from location data.

        Basic mapping for common countries. Can be enhanced with
        a proper timezone database later.
        """
        if not country:
            return None

        country_lower = country.lower()

        # Australia (primary market)
        if country_lower in ("australia", "au"):
            state_lower = (state or "").lower()
            if state_lower in ("western australia", "wa"):
                return "Australia/Perth"
            elif state_lower in ("south australia", "sa"):
                return "Australia/Adelaide"
            elif state_lower in ("queensland", "qld"):
                return "Australia/Brisbane"
            elif state_lower in ("northern territory", "nt"):
                return "Australia/Darwin"
            else:
                # Default to Sydney for NSW, VIC, TAS, ACT
                return "Australia/Sydney"

        # Common countries
        timezone_map = {
            "united states": "America/New_York",
            "us": "America/New_York",
            "usa": "America/New_York",
            "united kingdom": "Europe/London",
            "uk": "Europe/London",
            "canada": "America/Toronto",
            "new zealand": "Pacific/Auckland",
            "nz": "Pacific/Auckland",
            "singapore": "Asia/Singapore",
            "india": "Asia/Kolkata",
            "germany": "Europe/Berlin",
            "france": "Europe/Paris",
            "japan": "Asia/Tokyo",
            "china": "Asia/Shanghai",
            "hong kong": "Asia/Hong_Kong",
        }

        return timezone_map.get(country_lower)

    def _transform_company(self, org: dict) -> dict[str, Any]:
        """Transform Apollo organization response to standard format."""
        return {
            "found": True,
            "confidence": 0.95,  # Company data is usually reliable
            "source": "apollo",
            "name": org.get("name"),
            "domain": org.get("primary_domain"),
            "industry": org.get("industry"),
            "employee_count": org.get("estimated_num_employees"),
            "country": org.get("country"),
            "founded_year": org.get("founded_year"),
            "is_hiring": org.get("is_hiring"),
            "latest_funding_date": org.get("latest_funding_date"),
            "website": org.get("website_url"),
            "linkedin_url": org.get("linkedin_url"),
            "description": org.get("short_description"),
        }

    def _calculate_confidence(self, person: dict) -> float:
        """
        Calculate enrichment confidence score.

        Based on data completeness and verification status.
        """
        score = 0.0
        max_score = 0.0

        # Email (verified is best)
        max_score += 30
        if person.get("email"):
            if person.get("email_status") == "verified":
                score += 30
            elif person.get("email_status") == "guessed":
                score += 15
            else:
                score += 20

        # Name
        max_score += 20
        if person.get("first_name") and person.get("last_name"):
            score += 20
        elif person.get("first_name") or person.get("last_name"):
            score += 10

        # Title
        max_score += 15
        if person.get("title"):
            score += 15

        # Company
        max_score += 15
        if person.get("organization", {}).get("name"):
            score += 15

        # LinkedIn
        max_score += 10
        if person.get("linkedin_url"):
            score += 10

        # Phone
        max_score += 10
        if person.get("phone_numbers"):
            score += 10

        return round(score / max_score, 2) if max_score > 0 else 0.0


# Singleton instance
_apollo_client: ApolloClient | None = None


def get_apollo_client() -> ApolloClient:
    """Get or create Apollo client instance."""
    global _apollo_client
    if _apollo_client is None:
        _apollo_client = ApolloClient()
    return _apollo_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Retry logic with tenacity
# [x] Person enrichment by email/LinkedIn/name+domain
# [x] Company enrichment by domain
# [x] People search
# [x] Confidence calculation
# [x] Standard response format
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
# --- Phase 24A Additions ---
# [x] _transform_person_for_pool captures 50+ fields
# [x] enrich_person_for_pool method for pool enrichment
# [x] search_people_for_pool method for pool population
# [x] _infer_timezone helper for lead timezone
# [x] email_status capture (CRITICAL for bounce prevention)
