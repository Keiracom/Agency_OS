"""
Contract: src/integrations/gmb_scraper.py
Purpose: DIY Google Maps Business scraper using Autonomous Stealth Browser
Layer: 2 - integrations
Imports: external packages, config
Consumers: engines, orchestration

FILE: src/integrations/gmb_scraper.py
PURPOSE: Google Maps Business scraper - Tier 2 of Siege Waterfall
PHASE: FIXED_COST_OPTIMIZATION_PHASE_1
TASK: FCO-003
DEPENDENCIES:
  - tools/autonomous_browser.py
  - tools/proxy_manager.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Async-first design
  - Cost tracking in $AUD only

COST PROFILE:
  - Tier 2 of Siege Waterfall: ~$0.006/lead (proxy cost only)
  - Replaces Apify google-maps-scraper (~$0.02/lead)
  - Savings: ~70% cost reduction

GOVERNANCE EVENT: FIXED_COST_OPTIMIZATION_PHASE_1
DESCRIPTION: DIY GMB scraper replaces Apify dependency for Google Maps data
"""

import asyncio
import json
import logging
import random
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus, urljoin

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Add tools to path for autonomous_browser import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from tools.autonomous_browser import (
        autonomous_fetch,
        IdentityRotator,
        create_stealth_context,
    )
    from tools.proxy_manager import get_proxy_list, get_manager as get_proxy_manager
    HAS_BROWSER = True
except ImportError:
    HAS_BROWSER = False

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS & CONFIGURATION
# ============================================

# Cost per request in AUD (weighted average from proxy waterfall)
COST_PER_REQUEST_AUD = Decimal("0.006")

# Google Maps URLs
GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/{query}"
GOOGLE_MAPS_PLACE_URL = "https://www.google.com/maps/place/{place_id}"

# Rate limiting
MIN_REQUEST_DELAY_MS = 2000  # 2 seconds between requests
MAX_REQUEST_DELAY_MS = 5000  # 5 seconds max
MAX_CONCURRENT_REQUESTS = 3

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
RETRY_BACKOFF_MAX = 30

# Block detection patterns
BLOCK_INDICATORS = [
    "unusual traffic",
    "captcha",
    "automated queries",
    "please verify",
    "access denied",
    "rate limit",
]

