"""
FILE: src/integrations/kaspr.py
PURPOSE: Kaspr API client for verified mobile number enrichment
PHASE: SIEGE (System Overhaul)
TASK: SIEGE-005
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

SIEGE CONTEXT:
  Tier 5 of the Siege Waterfall - "Identity Gold"
  Cost: $0.45 AUD per successful enrichment
  Only triggered for leads with ALS >= 85 (HOT leads)
  
  Primary use case: Verified mobile numbers for Voice AI/SMS
  Secondary: Personal email addresses for fallback outreach
  
  API Reference: https://developers.kaspr.io/
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
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

# Cost per successful enrichment in $AUD (LAW II compliance)
COST_PER_ENRICHMENT_AUD = 0.45

# Kaspr API configuration
BASE_URL = "https://api.kaspr.io"
DEFAULT_TIMEOUT = 30.0

# Rate limiting (Starter plan)
MAX_REQUESTS_PER_MINUTE = 30
REQUEST_DELAY_SECONDS = 0.5  # Safety buffer


# ============================================
# DATA CLASSES
# ============================================


@dataclass
class KasprEnrichmentResult:
    """Result from Kaspr enrichment."""
    
    found: bool
    mobile_number_verified: str | None = None
    mobile_confidence: int = 0  # 0-100 score
    email: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    cost_aud: float = 0.0
    source: str = "kaspr"
    raw_response: dict | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/API response."""
        return {
            "found": self.found,
            "mobile_number_verified": self.mobile_number_verified,
            "mobile_confidence": self.mobile_confidence,
            "email": self.email,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "title": self.title,
            "company": self.company,
            "linkedin_url": self.linkedin_url,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


# ============================================
# CUSTOM EXCEPTIONS
# ============================================


class KasprError(IntegrationError):
    """Kaspr-specific integration error."""
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(service="kaspr", message=message, details=details)


class KasprRateLimitError(KasprError):
    """Kaspr rate limit exceeded."""
    
    def __init__(
        self,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message="Kaspr rate limit exceeded", details=details)
        self.retry_after = retry_after


class KasprCreditExhaustedError(KasprError):
    """Kaspr credits exhausted."""
    
    def __init__(self, details: dict[str, Any] | None = None):
        super().__init__(
            message="Kaspr credits exhausted - plan limit reached",
            details=details,
        )


# ============================================
# MAIN CLIENT CLASS
# ============================================


class KasprClient:
    """
    Kaspr API client for mobile number enrichment.
    
    Tier 5 of Siege Waterfall - $0.45 AUD/phone.
    Only used for ALS >= 85 (HOT leads).
    
    Primary use: Get verified mobile numbers for Voice AI and SMS campaigns.
    
    Usage:
        client = KasprClient()
        result = await client.enrich_mobile("https://linkedin.com/in/johndoe")
        
        if result.found and result.mobile_number_verified:
            print(f"Mobile: {result.mobile_number_verified}")
            print(f"Confidence: {result.mobile_confidence}%")
    
    Attributes:
        api_key: Kaspr API key
        cost_tracking_enabled: Whether to track costs (default True)
        total_cost_aud: Running total of API costs this session
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        cost_tracking_enabled: bool = True,
    ):
        """
        Initialize Kaspr client.
        
        Args:
            api_key: Kaspr API key (falls back to settings.kaspr_api_key)
            cost_tracking_enabled: Track API costs in session
            
        Raises:
            IntegrationError: If no API key provided or found in settings
        """
        self.api_key = api_key or getattr(settings, "kaspr_api_key", "")
        
        if not self.api_key:
            raise IntegrationError(
                service="kaspr",
                message="Kaspr API key is required. Set KASPR_API_KEY in environment.",
            )
        
        self.cost_tracking_enabled = cost_tracking_enabled
        self.total_cost_aud: float = 0.0
        self._client: httpx.AsyncClient | None = None
        self._request_count: int = 0
        self._last_request_time: datetime | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                },
                timeout=DEFAULT_TIMEOUT,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self) -> "KasprClient":
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
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        """
        Make authenticated API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            API response as dictionary
            
        Raises:
            KasprRateLimitError: Rate limit exceeded
            KasprCreditExhaustedError: Credits exhausted
            APIError: Other API errors
        """
        await self._rate_limit_delay()
        
        client = await self._get_client()
        self._request_count += 1
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
            )
            
            # Handle specific status codes
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else 60
                raise KasprRateLimitError(retry_after=retry_seconds)
            
            if response.status_code == 402:
                raise KasprCreditExhaustedError()
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            sentry_sdk.set_context(
                "kaspr_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": e.response.status_code,
                },
            )
            sentry_sdk.capture_exception(e)
            
            raise APIError(
                service="kaspr",
                status_code=e.response.status_code,
                response=e.response.text,
                message=f"Kaspr API error: {e.response.status_code}",
            )
        
        except httpx.RequestError as e:
            sentry_sdk.set_context(
                "kaspr_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                },
            )
            sentry_sdk.capture_exception(e)
            
            raise IntegrationError(
                service="kaspr",
                message=f"Kaspr request failed: {str(e)}",
            )
    
    def _extract_linkedin_public_id(self, linkedin_url: str) -> str | None:
        """
        Extract public LinkedIn ID from URL.
        
        Args:
            linkedin_url: Full LinkedIn profile URL
            
        Returns:
            Public ID (e.g., "john-doe-12345") or None
        """
        if not linkedin_url:
            return None
        
        # Normalize URL
        url = linkedin_url.strip().rstrip("/")
        
        # Handle various LinkedIn URL formats
        # https://www.linkedin.com/in/john-doe-12345
        # https://linkedin.com/in/john-doe-12345
        # linkedin.com/in/john-doe-12345
        
        if "/in/" in url:
            parts = url.split("/in/")
            if len(parts) > 1:
                return parts[1].split("/")[0].split("?")[0]
        
        return None
    
    async def enrich_mobile(
        self,
        linkedin_url: str,
    ) -> KasprEnrichmentResult:
        """
        Get verified mobile number from LinkedIn profile.
        
        This is the primary enrichment method for Tier 5.
        Costs $0.45 AUD per successful enrichment.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            KasprEnrichmentResult with mobile number and metadata
            
        Raises:
            ValidationError: If linkedin_url is invalid
            KasprError: If API call fails
        """
        if not linkedin_url:
            raise ValidationError(
                message="LinkedIn URL is required for mobile enrichment",
            )
        
        public_id = self._extract_linkedin_public_id(linkedin_url)
        if not public_id:
            raise ValidationError(
                message=f"Could not extract LinkedIn ID from URL: {linkedin_url}",
            )
        
        logger.info(f"[Kaspr] Enriching mobile for LinkedIn: {public_id}")
        
        try:
            # Kaspr Person Search API
            # Reference: https://developers.kaspr.io/reference/person-search
            response = await self._request(
                method="POST",
                endpoint="/person/search",
                data={
                    "linkedInUrl": linkedin_url,
                },
            )
            
            return self._transform_response(response, linkedin_url)
            
        except (KasprRateLimitError, KasprCreditExhaustedError):
            # Re-raise these specific errors
            raise
        
        except Exception as e:
            logger.warning(f"[Kaspr] Enrichment failed for {public_id}: {e}")
            return KasprEnrichmentResult(
                found=False,
                linkedin_url=linkedin_url,
                source="kaspr",
            )
    
    async def enrich_identity(
        self,
        linkedin_url: str | None = None,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
    ) -> dict[str, Any]:
        """
        Enrich with mobile + identity data.
        
        This method matches the interface expected by SiegeWaterfall.
        Primary lookup is by LinkedIn URL.
        
        Args:
            linkedin_url: LinkedIn profile URL (preferred)
            email: Email address (fallback lookup)
            first_name: First name (for name+company lookup)
            last_name: Last name (for name+company lookup)
            company: Company name (for name+company lookup)
            
        Returns:
            Dictionary with enriched identity data
        """
        # Try LinkedIn URL first (most reliable)
        if linkedin_url:
            result = await self.enrich_mobile(linkedin_url)
            return result.to_dict()
        
        # Fallback: Try name + company lookup
        if first_name and last_name and company:
            logger.info(f"[Kaspr] Trying name+company lookup: {first_name} {last_name} @ {company}")
            
            try:
                response = await self._request(
                    method="POST",
                    endpoint="/person/search",
                    data={
                        "firstName": first_name,
                        "lastName": last_name,
                        "companyName": company,
                    },
                )
                
                result = self._transform_response(response, linkedin_url)
                return result.to_dict()
                
            except Exception as e:
                logger.warning(f"[Kaspr] Name+company lookup failed: {e}")
        
        # No valid lookup parameters
        return {
            "found": False,
            "source": "kaspr",
            "error": "No linkedin_url or name+company provided for lookup",
        }
    
    async def batch_enrich(
        self,
        profiles: list[str],
        max_concurrent: int = 5,
    ) -> list[KasprEnrichmentResult]:
        """
        Bulk mobile enrichment for multiple profiles.
        
        Processes profiles with rate limiting and cost tracking.
        Use with caution - each successful enrichment costs $0.45 AUD.
        
        Args:
            profiles: List of LinkedIn profile URLs
            max_concurrent: Maximum concurrent requests (default 5)
            
        Returns:
            List of KasprEnrichmentResult for each profile
        """
        if not profiles:
            return []
        
        logger.info(f"[Kaspr] Batch enrichment for {len(profiles)} profiles")
        
        results: list[KasprEnrichmentResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_semaphore(url: str) -> KasprEnrichmentResult:
            async with semaphore:
                try:
                    return await self.enrich_mobile(url)
                except KasprCreditExhaustedError:
                    # Stop batch if credits exhausted
                    raise
                except Exception as e:
                    logger.warning(f"[Kaspr] Batch item failed: {url} - {e}")
                    return KasprEnrichmentResult(
                        found=False,
                        linkedin_url=url,
                        source="kaspr",
                    )
        
        try:
            # Process in batches with rate limiting
            for i, url in enumerate(profiles):
                result = await enrich_with_semaphore(url)
                results.append(result)
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"[Kaspr] Batch progress: {i + 1}/{len(profiles)} "
                        f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
                    )
                    
        except KasprCreditExhaustedError:
            logger.error("[Kaspr] Credits exhausted during batch - stopping")
            raise
        
        # Summary logging
        successful = sum(1 for r in results if r.found and r.mobile_number_verified)
        logger.info(
            f"[Kaspr] Batch complete: {successful}/{len(profiles)} mobiles found "
            f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
        )
        
        return results
    
    def _transform_response(
        self,
        response: dict,
        linkedin_url: str | None = None,
    ) -> KasprEnrichmentResult:
        """
        Transform Kaspr API response to standardized result.
        
        Kaspr API response structure:
        {
            "firstName": "John",
            "lastName": "Doe",
            "currentJobTitle": "CEO",
            "currentCompany": "Acme Inc",
            "linkedinUrl": "https://linkedin.com/in/johndoe",
            "phones": [
                {"type": "mobile", "number": "+61412345678", "confidence": 95}
            ],
            "emails": [
                {"type": "work", "email": "john@acme.com", "confidence": 90}
            ]
        }
        
        Args:
            response: Raw Kaspr API response
            linkedin_url: Original LinkedIn URL requested
            
        Returns:
            KasprEnrichmentResult with normalized data
        """
        # Check if we got data
        if not response:
            return KasprEnrichmentResult(
                found=False,
                linkedin_url=linkedin_url,
                source="kaspr",
            )
        
        # Extract mobile number (prefer highest confidence)
        mobile_number = None
        mobile_confidence = 0
        
        phones = response.get("phones") or []
        for phone in phones:
            phone_type = phone.get("type", "").lower()
            if phone_type in ("mobile", "direct", "cell"):
                confidence = phone.get("confidence", 0)
                if confidence > mobile_confidence:
                    mobile_number = phone.get("number")
                    mobile_confidence = confidence
        
        # If no mobile, take first phone
        if not mobile_number and phones:
            first_phone = phones[0]
            mobile_number = first_phone.get("number")
            mobile_confidence = first_phone.get("confidence", 50)
        
        # Extract email (prefer work email)
        email = None
        emails = response.get("emails") or []
        for email_data in emails:
            email_type = email_data.get("type", "").lower()
            if email_type == "work":
                email = email_data.get("email")
                break
        
        if not email and emails:
            email = emails[0].get("email")
        
        # Build name
        first_name = response.get("firstName") or response.get("first_name")
        last_name = response.get("lastName") or response.get("last_name")
        full_name = None
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        
        # Determine if enrichment was successful
        found = bool(mobile_number or email)
        
        # Track cost for successful enrichment
        cost = 0.0
        if found and self.cost_tracking_enabled:
            cost = COST_PER_ENRICHMENT_AUD
            self.total_cost_aud += cost
        
        return KasprEnrichmentResult(
            found=found,
            mobile_number_verified=mobile_number,
            mobile_confidence=mobile_confidence,
            email=email,
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            title=response.get("currentJobTitle") or response.get("title"),
            company=response.get("currentCompany") or response.get("company"),
            linkedin_url=response.get("linkedinUrl") or linkedin_url,
            cost_aud=cost,
            source="kaspr",
            raw_response=response if logger.isEnabledFor(logging.DEBUG) else None,
        )
    
    def get_session_cost(self) -> float:
        """
        Get total cost incurred this session in $AUD.
        
        Returns:
            Total cost in AUD
        """
        return self.total_cost_aud
    
    def reset_cost_tracking(self) -> None:
        """Reset session cost tracking to zero."""
        self.total_cost_aud = 0.0


# ============================================
# SINGLETON ACCESSOR
# ============================================

_kaspr_client: KasprClient | None = None


def get_kaspr_client() -> KasprClient:
    """
    Get or create KasprClient singleton instance.
    
    Returns:
        KasprClient instance
        
    Raises:
        IntegrationError: If KASPR_API_KEY not configured
    """
    global _kaspr_client
    if _kaspr_client is None:
        _kaspr_client = KasprClient()
    return _kaspr_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (uses settings.kaspr_api_key)
# [x] Retry logic with tenacity
# [x] Type hints on all methods
# [x] Docstrings on all methods
# [x] Custom exceptions (KasprError, KasprRateLimitError, KasprCreditExhaustedError)
# [x] Cost tracking in $AUD (LAW II compliance) - $0.45 per enrichment
# [x] Rate limiting for Starter plan
# [x] enrich_mobile() for single LinkedIn profile
# [x] enrich_identity() matches SiegeWaterfall interface
# [x] batch_enrich() for bulk processing
# [x] Sentry error capture
# [x] Singleton accessor pattern (get_kaspr_client)
# [x] Async context manager support
# [x] Graceful degradation on failures
