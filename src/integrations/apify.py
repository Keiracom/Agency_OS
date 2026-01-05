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
    GOOGLE_SEARCH = "apify/google-search-scraper"
    WEBSITE_CONTENT = "apify/website-content-crawler"

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
    ) -> dict[str, Any]:
        """
        Scrape website content.

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl

        Returns:
            Scraped content
        """
        actor = self._get_actor(self.WEBSITE_CONTENT)

        run_input = {
            "startUrls": [{"url": url}],
            "maxCrawlPages": max_pages,
            "crawlerType": "cheerio",
        }

        try:
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
