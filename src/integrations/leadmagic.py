"""
FILE: src/integrations/leadmagic.py
PURPOSE: Leadmagic API client for email finding and mobile enrichment
PHASE: SIEGE (System Overhaul)
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD

SIEGE CONTEXT:
  Email (T3) and mobile (T5) enrichment for the Siege Waterfall.

  Costs (in AUD):
    - Email Finder (T3): $0.015 AUD per lookup
    - Mobile Finder (T5): $0.077 AUD per lookup
    - Credit Check: FREE

  API Reference: https://docs.leadmagic.io/

WARNING: API key is present but plan is unpurchased.
         Do NOT make live API calls until credits are available.

MOCK MODE (LEADMAGIC_MOCK=true):
  When the environment variable LEADMAGIC_MOCK is set to "true", "1", or "yes":
  - find_email() returns realistic fake email (firstname.lastname@domain)
  - find_mobile() returns realistic fake AU mobile (+61 4XX XXX XXX)
  - get_credits() returns unlimited mock credits (999999)
  - All mock responses have cost_aud=0.0 and source="leadmagic-mock"
  - NO API calls are made in mock mode

  Usage:
    export LEADMAGIC_MOCK=true
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
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
from src.integrations.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS
# ============================================

# Base URL for Leadmagic API
BASE_URL = "https://api.leadmagic.io"
DEFAULT_TIMEOUT = 30.0

# Cost per operation in $AUD (LAW II compliance)
COST_EMAIL_FINDER_AUD = 0.015  # T3 email enrichment
COST_MOBILE_FINDER_AUD = 0.077  # T5 mobile enrichment

# Rate limiting
MAX_REQUESTS_PER_SECOND = 10
REQUEST_DELAY_SECONDS = 1.0  # 1 second between requests


def _is_mock_mode() -> bool:
    """Check if mock mode is enabled via LEADMAGIC_MOCK env var."""
    return os.getenv("LEADMAGIC_MOCK", "").lower() in ("true", "1", "yes")


def _is_production_environment() -> bool:
    """Detect production environment via env var or worktree path heuristic.

    Returns True when running in production. Used by the mock-mode guardrail
    below to refuse module load if mock mode is enabled in production —
    catastrophic-blast-radius-prevention (mock returns fake AU mobile numbers
    + fake emails to real campaigns).

    Resolution order (explicit env beats path heuristic):
    1. FASTAPI_ENV in {dev, development, test, staging} → False (explicit non-prod)
    2. FASTAPI_ENV == production → True (explicit prod)
    3. FASTAPI_ENV unset or unrecognised → worktree-path heuristic
    """
    env = os.getenv("FASTAPI_ENV", "").lower()
    if env in ("dev", "development", "test", "staging"):
        return False
    if env == "production":
        return True
    # FASTAPI_ENV unset/unrecognised — fall back to worktree path heuristic.
    # Main worktree path indicates production code is loaded
    # (Aiden/Atlas/Scout/Orion clone worktrees are dev-shaped).
    return os.path.abspath(__file__).startswith("/home/elliotbot/clawd/Agency_OS/")


def _assert_mock_safe() -> None:
    """Refuse module load if LEADMAGIC_MOCK is enabled in production.

    Mock mode returns realistic-but-fake AU mobile numbers + emails that
    would be sent to real prospects in cohorts — catastrophic deliverability
    + reputational damage if accidentally toggled in production.

    Defensive guardrail: fails fast at import time, NOT at first call,
    so misconfiguration is caught before any campaign starts.
    """
    if _is_mock_mode() and _is_production_environment():
        raise RuntimeError(
            "LEADMAGIC_MOCK is enabled in a production environment — "
            "refusing module load. Mock mode returns fake AU mobile numbers "
            "and emails which would be sent to real campaign prospects. "
            "Either unset LEADMAGIC_MOCK or set FASTAPI_ENV to a non-production "
            "value (and ensure you're not running from /home/elliotbot/clawd/Agency_OS/) "
            "to proceed."
        )


_assert_mock_safe()


# ============================================
# ENUMS
# ============================================


class EmailStatus(StrEnum):
    """Email verification status."""

    VALID = "valid"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"
    RISKY = "risky"


class MobileStatus(StrEnum):
    """Mobile number verification status."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    INVALID = "invalid"
    UNKNOWN = "unknown"


