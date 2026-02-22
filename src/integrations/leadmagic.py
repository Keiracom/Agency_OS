#!/usr/bin/env python3
"""
Leadmagic Integration — Replaces Hunter (T3) + Kaspr (T5)
CEO Directive: Hunter/Kaspr deprecated, Leadmagic is canonical source

Endpoints:
- Email finder: POST https://api.leadmagic.io/email-finder
- Mobile finder: POST https://api.leadmagic.io/mobile-finder
- Credits: GET https://api.leadmagic.io/credits

Costs (AUD):
- Email: $0.015 AUD/record
- Mobile: $0.077 AUD/record

NOTE: API key present but plan unpurchased — do not call until credits available
"""
import os
import asyncio
import aiohttp
import structlog
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import time

logger = structlog.get_logger()

# Cost constants in AUD
COST_EMAIL_FINDER_AUD = 0.015
COST_MOBILE_FINDER_AUD = 0.077

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 60
REQUEST_INTERVAL_SECONDS = 1.0


@dataclass
class EmailFinderResult:
    """Result from email finder endpoint."""
    email: Optional[str]
    confidence: Optional[float]
    status: str  # found, not_found, error
    domain: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    cost_aud: float = COST_EMAIL_FINDER_AUD
    raw_response: Optional[Dict] = None


@dataclass
class MobileFinderResult:
    """Result from mobile finder endpoint."""
    mobile: Optional[str]
    status: str  # found, not_found, error
    linkedin_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    cost_aud: float = COST_MOBILE_FINDER_AUD
    raw_response: Optional[Dict] = None


@dataclass
class CreditBalance:
    """Credit balance from Leadmagic."""
    email_credits: int
    mobile_credits: int
    total_credits: int
    status: str


