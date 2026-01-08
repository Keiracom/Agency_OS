"""
FILE: src/integrations/apify.py
PURPOSE: Apify API integration for bulk scraping with waterfall architecture
PHASE: 3 (Integrations)
TASK: INT-004, SCR-002, SCR-003
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly

WATERFALL ARCHITECTURE (Phase 19):
  Tier 1: Cheerio (static HTML) - fast, cheap, ~60% success
  Tier 2: Playwright (JS rendering) - slower, ~80% success
  If both fail, returns needs_fallback=True for Tier 3/4 handling
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from apify_client import ApifyClient as BaseApifyClient
from apify_client.clients import ActorClient

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError

logger = logging.getLogger(__name__)

# Minimum content length to consider a scrape successful
MIN_CONTENT_LENGTH = 500

# Common agency page paths for seed URLs (ICP-FIX-002)
# These pages often contain portfolio/testimonial data that the homepage may not link to
AGENCY_SEED_PATHS = [
    "/about",
    "/about-us",
    "/case-studies",
    "/case-study",
    "/testimonials",
    "/reviews",
    "/our-work",
    "/work",
    "/portfolio",
    "/clients",
    "/our-clients",
    "/services",
]

# Indicators that content is blocked/empty
BLOCKED_CONTENT_INDICATORS = [
    "access denied",
    "ray id:",
    "please wait while we verify",
    "checking your browser",
    "just a moment...",
    "enable javascript and cookies",
    "cloudflare",
    "attention required",
    "please complete the security check",
    "bot protection",
    "captcha",
]


@dataclass
class ScrapeResult:
    """
    Result of a website scrape with tier tracking.

    Used by the Scraper Waterfall to track which tier succeeded
    and whether manual fallback is needed.
    """

    url: str
    pages: list[dict[str, Any]] = field(default_factory=list)
    page_count: int = 0
    raw_html: str = ""
    title: str = ""
    tier_used: int = 0  # 0=validation, 1=cheerio, 2=playwright, 3=camoufox, 4=manual
    needs_fallback: bool = False
    failure_reason: Optional[str] = None
    manual_fallback_url: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if scrape was successful."""
        return self.page_count > 0 and len(self.raw_html) >= MIN_CONTENT_LENGTH and not self.needs_fallback

    def has_valid_content(self) -> bool:
        """Check if the scraped content is valid (not blocked/empty)."""
        if not self.raw_html or len(self.raw_html) < MIN_CONTENT_LENGTH:
            return False

        # Check for blocked content indicators
        html_lower = self.raw_html.lower()
        blocked_count = sum(
            1 for indicator in BLOCKED_CONTENT_INDICATORS
            if indicator in html_lower
        )

        # If multiple blocked indicators found, likely blocked
        return blocked_count < 2


