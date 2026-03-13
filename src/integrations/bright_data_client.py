"""
Bright Data Unified Client

Wraps both SERP API and Scrapers API with cost tracking and error handling.
Supports Google/Maps searches via SERP API and LinkedIn scraping via Scrapers API.

Note: All methods are async - use with await.
"""

import asyncio
import json
import os
import urllib.parse
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# Verified dataset IDs from Directive #020d
DATASET_IDS = {
    "linkedin_company": "gd_l1vikfnt1wgvvqz95w",
    "linkedin_people": "gd_l1viktl72bvl7bjuj0",
    "linkedin_jobs": "gd_lpfll7v5hcqtkxl6l",
    # Siege Waterfall v3: GMB-first discovery (Directive #144)
    "gmb_business": "gd_m8ebnr0q2qlklc02fz",
    "gmb_reviews": "gd_m8ebnr0q2qlklc02fz",  # Same dataset, reviews in response
    "linkedin_posts": "gd_l1viktl72bvl7bjuj0",  # Posts included in people profile
    "x_posts": "gd_lwdb4vjm1qvm96sbq2",  # X/Twitter posts dataset
}

COSTS_AUD = {
    "serp_request": 0.0015,
    "scraper_record": 0.0015,
    # Siege Waterfall v3 costs (Directive #144)
    "gmb_discovery": 0.001,  # T0 GMB-first discovery
    "gmb_reviews": 0.001,  # T2.5 GMB reviews
    "linkedin_company": 0.025,  # T1.5 LinkedIn company
    "linkedin_profile": 0.0015,  # T-DM1 LinkedIn profile
    "linkedin_posts": 0.0015,  # T-DM2 LinkedIn posts 90d
    "x_posts": 0.0025,  # T-DM3 X posts 90d
}


class BrightDataError(Exception):
    """Bright Data API error"""

    pass


@dataclass
class CostTracker:
    """Tracks API usage costs for the session"""

    serp_requests: int = 0
    scraper_records: int = 0

    @property
    def total_aud(self) -> float:
        """Calculate total cost in AUD for this session"""
        return (
            self.serp_requests * COSTS_AUD["serp_request"]
            + self.scraper_records * COSTS_AUD["scraper_record"]
        )