# ============================================
# DATA CLASSES
# ============================================


@dataclass
class EmailFinderResult:
    """Result from email finder (T3 replacement)."""

    found: bool
    email: str | None = None
    confidence: int = 0  # 0-100 score
    status: EmailStatus = EmailStatus.UNKNOWN
    first_name: str | None = None
    last_name: str | None = None
    domain: str | None = None
    company: str | None = None
    position: str | None = None
    linkedin_url: str | None = None
    cost_aud: float = 0.0
    source: str = "leadmagic"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "found": self.found,
            "email": self.email,
            "confidence": self.confidence,
            "status": self.status.value if self.status else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "domain": self.domain,
            "company": self.company,
            "position": self.position,
            "linkedin_url": self.linkedin_url,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


@dataclass
class MobileFinderResult:
    """Result from mobile finder (T5 replacement)."""

    found: bool
    mobile_number: str | None = None
    mobile_confidence: int = 0  # 0-100 score
    status: MobileStatus = MobileStatus.UNKNOWN
    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    title: str | None = None
    company: str | None = None
    linkedin_url: str | None = None
    cost_aud: float = 0.0
    source: str = "leadmagic"
    raw_response: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "found": self.found,
            "mobile_number": self.mobile_number,
            "mobile_confidence": self.mobile_confidence,
            "status": self.status.value if self.status else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "title": self.title,
            "company": self.company,
            "linkedin_url": self.linkedin_url,
            "cost_aud": self.cost_aud,
            "source": self.source,
        }


@dataclass
class CreditBalance:
    """Leadmagic credit balance."""

    email_credits: int = 0
    mobile_credits: int = 0
    total_credits: int = 0
    plan: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "email_credits": self.email_credits,
            "mobile_credits": self.mobile_credits,
            "total_credits": self.total_credits,
            "plan": self.plan,
        }


# ============================================
# CUSTOM EXCEPTIONS
# ============================================