class ApifyClient:
    """
    Apify client for web scraping.

    Used in Tier 1 of enrichment waterfall alongside Apollo
    for bulk data extraction.
    """

    # Common actor IDs
    LINKEDIN_SCRAPER = "anchor/linkedin-people-scraper"
    LINKEDIN_COMPANY_SCRAPER = "curious_coder/linkedin-company-scraper"
    GOOGLE_SEARCH = "apify/google-search-scraper"
    WEBSITE_CONTENT = "apify/website-content-crawler"
    INSTAGRAM_SCRAPER = "apify/instagram-profile-scraper"
    FACEBOOK_SCRAPER = "apify/facebook-pages-scraper"
    GOOGLE_MAPS_SCRAPER = "apify/google-maps-scraper"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.apify_api_key
        if not self.api_key:
            raise IntegrationError(
                service="apify",
                message="Apify API key is required",
            )
        self._client = BaseApifyClient(self.api_key)

    def _get_actor(self, actor_id: str) -> ActorClient:
        """Get actor client."""
        return self._client.actor(actor_id)

    async def scrape_linkedin_profiles(
        self,
        linkedin_urls: list[str],
        proxy_config: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Scrape LinkedIn profiles in bulk.

        Args:
            linkedin_urls: List of LinkedIn profile URLs
            proxy_config: Optional proxy configuration

        Returns:
            List of scraped profile data
        """
        actor = self._get_actor(self.LINKEDIN_SCRAPER)

        run_input = {
            "startUrls": [{"url": url} for url in linkedin_urls],
            "proxy": proxy_config or {"useApifyProxy": True},
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())
            return [self._transform_linkedin_profile(item) for item in items]
        except Exception as e:
            raise APIError(
                service="apify",
                status_code=500,
                message=f"LinkedIn scraping failed: {str(e)}",
            )

    async def search_google(
        self,
        queries: list[str],
        results_per_query: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Perform Google searches.

        Args:
            queries: Search queries
            results_per_query: Number of results per query

        Returns:
            Search results
        """
        actor = self._get_actor(self.GOOGLE_SEARCH)

        run_input = {
            "queries": queries,
            "maxResultsPerPage": results_per_query,
            "languageCode": "en",
            "countryCode": "au",  # Australia focus
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            return list(dataset.iterate_items())
        except Exception as e:
            raise APIError(
                service="apify",
                status_code=500,
                message=f"Google search failed: {str(e)}",
            )

    async def scrape_website(
        self,
        url: str,
        max_pages: int = 10,
        use_javascript: bool = True,
    ) -> dict[str, Any]:
        """
        Scrape website content.

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl
            use_javascript: Whether to use Playwright for JS-heavy sites

        Returns:
            Scraped content
        """
        actor = self._get_actor(self.WEBSITE_CONTENT)

        # Use playwright for JavaScript rendering (most agency sites need this)
        crawler_type = "playwright" if use_javascript else "cheerio"

        run_input = {
            "startUrls": [{"url": url}],
            "maxCrawlPages": max_pages,
            "crawlerType": crawler_type,
            "saveHtml": True,  # Include HTML content in output
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            # Check if we got valid content
            has_content = any(
                item.get("html") or item.get("text")
                for item in items
            )

            # If playwright failed, try cheerio as fallback
            if not has_content and use_javascript:
                run_input["crawlerType"] = "cheerio"
                run = actor.call(run_input=run_input)
                dataset = self._client.dataset(run["defaultDatasetId"])
                items = list(dataset.iterate_items())

            return {
                "url": url,
                "pages": items,
                "page_count": len(items),
            }
        except Exception as e:
            raise APIError(
                service="apify",
                status_code=500,
                message=f"Website scraping failed: {str(e)}",
            )

    async def scrape_website_with_waterfall(
        self,
        url: str,
        max_pages: int = 10,
    ) -> ScrapeResult:
        """
        Scrape website with tiered fallback (Tier 1 → Tier 2).

        Implements the Scraper Waterfall architecture:
        - Tier 1: Cheerio (fast, static HTML, ~60% success)
        - Tier 2: Playwright (JS rendering, ~80% success)

        If both fail, returns needs_fallback=True for Tier 3/4 handling.

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl

        Returns:
            ScrapeResult with tier tracking and fallback status
        """
        logger.info(f"Starting waterfall scrape for {url}")

        # Tier 1: Try Cheerio first (fast, cheap)
        logger.debug(f"Tier 1: Attempting Cheerio scrape for {url}")
        result = await self._scrape_cheerio(url, max_pages)

        if result.has_valid_content():
            logger.info(f"Tier 1 success for {url}: {result.page_count} pages, {len(result.raw_html)} chars")
            return result

        logger.debug(f"Tier 1 failed for {url}: {result.failure_reason or 'empty/blocked content'}")

        # Tier 2: Fall back to Playwright (JS rendering)
        logger.debug(f"Tier 2: Attempting Playwright scrape for {url}")
        result = await self._scrape_playwright(url, max_pages)

        if result.has_valid_content():
            logger.info(f"Tier 2 success for {url}: {result.page_count} pages, {len(result.raw_html)} chars")
            return result

        logger.warning(f"Tier 2 failed for {url}: {result.failure_reason or 'empty/blocked content'}")

        # Both tiers failed - needs fallback to Tier 3 (Camoufox) or Tier 4 (Manual)
        return ScrapeResult(
            url=url,
            pages=[],
            page_count=0,
            raw_html="",
            tier_used=2,
            needs_fallback=True,
            failure_reason="Both Cheerio and Playwright returned empty or blocked content",
            manual_fallback_url=f"/onboarding/manual-entry?url={url}",
        )

    async def _scrape_cheerio(
        self,
        url: str,
        max_pages: int = 10,
        timeout_secs: int = 30,
    ) -> ScrapeResult:
        """
        Tier 1: Static HTML scraping with Cheerio.

        Fast and cheap, works for ~60% of sites.
        Fails on JS-rendered content and Cloudflare protection.

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl
            timeout_secs: Request timeout in seconds

        Returns:
            ScrapeResult with tier=1
        """
        actor = self._get_actor(self.WEBSITE_CONTENT)

        run_input = {
            "startUrls": [{"url": url}],
            "maxCrawlPages": max_pages,
            "crawlerType": "cheerio",
            "requestTimeoutSecs": timeout_secs,
            "saveHtml": True,
            "saveMarkdown": True,
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            # Combine all HTML content
            raw_html = "\n".join(
                item.get("html", "") or item.get("text", "")
                for item in items
            )

            # Get title from first page
            title = items[0].get("title", "") if items else ""

            return ScrapeResult(
                url=url,
                pages=items,
                page_count=len(items),
                raw_html=raw_html,
                title=title,
                tier_used=1,
                needs_fallback=False,
            )

        except Exception as e:
            logger.warning(f"Cheerio scrape failed for {url}: {e}")
            return ScrapeResult(
                url=url,
                pages=[],
                page_count=0,
                raw_html="",
                tier_used=1,
                needs_fallback=True,
                failure_reason=f"Cheerio scrape error: {str(e)}",
            )

    def _build_seed_urls(self, base_url: str) -> list[dict[str, str]]:
        """
        Build seed URLs for common agency pages (ICP-FIX-002).

        Many agency sites are JS-rendered and the homepage may not contain
        links to important pages like /case-studies, /testimonials.
        Adding these as seed URLs ensures they get crawled.

        Args:
            base_url: Base URL (e.g., https://dilate.com.au/)

        Returns:
            List of seed URL objects for Apify
        """
        from urllib.parse import urljoin

        # Start with the main URL
        seed_urls = [{"url": base_url}]

        # Add common agency paths
        for path in AGENCY_SEED_PATHS:
            full_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
            seed_urls.append({"url": full_url})

        logger.debug(f"Built {len(seed_urls)} seed URLs for {base_url}")
        return seed_urls

    async def _scrape_playwright(
        self,
        url: str,
        max_pages: int = 10,
        timeout_secs: int = 60,
    ) -> ScrapeResult:
        """
        Tier 2: JS-rendered scraping with Playwright.

        Handles React/Vue/Angular sites. Slower but more reliable.
        Fails on Cloudflare Turnstile and aggressive bot detection.

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl
            timeout_secs: Request timeout in seconds

        Returns:
            ScrapeResult with tier=2
        """
        actor = self._get_actor(self.WEBSITE_CONTENT)

        # Use seed URLs for common agency pages (ICP-FIX-002)
        # This ensures we crawl /case-studies, /testimonials, etc. even if
        # the JS-rendered homepage doesn't link to them directly
        seed_urls = self._build_seed_urls(url)

        run_input = {
            "startUrls": seed_urls,
            "maxCrawlPages": max_pages,
            "crawlerType": "playwright",
            "requestTimeoutSecs": timeout_secs,
            "saveHtml": True,
            "saveMarkdown": True,
            # Playwright-specific options for better success rate
            "pageLoadTimeoutSecs": 45,
            "maxRequestRetries": 2,
        }
        logger.info(f"Playwright scrape with {len(seed_urls)} seed URLs for {url}")

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            # Combine all HTML content
            raw_html = "\n".join(
                item.get("html", "") or item.get("text", "")
                for item in items
            )

            # Get title from first page
            title = items[0].get("title", "") if items else ""

            return ScrapeResult(
                url=url,
                pages=items,
                page_count=len(items),
                raw_html=raw_html,
                title=title,
                tier_used=2,
                needs_fallback=False,
            )

        except Exception as e:
            logger.warning(f"Playwright scrape failed for {url}: {e}")
            return ScrapeResult(
                url=url,
                pages=[],
                page_count=0,
                raw_html="",
                tier_used=2,
                needs_fallback=True,
                failure_reason=f"Playwright scrape error: {str(e)}",
            )

    def validate_scrape_content(self, html: str) -> tuple[bool, Optional[str]]:
        """
        Validate scraped content (SCR-003).

        Checks if the content is valid or if it's blocked/empty.

        Args:
            html: The scraped HTML content

        Returns:
            Tuple of (is_valid, failure_reason)
        """
        if not html:
            return False, "Empty content"

        if len(html) < MIN_CONTENT_LENGTH:
            return False, f"Content too short ({len(html)} chars, min {MIN_CONTENT_LENGTH})"

        # Check for blocked content indicators
        html_lower = html.lower()
        matched_indicators = [
            indicator for indicator in BLOCKED_CONTENT_INDICATORS
            if indicator in html_lower
        ]

        if len(matched_indicators) >= 2:
            return False, f"Blocked content detected: {', '.join(matched_indicators[:3])}"

        return True, None

    async def find_company_contacts(
        self,
        domain: str,
        titles: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find contacts at a company via LinkedIn search.

        Args:
            domain: Company domain
            titles: Filter by job titles

        Returns:
            List of found contacts
        """
        # Build search query
        company_name = domain.replace(".com", "").replace(".com.au", "")
        title_query = " OR ".join(titles) if titles else "CEO OR founder OR director"

        query = f'site:linkedin.com/in "{company_name}" ({title_query})'

        results = await self.search_google([query], results_per_query=20)

        contacts = []
        for result in results:
            if "linkedin.com/in/" in result.get("url", ""):
                contacts.append({
                    "linkedin_url": result["url"],
                    "title": result.get("title", ""),
                    "snippet": result.get("description", ""),
                })

        return contacts

    def _transform_linkedin_profile(self, data: dict) -> dict[str, Any]:
        """Transform Apify LinkedIn data to standard format."""
        return {
            "found": True,
            "source": "apify",
            "linkedin_url": data.get("url"),
            "first_name": data.get("firstName"),
            "last_name": data.get("lastName"),
            "title": data.get("headline"),
            "company": data.get("company"),
            "location": data.get("location"),
            "connections": data.get("connectionsCount"),
            "about": data.get("about"),
            "experience": data.get("experience", []),
            "education": data.get("education", []),
        }

    async def scrape_linkedin_company(
        self,
        linkedin_url: str,
    ) -> dict[str, Any]:
        """
        Scrape LinkedIn company page data.

        Args:
            linkedin_url: LinkedIn company page URL

        Returns:
            Company data: name, followers, employee_count, specialties,
            description, industry, headquarters
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Scraping LinkedIn company: {linkedin_url}")

        actor = self._get_actor(self.LINKEDIN_COMPANY_SCRAPER)

        run_input = {
            "startUrls": [{"url": linkedin_url}],
            "proxy": {"useApifyProxy": True},
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            if not items:
                return {"found": False, "source": "apify"}

            data = items[0]
            return {
                "found": True,
                "source": "apify",
                "name": data.get("name"),
                "followers": data.get("followersCount"),
                "employee_count": data.get("employeesCount"),
                "employee_range": data.get("employeeCountRange"),
                "specialties": data.get("specialities", []),
                "description": data.get("description"),
                "industry": data.get("industry"),
                "headquarters": data.get("headquarters"),
                "website": data.get("website"),
                "founded_year": data.get("foundedYear"),
                "linkedin_url": linkedin_url,
            }
        except Exception as e:
            logger.warning(f"LinkedIn company scraping failed: {str(e)}")
            raise APIError(
                service="apify",
                status_code=500,
                message=f"LinkedIn company scraping failed: {str(e)}",
            )

    async def scrape_instagram_profile(
        self,
        instagram_url: str,
    ) -> dict[str, Any]:
        """
        Scrape Instagram profile data.

        Args:
            instagram_url: Instagram profile URL

        Returns:
            Profile data: username, followers, following, posts_count,
            bio, is_verified
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Scraping Instagram profile: {instagram_url}")

        actor = self._get_actor(self.INSTAGRAM_SCRAPER)

        run_input = {
            "directUrls": [instagram_url],
            "proxy": {"useApifyProxy": True},
            "resultsType": "details",
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            if not items:
                return {"found": False, "source": "apify"}

            data = items[0]
            return {
                "found": True,
                "source": "apify",
                "username": data.get("username"),
                "followers": data.get("followersCount"),
                "following": data.get("followingCount"),
                "posts_count": data.get("postsCount"),
                "bio": data.get("biography"),
                "is_verified": data.get("verified", False),
                "full_name": data.get("fullName"),
                "profile_pic_url": data.get("profilePicUrl"),
                "external_url": data.get("externalUrl"),
                "instagram_url": instagram_url,
            }
        except Exception as e:
            logger.warning(f"Instagram scraping failed: {str(e)}")
            raise APIError(
                service="apify",
                status_code=500,
                message=f"Instagram scraping failed: {str(e)}",
            )

    async def scrape_facebook_page(
        self,
        facebook_url: str,
    ) -> dict[str, Any]:
        """
        Scrape Facebook page data.

        Args:
            facebook_url: Facebook page URL

        Returns:
            Page data: name, likes, followers, category, about,
            rating, review_count
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Scraping Facebook page: {facebook_url}")

        actor = self._get_actor(self.FACEBOOK_SCRAPER)

        run_input = {
            "startUrls": [{"url": facebook_url}],
            "proxy": {"useApifyProxy": True},
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            if not items:
                return {"found": False, "source": "apify"}

            data = items[0]
            return {
                "found": True,
                "source": "apify",
                "name": data.get("name"),
                "likes": data.get("likes"),
                "followers": data.get("followers"),
                "category": data.get("categories", [None])[0] if data.get("categories") else None,
                "about": data.get("about"),
                "rating": data.get("overallStarRating"),
                "review_count": data.get("reviewsCount"),
                "website": data.get("website"),
                "phone": data.get("phone"),
                "address": data.get("address"),
                "facebook_url": facebook_url,
            }
        except Exception as e:
            logger.warning(f"Facebook scraping failed: {str(e)}")
            raise APIError(
                service="apify",
                status_code=500,
                message=f"Facebook scraping failed: {str(e)}",
            )

    async def scrape_google_business(
        self,
        business_name: str,
        location: str = "Australia",
    ) -> dict[str, Any]:
        """
        Scrape Google Business (Google Maps) data.

        Args:
            business_name: Name of the business to search
            location: Location to search in (default: Australia)

        Returns:
            Business data: name, rating, review_count, address,
            phone, website
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Scraping Google Business: {business_name} in {location}")

        actor = self._get_actor(self.GOOGLE_MAPS_SCRAPER)

        # Search query combining business name and location
        search_query = f"{business_name} {location}"

        run_input = {
            "searchStringsArray": [search_query],
            "maxCrawledPlacesPerSearch": 1,  # Only need the top result
            "language": "en",
            "proxy": {"useApifyProxy": True},
        }

        try:
            run = actor.call(run_input=run_input)
            dataset = self._client.dataset(run["defaultDatasetId"])
            items = list(dataset.iterate_items())

            if not items:
                return {"found": False, "source": "apify"}

            data = items[0]
            return {
                "found": True,
                "source": "apify",
                "name": data.get("title"),
                "rating": data.get("totalScore"),
                "review_count": data.get("reviewsCount"),
                "address": data.get("address"),
                "phone": data.get("phone"),
                "website": data.get("website"),
                "category": data.get("categoryName"),
                "place_id": data.get("placeId"),
                "google_maps_url": data.get("url"),
                "opening_hours": data.get("openingHours"),
            }
        except Exception as e:
            logger.warning(f"Google Business scraping failed: {str(e)}")
            raise APIError(
                service="apify",
                status_code=500,
                message=f"Google Business scraping failed: {str(e)}",
            )


# Singleton instance
_apify_client: ApifyClient | None = None


def get_apify_client() -> ApifyClient:
    """Get or create Apify client instance."""
    global _apify_client
    if _apify_client is None:
        _apify_client = ApifyClient()
    return _apify_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] LinkedIn profile scraping
# [x] Google search
# [x] Website content scraping
# [x] Company contact finder
# [x] Standard response format
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
