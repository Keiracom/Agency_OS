"""
Contract: src/engines/url_validator.py
Purpose: Validate and normalize URLs before scraping (Tier 0 of Scraper Waterfall)
Layer: 3 - engines
Imports: models only (no integrations needed)
Consumers: icp_scraper.py, orchestration
"""

from __future__ import annotations

import logging
import re
import socket
from urllib.parse import urlparse

import httpx

from src.models.url_validation import URLValidationResult

logger = logging.getLogger(__name__)

# Default timeout for HTTP requests (seconds)
DEFAULT_TIMEOUT = 10.0

# Known parked domain indicators in URLs or redirects
PARKED_DOMAIN_HOSTS = [
    "sedoparking.com",
    "parking.godaddy.com",
    "godaddy.com/parking",
    "dan.com",
    "afternic.com",
    "hugedomains.com",
    "undeveloped.com",
    "sav.com",
    "epik.com",
    "porkbun.com/park",
    "domainnamesales.com",
    "bodis.com",
    "parkingcrew.net",
]

# Content indicators that suggest a parked/for-sale domain
PARKED_CONTENT_INDICATORS = [
    "this domain is for sale",
    "domain for sale",
    "buy this domain",
    "domain is parked",
    "domain parking",
    "this website is for sale",
    "domain name for sale",
    "domain may be for sale",
    "this domain name has been registered",
    "parked free",
    "courtesy of godaddy",
    "related links",  # Common on parked pages
    "get this domain",
    "make an offer",
    "inquire about this domain",
]