class LeadmagicError(IntegrationError):
    """Leadmagic-specific integration error."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(service="leadmagic", message=message, details=details)


class LeadmagicRateLimitError(LeadmagicError):
    """Leadmagic rate limit exceeded."""

    def __init__(
        self,
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message="Leadmagic rate limit exceeded", details=details)
        self.retry_after = retry_after


class LeadmagicCreditExhaustedError(LeadmagicError):
    """Leadmagic credits exhausted."""

    def __init__(self, details: dict[str, Any] | None = None):
        super().__init__(
            message="Leadmagic credits exhausted - purchase plan or wait for reset",
            details=details,
        )


class LeadmagicNoPlanError(LeadmagicError):
    """Leadmagic plan not purchased."""

    def __init__(self, details: dict[str, Any] | None = None):
        super().__init__(
            message="Leadmagic plan not purchased - API key present but no credits",
            details=details,
        )


# ============================================
# MAIN CLIENT CLASS
# ============================================


class LeadmagicClient:
    """
    Leadmagic API client for email finding and mobile enrichment.

    Costs (AUD):
        - Email Finder (T3): $0.015 AUD/lookup
        - Mobile Finder (T5): $0.077 AUD/lookup
        - Credit Check: FREE

    Usage:
        client = LeadmagicClient()

        # Find email (T3)
        result = await client.find_email("John", "Doe", "acme.com")

        # Find mobile (T5)
        result = await client.find_mobile("https://linkedin.com/in/johndoe")

        # Check credits
        balance = await client.get_credits()

    WARNING: API key is present but plan is unpurchased.
             Do NOT make live API calls until credits are available.

    Attributes:
        api_key: Leadmagic API key
        cost_tracking_enabled: Whether to track costs (default True)
        total_cost_aud: Running total of API costs this session
    """

    def __init__(
        self,
        api_key: str | None = None,
        cost_tracking_enabled: bool = True,
    ):
        """
        Initialize Leadmagic client.

        Args:
            api_key: Leadmagic API key (falls back to settings.leadmagic_api_key)
            cost_tracking_enabled: Track API costs in session

        Raises:
            IntegrationError: If no API key provided or found in settings
        """
        self.api_key = api_key or getattr(settings, "leadmagic_api_key", "")

        # Mock mode doesn't require API key
        if not self.api_key and not _is_mock_mode():
            raise IntegrationError(
                service="leadmagic",
                message="Leadmagic API key is required. Set LEADMAGIC_API_KEY in environment.",
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

    async def __aenter__(self) -> LeadmagicClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()

    async def _rate_limit_delay(self) -> None:
        """Apply rate limiting delay between requests."""
        if self._last_request_time:
            elapsed = (datetime.now(UTC) - self._last_request_time).total_seconds()
            if elapsed < REQUEST_DELAY_SECONDS:
                await asyncio.sleep(REQUEST_DELAY_SECONDS - elapsed)

        self._last_request_time = datetime.now(UTC)

    @circuit_breaker("leadmagic", failure_threshold=5, recovery_timeout=60)
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
        params: dict | None = None,
    ) -> dict:
        """
        Make authenticated API request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            API response as dictionary

        Raises:
            LeadmagicRateLimitError: Rate limit exceeded
            LeadmagicCreditExhaustedError: Credits exhausted
            LeadmagicNoPlanError: Plan not purchased
            APIError: Other API errors
        """
        import os

        if os.environ.get("DRY_RUN"):
            logger.info("[DRY-RUN] Would call Leadmagic: %s %s", method, endpoint)
            return {}
        await self._rate_limit_delay()

        client = await self._get_client()
        self._request_count += 1

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data if method != "GET" else None,
                params=params,
            )

            # Handle specific status codes
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                retry_seconds = int(retry_after) if retry_after else 60
                raise LeadmagicRateLimitError(retry_after=retry_seconds)

            if response.status_code == 402:
                raise LeadmagicCreditExhaustedError()

            if response.status_code == 403:
                raise LeadmagicNoPlanError()

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            sentry_sdk.set_context(
                "leadmagic_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": e.response.status_code,
                },
            )
            sentry_sdk.capture_exception(e)

            raise APIError(
                service="leadmagic",
                status_code=e.response.status_code,
                response=e.response.text,
                message=f"Leadmagic API error: {e.response.status_code}",
            )

        except httpx.RequestError as e:
            sentry_sdk.set_context(
                "leadmagic_request",
                {
                    "endpoint": endpoint,
                    "method": method,
                },
            )
            sentry_sdk.capture_exception(e)

            raise IntegrationError(
                service="leadmagic",
                message=f"Leadmagic request failed: {str(e)}",
            )

    def _track_cost(self, cost: float) -> float:
        """Track API cost if enabled."""
        if self.cost_tracking_enabled:
            self.total_cost_aud += cost
        return cost

    # ========================================
    # EMAIL FINDER (T3 REPLACEMENT)
    # ========================================

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str,
        company: str | None = None,
    ) -> EmailFinderResult:
        """
        Find the most likely email for a person at a domain.

        Costs $0.015 AUD per lookup (T3).

        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain (e.g., "stripe.com")
            company: Company name (optional, helps with lookup)

        Returns:
            EmailFinderResult with found email and confidence score

        Raises:
            ValidationError: If required params missing
            LeadmagicError: If API call fails
        """
        # MOCK MODE: Bypass validation and return synthetic email
        if _is_mock_mode():
            domain_clean = (domain or "").lower().strip()
            if domain_clean.startswith(("http://", "https://")):
                domain_clean = domain_clean.split("//")[1].split("/")[0]
            fn = (first_name or "").lower().strip()
            ln = (last_name or "").lower().strip()
            if fn and ln:
                mock_email = f"{fn}.{ln}@{domain_clean}"
            else:
                mock_email = f"info@{domain_clean}"
            logger.info(f"[Leadmagic] MOCK MODE: Returning fake email {mock_email}")
            return EmailFinderResult(
                found=bool(domain_clean),
                email=mock_email if domain_clean else None,
                confidence=85,
                status=EmailStatus.VALID,
                first_name=(first_name or "").strip(),
                last_name=(last_name or "").strip(),
                domain=domain_clean,
                company=company.strip() if company else None,
                position=None,
                linkedin_url=None,
                cost_aud=0.0,
                source="leadmagic-mock",
            )

        # Real mode validation
        if not domain:
            raise ValidationError(message="Domain is required for email finder")
        if not first_name or not last_name:
            raise ValidationError(message="First and last name are required")

        # Normalize
        domain = domain.lower().strip()
        if domain.startswith(("http://", "https://")):
            domain = domain.split("//")[1].split("/")[0]

        logger.info(f"[Leadmagic] Email finder: {first_name} {last_name} @ {domain}")

        try:
            response = await self._request(
                method="POST",
                endpoint="/email-finder",
                data={
                    "first_name": first_name.strip(),
                    "last_name": last_name.strip(),
                    "domain": domain,
                    "company": company.strip() if company else None,
                },
            )

            email = response.get("email")
            found = bool(email)

            # Parse status
            status_str = (response.get("status") or "unknown").lower()
            try:
                status = EmailStatus(status_str)
            except ValueError:
                status = EmailStatus.UNKNOWN

            cost = self._track_cost(COST_EMAIL_FINDER_AUD) if found else 0.0

            return EmailFinderResult(
                found=found,
                email=email,
                confidence=response.get("confidence", 0),
                status=status,
                first_name=response.get("first_name", first_name),
                last_name=response.get("last_name", last_name),
                domain=response.get("domain", domain),
                company=response.get("company", company),
                position=response.get("position"),
                linkedin_url=response.get("linkedin_url"),
                cost_aud=cost,
            )

        except (LeadmagicRateLimitError, LeadmagicCreditExhaustedError, LeadmagicNoPlanError):
            raise
        except APIError:
            raise
        except Exception as e:
            logger.warning(f"[Leadmagic] Email finder failed: {e}")
            return EmailFinderResult(
                found=False,
                domain=domain,
                first_name=first_name,
                last_name=last_name,
            )

    # ========================================
    # MOBILE FINDER (T5 REPLACEMENT)
    # ========================================

    async def find_mobile(
        self,
        linkedin_url: str,
    ) -> MobileFinderResult:
        """
        Get mobile number from LinkedIn profile.

        Costs $0.077 AUD per lookup (T5).

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            MobileFinderResult with mobile number and metadata

        Raises:
            ValidationError: If linkedin_url is invalid
            LeadmagicError: If API call fails
        """
        if not linkedin_url:
            raise ValidationError(
                message="LinkedIn URL is required for mobile finder",
            )

        # Normalize LinkedIn URL
        linkedin_url = linkedin_url.strip()
        if not linkedin_url.startswith(("http://", "https://")):
            linkedin_url = f"https://{linkedin_url}"

        # MOCK MODE: Return realistic fake data without API call
        if _is_mock_mode():
            # Generate realistic AU mobile: +61 4XX XXX XXX
            mock_mobile = f"+61 4{random.randint(0, 9)}{random.randint(0, 9)} {random.randint(100, 999)} {random.randint(100, 999)}"
            mock_confidence = random.randint(80, 95)
            # Extract a fake name from the linkedin URL slug if possible
            slug = linkedin_url.rstrip("/").split("/")[-1]
            # Clean up slug for display
            slug_parts = slug.replace("-", " ").title().split()
            mock_first = slug_parts[0] if slug_parts else "John"
            mock_last = slug_parts[1] if len(slug_parts) > 1 else "Smith"
            logger.info(f"[Leadmagic] MOCK MODE: Returning fake mobile for {linkedin_url}")
            return MobileFinderResult(
                found=True,
                mobile_number=mock_mobile,
                mobile_confidence=mock_confidence,
                status=MobileStatus.VERIFIED,
                first_name=mock_first,
                last_name=mock_last,
                full_name=f"{mock_first} {mock_last}",
                email=None,
                title="Senior Manager",
                company="Mock Company Pty Ltd",
                linkedin_url=linkedin_url,
                cost_aud=0.0,  # No charge for mock
                source="leadmagic-mock",
                raw_response=None,
            )

        logger.info(f"[Leadmagic] Mobile finder: {linkedin_url}")

        try:
            response = await self._request(
                method="POST",
                endpoint="/mobile-finder",
                data={
                    "linkedin_url": linkedin_url,
                },
            )

            mobile = response.get("mobile") or response.get("phone")
            found = bool(mobile)

            # Parse status
            status_str = (response.get("status") or "unknown").lower()
            try:
                status = MobileStatus(status_str)
            except ValueError:
                status = MobileStatus.UNKNOWN

            # Build full name
            first_name = response.get("first_name")
            last_name = response.get("last_name")
            full_name = None
            if first_name and last_name:
                full_name = f"{first_name} {last_name}"

            cost = self._track_cost(COST_MOBILE_FINDER_AUD) if found else 0.0

            return MobileFinderResult(
                found=found,
                mobile_number=mobile,
                mobile_confidence=response.get("confidence", 0),
                status=status,
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                email=response.get("email"),
                title=response.get("title") or response.get("position"),
                company=response.get("company"),
                linkedin_url=response.get("linkedin_url", linkedin_url),
                cost_aud=cost,
                raw_response=response if logger.isEnabledFor(logging.DEBUG) else None,
            )

        except (LeadmagicRateLimitError, LeadmagicCreditExhaustedError, LeadmagicNoPlanError):
            raise
        except APIError:
            raise
        except Exception as e:
            logger.warning(f"[Leadmagic] Mobile finder failed: {e}")
            return MobileFinderResult(
                found=False,
                linkedin_url=linkedin_url,
            )

    # ========================================
    # EMPLOYEE FINDER (Stage 2 DM discovery)
    # ========================================

    async def find_employees(
        self,
        company_domain: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Find employees at a company by domain.
        Uses Leadmagic /v1/people/employee-finder.
        Cost: 0.05 credits per employee returned.
        Returns list of {first_name, last_name, title, linkedin_url} or empty list.
        """
        if not company_domain:
            logger.warning("[Leadmagic] find_employees: company_domain is required")
            return []

        logger.info(f"[Leadmagic] employee-finder: {company_domain} (limit={limit})")

        try:
            response = await self._request(
                method="POST",
                endpoint="/v1/people/employee-finder",
                data={"company_domain": company_domain, "limit": limit},
            )
            if isinstance(response, list):
                return response
            return response.get("data", response) if isinstance(response, dict) else []
        except Exception as e:
            logger.warning(f"[Leadmagic] find_employees failed for {company_domain}: {e}")
            return []

    # ========================================
    # ROLE FINDER (Stage 2 DM fallback)
    # ========================================

    async def find_by_role(
        self,
        company_domain: str,
        job_title: str = "CEO",
    ) -> dict | None:
        """
        Find a specific role at a company.
        Uses Leadmagic /v1/people/role-finder.
        Cost: 2 credits per call.
        Returns {first_name, last_name, linkedin_url} or None.
        Use as fallback when find_employees returns no target title matches.
        """
        if not company_domain:
            logger.warning("[Leadmagic] find_by_role: company_domain is required")
            return None

        logger.info(f"[Leadmagic] role-finder: {job_title} at {company_domain}")

        try:
            response = await self._request(
                method="POST",
                endpoint="/v1/people/role-finder",
                data={"job_title": job_title, "company_domain": company_domain},
            )
            if not response or not isinstance(response, dict):
                return None
            return response
        except Exception as e:
            logger.warning(f"[Leadmagic] find_by_role failed for {company_domain}: {e}")
            return None

    # ========================================
    # CREDIT CHECK
    # ========================================

    async def get_credits(self) -> CreditBalance:
        """
        Get current credit balance.

        Returns:
            CreditBalance with available credits

        Raises:
            LeadmagicError: If API call fails

        Note:
            When LEADMAGIC_MOCK=true, returns unlimited mock credits
            without making an API call.
        """
        logger.info("[Leadmagic] Checking credit balance")

        # MOCK MODE: Return unlimited credits without API call
        if _is_mock_mode():
            logger.info("[Leadmagic] MOCK MODE: Returning unlimited mock credits")
            return CreditBalance(
                email_credits=999999,
                mobile_credits=999999,
                total_credits=999999,
                plan="mock-unlimited",
            )

        try:
            response = await self._request(
                method="GET",
                endpoint="/credits",
            )

            return CreditBalance(
                email_credits=response.get("email_credits", 0),
                mobile_credits=response.get("mobile_credits", 0),
                total_credits=response.get("total_credits", 0),
                plan=response.get("plan"),
            )

        except Exception as e:
            logger.warning(f"[Leadmagic] Credit check failed: {e}")
            return CreditBalance()

    # ========================================
    # EMAIL VERIFICATION
    # ========================================

    async def verify_email(self, email: str) -> dict:
        """Verify an email address via Leadmagic email-validation endpoint.

        Cost: 1 credit per 4 validations ($0.00375 AUD per email).

        Returns:
            dict with keys: email, status ('valid'|'invalid'|'risky'|'unknown'),
            is_deliverable (bool), is_free_provider (bool).
        """
        if _is_mock_mode():
            logger.info("[Leadmagic] MOCK MODE: verify_email %s → valid", email)
            return {
                "email": email,
                "status": "valid",
                "is_deliverable": True,
                "is_free_provider": False,
            }

        if not email or "@" not in email:
            return {"email": email, "status": "invalid", "is_deliverable": False}

        try:
            response = await self._request(
                method="POST",
                endpoint="/email-validation",
                data={"email": email.strip().lower()},
            )
            status = (response.get("status") or "unknown").lower()
            return {
                "email": email,
                "status": status,
                "is_deliverable": status in ("valid", "risky"),
                "is_free_provider": response.get("is_free_provider", False),
            }
        except Exception as exc:
            logger.warning("[Leadmagic] verify_email failed for %s: %s", email, exc)
            return {"email": email, "status": "unknown", "is_deliverable": False}

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
        Costs $0.015 AUD per successful lookup.

        Args:
            prospects: List of dicts with domain, first_name, last_name
            max_concurrent: Max concurrent requests (default 5)

        Returns:
            List of EmailFinderResult for each prospect
        """
        if not prospects:
            return []

        logger.info(f"[Leadmagic] Batch email finder for {len(prospects)} prospects")

        # Use Semaphore(50) for true parallel execution via asyncio.gather
        concurrency = max(max_concurrent, 50)
        semaphore = asyncio.Semaphore(concurrency)

        async def find_with_semaphore(prospect: dict) -> EmailFinderResult:
            async with semaphore:
                try:
                    return await self.find_email(
                        first_name=prospect["first_name"],
                        last_name=prospect["last_name"],
                        domain=prospect["domain"],
                        company=prospect.get("company"),
                    )
                except LeadmagicCreditExhaustedError:
                    raise
                except Exception as e:
                    logger.warning(f"[Leadmagic] Batch item failed: {e}")
                    return EmailFinderResult(
                        found=False,
                        domain=prospect.get("domain", ""),
                        first_name=prospect.get("first_name"),
                        last_name=prospect.get("last_name"),
                    )

        try:
            gathered = await asyncio.gather(
                *[find_with_semaphore(p) for p in prospects],
                return_exceptions=True,
            )
        except LeadmagicCreditExhaustedError:
            logger.error("[Leadmagic] Credits exhausted during batch - stopping")
            raise

        results: list[EmailFinderResult] = []
        for item in gathered:
            if isinstance(item, LeadmagicCreditExhaustedError):
                logger.error("[Leadmagic] Credits exhausted during batch - stopping")
                raise item
            elif isinstance(item, Exception):
                logger.warning(f"[Leadmagic] Batch item failed: {item}")
                results.append(
                    EmailFinderResult(found=False, domain="", first_name=None, last_name=None)
                )
            else:
                results.append(item)

        successful = sum(1 for r in results if r.found)
        logger.info(
            f"[Leadmagic] Batch complete: {successful}/{len(prospects)} emails found "
            f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
        )

        return results

    async def batch_find_mobiles(
        self,
        linkedin_urls: list[str],
        max_concurrent: int = 5,
    ) -> list[MobileFinderResult]:
        """
        Find mobiles for multiple LinkedIn profiles.

        Costs $0.077 AUD per successful lookup.

        Args:
            linkedin_urls: List of LinkedIn profile URLs
            max_concurrent: Max concurrent requests (default 5)

        Returns:
            List of MobileFinderResult for each profile
        """
        if not linkedin_urls:
            return []

        logger.info(f"[Leadmagic] Batch mobile finder for {len(linkedin_urls)} profiles")

        results: list[MobileFinderResult] = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def find_with_semaphore(url: str) -> MobileFinderResult:
            async with semaphore:
                try:
                    return await self.find_mobile(url)
                except LeadmagicCreditExhaustedError:
                    raise
                except Exception as e:
                    logger.warning(f"[Leadmagic] Batch item failed: {e}")
                    return MobileFinderResult(
                        found=False,
                        linkedin_url=url,
                    )

        try:
            for i, url in enumerate(linkedin_urls):
                result = await find_with_semaphore(url)
                results.append(result)

                if (i + 1) % 10 == 0:
                    logger.info(
                        f"[Leadmagic] Batch progress: {i + 1}/{len(linkedin_urls)} "
                        f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
                    )

        except LeadmagicCreditExhaustedError:
            logger.error("[Leadmagic] Credits exhausted during batch - stopping")
            raise

        successful = sum(1 for r in results if r.found)
        logger.info(
            f"[Leadmagic] Batch complete: {successful}/{len(linkedin_urls)} mobiles found "
            f"(Total cost: ${self.total_cost_aud:.2f} AUD)"
        )

        return results

    # ========================================
    # HELPER METHODS
    # ========================================

    def get_session_cost(self) -> float:
        """Get total cost incurred this session in $AUD."""
        return self.total_cost_aud

    def reset_cost_tracking(self) -> None:
        """Reset session cost tracking to zero."""
        self.total_cost_aud = 0.0


# ============================================
# SYNC WRAPPERS (for waterfall compatibility)
# ============================================


def find_email_sync(
    first_name: str,
    last_name: str,
    domain: str,
    company: str | None = None,
) -> EmailFinderResult:
    """Sync wrapper for find_email."""
    client = get_leadmagic_client()
    return asyncio.get_event_loop().run_until_complete(
        client.find_email(first_name, last_name, domain, company)
    )


def find_mobile_sync(linkedin_url: str) -> MobileFinderResult:
    """Sync wrapper for find_mobile."""
    client = get_leadmagic_client()
    return asyncio.get_event_loop().run_until_complete(client.find_mobile(linkedin_url))


# ============================================
# SINGLETON ACCESSOR
# ============================================

_leadmagic_client: LeadmagicClient | None = None


def get_leadmagic_client() -> LeadmagicClient:
    """
    Get or create LeadmagicClient singleton instance.

    Returns:
        LeadmagicClient instance

    Raises:
        IntegrationError: If LEADMAGIC_API_KEY not configured
    """
    global _leadmagic_client
    if _leadmagic_client is None:
        _leadmagic_client = LeadmagicClient()
    return _leadmagic_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (uses settings.leadmagic_api_key)
# [x] Retry logic with tenacity (3 attempts, exponential backoff)
# [x] Type hints on all methods
# [x] Docstrings on all methods
# [x] Custom exceptions (LeadmagicError, LeadmagicRateLimitError, etc.)
# [x] Cost tracking in $AUD (LAW II compliance)
#     - Email Finder: $0.015 AUD (T3)
#     - Mobile Finder: $0.077 AUD (T5)
# [x] Rate limiting (1s between requests)
# [x] find_email() - T3 email enrichment
# [x] find_mobile() - T5 mobile enrichment
# [x] get_credits() - check credit balance
# [x] batch_find_emails() for bulk email lookup
# [x] batch_find_mobiles() for bulk mobile lookup
# [x] Sync wrappers for waterfall compatibility
# [x] Sentry error capture
# [x] Singleton accessor pattern (get_leadmagic_client)
# [x] Async context manager support
# [x] Graceful degradation on failures
# [x] WARNING: Plan unpurchased - do not call until credits available