# User agents for httpx fallback
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class GMBResult:
    """Result from a GMB scrape operation."""
    found: bool = False
    source: str = "gmb_scraper"
    
    # Core business data
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    
    # Rating & reviews
    rating: Optional[float] = None
    review_count: Optional[int] = None
    
    # Additional data
    category: Optional[str] = None
    place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    opening_hours: Optional[list] = None
    
    # Cost tracking
    cost_aud: Decimal = Decimal("0.00")
    requests_made: int = 0
    
    # Error info
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching Apify output format."""
        return {
            "found": self.found,
            "source": self.source,
            "name": self.name,
            "phone": self.phone,
            "address": self.address,
            "website": self.website,
            "rating": self.rating,
            "review_count": self.review_count,
            "category": self.category,
            "place_id": self.place_id,
            "google_maps_url": self.google_maps_url,
            "opening_hours": self.opening_hours,
            "cost_aud": float(self.cost_aud),
            "requests_made": self.requests_made,
            "error": self.error,
        }


@dataclass
class BatchResult:
    """Result from batch scraping operation."""
    total: int = 0
    success: int = 0
    failed: int = 0
    results: list[dict] = field(default_factory=list)
    total_cost_aud: Decimal = Decimal("0.00")
    total_requests: int = 0


# ============================================
# EXCEPTIONS
# ============================================

class GMBScraperError(Exception):
    """Base exception for GMB scraper."""
    pass


class BlockedError(GMBScraperError):
    """Raised when request is blocked by Google."""
    pass


class RateLimitError(GMBScraperError):
    """Raised when rate limited."""
    pass


class ParseError(GMBScraperError):
    """Raised when parsing fails."""
    pass


# ============================================
# HTML PARSING UTILITIES
# ============================================

class GMBParser:
    """
    Parser for Google Maps HTML/JSON data.
    
    Google Maps embeds business data in JavaScript arrays within the HTML.
    This parser extracts that data using regex and JSON parsing.
    """
    
    # Patterns for extracting data from Google Maps HTML
    PHONE_PATTERNS = [
        r'"(\+?[\d\s\-\(\)]{10,20})"',  # Phone in quotes
        r'tel:(\+?[\d\-]+)',  # tel: links
        r'data-phone-number="([^"]+)"',  # data attributes
    ]
    
    RATING_PATTERN = r'(\d+\.?\d*)\s*(?:stars?|out of 5)'
    REVIEW_COUNT_PATTERN = r'(\d+(?:,\d+)*)\s*(?:reviews?|Google reviews?)'
    
    ADDRESS_PATTERNS = [
        r'data-address="([^"]+)"',
        r'"formatted_address"\s*:\s*"([^"]+)"',
    ]
    
    WEBSITE_PATTERNS = [
        r'"website"\s*:\s*"([^"]+)"',
        r'href="(https?://(?!www\.google)[^"]+)"[^>]*>.*?(?:Website|Visit)',
    ]
    
    PLACE_ID_PATTERN = r'data-pid="([^"]+)"|/maps/place/[^/]+/data=[^"]*!1s([^!]+)'
    
    @classmethod
    def parse_business_data(cls, html: str, url: str = "") -> GMBResult:
        """
        Parse business data from Google Maps HTML.
        
        Args:
            html: Raw HTML content from Google Maps
            url: Original URL for reference
        
        Returns:
            GMBResult with extracted data
        """
        result = GMBResult(google_maps_url=url)
        
        if not html or len(html) < 1000:
            result.error = "Empty or insufficient HTML content"
            return result
        
        # Check for blocks
        html_lower = html.lower()
        for indicator in BLOCK_INDICATORS:
            if indicator in html_lower:
                result.error = f"Blocked: {indicator} detected"
                return result
        
        # Try to extract structured data from script tags
        structured_data = cls._extract_structured_data(html)
        if structured_data:
            result = cls._parse_structured_data(structured_data, result)
            if result.name:
                result.found = True
                return result
        
        # Fall back to regex parsing
        result = cls._parse_with_regex(html, result)
        
        if result.name or result.phone or result.address:
            result.found = True
        
        return result
    
    @classmethod
    def _extract_structured_data(cls, html: str) -> Optional[dict]:
        """
        Extract structured JSON data from Google Maps script tags.
        
        Google embeds business data in JavaScript arrays like:
        window.APP_INITIALIZATION_STATE=[[...business data...]]
        """
        # Look for APP_INITIALIZATION_STATE
        patterns = [
            r'window\.APP_INITIALIZATION_STATE\s*=\s*(\[\[.*?\]\]);',
            r'window\.APP_OPTIONS\s*=\s*({.*?});',
            r'"localizedPrimaryCategory"\s*:\s*"([^"]+)"',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return data
                except json.JSONDecodeError:
                    continue
        
        # Try to find LD+JSON structured data
        ld_json_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
        for match in re.finditer(ld_json_pattern, html, re.DOTALL | re.IGNORECASE):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and data.get("@type") in [
                    "LocalBusiness", "Organization", "Restaurant", "Store"
                ]:
                    return data
            except json.JSONDecodeError:
                continue
        
        return None
    
    @classmethod
    def _parse_structured_data(cls, data: dict, result: GMBResult) -> GMBResult:
        """Parse structured LD+JSON or similar data."""
        if isinstance(data, dict):
            result.name = data.get("name")
            result.phone = data.get("telephone")
            result.website = data.get("url") or data.get("website")
            
            # Address
            address_data = data.get("address", {})
            if isinstance(address_data, dict):
                parts = [
                    address_data.get("streetAddress"),
                    address_data.get("addressLocality"),
                    address_data.get("addressRegion"),
                    address_data.get("postalCode"),
                    address_data.get("addressCountry"),
                ]
                result.address = ", ".join(filter(None, parts))
            elif isinstance(address_data, str):
                result.address = address_data
            
            # Rating
            rating_data = data.get("aggregateRating", {})
            if isinstance(rating_data, dict):
                try:
                    result.rating = float(rating_data.get("ratingValue", 0))
                    result.review_count = int(rating_data.get("reviewCount", 0))
                except (ValueError, TypeError):
                    pass
            
            # Category
            result.category = data.get("@type") or data.get("category")
            
            # Opening hours
            hours = data.get("openingHoursSpecification", [])
            if hours:
                result.opening_hours = hours
        
        return result
    
    @classmethod
    def _parse_with_regex(cls, html: str, result: GMBResult) -> GMBResult:
        """Parse using regex patterns as fallback."""
        
        # Extract name from title
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title = title_match.group(1)
            # Clean up title (remove " - Google Maps" suffix)
            title = re.sub(r'\s*[-–]\s*Google Maps.*$', '', title)
            result.name = title.strip()
        
        # Extract phone
        for pattern in cls.PHONE_PATTERNS:
            match = re.search(pattern, html)
            if match:
                phone = match.group(1)
                # Clean phone number
                phone = re.sub(r'[^\d\+\-\(\)\s]', '', phone).strip()
                if len(phone) >= 10:
                    result.phone = phone
                    break
        
        # Extract rating
        rating_match = re.search(cls.RATING_PATTERN, html, re.IGNORECASE)
        if rating_match:
            try:
                result.rating = float(rating_match.group(1))
            except ValueError:
                pass
        
        # Extract review count
        review_match = re.search(cls.REVIEW_COUNT_PATTERN, html, re.IGNORECASE)
        if review_match:
            try:
                result.review_count = int(review_match.group(1).replace(",", ""))
            except ValueError:
                pass
        
        # Extract address
        for pattern in cls.ADDRESS_PATTERNS:
            match = re.search(pattern, html)
            if match:
                result.address = match.group(1)
                break
        
        # Extract website
        for pattern in cls.WEBSITE_PATTERNS:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                website = match.group(1)
                if not website.startswith("http"):
                    website = "https://" + website
                result.website = website
                break
        
        # Extract place ID
        place_match = re.search(cls.PLACE_ID_PATTERN, html)
        if place_match:
            result.place_id = place_match.group(1) or place_match.group(2)
        
        # Extract category (look for aria-label patterns)
        category_match = re.search(r'aria-label="([^"]+)\s+category"', html, re.IGNORECASE)
        if category_match:
            result.category = category_match.group(1)
        
        return result
    
    @classmethod
    def extract_search_results(cls, html: str) -> list[dict]:
        """
        Extract business listings from Google Maps search results.
        
        Returns list of basic business info from search page.
        """
        results = []
        
        # Look for search result items
        # Google Maps search results contain data in specific patterns
        item_pattern = r'<a[^>]*href="([^"]*maps/place/[^"]+)"[^>]*>.*?</a>'
        
        for match in re.finditer(item_pattern, html, re.DOTALL):
            url = match.group(1)
            if not url.startswith("http"):
                url = "https://www.google.com" + url
            
            # Extract place name from URL
            name_match = re.search(r'/maps/place/([^/]+)/', url)
            name = name_match.group(1).replace("+", " ") if name_match else None
            
            # Extract place ID
            pid_match = re.search(r'!1s([^!]+)', url)
            place_id = pid_match.group(1) if pid_match else None
            
            if name or place_id:
                results.append({
                    "name": name,
                    "place_id": place_id,
                    "url": url,
                })
        
        return results


# ============================================
# GMB SCRAPER CLASS
# ============================================

class GMBScraper:
    """
    Google Maps Business scraper using Autonomous Stealth Browser.
    
    Tier 2 of Siege Waterfall - $0.006/lead (proxy cost only).
    Replaces Apify google-maps-scraper (~$0.02/lead).
    
    Features:
    - Stealth browser with proxy rotation
    - Automatic retry with identity rotation
    - Rate limiting to avoid blocks
    - Cost tracking in AUD
    - Fallback parsing strategies
    
    Usage:
        scraper = GMBScraper()
        result = await scraper.search_business("Acme Corp", "Sydney, Australia")
        print(result)
    """
    
    def __init__(
        self,
        proxy_list: Optional[list[str]] = None,
        rate_limit_ms: int = MIN_REQUEST_DELAY_MS,
    ):
        """
        Initialize GMB scraper.
        
        Args:
            proxy_list: Optional list of proxy URLs. If not provided,
                       loads from proxy_manager.
            rate_limit_ms: Minimum delay between requests in milliseconds.
        """
        self._proxy_list = proxy_list
        self._rate_limit_ms = rate_limit_ms
        self._last_request_time = 0
        self._request_count = 0
        self._total_cost = Decimal("0.00")
        
        # Load proxies if not provided
        if not self._proxy_list and HAS_BROWSER:
            try:
                self._proxy_list = get_proxy_list()
            except Exception as e:
                logger.warning(f"Failed to load proxies: {e}")
                self._proxy_list = []
        
        # Identity rotator for stealth
        if HAS_BROWSER:
            self._rotator = IdentityRotator()
        else:
            self._rotator = None
        
        logger.info(
            f"GMBScraper initialized with {len(self._proxy_list or [])} proxies"
        )
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        import time
        
        elapsed = (time.time() * 1000) - self._last_request_time
        delay_ms = random.randint(self._rate_limit_ms, MAX_REQUEST_DELAY_MS)
        
        if elapsed < delay_ms:
            await asyncio.sleep((delay_ms - elapsed) / 1000)
        
        self._last_request_time = time.time() * 1000
    
    def _track_cost(self, requests: int = 1) -> Decimal:
        """Track cost for requests made."""
        cost = COST_PER_REQUEST_AUD * requests
        self._total_cost += cost
        self._request_count += requests
        return cost
    
    def _get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from the pool."""
        if not self._proxy_list:
            return None
        return random.choice(self._proxy_list)
    
    async def search_business(
        self,
        name: str,
        location: str,
    ) -> dict[str, Any]:
        """
        Search Google Maps for a business by name + location.
        
        This searches Google Maps and returns the first matching result's
        full details.
        
        Args:
            name: Business name to search for
            location: Location (city, state, country)
        
        Returns:
            dict with business data matching Apify output format:
            - found: bool
            - source: "gmb_scraper"
            - name, phone, address, website
            - rating, review_count
            - category, place_id, google_maps_url, opening_hours
        """
        logger.info(f"Searching for business: {name} in {location}")
        
        # Build search query
        query = f"{name} {location}"
        search_url = GOOGLE_MAPS_SEARCH_URL.format(query=quote_plus(query))
        
        await self._rate_limit()
        
        # Fetch search results
        try:
            html = await self._fetch_with_stealth(search_url)
            cost = self._track_cost(1)
        except BlockedError as e:
            return GMBResult(
                error=str(e),
                cost_aud=self._track_cost(1),
                requests_made=1,
            ).to_dict()
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return GMBResult(
                error=str(e),
                cost_aud=COST_PER_REQUEST_AUD,
                requests_made=1,
            ).to_dict()
        
        # Parse the page - Google Maps search often shows details directly
        result = GMBParser.parse_business_data(html, search_url)
        result.cost_aud = cost
        result.requests_made = 1
        
        # If we got a match, try to get more details
        if result.found and result.place_id:
            await self._rate_limit()
            try:
                details = await self.scrape_details(result.google_maps_url or search_url)
                # Merge details into result
                if details.get("found"):
                    result.phone = details.get("phone") or result.phone
                    result.website = details.get("website") or result.website
                    result.opening_hours = details.get("opening_hours") or result.opening_hours
                    result.cost_aud += Decimal(str(details.get("cost_aud", 0)))
                    result.requests_made += details.get("requests_made", 0)
            except Exception as e:
                logger.warning(f"Failed to get additional details: {e}")
        
        return result.to_dict()
    
    async def scrape_details(
        self,
        place_url: str,
    ) -> dict[str, Any]:
        """
        Scrape full business details from a Google Maps URL.
        
        Args:
            place_url: Full Google Maps URL for the place
        
        Returns:
            dict with business data matching Apify output format
        """
        logger.info(f"Scraping details from: {place_url[:60]}...")
        
        await self._rate_limit()
        
        try:
            html = await self._fetch_with_stealth(place_url)
            cost = self._track_cost(1)
        except BlockedError as e:
            return GMBResult(
                error=str(e),
                google_maps_url=place_url,
                cost_aud=self._track_cost(1),
                requests_made=1,
            ).to_dict()
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return GMBResult(
                error=str(e),
                google_maps_url=place_url,
                cost_aud=COST_PER_REQUEST_AUD,
                requests_made=1,
            ).to_dict()
        
        result = GMBParser.parse_business_data(html, place_url)
        result.cost_aud = cost
        result.requests_made = 1
        
        return result.to_dict()
    
    async def batch_scrape(
        self,
        businesses: list[dict],
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    ) -> list[dict[str, Any]]:
        """
        Bulk scrape multiple businesses.
        
        Args:
            businesses: List of dicts with 'name' and 'location' keys,
                       or 'url' for direct place URLs
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of business data dicts
        """
        logger.info(f"Batch scraping {len(businesses)} businesses")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_one(biz: dict) -> dict:
            async with semaphore:
                if "url" in biz:
                    return await self.scrape_details(biz["url"])
                else:
                    return await self.search_business(
                        biz.get("name", ""),
                        biz.get("location", "Australia"),
                    )
        
        # Process in batches
        tasks = [scrape_one(biz) for biz in businesses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(GMBResult(
                    error=str(r),
                    cost_aud=COST_PER_REQUEST_AUD,
                    requests_made=1,
                ).to_dict())
            else:
                final_results.append(r)
        
        # Log summary
        success_count = sum(1 for r in final_results if r.get("found"))
        total_cost = sum(Decimal(str(r.get("cost_aud", 0))) for r in final_results)
        
        logger.info(
            f"Batch complete: {success_count}/{len(businesses)} found, "
            f"cost: ${total_cost:.4f} AUD"
        )
        
        return final_results
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ProxyError)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_BACKOFF_BASE, max=RETRY_BACKOFF_MAX),
    )
    async def _fetch_with_stealth(self, url: str) -> str:
        """
        Fetch URL using stealth browser with proxy rotation.
        
        Uses Playwright-based autonomous_browser if available,
        falls back to httpx with proxy rotation.
        
        Args:
            url: URL to fetch
        
        Returns:
            HTML content
        
        Raises:
            BlockedError: If request is blocked
            httpx.TimeoutException: On timeout (will retry)
        """
        # Try autonomous browser first (best success rate)
        if HAS_BROWSER and HAS_PLAYWRIGHT:
            try:
                result = await autonomous_fetch(
                    url,
                    stealth=True,
                    use_cache=False,  # Don't cache GMB results
                    scroll=True,  # Load lazy content
                )
                
                if result.get("success"):
                    return result.get("content", "")
                
                error = result.get("error", "Unknown error")
                if any(ind in error.lower() for ind in BLOCK_INDICATORS):
                    raise BlockedError(error)
                
                logger.warning(f"Browser fetch failed: {error}")
            except BlockedError:
                raise
            except Exception as e:
                logger.warning(f"Browser fetch error: {e}")
        
        # Fallback to httpx with proxy
        proxy = self._get_random_proxy()
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        async with httpx.AsyncClient(
            proxy=proxy,
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url, headers=headers)
            
            # Check for blocks
            if response.status_code in (403, 429, 503):
                raise BlockedError(f"HTTP {response.status_code}")
            
            response.raise_for_status()
            
            html = response.text
            
            # Check content for block indicators
            html_lower = html.lower()
            for indicator in BLOCK_INDICATORS:
                if indicator in html_lower:
                    raise BlockedError(f"Block indicator detected: {indicator}")
            
            return html
    
    def get_stats(self) -> dict[str, Any]:
        """Get scraper statistics."""
        return {
            "total_requests": self._request_count,
            "total_cost_aud": float(self._total_cost),
            "avg_cost_per_request": float(
                self._total_cost / self._request_count
                if self._request_count > 0
                else COST_PER_REQUEST_AUD
            ),
            "proxies_available": len(self._proxy_list or []),
        }


