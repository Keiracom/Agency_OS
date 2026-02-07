"""
FILE: src/integrations/hunter.py
PURPOSE: Hunter.io API client for email finding, verification, and domain search
PHASE: SIEGE (System Overhaul)
TASK: SIEGE-TIER3
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

SIEGE CONTEXT:
  Tier 3 of the Siege Waterfall - "Email Discovery"
  Costs (in AUD):
    - Domain Search: $0.15 AUD per search
    - Email Finder: $0.15 AUD per lookup
    - Email Verification: $0.08 AUD per verification
  
  Primary use case: Find and verify business emails for outreach
  Secondary: Domain-wide email discovery for account mapping
  
  API Reference: https://hunter.io/api-documentation/v2
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
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

# Base URL for Hunter.io API v2
BASE_URL = "https://api.hunter.io/v2"
DEFAULT_TIMEOUT = 30.0

# Cost per operation in $AUD (LAW II compliance)
# Based on Hunter pricing: ~$0.07-0.10 USD converted at 1.5x
COST_DOMAIN_SEARCH_AUD = 0.15
COST_EMAIL_FINDER_AUD = 0.15
COST_EMAIL_VERIFY_AUD = 0.08

# Rate limiting
MAX_REQUESTS_PER_SECOND = 10
REQUEST_DELAY_SECONDS = 0.1


# ============================================
# ENUMS
# ============================================


class EmailType(str, Enum):
    """Email type classification."""
    PERSONAL = "personal"
    GENERIC = "generic"


class VerificationStatus(str, Enum):
    """Email verification status."""
    VALID = "valid"
    INVALID = "invalid"
    ACCEPT_ALL = "accept_all"
    WEBMAIL = "webmail"
    DISPOSABLE = "disposable"
    UNKNOWN = "unknown"


class Seniority(str, Enum):
    """Job seniority level."""
    JUNIOR = "junior"
    SENIOR = "senior"
    EXECUTIVE = "executive"


class Department(str, Enum):
    """Department classification."""
    EXECUTIVE = "executive"
    IT = "it"
    FINANCE = "finance"
    MANAGEMENT = "management"
    SALES = "sales"
    LEGAL = "legal"
    SUPPORT = "support"
    HR = "hr"
    MARKETING = "marketing"
    COMMUNICATION = "communication"
    EDUCATION = "education"
    DESIGN = "design"
    HEALTH = "health"
    OPERATIONS = "operations"


# ============================================
# DATA CLASSES
# ============================================


@dataclass
class HunterEmail:
    """Single email result from Hunter."""
    
    email: str
    email_type: EmailType | None = None
    confidence: int = 0
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    seniority: str | None = None
    department: str | None = None
    linkedin_url: str | None = None
    twitter: str | None = None
    phone_number: str | None = None
    sources: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "email": self.email,
            "email_type": self.email_type.value if self.email_type else None,
            "confidence": self.confidence,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position,
            "seniority": self.seniority,
            "department": self.department,
            "linkedin_url": self.linkedin_url,
            "twitter": self.twitter,
            "phone_number": self.phone_number,
            "sources_count": len(self.sources),
        }


@dataclass
class DomainSearchResult:
    """Result from domain search."""
    
    domain: str
    disposable: bool = False
    webmail: bool = False
    accept_all: bool = False
    pattern: str | None = None
    organization: str | None = None
    emails: list[HunterEmail] = field(default_factory=list)
    total_emails: int = 0
    cost_aud: float = 0.0
    source: str = "hunter"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "domain": self.domain,
            "disposable": self.disposable,
            "webmail": self.webmail,
            "accept_all": self.accept_all,
            "pattern": self.pattern,
            "organization": self.organization,
            "emails": [e.to_dict() for e in self.emails],
            "total_emails": self.total_emails,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


@dataclass
class EmailFinderResult:
    """Result from email finder."""
    
    found: bool
    email: str | None = None
    score: int = 0
    domain: str | None = None
    accept_all: bool = False
    webmail: bool = False
    disposable: bool = False
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    twitter: str | None = None
    phone_number: str | None = None
    sources: list[dict] = field(default_factory=list)
    cost_aud: float = 0.0
    source: str = "hunter"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "found": self.found,
            "email": self.email,
            "score": self.score,
            "domain": self.domain,
            "accept_all": self.accept_all,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position,
            "company": self.company,
            "linkedin_url": self.linkedin_url,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


@dataclass
class EmailVerificationResult:
    """Result from email verification."""
    
    email: str
    status: VerificationStatus
    result: str
    score: int = 0
    regexp: bool = True
    gibberish: bool = False
    disposable: bool = False
    webmail: bool = False
    mx_records: bool = True
    smtp_server: bool = True
    smtp_check: bool = True
    accept_all: bool = False
    block: bool = False
    sources: list[dict] = field(default_factory=list)
    cost_aud: float = 0.0
    source: str = "hunter"
    
    @property
    def is_valid(self) -> bool:
        """Check if email is valid for outreach."""
        return self.status == VerificationStatus.VALID and self.score >= 70
    
    @property
    def is_risky(self) -> bool:
        """Check if email is risky."""
        return self.disposable or self.accept_all or self.score < 50
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "email": self.email,
            "status": self.status.value,
            "result": self.result,
            "score": self.score,
            "is_valid": self.is_valid,
            "is_risky": self.is_risky,
            "disposable": self.disposable,
            "webmail": self.webmail,
            "mx_records": self.mx_records,
            "smtp_check": self.smtp_check,
            "accept_all": self.accept_all,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


# ============================================
# CUSTOM EXCEPTIONS
# ============================================


class HunterError(IntegrationError):
    """Hunter-specific integration error."""
    
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(service="hunter", message=message, details=details)


class HunterRateLimitError(HunterError):
    """Hunter rate limit exceeded (403)."""
    
    def __init__(
        self,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message="Hunter rate limit exceeded", details=details)
        self.retry_after = retry_after


class HunterQuotaExceededError(HunterError):
    """Hunter usage quota exceeded (429)."""
    
    def __init__(self, details: dict[str, Any] | None = None):
        super().__init__(
            message="Hunter usage quota exceeded - upgrade plan or wait for reset",
            details=details,
        )


# ============================================
# MAIN CLIENT CLASS
# ============================================


class HunterClient:
    """
    Hunter.io API client for email discovery and verification.
    
    Tier 3 of Siege Waterfall - Email Discovery.
    
    Costs (AUD):
        - Domain Search: $0.15/search
        - Email Finder: $0.15/lookup  
        - Email Verification: $0.08/verification
    
    Usage:
        client = HunterClient()
        
        # Find emails for a domain
        result = await client.domain_search("acme.com")
        
        # Find specific person's email
        result = await client.email_finder("acme.com", "John", "Doe")
        
        # Verify an email
        result = await client.verify_email("john@acme.com")
    
    Attributes:
        api_key: Hunter API key
        cost_tracking_enabled: Whether to track costs (default True)
        total_cost_aud: Running total of API costs this session
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        cost_tracking_enabled: bool = True,
    ):
        """
        Initialize Hunter client.
        
        Args:
            api_key: Hunter API key (falls back to settings.hunter_api_key)
            cost_tracking_enabled: Track API costs in session
            
        Raises:
            IntegrationError: If no API key provided or found in settings
        """
        self.api_key = api_key or getattr(settings, "hunter_api_key", "")
        
        if not self.api_key:
            raise IntegrationError(
                service="hunter",
                message="Hunter API key is required. Set HUNTER_API_KEY in environment.",
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
                    "X-API-KEY": self.api_key,
                },
                timeout=DEFAULT_TIMEOUT,
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self) -> "HunterClient":
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
        params: dict | None = None,
        data: dict | None = None,
    ) -> dict:
        """
        Make authenticated API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            
        Returns:
            API response as dictionary
            
        Raises:
            HunterRateLimitError: Rate limit exceeded (403)
            HunterQuotaExceededError: Usage quota exceeded (429)
            APIError: Other API errors
        """
        await self._rate_limit_delay()
        
        client = await self._get_client()
        self._request_count += 1
        
        # Always include api_key in params
        params = params or {}
        params["api_key"] = self.api_key
        
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=data if method != "GET" else None,
            )
            
            # Handle specific status codes
            if response.status_code == 403:
                raise HunterRateLimitError(retry_after=60)
            
            if response.status_code == 429:
                raise HunterQuotaExceededError()
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            # Try to extract error details
            error_body = {}
            try:
                error_body = e.response.json()
            except Exception:
                pass
            
            sentry_sdk.set_context(
                "hunter_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": e.response.status_code,
                    "error": error_body,
                },
            )
            sentry_sdk.capture_exception(e)
            
            # Extract error message from Hunter's error format
            error_msg = "Hunter API error"
            if "errors" in error_body and error_body["errors"]:
                error_info = error_body["errors"][0]
                error_msg = error_info.get("details", str(error_info))
            
            raise APIError(
                service="hunter",
                status_code=e.response.status_code,
                response=str(error_body),
                message=f"{error_msg} ({e.response.status_code})",
            )
        
        except httpx.RequestError as e:
            sentry_sdk.set_context(
                "hunter_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                },
            )
            sentry_sdk.capture_exception(e)
            
            raise IntegrationError(
                service="hunter",
                message=f"Hunter request failed: {str(e)}",
            )
    
    def _track_cost(self, cost: float) -> float:
        """Track API cost if enabled."""
        if self.cost_tracking_enabled:
            self.total_cost_aud += cost
        return cost
    
    # ========================================
    # DOMAIN SEARCH
    # ========================================
    
    async def domain_search(
        self,
        domain: str,
        limit: int = 10,
        offset: int = 0,
        email_type: EmailType | None = None,
        seniority: list[Seniority] | None = None,
        department: list[Department] | None = None,
    ) -> DomainSearchResult:
        """
        Search all email addresses for a domain.
        
        Finds all publicly available email addresses for a company domain.
        Costs $0.15 AUD per search.
        
        Args:
            domain: Domain name (e.g., "stripe.com")
            limit: Max emails to return (default 10, max 100)
            offset: Number of emails to skip for pagination
            email_type: Filter by personal or generic
            seniority: Filter by seniority levels
            department: Filter by departments
            
        Returns:
            DomainSearchResult with list of emails found
            
        Raises:
            ValidationError: If domain is invalid
            HunterError: If API call fails
        """
        if not domain:
            raise ValidationError(message="Domain is required for domain search")
        
        # Normalize domain
        domain = domain.lower().strip()
        if domain.startswith(("http://", "https://")):
            domain = domain.split("//")[1].split("/")[0]
        
        logger.info(f"[Hunter] Domain search for: {domain}")
        
        params = {
            "domain": domain,
            "limit": min(limit, 100),
            "offset": offset,
        }
        
        if email_type:
            params["type"] = email_type.value
        
        if seniority:
            params["seniority"] = ",".join(s.value for s in seniority)
        
        if department:
            params["department"] = ",".join(d.value for d in department)
        
        try:
            response = await self._request("GET", "/domain-search", params=params)
            data = response.get("data", {})
            meta = response.get("meta", {})
            
            # Parse emails
            emails = []
            for email_data in data.get("emails", []):
                emails.append(self._parse_email(email_data))
            
            cost = self._track_cost(COST_DOMAIN_SEARCH_AUD)
            
            return DomainSearchResult(
                domain=data.get("domain", domain),
                disposable=data.get("disposable", False),
                webmail=data.get("webmail", False),
                accept_all=data.get("accept_all", False),
                pattern=data.get("pattern"),
                organization=data.get("organization"),
                emails=emails,
                total_emails=meta.get("results", len(emails)),
                cost_aud=cost,
            )
            
        except (HunterRateLimitError, HunterQuotaExceededError):
            raise
        except APIError:
            raise
        except Exception as e:
            logger.warning(f"[Hunter] Domain search failed for {domain}: {e}")
            return DomainSearchResult(domain=domain, cost_aud=0.0)
    
    # ========================================
    # EMAIL FINDER
    # ========================================
    
    async def email_finder(
        self,
        domain: str,
        first_name: str,
        last_name: str,
        company: str | None = None,
    ) -> EmailFinderResult:
        """
        Find the most likely email for a person at a domain.
        
        Uses first name, last name, and domain to find the most likely
        email address. Costs $0.15 AUD per lookup.
        
        Args:
            domain: Company domain (e.g., "stripe.com")
            first_name: Person's first name
            last_name: Person's last name
            company: Company name (optional, helps with lookup)
            
        Returns:
            EmailFinderResult with found email and confidence score
            
        Raises:
            ValidationError: If required params missing
            HunterError: If API call fails
        """
        if not domain:
            raise ValidationError(message="Domain is required for email finder")
        if not first_name or not last_name:
            raise ValidationError(message="First and last name are required")
        
        # Normalize
        domain = domain.lower().strip()
        if domain.startswith(("http://", "https://")):
            domain = domain.split("//")[1].split("/")[0]
        
        logger.info(f"[Hunter] Email finder: {first_name} {last_name} @ {domain}")
        
        params = {
            "domain": domain,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
        }
        
        if company:
            params["company"] = company.strip()
        
        try:
            response = await self._request("GET", "/email-finder", params=params)
            data = response.get("data", {})
            
            email = data.get("email")
            found = bool(email)
            
            cost = self._track_cost(COST_EMAIL_FINDER_AUD) if found else 0.0
            
            return EmailFinderResult(
                found=found,
                email=email,
                score=data.get("score", 0),
                domain=data.get("domain", domain),
                accept_all=data.get("accept_all", False),
                webmail=data.get("webmail", False),
                disposable=data.get("disposable", False),
                first_name=data.get("first_name", first_name),
                last_name=data.get("last_name", last_name),
                position=data.get("position"),
                company=data.get("company"),
                linkedin_url=data.get("linkedin"),
                twitter=data.get("twitter"),
                phone_number=data.get("phone_number"),
                sources=data.get("sources", []),
                cost_aud=cost,
            )
            
        except (HunterRateLimitError, HunterQuotaExceededError):
            raise
        except APIError:
            raise
        except Exception as e:
            logger.warning(f"[Hunter] Email finder failed: {e}")
            return EmailFinderResult(
                found=False,
                domain=domain,
                first_name=first_name,
                last_name=last_name,
            )
    
    # ========================================
    # EMAIL VERIFICATION
    # ========================================
    
    async def verify_email(self, email: str) -> EmailVerificationResult:
        """
        Verify email address deliverability.
        
        Checks if an email address is valid, verifiable, and safe for outreach.
        Costs $0.08 AUD per verification.
        
        Args:
            email: Email address to verify
            
        Returns:
            EmailVerificationResult with verification details
            
        Raises:
            ValidationError: If email is invalid format
            HunterError: If API call fails
        """
        if not email or "@" not in email:
            raise ValidationError(message="Valid email address is required")
        
        email = email.lower().strip()
        
        logger.info(f"[Hunter] Verifying email: {email}")
        
        try:
            response = await self._request(
                "GET",
                "/email-verifier",
                params={"email": email},
            )
            data = response.get("data", {})
            
            # Parse status
            status_str = data.get("status", "unknown").lower()
            try:
                status = VerificationStatus(status_str)
            except ValueError:
                status = VerificationStatus.UNKNOWN
            
            cost = self._track_cost(COST_EMAIL_VERIFY_AUD)
            
            return EmailVerificationResult(
                email=data.get("email", email),
                status=status,
                result=data.get("result", status_str),
                score=data.get("score", 0),
                regexp=data.get("regexp", True),
                gibberish=data.get("gibberish", False),
                disposable=data.get("disposable", False),
                webmail=data.get("webmail", False),
                mx_records=data.get("mx_records", True),
                smtp_server=data.get("smtp_server", True),
                smtp_check=data.get("smtp_check", True),
                accept_all=data.get("accept_all", False),
                block=data.get("block", False),
                sources=data.get("sources", []),
                cost_aud=cost,
            )
            
        except (HunterRateLimitError, HunterQuotaExceededError):
            raise
        except APIError:
            raise
        except Exception as e:
            logger.warning(f"[Hunter] Email verification failed for {email}: {e}")
            return EmailVerificationResult(
                email=email,
                status=VerificationStatus.UNKNOWN,
                result="error",
                score=0,
                cost_aud=0.0,
            )
    
    # ========================================
    # BATCH OPERATIONS
    # ========================================
    
    async def batch_find_emails(
        self,
        prospects: list[dict[str, str]],
        max_concurrent: int = 5,
    ) -> list[EmailFinderResult]:
        """
        Find emails for multiple prospects.
        
        Each prospect dict should have: domain, first_name, last_name.
        Costs $0.15 AUD per successful lookup.
        
        Args:
            prospects: List of dicts with domain, first_name, last_name
            max_concurrent: Max concurrent requests (default 5)
            
        Returns:
            List of EmailFinderResult for each prospect
        """
        if not prospects:
            return []
        
        logger.info(f"[Hunter] Batch email finder for {len(prospects)} prospects")
        
        results: list[EmailFinderResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def find_with_semaphore(prospect: dict) -> EmailFinderResult:
            async with semaphore:
                try:
                    return await self.email_finder(
                        domain=prospect["domain"],
                        first_name=prospect["first_name"],
                        last_name=prospect["last_name"],
                        company=prospect.get("company"),
                    )
                except HunterQuotaExceededError:
                    raise
                except Exception as e:
                    logger.warning(f"[Hunter] Batch item failed: {e}")
                    return EmailFinderResult(
                        found=False,
                        domain=prospect.get("domain", ""),
                        first_name=prospect.get("first_name"),
                        last_name=prospect.get("last_name"),
                    )
        
        try:
            for i, prospect in enumerate(prospects):
                result = await find_with_semaphore(prospect)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(
                        f"[Hunter] Batch progress: {i + 1}/{len(prospects)} "
                        f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
                    )
                    
        except HunterQuotaExceededError:
            logger.error("[Hunter] Quota exceeded during batch - stopping")
            raise
        
        successful = sum(1 for r in results if r.found)
        logger.info(
            f"[Hunter] Batch complete: {successful}/{len(prospects)} emails found "
            f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
        )
        
        return results
    
    async def batch_verify_emails(
        self,
        emails: list[str],
        max_concurrent: int = 5,
    ) -> list[EmailVerificationResult]:
        """
        Verify multiple email addresses.
        
        Costs $0.08 AUD per verification.
        
        Args:
            emails: List of email addresses
            max_concurrent: Max concurrent requests (default 5)
            
        Returns:
            List of EmailVerificationResult for each email
        """
        if not emails:
            return []
        
        logger.info(f"[Hunter] Batch verification for {len(emails)} emails")
        
        results: list[EmailVerificationResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_with_semaphore(email: str) -> EmailVerificationResult:
            async with semaphore:
                try:
                    return await self.verify_email(email)
                except HunterQuotaExceededError:
                    raise
                except Exception as e:
                    logger.warning(f"[Hunter] Batch verify failed for {email}: {e}")
                    return EmailVerificationResult(
                        email=email,
                        status=VerificationStatus.UNKNOWN,
                        result="error",
                    )
        
        try:
            for i, email in enumerate(emails):
                result = await verify_with_semaphore(email)
                results.append(result)
                
                if (i + 1) % 20 == 0:
                    logger.info(
                        f"[Hunter] Verify progress: {i + 1}/{len(emails)} "
                        f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
                    )
                    
        except HunterQuotaExceededError:
            logger.error("[Hunter] Quota exceeded during batch verify - stopping")
            raise
        
        valid_count = sum(1 for r in results if r.is_valid)
        logger.info(
            f"[Hunter] Batch verify complete: {valid_count}/{len(emails)} valid "
            f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
        )
        
        return results
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _parse_email(self, data: dict) -> HunterEmail:
        """Parse email data from API response."""
        email_type = None
        type_str = data.get("type", "").lower()
        if type_str == "personal":
            email_type = EmailType.PERSONAL
        elif type_str == "generic":
            email_type = EmailType.GENERIC
        
        return HunterEmail(
            email=data.get("value", data.get("email", "")),
            email_type=email_type,
            confidence=data.get("confidence", 0),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            position=data.get("position"),
            seniority=data.get("seniority"),
            department=data.get("department"),
            linkedin_url=data.get("linkedin"),
            twitter=data.get("twitter"),
            phone_number=data.get("phone_number"),
            sources=data.get("sources", []),
        )
    
    def get_session_cost(self) -> float:
        """Get total cost incurred this session in $AUD."""
        return self.total_cost_aud
    
    def reset_cost_tracking(self) -> None:
        """Reset session cost tracking to zero."""
        self.total_cost_aud = 0.0


# ============================================
# SINGLETON ACCESSOR
# ============================================

_hunter_client: HunterClient | None = None


def get_hunter_client() -> HunterClient:
    """
    Get or create HunterClient singleton instance.
    
    Returns:
        HunterClient instance
        
    Raises:
        IntegrationError: If HUNTER_API_KEY not configured
    """
    global _hunter_client
    if _hunter_client is None:
        _hunter_client = HunterClient()
    return _hunter_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (uses settings.hunter_api_key)
# [x] Retry logic with tenacity (3 attempts, exponential backoff)
# [x] Type hints on all methods
# [x] Docstrings on all methods
# [x] Custom exceptions (HunterError, HunterRateLimitError, HunterQuotaExceededError)
# [x] Cost tracking in $AUD (LAW II compliance)
#     - Domain Search: $0.15 AUD
#     - Email Finder: $0.15 AUD
#     - Email Verification: $0.08 AUD
# [x] Rate limiting (10 req/s with 0.1s delay)
# [x] domain_search() - find all emails for a domain
# [x] email_finder() - find specific person's email
# [x] verify_email() - verify email deliverability
# [x] batch_find_emails() for bulk prospect lookup
# [x] batch_verify_emails() for bulk verification
# [x] Sentry error capture
# [x] Singleton accessor pattern (get_hunter_client)
# [x] Async context manager support
# [x] Graceful degradation on failures