class LeadmagicClient:
    """
    Client for Leadmagic API — Canonical source for email and mobile enrichment.
    
    Replaces:
    - Hunter.io (T3 email verification)
    - Kaspr (T5 mobile enrichment)
    
    WARNING: API key present but plan unpurchased — do not call until credits available.
    """
    
    BASE_URL = "https://api.leadmagic.io"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Leadmagic client.
        
        Args:
            api_key: Leadmagic API key. Defaults to LEADMAGIC_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("LEADMAGIC_API_KEY")
        if not self.api_key:
            raise ValueError("LEADMAGIC_API_KEY environment variable is required")
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time: float = 0
        self._total_cost_aud: float = 0.0
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def _rate_limit(self):
        """Implement rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < REQUEST_INTERVAL_SECONDS:
            await asyncio.sleep(REQUEST_INTERVAL_SECONDS - elapsed)
        self._last_request_time = time.time()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            data: Request body data (for POST)
            max_retries: Maximum retry attempts
            
        Returns:
            Response JSON data
            
        Raises:
            ValueError: For authentication or validation errors
            RuntimeError: For server errors after retries
        """
        await self._ensure_session()
        await self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers()
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    async with self.session.get(url, headers=headers) as response:
                        return await self._handle_response(response)
                elif method == "POST":
                    async with self.session.post(url, headers=headers, json=data) as response:
                        return await self._handle_response(response)
                        
            except aiohttp.ClientError as e:
                logger.warning(
                    "leadmagic_request_failed",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise RuntimeError(f"Request failed after {max_retries} attempts: {e}")
        
        raise RuntimeError(f"Request failed after {max_retries} attempts")
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response."""
        if response.status == 200:
            return await response.json()
        elif response.status == 401:
            raise ValueError("Invalid Leadmagic API key")
        elif response.status == 402:
            raise ValueError("Insufficient credits — purchase plan before making API calls")
        elif response.status == 429:
            raise ValueError("Rate limit exceeded — slow down requests")
        elif response.status == 400:
            error_data = await response.json()
            raise ValueError(f"Bad request: {error_data.get('message', 'Unknown error')}")
        else:
            response_text = await response.text()
            raise RuntimeError(f"API error {response.status}: {response_text}")
    
    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str
    ) -> EmailFinderResult:
        """
        Find email address for a person at a company.
        Replaces Hunter.io T3 functionality.
        
        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain (e.g., "company.com")
            
        Returns:
            EmailFinderResult with email and confidence score
            
        Cost: $0.015 AUD per successful lookup
        """
        logger.info(
            "leadmagic_email_finder",
            first_name=first_name,
            last_name=last_name,
            domain=domain,
            cost_aud=COST_EMAIL_FINDER_AUD
        )
        
        try:
            data = {
                "first_name": first_name,
                "last_name": last_name,
                "domain": domain
            }
            
            response = await self._make_request("POST", "email-finder", data)
            
            # Log cost
            self._total_cost_aud += COST_EMAIL_FINDER_AUD
            logger.info(
                "leadmagic_email_finder_success",
                domain=domain,
                cost_aud=COST_EMAIL_FINDER_AUD,
                total_session_cost_aud=self._total_cost_aud
            )
            
            return EmailFinderResult(
                email=response.get("email"),
                confidence=response.get("confidence"),
                status="found" if response.get("email") else "not_found",
                domain=domain,
                first_name=first_name,
                last_name=last_name,
                cost_aud=COST_EMAIL_FINDER_AUD,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(
                "leadmagic_email_finder_error",
                domain=domain,
                error=str(e)
            )
            return EmailFinderResult(
                email=None,
                confidence=None,
                status="error",
                domain=domain,
                first_name=first_name,
                last_name=last_name,
                cost_aud=0.0,  # No charge on error
                raw_response={"error": str(e)}
            )
    
    async def find_mobile(self, linkedin_url: str) -> MobileFinderResult:
        """
        Find mobile number from LinkedIn profile.
        Replaces Kaspr T5 functionality.
        
        Args:
            linkedin_url: Full LinkedIn profile URL
            
        Returns:
            MobileFinderResult with mobile number
            
        Cost: $0.077 AUD per successful lookup
        """
        logger.info(
            "leadmagic_mobile_finder",
            linkedin_url=linkedin_url,
            cost_aud=COST_MOBILE_FINDER_AUD
        )
        
        try:
            data = {
                "linkedin_url": linkedin_url
            }
            
            response = await self._make_request("POST", "mobile-finder", data)
            
            # Log cost
            self._total_cost_aud += COST_MOBILE_FINDER_AUD
            logger.info(
                "leadmagic_mobile_finder_success",
                linkedin_url=linkedin_url,
                cost_aud=COST_MOBILE_FINDER_AUD,
                total_session_cost_aud=self._total_cost_aud
            )
            
            return MobileFinderResult(
                mobile=response.get("mobile") or response.get("phone"),
                status="found" if response.get("mobile") or response.get("phone") else "not_found",
                linkedin_url=linkedin_url,
                first_name=response.get("first_name"),
                last_name=response.get("last_name"),
                company=response.get("company"),
                cost_aud=COST_MOBILE_FINDER_AUD,
                raw_response=response
            )
            
        except Exception as e:
            logger.error(
                "leadmagic_mobile_finder_error",
                linkedin_url=linkedin_url,
                error=str(e)
            )
            return MobileFinderResult(
                mobile=None,
                status="error",
                linkedin_url=linkedin_url,
                cost_aud=0.0,  # No charge on error
                raw_response={"error": str(e)}
            )
    
    async def get_credits(self) -> CreditBalance:
        """
        Check remaining credit balance.
        
        Returns:
            CreditBalance with remaining credits
        """
        logger.info("leadmagic_credit_check")
        
        try:
            response = await self._make_request("GET", "credits")
            
            return CreditBalance(
                email_credits=response.get("email_credits", 0),
                mobile_credits=response.get("mobile_credits", 0),
                total_credits=response.get("total_credits", 0),
                status="ok"
            )
            
        except Exception as e:
            logger.error("leadmagic_credit_check_error", error=str(e))
            return CreditBalance(
                email_credits=0,
                mobile_credits=0,
                total_credits=0,
                status=f"error: {str(e)}"
            )
    
    @property
    def total_session_cost_aud(self) -> float:
        """Get total cost incurred this session in AUD."""
        return self._total_cost_aud
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None


# ----- Synchronous wrapper functions for compatibility with existing waterfall -----

def find_email_sync(first_name: str, last_name: str, domain: str) -> EmailFinderResult:
    """
    Synchronous wrapper for find_email.
    For use in non-async contexts (waterfall worker compatibility).
    """
    async def _run():
        async with LeadmagicClient() as client:
            return await client.find_email(first_name, last_name, domain)
    
    return asyncio.run(_run())


def find_mobile_sync(linkedin_url: str) -> MobileFinderResult:
    """
    Synchronous wrapper for find_mobile.
    For use in non-async contexts (waterfall worker compatibility).
    """
    async def _run():
        async with LeadmagicClient() as client:
            return await client.find_mobile(linkedin_url)
    
    return asyncio.run(_run())


def get_credits_sync() -> CreditBalance:
    """
    Synchronous wrapper for get_credits.
    For use in non-async contexts.
    """
    async def _run():
        async with LeadmagicClient() as client:
            return await client.get_credits()
    
    return asyncio.run(_run())


# ----- Legacy interface compatibility (replaces Hunter signatures) -----

async def verify_domain(domain: str) -> Optional[Dict]:
    """
    DEPRECATED: Use find_email() directly.
    Legacy interface for Hunter.io compatibility.
    
    Note: Leadmagic requires name + domain, not just domain.
    This stub exists for import compatibility only.
    """
    logger.warning(
        "leadmagic_legacy_verify_domain_called",
        domain=domain,
        message="verify_domain is deprecated. Use find_email(first_name, last_name, domain) instead."
    )
    return {
        "domain": domain,
        "status": "deprecated",
        "message": "Use find_email(first_name, last_name, domain) instead of verify_domain"
    }


async def find_emails(domain: str, limit: int = 10) -> list:
    """
    DEPRECATED: Use find_email() directly.
    Legacy interface for Hunter.io compatibility.
    
    Note: Leadmagic requires name + domain, not just domain.
    This stub exists for import compatibility only.
    """
    logger.warning(
        "leadmagic_legacy_find_emails_called",
        domain=domain,
        message="find_emails is deprecated. Use find_email(first_name, last_name, domain) instead."
    )
    return []


async def verify_email(email: str) -> Optional[Dict]:
    """
    DEPRECATED: Use find_email() directly.
    Legacy interface for Hunter.io compatibility.
    
    Note: Leadmagic email finder creates verified emails.
    This stub exists for import compatibility only.
    """
    logger.warning(
        "leadmagic_legacy_verify_email_called",
        email=email,
        message="verify_email is deprecated. Leadmagic email finder returns verified emails."
    )
    return {
        "email": email,
        "status": "deprecated",
        "message": "Leadmagic email finder returns pre-verified emails"
    }


# ----- CLI for testing -----

async def main():
    """Command line interface for testing Leadmagic integration."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Leadmagic API Client")
    parser.add_argument("--email", action="store_true", help="Find email")
    parser.add_argument("--mobile", action="store_true", help="Find mobile")
    parser.add_argument("--credits", action="store_true", help="Check credits")
    parser.add_argument("--first-name", help="First name (for email)")
    parser.add_argument("--last-name", help="Last name (for email)")
    parser.add_argument("--domain", help="Domain (for email)")
    parser.add_argument("--linkedin-url", help="LinkedIn URL (for mobile)")
    
    args = parser.parse_args()
    
    async with LeadmagicClient() as client:
        if args.credits:
            result = await client.get_credits()
            print(f"Credits: {result}")
            
        elif args.email:
            if not all([args.first_name, args.last_name, args.domain]):
                print("Error: --email requires --first-name, --last-name, and --domain")
                return
            result = await client.find_email(args.first_name, args.last_name, args.domain)
            print(f"Email Result: {result}")
            print(f"Cost: ${result.cost_aud:.3f} AUD")
            
        elif args.mobile:
            if not args.linkedin_url:
                print("Error: --mobile requires --linkedin-url")
                return
            result = await client.find_mobile(args.linkedin_url)
            print(f"Mobile Result: {result}")
            print(f"Cost: ${result.cost_aud:.3f} AUD")
            
        else:
            print("Leadmagic Integration — Replaces Hunter (T3) + Kaspr (T5)")
            print("\nCosts (AUD):")
            print(f"  - Email finder: ${COST_EMAIL_FINDER_AUD:.3f}/record")
            print(f"  - Mobile finder: ${COST_MOBILE_FINDER_AUD:.3f}/record")
            print("\n⚠️  WARNING: API key present but plan unpurchased")
            print("    Do not call until credits available")
            
            # Check credits
            credits = await client.get_credits()
            print(f"\nCredit Balance: {credits}")


if __name__ == "__main__":
    asyncio.run(main())
