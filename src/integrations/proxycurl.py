"""
FILE: src/integrations/proxycurl.py
PURPOSE: Proxycurl API client for LinkedIn profile and company enrichment
PHASE: SIEGE (System Overhaul)
TASK: SIEGE-004
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

SIEGE CONTEXT:
  Tier 4 of the Siege Waterfall - "LinkedIn Intelligence"
  Cost: ~$0.015 AUD per credit ($0.01 USD @ 1.50 AUD/USD)
  
  Primary use case: LinkedIn profile enrichment for lead qualification
  Secondary: Company enrichment for firmographic data
  
  API Reference: https://nubela.co/proxycurl/docs
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
import sentry_sdk
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ValidationError

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS
# ============================================

# Cost per credit in $AUD (LAW II compliance)
# Proxycurl charges ~$0.01 USD per credit, converted to AUD @ ~1.50
COST_PER_CREDIT_AUD = 0.015

# Credit costs per endpoint (approximate)
CREDITS_PROFILE_ENRICHMENT = 1  # Person Profile endpoint
CREDITS_COMPANY_ENRICHMENT = 1  # Company Profile endpoint
CREDITS_PROFILE_SEARCH = 3      # Person Search endpoint

# Proxycurl API configuration
BASE_URL = "https://nubela.co/proxycurl/api"
DEFAULT_TIMEOUT = 60.0  # Profile enrichment can be slow

# Rate limiting (Pro plan: 300/min, Free: 5/min)
MAX_REQUESTS_PER_MINUTE = 100  # Conservative for burst protection
REQUEST_DELAY_SECONDS = 0.2  # Safety buffer


# ============================================
# DATA CLASSES
# ============================================


@dataclass
class ProxycurlProfileResult:
    """Result from Proxycurl profile enrichment."""
    
    found: bool
    linkedin_url: str | None = None
    
    # Personal info
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    profile_picture_url: str | None = None
    
    # Current position
    occupation: str | None = None
    current_company: str | None = None
    current_company_linkedin_url: str | None = None
    current_title: str | None = None
    
    # Contact info (if available)
    email: str | None = None
    phone_numbers: list[str] = field(default_factory=list)
    
    # Location
    city: str | None = None
    state: str | None = None
    country: str | None = None
    country_full_name: str | None = None
    
    # Professional details
    industry: str | None = None
    connections: int | None = None
    follower_count: int | None = None
    
    # Experience and education (summarized)
    experience_count: int = 0
    education_count: int = 0
    languages: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    
    # Cost tracking
    credits_used: int = 0
    cost_aud: float = 0.0
    source: str = "proxycurl"
    
    # Raw data for debugging
    raw_response: dict | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/API response."""
        return {
            "found": self.found,
            "linkedin_url": self.linkedin_url,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "headline": self.headline,
            "summary": self.summary,
            "profile_picture_url": self.profile_picture_url,
            "occupation": self.occupation,
            "current_company": self.current_company,
            "current_company_linkedin_url": self.current_company_linkedin_url,
            "current_title": self.current_title,
            "email": self.email,
            "phone_numbers": self.phone_numbers,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "country_full_name": self.country_full_name,
            "industry": self.industry,
            "connections": self.connections,
            "follower_count": self.follower_count,
            "experience_count": self.experience_count,
            "education_count": self.education_count,
            "languages": self.languages,
            "skills": self.skills[:10] if self.skills else [],  # Top 10 skills
            "credits_used": self.credits_used,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


@dataclass
class ProxycurlCompanyResult:
    """Result from Proxycurl company enrichment."""
    
    found: bool
    linkedin_url: str | None = None
    
    # Company info
    name: str | None = None
    universal_name_id: str | None = None
    description: str | None = None
    tagline: str | None = None
    website: str | None = None
    logo_url: str | None = None
    
    # Firmographics
    industry: str | None = None
    company_size: str | None = None  # e.g., "51-200"
    company_size_on_linkedin: int | None = None
    company_type: str | None = None  # e.g., "PRIVATELY_HELD"
    founded_year: int | None = None
    
    # Location
    headquarters_city: str | None = None
    headquarters_state: str | None = None
    headquarters_country: str | None = None
    
    # Social/online presence
    follower_count: int | None = None
    specialities: list[str] = field(default_factory=list)
    
    # Funding (if available)
    funding_data: dict | None = None
    
    # Cost tracking
    credits_used: int = 0
    cost_aud: float = 0.0
    source: str = "proxycurl"
    
    # Raw data for debugging
    raw_response: dict | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/API response."""
        return {
            "found": self.found,
            "linkedin_url": self.linkedin_url,
            "name": self.name,
            "universal_name_id": self.universal_name_id,
            "description": self.description,
            "tagline": self.tagline,
            "website": self.website,
            "logo_url": self.logo_url,
            "industry": self.industry,
            "company_size": self.company_size,
            "company_size_on_linkedin": self.company_size_on_linkedin,
            "company_type": self.company_type,
            "founded_year": self.founded_year,
            "headquarters_city": self.headquarters_city,
            "headquarters_state": self.headquarters_state,
            "headquarters_country": self.headquarters_country,
            "follower_count": self.follower_count,
            "specialities": self.specialities[:10] if self.specialities else [],
            "funding_data": self.funding_data,
            "credits_used": self.credits_used,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


# ============================================
# CUSTOM EXCEPTIONS
# ============================================


class ProxycurlError(IntegrationError):
    """Proxycurl-specific integration error."""
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(service="proxycurl", message=message, details=details)


class ProxycurlRateLimitError(ProxycurlError):
    """Proxycurl rate limit exceeded."""
    
    def __init__(
        self,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message="Proxycurl rate limit exceeded", details=details)
        self.retry_after = retry_after


class ProxycurlCreditExhaustedError(ProxycurlError):
    """Proxycurl credits exhausted."""
    
    def __init__(self, details: dict[str, Any] | None = None):
        super().__init__(
            message="Proxycurl credits exhausted - plan limit reached",
            details=details,
        )


class ProxycurlProfileNotFoundError(ProxycurlError):
    """LinkedIn profile not found."""
    
    def __init__(self, linkedin_url: str, details: dict[str, Any] | None = None):
        details = details or {}
        details["linkedin_url"] = linkedin_url
        super().__init__(
            message=f"LinkedIn profile not found: {linkedin_url}",
            details=details,
        )


# ============================================
# MAIN CLIENT CLASS
# ============================================


class ProxycurlClient:
    """
    Proxycurl API client for LinkedIn enrichment.
    
    Tier 4 of Siege Waterfall - ~$0.015 AUD/credit.
    Used for LinkedIn profile and company enrichment.
    
    Primary use: Get detailed LinkedIn profile data for lead qualification.
    Secondary: Company enrichment for firmographic targeting.
    
    Usage:
        async with ProxycurlClient() as client:
            # Profile enrichment
            profile = await client.enrich_profile("https://linkedin.com/in/johndoe")
            print(f"Name: {profile.full_name}")
            print(f"Company: {profile.current_company}")
            
            # Company enrichment
            company = await client.enrich_company("https://linkedin.com/company/acme")
            print(f"Industry: {company.industry}")
            print(f"Size: {company.company_size}")
    
    Attributes:
        api_key: Proxycurl API key
        cost_tracking_enabled: Whether to track costs (default True)
        total_cost_aud: Running total of API costs this session
        total_credits_used: Running total of credits used this session
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        cost_tracking_enabled: bool = True,
    ):
        """
        Initialize Proxycurl client.
        
        Args:
            api_key: Proxycurl API key (falls back to settings.proxycurl_api_key)
            cost_tracking_enabled: Track API costs in session
            
        Raises:
            IntegrationError: If no API key provided or found in settings
        """
        self.api_key = api_key or getattr(settings, "proxycurl_api_key", "")
        
        if not self.api_key:
            raise IntegrationError(
                service="proxycurl",
                message="Proxycurl API key is required. Set PROXYCURL_API_KEY in environment.",
            )
        
        self.cost_tracking_enabled = cost_tracking_enabled
        self.total_cost_aud: float = 0.0
        self.total_credits_used: int = 0
        self._client: httpx.AsyncClient | None = None
        self._request_count: int = 0
        self._last_request_time: datetime | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                },
                timeout=DEFAULT_TIMEOUT,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self) -> "ProxycurlClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def _rate_limit_delay(self) -> None:
        """Apply rate limiting delay between requests."""
        if self._last_request_time:
            elapsed = (
                datetime.now(timezone.utc) - self._last_request_time
            ).total_seconds()
            if elapsed < REQUEST_DELAY_SECONDS:
                await asyncio.sleep(REQUEST_DELAY_SECONDS - elapsed)
        
        self._last_request_time = datetime.now(timezone.utc)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """
        Make authenticated API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response as dictionary
            
        Raises:
            ProxycurlRateLimitError: Rate limit exceeded
            ProxycurlCreditExhaustedError: Credits exhausted
            APIError: Other API errors
        """
        await self._rate_limit_delay()
        
        client = await self._get_client()
        self._request_count += 1
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
            )
            
            # Handle specific status codes
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else 60
                raise ProxycurlRateLimitError(retry_after=retry_seconds)
            
            if response.status_code == 403:
                # Check if it's credit exhaustion
                try:
                    error_data = response.json()
                    if "credit" in str(error_data).lower():
                        raise ProxycurlCreditExhaustedError(details=error_data)
                except Exception:
                    pass
                raise ProxycurlError(
                    message="Proxycurl access forbidden - check API key",
                    details={"status_code": 403},
                )
            
            if response.status_code == 404:
                # Profile/company not found - not necessarily an error
                return {"_not_found": True}
            
            if response.status_code == 400:
                # Bad request - usually invalid URL
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"raw": response.text}
                raise ValidationError(
                    message=f"Invalid request to Proxycurl: {error_data}",
                )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            sentry_sdk.set_context(
                "proxycurl_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                    "params": params,
                    "status_code": e.response.status_code,
                },
            )
            sentry_sdk.capture_exception(e)
            
            raise APIError(
                service="proxycurl",
                status_code=e.response.status_code,
                response=e.response.text,
                message=f"Proxycurl API error: {e.response.status_code}",
            )
        
        except httpx.RequestError as e:
            sentry_sdk.set_context(
                "proxycurl_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                    "params": params,
                },
            )
            sentry_sdk.capture_exception(e)
            
            raise IntegrationError(
                service="proxycurl",
                message=f"Proxycurl request failed: {str(e)}",
            )
    
    def _normalize_linkedin_url(self, url: str, url_type: str = "profile") -> str:
        """
        Normalize LinkedIn URL to standard format.
        
        Args:
            url: LinkedIn URL (various formats accepted)
            url_type: "profile" or "company"
            
        Returns:
            Normalized LinkedIn URL
            
        Raises:
            ValidationError: If URL is invalid
        """
        if not url:
            raise ValidationError(message="LinkedIn URL is required")
        
        url = url.strip().rstrip("/")
        
        # Handle already full URLs
        if url.startswith("https://"):
            return url
        if url.startswith("http://"):
            return url.replace("http://", "https://")
        
        # Handle linkedin.com without protocol
        if url.startswith("linkedin.com") or url.startswith("www.linkedin.com"):
            return f"https://{url}"
        
        # Handle just the path like "in/johndoe" or "company/acme"
        if url_type == "profile":
            if url.startswith("in/"):
                return f"https://www.linkedin.com/{url}"
            # Assume it's just the profile ID
            return f"https://www.linkedin.com/in/{url}"
        
        if url_type == "company":
            if url.startswith("company/"):
                return f"https://www.linkedin.com/{url}"
            return f"https://www.linkedin.com/company/{url}"
        
        raise ValidationError(
            message=f"Could not normalize LinkedIn URL: {url}"
        )
    
    def _track_cost(self, credits: int) -> float:
        """
        Track API credit usage and cost.
        
        Args:
            credits: Number of credits used
            
        Returns:
            Cost in AUD for this operation
        """
        cost = credits * COST_PER_CREDIT_AUD
        if self.cost_tracking_enabled:
            self.total_credits_used += credits
            self.total_cost_aud += cost
        return cost
    
    async def enrich_profile(
        self,
        linkedin_url: str,
        skills: str = "include",
        use_cache: str = "if-present",
        fallback_to_cache: str = "on-error",
    ) -> ProxycurlProfileResult:
        """
        Enrich a LinkedIn profile with detailed data.
        
        This is the primary enrichment method for Tier 4.
        Costs ~1 credit (~$0.015 AUD) per request.
        
        Args:
            linkedin_url: LinkedIn profile URL
            skills: "include", "exclude", or "inferred"
            use_cache: "if-present", "if-recent", or "never"
            fallback_to_cache: "on-error" or "never"
            
        Returns:
            ProxycurlProfileResult with profile data
            
        Raises:
            ValidationError: If linkedin_url is invalid
            ProxycurlError: If API call fails
        """
        normalized_url = self._normalize_linkedin_url(linkedin_url, "profile")
        
        logger.info(f"[Proxycurl] Enriching profile: {normalized_url}")
        
        try:
            response = await self._request(
                method="GET",
                endpoint="/v2/linkedin",
                params={
                    "linkedin_profile_url": normalized_url,
                    "skills": skills,
                    "use_cache": use_cache,
                    "fallback_to_cache": fallback_to_cache,
                },
            )
            
            # Handle not found
            if response.get("_not_found"):
                logger.info(f"[Proxycurl] Profile not found: {normalized_url}")
                return ProxycurlProfileResult(
                    found=False,
                    linkedin_url=normalized_url,
                    source="proxycurl",
                )
            
            return self._transform_profile_response(response, normalized_url)
            
        except (ProxycurlRateLimitError, ProxycurlCreditExhaustedError):
            raise
        
        except ValidationError:
            raise
        
        except Exception as e:
            logger.warning(f"[Proxycurl] Profile enrichment failed: {normalized_url} - {e}")
            return ProxycurlProfileResult(
                found=False,
                linkedin_url=normalized_url,
                source="proxycurl",
            )
    
    async def enrich_company(
        self,
        linkedin_url: str,
        use_cache: str = "if-present",
        fallback_to_cache: str = "on-error",
    ) -> ProxycurlCompanyResult:
        """
        Enrich a LinkedIn company profile with firmographic data.
        
        Costs ~1 credit (~$0.015 AUD) per request.
        
        Args:
            linkedin_url: LinkedIn company URL
            use_cache: "if-present", "if-recent", or "never"
            fallback_to_cache: "on-error" or "never"
            
        Returns:
            ProxycurlCompanyResult with company data
            
        Raises:
            ValidationError: If linkedin_url is invalid
            ProxycurlError: If API call fails
        """
        normalized_url = self._normalize_linkedin_url(linkedin_url, "company")
        
        logger.info(f"[Proxycurl] Enriching company: {normalized_url}")
        
        try:
            response = await self._request(
                method="GET",
                endpoint="/v2/linkedin/company",
                params={
                    "url": normalized_url,
                    "use_cache": use_cache,
                    "fallback_to_cache": fallback_to_cache,
                },
            )
            
            # Handle not found
            if response.get("_not_found"):
                logger.info(f"[Proxycurl] Company not found: {normalized_url}")
                return ProxycurlCompanyResult(
                    found=False,
                    linkedin_url=normalized_url,
                    source="proxycurl",
                )
            
            return self._transform_company_response(response, normalized_url)
            
        except (ProxycurlRateLimitError, ProxycurlCreditExhaustedError):
            raise
        
        except ValidationError:
            raise
        
        except Exception as e:
            logger.warning(f"[Proxycurl] Company enrichment failed: {normalized_url} - {e}")
            return ProxycurlCompanyResult(
                found=False,
                linkedin_url=normalized_url,
                source="proxycurl",
            )
    
    async def enrich_identity(
        self,
        linkedin_url: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Enrich with profile data - matches SiegeWaterfall interface.
        
        This method provides a consistent interface for the enrichment pipeline.
        
        Args:
            linkedin_url: LinkedIn profile URL (required)
            **kwargs: Additional arguments (ignored for interface compatibility)
            
        Returns:
            Dictionary with enriched profile data
        """
        if not linkedin_url:
            return {
                "found": False,
                "source": "proxycurl",
                "error": "linkedin_url is required for Proxycurl enrichment",
            }
        
        result = await self.enrich_profile(linkedin_url)
        return result.to_dict()
    
    async def batch_enrich_profiles(
        self,
        linkedin_urls: list[str],
        max_concurrent: int = 5,
    ) -> list[ProxycurlProfileResult]:
        """
        Batch profile enrichment for multiple LinkedIn URLs.
        
        Processes profiles with rate limiting and cost tracking.
        
        Args:
            linkedin_urls: List of LinkedIn profile URLs
            max_concurrent: Maximum concurrent requests (default 5)
            
        Returns:
            List of ProxycurlProfileResult for each profile
        """
        if not linkedin_urls:
            return []
        
        logger.info(f"[Proxycurl] Batch profile enrichment for {len(linkedin_urls)} profiles")
        
        results: list[ProxycurlProfileResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_semaphore(url: str) -> ProxycurlProfileResult:
            async with semaphore:
                try:
                    return await self.enrich_profile(url)
                except ProxycurlCreditExhaustedError:
                    raise
                except Exception as e:
                    logger.warning(f"[Proxycurl] Batch item failed: {url} - {e}")
                    return ProxycurlProfileResult(
                        found=False,
                        linkedin_url=url,
                        source="proxycurl",
                    )
        
        try:
            for i, url in enumerate(linkedin_urls):
                result = await enrich_with_semaphore(url)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"[Proxycurl] Batch progress: {i + 1}/{len(linkedin_urls)} "
                        f"(Credits: {self.total_credits_used}, Cost: ${self.total_cost_aud:.2f} AUD)"
                    )
                    
        except ProxycurlCreditExhaustedError:
            logger.error("[Proxycurl] Credits exhausted during batch - stopping")
            raise
        
        successful = sum(1 for r in results if r.found)
        logger.info(
            f"[Proxycurl] Batch complete: {successful}/{len(linkedin_urls)} found "
            f"(Total: {self.total_credits_used} credits, ${self.total_cost_aud:.2f} AUD)"
        )
        
        return results
    
    async def batch_enrich_companies(
        self,
        linkedin_urls: list[str],
        max_concurrent: int = 5,
    ) -> list[ProxycurlCompanyResult]:
        """
        Batch company enrichment for multiple LinkedIn company URLs.
        
        Args:
            linkedin_urls: List of LinkedIn company URLs
            max_concurrent: Maximum concurrent requests (default 5)
            
        Returns:
            List of ProxycurlCompanyResult for each company
        """
        if not linkedin_urls:
            return []
        
        logger.info(f"[Proxycurl] Batch company enrichment for {len(linkedin_urls)} companies")
        
        results: list[ProxycurlCompanyResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_semaphore(url: str) -> ProxycurlCompanyResult:
            async with semaphore:
                try:
                    return await self.enrich_company(url)
                except ProxycurlCreditExhaustedError:
                    raise
                except Exception as e:
                    logger.warning(f"[Proxycurl] Batch item failed: {url} - {e}")
                    return ProxycurlCompanyResult(
                        found=False,
                        linkedin_url=url,
                        source="proxycurl",
                    )
        
        try:
            for i, url in enumerate(linkedin_urls):
                result = await enrich_with_semaphore(url)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"[Proxycurl] Batch progress: {i + 1}/{len(linkedin_urls)} "
                        f"(Credits: {self.total_credits_used}, Cost: ${self.total_cost_aud:.2f} AUD)"
                    )
                    
        except ProxycurlCreditExhaustedError:
            logger.error("[Proxycurl] Credits exhausted during batch - stopping")
            raise
        
        successful = sum(1 for r in results if r.found)
        logger.info(
            f"[Proxycurl] Batch complete: {successful}/{len(linkedin_urls)} found "
            f"(Total: {self.total_credits_used} credits, ${self.total_cost_aud:.2f} AUD)"
        )
        
        return results
    
    def _transform_profile_response(
        self,
        response: dict,
        linkedin_url: str,
    ) -> ProxycurlProfileResult:
        """
        Transform Proxycurl profile API response to standardized result.
        
        Args:
            response: Raw Proxycurl API response
            linkedin_url: Original LinkedIn URL requested
            
        Returns:
            ProxycurlProfileResult with normalized data
        """
        if not response:
            return ProxycurlProfileResult(
                found=False,
                linkedin_url=linkedin_url,
                source="proxycurl",
            )
        
        # Extract current position from experiences
        current_company = None
        current_company_linkedin_url = None
        current_title = None
        
        experiences = response.get("experiences") or []
        for exp in experiences:
            # Find current position (no end date or ends_at is None)
            if exp.get("ends_at") is None:
                current_company = exp.get("company")
                current_company_linkedin_url = exp.get("company_linkedin_profile_url")
                current_title = exp.get("title")
                break
        
        # Extract skills
        skills = []
        skill_list = response.get("skills") or []
        for skill in skill_list:
            if isinstance(skill, str):
                skills.append(skill)
            elif isinstance(skill, dict) and skill.get("name"):
                skills.append(skill["name"])
        
        # Extract languages
        languages = []
        lang_list = response.get("languages") or []
        for lang in lang_list:
            if isinstance(lang, str):
                languages.append(lang)
            elif isinstance(lang, dict) and lang.get("name"):
                languages.append(lang["name"])
        
        # Extract phone numbers
        phone_numbers = []
        personal_numbers = response.get("personal_numbers") or []
        for phone in personal_numbers:
            if phone:
                phone_numbers.append(phone)
        
        # Track cost
        credits = CREDITS_PROFILE_ENRICHMENT
        cost = self._track_cost(credits)
        
        return ProxycurlProfileResult(
            found=True,
            linkedin_url=response.get("public_identifier") 
                and f"https://www.linkedin.com/in/{response.get('public_identifier')}"
                or linkedin_url,
            full_name=response.get("full_name"),
            first_name=response.get("first_name"),
            last_name=response.get("last_name"),
            headline=response.get("headline"),
            summary=response.get("summary"),
            profile_picture_url=response.get("profile_pic_url"),
            occupation=response.get("occupation"),
            current_company=current_company,
            current_company_linkedin_url=current_company_linkedin_url,
            current_title=current_title,
            email=response.get("personal_emails", [None])[0] if response.get("personal_emails") else None,
            phone_numbers=phone_numbers,
            city=response.get("city"),
            state=response.get("state"),
            country=response.get("country"),
            country_full_name=response.get("country_full_name"),
            industry=response.get("industry"),
            connections=response.get("connections"),
            follower_count=response.get("follower_count"),
            experience_count=len(experiences),
            education_count=len(response.get("education") or []),
            languages=languages,
            skills=skills,
            credits_used=credits,
            cost_aud=cost,
            source="proxycurl",
            raw_response=response if logger.isEnabledFor(logging.DEBUG) else None,
        )
    
    def _transform_company_response(
        self,
        response: dict,
        linkedin_url: str,
    ) -> ProxycurlCompanyResult:
        """
        Transform Proxycurl company API response to standardized result.
        
        Args:
            response: Raw Proxycurl API response
            linkedin_url: Original LinkedIn URL requested
            
        Returns:
            ProxycurlCompanyResult with normalized data
        """
        if not response:
            return ProxycurlCompanyResult(
                found=False,
                linkedin_url=linkedin_url,
                source="proxycurl",
            )
        
        # Extract headquarters location
        hq = response.get("hq") or {}
        hq_city = hq.get("city")
        hq_state = hq.get("state")
        hq_country = hq.get("country")
        
        # If no HQ, try locations array
        if not hq_city:
            locations = response.get("locations") or []
            if locations:
                first_loc = locations[0]
                hq_city = first_loc.get("city")
                hq_state = first_loc.get("state")
                hq_country = first_loc.get("country")
        
        # Extract specialities
        specialities = response.get("specialities") or []
        
        # Extract funding data if available
        funding_data = None
        if response.get("funding_data"):
            funding_data = response["funding_data"]
        
        # Map company size
        company_size = None
        size_range = response.get("company_size")
        if size_range:
            # Proxycurl returns ranges like [11, 50]
            if isinstance(size_range, list) and len(size_range) == 2:
                company_size = f"{size_range[0]}-{size_range[1]}"
            else:
                company_size = str(size_range)
        
        # Track cost
        credits = CREDITS_COMPANY_ENRICHMENT
        cost = self._track_cost(credits)
        
        return ProxycurlCompanyResult(
            found=True,
            linkedin_url=response.get("linkedin_internal_id")
                and f"https://www.linkedin.com/company/{response.get('universal_name_id')}"
                or linkedin_url,
            name=response.get("name"),
            universal_name_id=response.get("universal_name_id"),
            description=response.get("description"),
            tagline=response.get("tagline"),
            website=response.get("website"),
            logo_url=response.get("profile_pic_url"),
            industry=response.get("industry"),
            company_size=company_size,
            company_size_on_linkedin=response.get("company_size_on_linkedin"),
            company_type=response.get("company_type"),
            founded_year=response.get("founded_year"),
            headquarters_city=hq_city,
            headquarters_state=hq_state,
            headquarters_country=hq_country,
            follower_count=response.get("follower_count"),
            specialities=specialities,
            funding_data=funding_data,
            credits_used=credits,
            cost_aud=cost,
            source="proxycurl",
            raw_response=response if logger.isEnabledFor(logging.DEBUG) else None,
        )
    
    def get_session_cost(self) -> float:
        """
        Get total cost incurred this session in $AUD.
        
        Returns:
            Total cost in AUD
        """
        return self.total_cost_aud
    
    def get_session_credits(self) -> int:
        """
        Get total credits used this session.
        
        Returns:
            Total credits used
        """
        return self.total_credits_used
    
    def reset_cost_tracking(self) -> None:
        """Reset session cost and credit tracking to zero."""
        self.total_cost_aud = 0.0
        self.total_credits_used = 0


# ============================================
# SINGLETON ACCESSOR
# ============================================

_proxycurl_client: ProxycurlClient | None = None


def get_proxycurl_client() -> ProxycurlClient:
    """
    Get or create ProxycurlClient singleton instance.
    
    Returns:
        ProxycurlClient instance
        
    Raises:
        IntegrationError: If PROXYCURL_API_KEY not configured
    """
    global _proxycurl_client
    if _proxycurl_client is None:
        _proxycurl_client = ProxycurlClient()
    return _proxycurl_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (uses settings.proxycurl_api_key)
# [x] Retry logic with tenacity
# [x] Type hints on all methods
# [x] Docstrings on all methods
# [x] Custom exceptions (ProxycurlError, ProxycurlRateLimitError, etc.)
# [x] Cost tracking in $AUD (LAW II compliance) - ~$0.015 per credit
# [x] Rate limiting safety buffer
# [x] enrich_profile() for LinkedIn profiles
# [x] enrich_company() for LinkedIn companies
# [x] enrich_identity() matches SiegeWaterfall interface
# [x] batch_enrich_profiles() for bulk processing
# [x] batch_enrich_companies() for bulk company processing
# [x] Sentry error capture
# [x] Singleton accessor pattern (get_proxycurl_client)
# [x] Async context manager support
# [x] Graceful degradation on failures
# [x] URL normalization for various LinkedIn URL formats