# Headers to mimic a real browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class URLValidator:
    """
    Validate and normalize URLs before scraping.

    This is Tier 0 of the Scraper Waterfall architecture.
    It performs the following checks:
    1. Parse and validate URL format
    2. Add https:// if missing
    3. Follow redirects to get canonical URL
    4. Check if domain resolves (DNS lookup)
    5. Detect parked/placeholder domains

    Cost: FREE | Time: <2s | Success: 100% (validation only)
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize URL validator.

        Args:
            timeout: HTTP request timeout in seconds (default: 10s)
        """
        self.timeout = timeout

    async def validate_and_normalize(self, url: str) -> URLValidationResult:
        """
        Validate and normalize a URL before scraping.

        Args:
            url: The URL to validate (with or without protocol)

        Returns:
            URLValidationResult with validation status and details
        """
        # Step 1: Normalize URL format
        normalized_url, error = self._normalize_url(url)
        if error:
            return URLValidationResult(
                valid=False,
                error=error,
                error_type="invalid_format",
                domain=self._extract_domain(url),
            )

        domain = self._extract_domain(normalized_url)

        # Step 2: Check DNS resolution
        dns_resolves = await self._check_dns(domain)
        if not dns_resolves:
            return URLValidationResult(
                valid=False,
                error=f"Domain does not resolve: {domain}",
                error_type="dns_failure",
                domain=domain,
            )

        # Step 3: Follow redirects and check response
        try:
            result = await self._check_url(normalized_url, domain)
            return result
        except Exception as e:
            logger.error(f"URL validation error for {normalized_url}: {e}")
            return URLValidationResult(
                valid=False,
                error=str(e),
                error_type="unknown_error",
                domain=domain,
            )

    def _normalize_url(self, url: str) -> tuple[str, str | None]:
        """
        Normalize URL format - add https:// if missing.

        Returns:
            Tuple of (normalized_url, error_message)
        """
        url = url.strip()

        if not url:
            return "", "URL is empty"

        # Add protocol if missing
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Parse and validate
        try:
            parsed = urlparse(url)

            if not parsed.netloc:
                return "", "Invalid URL format: missing domain"

            # Basic domain format validation
            domain = parsed.netloc.lower()

            # Remove port if present for validation
            domain_without_port = domain.split(":")[0]

            # Check for valid domain pattern
            if not re.match(
                r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$",
                domain_without_port,
            ):
                # Allow IP addresses
                if not self._is_valid_ip(domain_without_port):
                    return "", f"Invalid domain format: {domain}"

            # Reconstruct clean URL
            path = parsed.path or "/"
            clean_url = f"{parsed.scheme}://{parsed.netloc}{path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            return clean_url, None

        except Exception as e:
            return "", f"URL parsing error: {e}"

    def _is_valid_ip(self, ip_str: str) -> bool:
        """Check if string is a valid IP address."""
        try:
            socket.inet_aton(ip_str)
            return True
        except OSError:
            try:
                socket.inet_pton(socket.AF_INET6, ip_str)
                return True
            except OSError:
                return False

    def _extract_domain(self, url: str) -> str | None:
        """Extract domain from URL."""
        try:
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove port if present
            return domain.split(":")[0] if domain else None
        except Exception:
            return None

    async def _check_dns(self, domain: str) -> bool:
        """
        Check if domain resolves via DNS.

        Uses socket.getaddrinfo which is more reliable than gethostbyname.
        """
        if not domain:
            return False

        try:
            # Run DNS lookup in thread pool to avoid blocking
            import asyncio

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: socket.getaddrinfo(domain, None, socket.AF_UNSPEC)
            )
            return True
        except socket.gaierror:
            logger.debug(f"DNS lookup failed for {domain}")
            return False
        except Exception as e:
            logger.warning(f"DNS check error for {domain}: {e}")
            return False

    async def _check_url(self, url: str, domain: str) -> URLValidationResult:
        """
        Check URL accessibility and detect parked domains.

        Follows redirects and checks the final response.
        """
        redirect_chain: list[str] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            verify=True,  # Verify SSL by default
        ) as client:
            try:
                # First try HEAD request (faster)
                response = await client.head(url)

                # Track redirects
                if response.history:
                    redirect_chain = [str(r.url) for r in response.history]

                canonical_url = str(response.url)
                redirected = canonical_url.rstrip("/") != url.rstrip("/")

                # Check if redirected to a known parked domain
                if self._is_parked_redirect(canonical_url, redirect_chain):
                    return URLValidationResult(
                        valid=False,
                        canonical_url=canonical_url,
                        redirected=redirected,
                        redirect_chain=redirect_chain,
                        error="Domain appears to be parked or for sale",
                        error_type="parked_domain",
                        status_code=response.status_code,
                        is_parked=True,
                        domain=domain,
                    )

                # For 4xx/5xx responses, try GET to get content for parked detection
                if response.status_code >= 400:
                    return URLValidationResult(
                        valid=False,
                        canonical_url=canonical_url,
                        redirected=redirected,
                        redirect_chain=redirect_chain,
                        error=f"HTTP error: {response.status_code}",
                        error_type="http_error",
                        status_code=response.status_code,
                        is_parked=False,
                        domain=domain,
                    )

                # Do a GET request to check content for parked indicators
                # Only fetch first 50KB to check for parked page indicators
                get_response = await client.get(
                    url,
                    headers={**DEFAULT_HEADERS, "Range": "bytes=0-51200"},
                )

                content = get_response.text[:50000] if get_response.text else ""
                is_parked = self._is_parked_content(content)

                if is_parked:
                    return URLValidationResult(
                        valid=False,
                        canonical_url=canonical_url,
                        redirected=redirected,
                        redirect_chain=redirect_chain,
                        error="Domain appears to be parked or for sale",
                        error_type="parked_domain",
                        status_code=response.status_code,
                        is_parked=True,
                        domain=domain,
                    )

                # URL is valid
                return URLValidationResult(
                    valid=True,
                    canonical_url=canonical_url,
                    redirected=redirected,
                    redirect_chain=redirect_chain,
                    error=None,
                    error_type=None,
                    status_code=response.status_code,
                    is_parked=False,
                    domain=domain,
                )

            except httpx.ConnectError as e:
                return URLValidationResult(
                    valid=False,
                    error=f"Connection failed: {e}",
                    error_type="connection_error",
                    domain=domain,
                )
            except httpx.TimeoutException:
                return URLValidationResult(
                    valid=False,
                    error=f"Connection timeout after {self.timeout}s",
                    error_type="timeout",
                    domain=domain,
                )
            except httpx.TooManyRedirects:
                return URLValidationResult(
                    valid=False,
                    error="Too many redirects",
                    error_type="redirect_loop",
                    redirect_chain=redirect_chain,
                    domain=domain,
                )
            except httpx.HTTPStatusError as e:
                return URLValidationResult(
                    valid=False,
                    error=f"HTTP error: {e.response.status_code}",
                    error_type="http_error",
                    status_code=e.response.status_code,
                    domain=domain,
                )
            except Exception as e:
                # Try without SSL verification as fallback
                try:
                    return await self._check_url_no_ssl(url, domain)
                except Exception:
                    return URLValidationResult(
                        valid=False,
                        error=f"SSL/Connection error: {e}",
                        error_type="ssl_error",
                        domain=domain,
                    )

    async def _check_url_no_ssl(self, url: str, domain: str) -> URLValidationResult:
        """
        Fallback check without SSL verification.

        Some sites have misconfigured SSL but are still valid.
        """
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            verify=False,  # Skip SSL verification
        ) as client:
            response = await client.head(url)

            canonical_url = str(response.url)
            redirected = canonical_url.rstrip("/") != url.rstrip("/")
            redirect_chain = [str(r.url) for r in response.history] if response.history else []

            # Check for parked domain in redirect
            if self._is_parked_redirect(canonical_url, redirect_chain):
                return URLValidationResult(
                    valid=False,
                    canonical_url=canonical_url,
                    redirected=redirected,
                    redirect_chain=redirect_chain,
                    error="Domain appears to be parked or for sale (SSL warning)",
                    error_type="parked_domain",
                    status_code=response.status_code,
                    is_parked=True,
                    domain=domain,
                )

            return URLValidationResult(
                valid=True,
                canonical_url=canonical_url,
                redirected=redirected,
                redirect_chain=redirect_chain,
                error=None,
                error_type=None,
                status_code=response.status_code,
                is_parked=False,
                domain=domain,
            )

    def _is_parked_redirect(self, canonical_url: str, redirect_chain: list[str]) -> bool:
        """
        Check if URL redirected to a known parked domain provider.
        """
        all_urls = redirect_chain + [canonical_url]

        for url in all_urls:
            url_lower = url.lower()
            for parked_host in PARKED_DOMAIN_HOSTS:
                if parked_host in url_lower:
                    return True

        return False

    def _is_parked_content(self, content: str) -> bool:
        """
        Check if page content indicates a parked/for-sale domain.

        Analyzes page content for common parking page indicators.
        """
        if not content:
            return False

        content_lower = content.lower()

        # Count matching indicators
        matches = sum(1 for indicator in PARKED_CONTENT_INDICATORS if indicator in content_lower)

        # If multiple indicators match, likely parked
        if matches >= 2:
            return True

        # Check for specific high-confidence patterns
        high_confidence_patterns = [
            "sedoparking",
            "godaddy.com/parking",
            "dan.com/buy-domain",
            "hugedomains.com",
            "this domain is for sale",
        ]

        return any(pattern in content_lower for pattern in high_confidence_patterns)


# Singleton instance for convenience
_validator: URLValidator | None = None


def get_url_validator(timeout: float = DEFAULT_TIMEOUT) -> URLValidator:
    """
    Get or create URL validator instance.

    Args:
        timeout: HTTP request timeout in seconds

    Returns:
        URLValidator instance
    """
    global _validator
    if _validator is None:
        _validator = URLValidator(timeout=timeout)
    return _validator


async def validate_url(url: str, timeout: float = DEFAULT_TIMEOUT) -> URLValidationResult:
    """
    Convenience function to validate a URL.

    Args:
        url: URL to validate
        timeout: HTTP request timeout in seconds

    Returns:
        URLValidationResult with validation status

    Example:
        >>> result = await validate_url("example.com")
        >>> if result.valid:
        >>>     print(f"Valid URL: {result.canonical_url}")
        >>> else:
        >>>     print(f"Invalid: {result.error}")
    """
    validator = get_url_validator(timeout)
    return await validator.validate_and_normalize(url)