class BrightDataClient:
    """
    Unified async client for Bright Data SERP API and Scrapers API.

    Provides methods for:
    - Google/Maps searches via SERP API
    - LinkedIn scraping via Scrapers API
    - Cost tracking across both services

    All methods are async and should be called with await.
    """

    def __init__(self, api_key: str, serp_zone: str = "serp_api1"):
        """
        Initialize the Bright Data client.

        Args:
            api_key: Your Bright Data API key
            serp_zone: Zone for SERP API proxy (default: "serp_api1")
        """
        self.api_key = api_key
        self.serp_zone = serp_zone
        self.costs = CostTracker()
        self._client: httpx.AsyncClient | None = None
        # Bulk pre-fetch cache: keyed by normalised LinkedIn URL → company dict
        self._bulk_company_cache: dict[str, dict] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0, verify=False)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # SERP API Methods

    async def search_google_maps(
        self, query: str, location: str, max_results: int = 20
    ) -> list[dict]:
        """
        Search Google Maps via SERP API.

        Args:
            query: Search query (e.g., "restaurants")
            location: Location to search in (e.g., "Melbourne")
            max_results: Maximum results to return (default 20)

        Returns:
            List of business results with name, phone, website, address, rating, etc.

        Cost: $0.0015 AUD per request
        """
        encoded_query = urllib.parse.quote(f"{query} {location}")
        url = f"https://www.google.com/maps/search/{encoded_query}?brd_json=1"

        result = await self._serp_request(url)

        # Extract business results (limit to max_results)
        # Response format: {"status_code": 200, "body": "{\"organic\": [...]}"}
        if isinstance(result, dict) and "body" in result:
            try:
                body = json.loads(result["body"])
                return body.get("organic", [])[:max_results]
            except (json.JSONDecodeError, KeyError, TypeError):
                return []
        elif isinstance(result, list):
            return result[:max_results]
        elif isinstance(result, dict) and "organic" in result:
            return result["organic"][:max_results]

        return []

    async def search_google(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search Google via SERP API.

        Args:
            query: Search query (e.g., 'site:linkedin.com/company "business name"')
            max_results: Maximum results to return (default 10)

        Returns:
            List of organic search results

        Cost: $0.0015 AUD per request
        """
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}&brd_json=1"

        result = await self._serp_request(url)

        # Parse response body - handle both "organic" and "results" keys
        if isinstance(result, dict) and "body" in result:
            try:
                body = json.loads(result["body"])
                # Handle both formats from Bright Data SERP
                if "organic" in body:
                    return body["organic"][:max_results]
                elif "results" in body:
                    # Filter for organic type results
                    organic = [r for r in body["results"] if r.get("type") == "organic"]
                    return organic[:max_results]
                return []
            except (json.JSONDecodeError, KeyError, TypeError):
                return []
        elif isinstance(result, dict) and "organic" in result:
            return result["organic"][:max_results]
        elif isinstance(result, dict) and "results" in result:
            organic = [r for r in result["results"] if r.get("type") == "organic"]
            return organic[:max_results]

        return []

    async def _serp_request(self, url: str, max_retries: int = 2) -> Any:
        """Execute SERP API request via Direct API with Bearer token auth."""
        # Use Direct API endpoint with Bearer token (not proxy format)
        # serp_api1 zone uses: Authorization: Bearer {api_key}
        api_endpoint = "https://api.brightdata.com/request"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        client = await self._get_client()
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Direct API request with URL in body
                response = await client.post(
                    api_endpoint,
                    headers=headers,
                    json={
                        "zone": self.serp_zone,
                        "url": url,
                        "format": "json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                self.costs.serp_requests += 1

                logger.debug("serp_request_complete", url=url[:100], status=response.status_code)
                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                logger.warning("serp_request_error", attempt=attempt, error=last_error)
            except httpx.RequestError as e:
                last_error = str(e)
                logger.warning("serp_request_error", attempt=attempt, error=last_error)
            except Exception as e:
                last_error = str(e)
                logger.warning("serp_request_error", attempt=attempt, error=last_error)

            if attempt < max_retries:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        # All retries exhausted - fire alert
        await self._fire_bright_data_alert(last_error, max_retries + 1)
        raise BrightDataError(f"SERP request failed after {max_retries + 1} attempts: {last_error}")

    async def _fire_bright_data_alert(self, error_message: str, retry_count: int) -> None:
        """Fire alert for Bright Data failure (Directive 048 Part F)."""
        try:
            from src.integrations.supabase import get_db_session
            from src.services.alert_service import get_alert_service

            async with get_db_session() as db:
                alert_service = get_alert_service(db)
                await alert_service.alert_bright_data_error(
                    error_message=error_message,
                    retry_count=retry_count,
                    metadata={"api_type": "serp"},
                )
        except Exception as e:
            logger.error("failed_to_fire_bright_data_alert", error=str(e))

    # Scrapers API Methods

    async def scrape_linkedin_company(self, linkedin_url: str) -> dict:
        """
        Scrape LinkedIn Company via Scrapers API.

        Args:
            linkedin_url: LinkedIn company URL

        Returns:
            Company profile with name, industry, employees[], updates[], etc.

        Cost: $0.0015 AUD per record
        """
        results = await self._scraper_request(
            DATASET_IDS["linkedin_company"], [{"url": linkedin_url}]
        )
        return results[0] if results else {}

    async def scrape_linkedin_profile(self, linkedin_url: str) -> dict:
        """
        Scrape LinkedIn People Profile via Scrapers API.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            Person profile with name, experience, education, skills, etc.

        Cost: $0.0015 AUD per record
        """
        results = await self._scraper_request(
            DATASET_IDS["linkedin_people"], [{"url": linkedin_url}]
        )
        return results[0] if results else {}

    async def scrape_linkedin_jobs(
        self, keyword: str, location: str, country: str = "AU"
    ) -> list[dict]:
        """
        Discover LinkedIn Jobs via keyword search.

        Args:
            keyword: Job keyword (e.g., "marketing")
            location: Location (e.g., "Melbourne")
            country: Country code (default: "AU")

        Returns:
            List of job postings

        Cost: $0.0015 AUD per record
        """
        return await self._scraper_request(
            DATASET_IDS["linkedin_jobs"],
            [{"keyword": keyword, "location": location, "country": country}],
            discover_by="keyword",
        )

    async def _scraper_request(
        self, dataset_id: str, inputs: list[dict], discover_by: str = None
    ) -> list[dict]:
        """Execute Scraper API: trigger → poll → download."""
        base_url = "https://api.brightdata.com/datasets/v3"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        # Build trigger URL
        trigger_url = f"{base_url}/trigger?dataset_id={dataset_id}&include_errors=true"
        if discover_by:
            trigger_url += f"&type=discover_new&discover_by={discover_by}"

        client = await self._get_client()

        # Trigger
        try:
            response = await client.post(trigger_url, headers=headers, json=inputs, timeout=30.0)
            response.raise_for_status()
            snapshot_id = response.json()["snapshot_id"]
            logger.info("scraper_triggered", snapshot_id=snapshot_id, dataset_id=dataset_id)
        except httpx.HTTPStatusError as e:
            raise BrightDataError(f"Scraper trigger failed: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise BrightDataError(f"Scraper trigger failed: {str(e)}")

        # Poll until ready (max 5 minutes)
        for _ in range(60):
            try:
                progress = await client.get(
                    f"{base_url}/progress/{snapshot_id}", headers=headers, timeout=10.0
                )
                status_data = progress.json()
                status = status_data.get("status")

                if status == "ready":
                    records = status_data.get("records", 0)
                    self.costs.scraper_records += records
                    logger.info("scraper_ready", snapshot_id=snapshot_id, records=records)
                    break
                elif status == "failed":
                    raise BrightDataError(f"Scraper job failed: {status_data}")

            except httpx.RequestError:
                pass  # Retry on network errors

            await asyncio.sleep(5)
        else:
            raise BrightDataError(f"Scraper timeout for snapshot {snapshot_id}")

        # Download results
        try:
            data = await client.get(
                f"{base_url}/snapshot/{snapshot_id}?format=json", headers=headers, timeout=60.0
            )
            data.raise_for_status()
            return data.json()
        except httpx.HTTPStatusError as e:
            raise BrightDataError(f"Scraper download failed: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            raise BrightDataError(f"Scraper download failed: {str(e)}")

    # ============================================
    # SIEGE WATERFALL V3 METHODS (Directive #144)
    # ============================================

    async def discover_gmb_by_category(
        self, category: str, location: str, limit: int = 100
    ) -> list[dict]:
        """
        T0 GMB-first discovery via Bright Data Web Scraper API.

        Dataset: gd_m8ebnr0q2qlklc02fz
        Cost: $0.001/record

        Args:
            category: Business category (e.g., "plumber", "accountant")
            location: Location string (e.g., "Melbourne VIC", "Sydney NSW")
            limit: Maximum results to return

        Returns:
            List of business records with phone, website, address, rating, etc.
        """
        results = await self._scraper_request(
            DATASET_IDS["gmb_business"],
            [{"keyword": category, "country": "AU"}],
            discover_by="location",
        )

        # Track GMB-specific cost
        records_returned = min(len(results), limit)
        self.costs.scraper_records += records_returned

        logger.info(
            "gmb_discovery_complete",
            category=category,
            location=location,
            records=records_returned,
            cost_aud=records_returned * COSTS_AUD["gmb_discovery"],
        )

        return results[:limit]

    async def scrape_gmb_reviews(self, place_id: str, limit: int = 20) -> list[dict]:
        """
        T2.5 GMB Reviews via Bright Data Web Scraper API.

        Dataset: gd_m8ebnr0q2qlklc02fz (reviews field)
        Cost: $0.001/record
        Gate: Propensity >= 70

        Args:
            place_id: Google Maps place_id
            limit: Maximum reviews to return

        Returns:
            List of review records with rating, text, date, etc.
        """
        results = await self._scraper_request(
            DATASET_IDS["gmb_reviews"],
            [{"place_id": place_id}],
        )

        if results and len(results) > 0:
            # Reviews are nested in the first result
            reviews = results[0].get("reviews", [])[:limit]
            logger.info(
                "gmb_reviews_complete",
                place_id=place_id,
                reviews_count=len(reviews),
                cost_aud=COSTS_AUD["gmb_reviews"],
            )
            return reviews

        return []

    async def scrape_linkedin_company_enriched(self, linkedin_url: str) -> dict:
        """
        T1.5 LinkedIn Company enrichment via Bright Data.

        Dataset: gd_l1vikfnt1wgvvqz95w
        Cost: $0.025/record
        Gate: ICP pass

        Returns company info + recent posts for T-DM2b.
        Checks _bulk_company_cache first (populated by scrape_linkedin_companies_bulk).

        Args:
            linkedin_url: LinkedIn company URL

        Returns:
            Company profile with posts field for T-DM2b (FREE reuse)
        """
        # Check bulk pre-fetch cache first (zero additional cost / latency)
        cache_key = linkedin_url.rstrip("/").lower()
        if cache_key in self._bulk_company_cache:
            logger.info("linkedin_company_bulk_cache_hit", url=linkedin_url)
            return self._bulk_company_cache[cache_key]

        results = await self._scraper_request(
            DATASET_IDS["linkedin_company"],
            [{"url": linkedin_url}],
        )

        if results:
            result = results[0] if results else {}
            logger.info(
                "linkedin_company_enriched",
                url=linkedin_url,
                has_posts=bool(result.get("updates", [])),
                cost_aud=COSTS_AUD["linkedin_company"],
            )
            return result

        return {}

    async def scrape_linkedin_companies_bulk(
        self,
        urls: list[str],
        batch_size: int = 500,
    ) -> list[dict]:
        """
        Bulk LinkedIn company enrichment via Bright Data.

        Sends up to batch_size URLs per _scraper_request call.
        Empirically tested: 500 URLs processed in parallel, ~60s per batch.
        For 1,250 URLs: 3 jobs × ~60s = ~3 min total.
        Cost: $0.0015/profile.

        Args:
            urls: LinkedIn company URLs to enrich
            batch_size: URLs per Bright Data job (default 500)

        Returns:
            List of company profile dicts
        """
        if not urls:
            return []

        all_results: list[dict] = []
        for i in range(0, len(urls), batch_size):
            batch = urls[i : i + batch_size]
            inputs = [{"url": url} for url in batch]
            batch_num = i // batch_size + 1
            try:
                results = await self._scraper_request(
                    DATASET_IDS["linkedin_company"],
                    inputs,
                )
                all_results.extend(results)
                logger.info(
                    "linkedin_bulk_complete",
                    batch=batch_num,
                    urls=len(batch),
                    profiles=len(results),
                )
            except Exception as e:
                logger.warning(f"LinkedIn bulk batch {batch_num} failed: {e}")

        return all_results

    async def scrape_linkedin_profile_enriched(self, linkedin_url: str) -> dict:
        """
        T-DM1 LinkedIn Profile enrichment via Bright Data.

        Dataset: gd_l1viktl72bvl7bjuj0
        Cost: $0.0015/record
        Gate: ICP pass

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            Person profile with experience, education, skills
        """
        results = await self._scraper_request(
            DATASET_IDS["linkedin_people"],
            [{"url": linkedin_url}],
        )

        if results:
            result = results[0] if results else {}
            logger.info(
                "linkedin_profile_enriched",
                url=linkedin_url,
                cost_aud=COSTS_AUD["linkedin_profile"],
            )
            return result

        return {}

    async def scrape_linkedin_posts_90d(self, linkedin_url: str, days: int = 90) -> list[dict]:
        """
        T-DM2 LinkedIn Posts (90 days) via Bright Data.

        Dataset: gd_l1viktl72bvl7bjuj0 (posts field from profile)
        Cost: $0.0015/record
        Gate: Propensity >= 70

        Args:
            linkedin_url: LinkedIn profile URL
            days: Days of posts to retrieve (default 90)

        Returns:
            List of posts from the last N days
        """
        from datetime import UTC, datetime, timedelta

        results = await self._scraper_request(
            DATASET_IDS["linkedin_people"],
            [{"url": linkedin_url}],
        )

        if results and len(results) > 0:
            profile = results[0]
            posts = profile.get("posts", []) or profile.get("updates", [])

            # Filter to last N days
            cutoff = datetime.now(UTC) - timedelta(days=days)
            filtered_posts = []

            for post in posts:
                post_date_str = post.get("posted_date") or post.get("date")
                if post_date_str:
                    try:
                        # Parse ISO date
                        post_date = datetime.fromisoformat(post_date_str[:10])
                        if post_date >= cutoff:
                            filtered_posts.append(post)
                    except (ValueError, TypeError):
                        # Include if we can't parse date
                        filtered_posts.append(post)
                else:
                    filtered_posts.append(post)

            logger.info(
                "linkedin_posts_90d_complete",
                url=linkedin_url,
                posts_count=len(filtered_posts),
                cost_aud=COSTS_AUD["linkedin_posts"],
            )
            return filtered_posts

        return []

    async def scrape_x_posts_90d(self, x_handle: str, days: int = 90) -> list[dict]:
        """
        T-DM3 X/Twitter Posts (90 days) via Bright Data.

        Dataset: gd_lwdb4vjm1qvm96sbq2
        Cost: $0.0025/record
        Gate: Propensity >= 70

        Args:
            x_handle: X/Twitter handle (with or without @)
            days: Days of posts to retrieve (default 90)

        Returns:
            List of tweets/posts from the last N days
        """
        from datetime import UTC, datetime, timedelta

        # Normalize handle
        handle = x_handle.lstrip("@")

        results = await self._scraper_request(
            DATASET_IDS["x_posts"],
            [{"handle": handle}],
            discover_by="keyword",
        )

        if results:
            # Filter to last N days
            cutoff = datetime.now(UTC) - timedelta(days=days)
            filtered_posts = []

            for post in results:
                post_date_str = post.get("created_at") or post.get("date")
                if post_date_str:
                    try:
                        post_date = datetime.fromisoformat(post_date_str[:10])
                        if post_date >= cutoff:
                            filtered_posts.append(post)
                    except (ValueError, TypeError):
                        filtered_posts.append(post)
                else:
                    filtered_posts.append(post)

            logger.info(
                "x_posts_90d_complete",
                handle=handle,
                posts_count=len(filtered_posts),
                cost_aud=COSTS_AUD["x_posts"],
            )
            return filtered_posts

        return []

    # Cost tracking methods

    def get_total_cost(self) -> float:
        """Return total AUD spent this session."""
        return self.costs.total_aud

    def get_cost_breakdown(self) -> dict[str, Any]:
        """Return costs by method/tier."""
        return {
            "serp_requests": self.costs.serp_requests,
            "serp_cost_aud": self.costs.serp_requests * COSTS_AUD["serp_request"],
            "scraper_records": self.costs.scraper_records,
            "scraper_cost_aud": self.costs.scraper_records * COSTS_AUD["scraper_record"],
            "total_aud": self.costs.total_aud,
        }


# ============================================
# FACTORY FUNCTION
# ============================================

# Module-level singleton
_bright_data_client: BrightDataClient | None = None


def get_bright_data_client() -> BrightDataClient:
    """
    Get or create BrightDataClient singleton instance.

    Returns:
        BrightDataClient instance

    Raises:
        ValueError: If BRIGHTDATA_API_KEY not configured
    """
    global _bright_data_client
    if _bright_data_client is None:
        api_key = os.getenv("BRIGHTDATA_API_KEY")
        if not api_key:
            raise ValueError("BRIGHTDATA_API_KEY not set")
        _bright_data_client = BrightDataClient(api_key=api_key)
    return _bright_data_client