# ============================================
# SINGLETON FACTORY
# ============================================

_gmb_scraper: Optional[GMBScraper] = None


def get_gmb_scraper() -> GMBScraper:
    """Get or create GMBScraper singleton."""
    global _gmb_scraper
    if _gmb_scraper is None:
        _gmb_scraper = GMBScraper()
    return _gmb_scraper


# ============================================
# CONVENIENCE FUNCTIONS (Match Apify API)
# ============================================

async def scrape_google_business(
    business_name: str,
    location: str = "Australia",
) -> dict[str, Any]:
    """
    Scrape Google Business data.
    
    Drop-in replacement for apify.scrape_google_business().
    
    Args:
        business_name: Name of the business to search
        location: Location to search in (default: Australia)
    
    Returns:
        Business data dict matching Apify output format
    """
    scraper = get_gmb_scraper()
    return await scraper.search_business(business_name, location)


async def batch_scrape_google_business(
    businesses: list[dict],
) -> list[dict[str, Any]]:
    """
    Batch scrape Google Business data.
    
    Args:
        businesses: List of dicts with 'name' and 'location' keys
    
    Returns:
        List of business data dicts
    """
    scraper = get_gmb_scraper()
    return await scraper.batch_scrape(businesses)


# ============================================
# CLI INTERFACE
# ============================================

async def _cli_main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GMB Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for a business")
    search_parser.add_argument("name", help="Business name")
    search_parser.add_argument("--location", "-l", default="Australia", help="Location")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape a Maps URL")
    scrape_parser.add_argument("url", help="Google Maps URL")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show scraper stats")
    
    args = parser.parse_args()
    
    if args.command == "search":
        result = await scrape_google_business(args.name, args.location)
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == "scrape":
        scraper = get_gmb_scraper()
        result = await scraper.scrape_details(args.url)
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == "stats":
        scraper = get_gmb_scraper()
        stats = scraper.get_stats()
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(_cli_main())


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] GMBScraper class with search_business, scrape_details, batch_scrape
# [x] Data extraction: name, phone, address, website, rating, review_count
# [x] Data extraction: category, place_id, opening_hours
# [x] Uses httpx + proxy rotation
# [x] Retry logic with tenacity
# [x] Rate limiting
# [x] Cost tracking (~$0.006/request)
# [x] Output format matches Apify
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
