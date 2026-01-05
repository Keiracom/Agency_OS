"""
FILE: src/integrations/apify.py
PURPOSE: Apify API integration for bulk scraping
PHASE: 3 (Integrations)
TASK: INT-004
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
"""

from typing import Any

from apify_client import ApifyClient as BaseApifyClient
from apify_client.clients import ActorClient

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


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
