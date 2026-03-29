# FILE: src/clients/dfs_labs_client.py
# PURPOSE: DataForSEO Labs + Domain Analytics client for pipeline v4 discovery/intelligence
# PHASE: Pipeline v4 — Stages 1 & 2
# DEPENDENCIES: httpx, tenacity, src.config.settings
# DIRECTIVE: #255

"""
DFS Labs Client — Directive #255
Wraps 7 DataForSEO endpoints for pipeline v4 discovery and intelligence.
"""

import base64
import logging
import time
from datetime import date, timedelta
from decimal import Decimal

import httpx
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ============================================
# Module-level Constants
# ============================================

DFS_BASE_URL = "https://api.dataforseo.com"

DFS_STATUS_SUCCESS = 20000
DFS_STATUS_AUTH_FAILURE = 40200
DFS_STATUS_NO_DATA = 40501

AUD_RATE = Decimal("1.55")


# ============================================
# Custom Exceptions
# ============================================


class DFSAuthError(Exception):
    """Raised when DataForSEO authentication fails."""

    pass


# ============================================
# Client
# ============================================


class DFSLabsClient:
    """
    Async client for DataForSEO Labs and Domain Analytics APIs.

    Wraps 7 endpoints for pipeline v4 discovery and intelligence:
    - get_categories()             — FREE, cached
    - domains_by_technology()      — $0.015/call, S1 Source A discovery
    - competitors_domain()         — $0.011/call, S1 Source B discovery
    - domain_rank_overview()       — $0.010/call, S2 budget/traffic signal
    - domain_technologies()        — $0.010/call, S2 tech stack detection
    - keywords_for_site()          — $0.011/call, keyword intelligence
    - historical_rank_overview()   — $0.106/call, trend signal (EXPENSIVE — gate callers)
    """

    def __init__(self, login: str, password: str) -> None:
        self.login = login
        self.password = password
        self._client: httpx.AsyncClient | None = None

        # Pre-compute Basic Auth header
        credentials = f"{self.login}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"

        # Per-endpoint cost counters
        self._cost_domains_by_technology = Decimal("0")
        self._cost_competitors_domain = Decimal("0")
        self._cost_domain_rank_overview = Decimal("0")
        self._cost_domain_technologies = Decimal("0")
        self._cost_keywords_for_site = Decimal("0")
        self._cost_historical_rank_overview = Decimal("0")
        # Layer 2 discovery endpoints (Directive #272)
        self._cost_domain_metrics_by_categories = Decimal("0")
        self._cost_google_ads_advertisers = Decimal("0")
        self._cost_domains_by_html_terms = Decimal("0")
        self._cost_google_jobs_advertisers = Decimal("0")
        # Layer 3 bulk filter endpoint (Directive #274)
        self._cost_bulk_domain_metrics = Decimal("0")
        # SERP LinkedIn people lookup (Directive #287)
        self._cost_search_linkedin_people = Decimal("0")
        # SERP Google Maps GMB lookup (Directive #290)
        self._cost_maps_search_gmb = Decimal("0")
        # Ads Search by domain (Directive #291)
        self._cost_ads_search_by_domain = Decimal("0")

        # Cache for get_categories (free, rarely changes)
        self._categories_cache: list[dict] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init httpx.AsyncClient with Basic Auth header."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=DFS_BASE_URL,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def total_cost_usd(self) -> float:
        """Total API cost in USD for this client instance."""
        total = (
            self._cost_domains_by_technology
            + self._cost_competitors_domain
            + self._cost_domain_rank_overview
            + self._cost_domain_technologies
            + self._cost_keywords_for_site
            + self._cost_historical_rank_overview
            + self._cost_domain_metrics_by_categories
            + self._cost_google_ads_advertisers
            + self._cost_domains_by_html_terms
            + self._cost_google_jobs_advertisers
            + self._cost_bulk_domain_metrics
            + self._cost_search_linkedin_people
            + self._cost_maps_search_gmb
            + self._cost_ads_search_by_domain
        )
        return float(total)

    @property
    def total_cost_aud(self) -> float:
        """Total API cost in AUD for this client instance."""
        total_usd = (
            self._cost_domains_by_technology
            + self._cost_competitors_domain
            + self._cost_domain_rank_overview
            + self._cost_domain_technologies
            + self._cost_keywords_for_site
            + self._cost_historical_rank_overview
            + self._cost_domain_metrics_by_categories
            + self._cost_google_ads_advertisers
            + self._cost_domains_by_html_terms
            + self._cost_google_jobs_advertisers
            + self._cost_bulk_domain_metrics
            + self._cost_search_linkedin_people
            + self._cost_maps_search_gmb
            + self._cost_ads_search_by_domain
        )
        return float(total_usd * AUD_RATE)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _post(
        self,
        endpoint: str,
        payload: list,
        cost_per_call: Decimal,
        cost_attr: str,
        swallow_no_data: bool = True,
    ) -> dict:
        """
        POST to a DataForSEO endpoint with retry, cost tracking, and error handling.

        Args:
            endpoint: API endpoint path (e.g. /v3/dataforseo_labs/google/...)
            payload: Request payload list
            cost_per_call: USD cost to add to counter
            cost_attr: Name of the instance attribute to accumulate cost into

        Returns:
            tasks[0].result[0] or empty dict

        Raises:
            DFSAuthError: If DFS returns auth failure status
            httpx.HTTPStatusError: On 429/500/502/503 (triggers tenacity retry)
        """
        client = await self._get_client()
        t0 = time.monotonic()
        response = await client.post(endpoint, json=payload)
        elapsed = time.monotonic() - t0

        # Trigger tenacity retry on transient HTTP errors
        if response.status_code in (429, 500, 502, 503):
            response.raise_for_status()

        response.raise_for_status()
        data = response.json()

        tasks = data.get("tasks", [])
        if not tasks:
            logger.warning(f"DFS {endpoint}: no tasks in response")
            return {}

        task = tasks[0]
        dfs_status = task.get("status_code")
        dfs_message = task.get("status_message", "")

        # Auth failure
        if dfs_status == DFS_STATUS_AUTH_FAILURE:
            raise DFSAuthError(f"DataForSEO authentication failed: {dfs_message}")

        # No data / invalid field (40501)
        if dfs_status == DFS_STATUS_NO_DATA:
            if not swallow_no_data:
                raise ValueError(
                    f"DFS {endpoint}: 40501 Invalid Field — {dfs_message}. "
                    "This is a programming error (bad payload), not a missing-data condition."
                )
            logger.info(
                f"DFS {endpoint}: 40501 no data (expected for unknown domains), "
                f"elapsed={elapsed:.2f}s"
            )
            return {"items": [], "total_count": 0}

        # Accumulate cost
        current = getattr(self, cost_attr, Decimal("0"))
        setattr(self, cost_attr, current + cost_per_call)

        logger.info(
            f"DFS {endpoint}: status={dfs_status}, cost_usd={cost_per_call}, elapsed={elapsed:.2f}s"
        )

        result = task.get("result") or []
        return result[0] if result else {}

    # ============================================
    # ENDPOINT 1: get_categories
    # ============================================

    async def get_categories(self) -> list[dict]:
        """
        Fetch DataForSEO Labs categories (FREE, cached after first call).

        Returns:
            List of dicts with category_code and category_name.
        """
        if self._categories_cache is not None:
            return self._categories_cache

        client = await self._get_client()
        response = await client.get("/v3/dataforseo_labs/categories")
        response.raise_for_status()
        data = response.json()

        tasks = data.get("tasks", [])
        if not tasks:
            return []

        task = tasks[0]
        dfs_status = task.get("status_code")
        if dfs_status == DFS_STATUS_AUTH_FAILURE:
            raise DFSAuthError("DataForSEO authentication failed")

        result = task.get("result") or []
        categories = result[0] if result else []

        # Normalize to list of {category_code, category_name}
        if isinstance(categories, list):
            self._categories_cache = categories
        elif isinstance(categories, dict):
            # Some DFS endpoints wrap in a dict
            self._categories_cache = list(categories.values()) if categories else []
        else:
            self._categories_cache = []

        logger.info(f"DFS categories: fetched {len(self._categories_cache)} categories")
        return self._categories_cache

    # ============================================
    # ENDPOINT 2: domains_by_technology
    # ============================================

    async def domains_by_technology(
        self,
        technology_name: str,
        country: str = "Australia",
        limit: int = 100,
        offset: int = 0,
        filters: list | None = None,
    ) -> dict:
        """
        Find domains using a specific technology in a given country.

        Cost: $0.015 USD per call

        Args:
            technology_name: Technology to search for (e.g. "HubSpot")
            country: Country name (default "Australia")
            limit: Max results (default 100)
            offset: Pagination offset (default 0)
            filters: Optional DFS filter list

        Returns:
            {"total_count": int, "items": [{"domain": str, "title": str,
              "description": str, "technologies": dict}]}
        """
        payload_item: dict = {
            "technologies": [technology_name],
            "country_iso_code": "AU",
            "limit": limit,
            "offset": offset,
        }
        if filters:
            payload_item["filters"] = filters

        result = await self._post(
            endpoint="/v3/domain_analytics/technologies/domains_by_technology/live",
            payload=[payload_item],
            cost_per_call=Decimal("0.015"),
            cost_attr="_cost_domains_by_technology",
        )

        items = result.get("items") or []
        total_count = result.get("total_count", 0)

        return {
            "total_count": total_count,
            "items": [
                {
                    "domain": item.get("domain"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "technologies": item.get("technologies", {}),
                }
                for item in items
            ],
        }

    # ============================================
    # ENDPOINT 3: competitors_domain
    # ============================================

    async def competitors_domain(
        self,
        target_domain: str,
        location_code: int = 2036,
        language_code: str = "en",
        limit: int = 100,
        filters: list | None = None,
    ) -> dict:
        """
        Find competitor domains sharing organic keywords with the target.

        Cost: $0.011 USD per call

        Args:
            target_domain: Domain to find competitors for
            location_code: DFS location code (default 2036 = Australia)
            language_code: Language code (default "en")
            limit: Max results (default 100)
            filters: Optional DFS filter list

        Returns:
            {"items": [{"domain": str, "avg_position": float, "intersections": int,
              "full_domain_metrics": {"organic": {...}, "paid": {...}}}]}
        """
        payload_item: dict = {
            "target": target_domain,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
        }
        if filters:
            payload_item["filters"] = filters

        result = await self._post(
            endpoint="/v3/dataforseo_labs/google/competitors_domain/live",
            payload=[payload_item],
            cost_per_call=Decimal("0.011"),
            cost_attr="_cost_competitors_domain",
        )

        items = result.get("items") or []
        return {
            "items": [
                {
                    "domain": item.get("domain"),
                    "avg_position": item.get("avg_position"),
                    "intersections": item.get("intersections"),
                    "full_domain_metrics": item.get("full_domain_metrics", {}),
                }
                for item in items
            ]
        }

    # ============================================
    # ENDPOINT 4: domain_rank_overview
    # ============================================

    async def domain_rank_overview(
        self,
        target_domain: str,
        location_code: int = 2036,
        language_code: str = "en",
    ) -> dict | None:
        """
        Get organic and paid traffic overview for a domain.

        Cost: $0.010 USD per call

        CRITICAL: result path is tasks[0].result[0].items[0], NOT tasks[0].result[0]

        Args:
            target_domain: Domain to fetch overview for
            location_code: DFS location code (default 2036 = Australia)
            language_code: Language code (default "en")

        Returns:
            Dict with 8 mapped SEO metric fields, or None if domain not indexed.
        """
        result = await self._post(
            endpoint="/v3/dataforseo_labs/google/domain_rank_overview/live",
            payload=[
                {
                    "target": target_domain,
                    "location_code": location_code,
                    "language_code": language_code,
                }
            ],
            cost_per_call=Decimal("0.010"),
            cost_attr="_cost_domain_rank_overview",
        )

        # CRITICAL: result is tasks[0].result[0], but metrics are in .items[0]
        items = result.get("items") or []
        if not items:
            logger.info(f"DFS domain_rank_overview: no data for {target_domain}")
            return None

        item = items[0]
        metrics = item.get("metrics", {})
        organic = metrics.get("organic", {})
        paid = metrics.get("paid", {})

        return {
            "dfs_organic_etv": organic.get("etv"),
            "dfs_paid_etv": paid.get("etv"),
            "dfs_organic_keywords": organic.get("count"),
            "dfs_paid_keywords": paid.get("count"),
            "dfs_organic_pos_1": organic.get("pos_1"),
            "dfs_organic_pos_2_3": organic.get("pos_2_3"),
            "dfs_organic_pos_4_10": organic.get("pos_4_10"),
            "dfs_organic_pos_11_20": organic.get("pos_11_20"),
        }

    # ============================================
    # ENDPOINT 5: domain_technologies
    # ============================================

    async def domain_technologies(self, target_domain: str) -> dict | None:
        """
        Get the technology stack for a domain.

        Cost: $0.010 USD per call (may make 2 calls for www. fallback)

        GOTCHA: Redirected domains fail. Falls back to www. prefix if bare domain
        returns no technologies.

        The technologies response is a NESTED DICT by category:
        {"servers": {"web_servers": ["Nginx"]}, "analytics": {...}}

        Args:
            target_domain: Domain to detect technologies for

        Returns:
            {"tech_stack": [str], "tech_categories": dict, "tech_stack_depth": int}
            or None if no technologies detected after both attempts.
        """

        async def _fetch_technologies(domain: str) -> dict | None:
            result = await self._post(
                endpoint="/v3/domain_analytics/technologies/domain_technologies/live",
                payload=[{"target": domain}],
                cost_per_call=Decimal("0.010"),
                cost_attr="_cost_domain_technologies",
            )
            tech_categories = result.get("technologies")
            if not tech_categories:
                return None
            return tech_categories

        # First attempt: bare domain
        tech_categories = await _fetch_technologies(target_domain)

        # Fallback: try www. prefix if bare domain returned nothing
        if tech_categories is None and not target_domain.startswith("www."):
            www_domain = f"www.{target_domain}"
            logger.info(
                f"DFS domain_technologies: no data for {target_domain}, retrying with {www_domain}"
            )
            tech_categories = await _fetch_technologies(www_domain)

        if not tech_categories:
            logger.info(f"DFS domain_technologies: no technologies for {target_domain}")
            return None

        # Flatten nested dict: {"servers": {"web_servers": ["Nginx"]}} → ["Nginx"]
        all_techs: list[str] = []
        for _category, subcategories in tech_categories.items():
            if isinstance(subcategories, dict):
                for _subcat, tech_list in subcategories.items():
                    if isinstance(tech_list, list):
                        all_techs.extend(tech_list)
            elif isinstance(subcategories, list):
                all_techs.extend(subcategories)

        unique_techs = list(dict.fromkeys(all_techs))  # preserve order, deduplicate

        return {
            "tech_stack": unique_techs,
            "tech_categories": tech_categories,
            "tech_stack_depth": len(unique_techs),
        }

    # ============================================
    # ENDPOINT 6: keywords_for_site
    # ============================================

    async def keywords_for_site(
        self,
        target_domain: str,
        location_code: int = 2036,
        language_code: str = "en",
        limit: int = 100,
        filters: list | None = None,
    ) -> dict:
        """
        Get organic keywords for a domain.

        Cost: $0.011 USD per call

        Args:
            target_domain: Domain to fetch keywords for
            location_code: DFS location code (default 2036 = Australia)
            language_code: Language code (default "en")
            limit: Max results (default 100)
            filters: Optional DFS filter list (NO order_by support)

        Returns:
            {"items": [{"keyword": str, "search_volume": int, "cpc": float,
              "competition": float, "position": int}]}
        """
        payload_item: dict = {
            "target": target_domain,
            "location_code": location_code,
            "language_code": language_code,
            "limit": limit,
        }
        if filters:
            payload_item["filters"] = filters

        result = await self._post(
            endpoint="/v3/dataforseo_labs/google/keywords_for_site/live",
            payload=[payload_item],
            cost_per_call=Decimal("0.011"),
            cost_attr="_cost_keywords_for_site",
        )

        items = result.get("items") or []
        mapped_items = []
        for item in items:
            keyword_info = item.get("keyword_info") or {}
            serp_info = item.get("serp_info") or {}
            serp_items = serp_info.get("serp") or []
            # position: first SERP item's rank_group
            position = serp_items[0].get("rank_group") if serp_items else None

            mapped_items.append(
                {
                    "keyword": item.get("keyword"),
                    "search_volume": keyword_info.get("search_volume"),
                    "cpc": keyword_info.get("cpc"),
                    "competition": keyword_info.get("competition"),
                    "position": position,
                }
            )

        return {"items": mapped_items}

    # ============================================
    # ENDPOINT 7: historical_rank_overview
    # ============================================

    async def historical_rank_overview(
        self,
        target_domain: str,
        location_code: int = 2036,
        language_code: str = "en",
    ) -> dict | None:
        """
        Get historical monthly rank data for a domain.

        Cost: $0.106 USD per call — EXPENSIVE. Callers must gate this.

        Args:
            target_domain: Domain to fetch history for
            location_code: DFS location code (default 2036 = Australia)
            language_code: Language code (default "en")

        Returns:
            {"items": [{"year": int, "month": int, "metrics": {...}}]}
            or None if no history available.
        """
        result = await self._post(
            endpoint="/v3/dataforseo_labs/google/historical_rank_overview/live",
            payload=[
                {
                    "target": target_domain,
                    "location_code": location_code,
                    "language_code": language_code,
                }
            ],
            cost_per_call=Decimal("0.106"),
            cost_attr="_cost_historical_rank_overview",
        )

        items = result.get("items") or []
        if not items:
            logger.info(f"DFS historical_rank_overview: no history for {target_domain}")
            return None

        return {
            "items": [
                {
                    "year": item.get("year"),
                    "month": item.get("month"),
                    "metrics": item.get("metrics", {}),
                }
                for item in items
            ]
        }

    # ============================================
    # ENDPOINT 8: domain_metrics_by_categories  (Directive #272 — Layer 2)
    # ============================================

    async def domain_metrics_by_categories(
        self,
        category_codes: list[int],
        location_name: str = "Australia",
        paid_etv_min: float = 0.0,
        first_date: str | None = None,
        second_date: str | None = None,
    ) -> list[dict]:
        """
        Discover domains with Google Ads spend in specified categories.
        Uses location_name (NOT location_code — causes 40501 error per DFS gotcha).
        Cost: ~$0.10/call.
        Returns list of {"domain": str, "paid_etv": float, "organic_etv": float}.

        Args:
            first_date: Start date YYYY-MM-DD (default: 6 months ago / today - 180 days).
            second_date: End date YYYY-MM-DD (default: today).
        """
        today = date.today()
        resolved_first_date = first_date or (today - timedelta(days=180)).strftime("%Y-%m-%d")
        resolved_second_date = second_date or today.strftime("%Y-%m-%d")

        result = await self._post(
            endpoint="/v3/dataforseo_labs/google/domain_metrics_by_categories/live",
            payload=[
                {
                    "category_codes": category_codes,
                    "location_name": location_name,
                    "language_name": "English",
                    "first_date": resolved_first_date,
                    "second_date": resolved_second_date,
                    "filters": [["metrics.organic.etv", ">", 0]],
                }
            ],
            cost_per_call=Decimal("0.10"),
            cost_attr="_cost_domain_metrics_by_categories",
            swallow_no_data=False,
        )
        items = result.get("items") or []
        results = []
        for item in items:
            metrics = item.get("metrics", {})
            paid_etv = (metrics.get("paid") or {}).get("etv", 0) or 0
            organic_etv = (metrics.get("organic") or {}).get("etv", 0) or 0
            if paid_etv >= paid_etv_min:
                domain = item.get("domain") or item.get("target")
                if domain:
                    results.append(
                        {"domain": domain, "paid_etv": paid_etv, "organic_etv": organic_etv}
                    )
        return results

    # ============================================
    # ENDPOINT 9: google_ads_advertisers  (Directive #272 — Layer 2)
    # ============================================

    async def google_ads_advertisers(
        self,
        keyword: str,
        location_name: str = "Australia",
    ) -> list[dict]:
        """
        Find domains currently bidding on a keyword via Google Ads SERP.
        Cost: ~$0.006/call.
        Returns list of {"domain": str, "title": str, "url": str}.
        TODO: verify payload format against DFS API docs before live run.
        """
        from urllib.parse import urlparse

        result = await self._post(
            endpoint="/v3/serp/google/ads/live/advanced",
            payload=[
                {
                    "keyword": keyword,
                    "location_name": location_name,
                    "language_name": "English",
                    "depth": 100,
                }
            ],
            cost_per_call=Decimal("0.006"),
            cost_attr="_cost_google_ads_advertisers",
        )
        items = result.get("items") or []
        results = []
        for item in items:
            url = item.get("url") or item.get("domain")
            if not url:
                continue
            parsed = urlparse(url)
            domain = parsed.netloc or url
            if domain.startswith("www."):
                domain = domain[4:]
            results.append(
                {
                    "domain": domain.lower().rstrip("/"),
                    "title": item.get("title", ""),
                    "url": url,
                }
            )
        return results

    # ============================================
    # ENDPOINT 9c: maps_search_gmb  (Directive #290)
    # ============================================

    async def maps_search_gmb(
        self,
        business_name: str,
        location_name: str = "Australia",
    ) -> dict | None:
        """
        Search DFS SERP Google Maps for a business GMB listing.
        Endpoint: /v3/serp/google/maps/live/advanced
        Cost: $0.0035/call.
        Returns dict with gmb_review_count, gmb_rating, etc. or None.
        """
        result = await self._post(
            endpoint="/v3/serp/google/maps/live/advanced",
            payload=[
                {
                    "keyword": business_name,
                    "location_name": location_name,
                    "language_name": "English",
                    "depth": 1,
                }
            ],
            cost_per_call=Decimal("0.0035"),
            cost_attr="_cost_maps_search_gmb",
        )
        items = result.get("items") or []
        if not items:
            return None
        item = items[0]
        return {
            "gmb_place_id": item.get("place_id"),
            "gmb_rating": item.get("rating"),
            "gmb_review_count": item.get("rating_count") or item.get("reviews_count") or 0,
            "gmb_address": item.get("address"),
            "gmb_phone": item.get("phone"),
            "gmb_found": True,
        }

    # ============================================
    # ENDPOINT 9d: ads_search_by_domain  (Directive #291)
    # ============================================

    async def ads_search_by_domain(
        self,
        domain: str,
        location_name: str = "Australia",
    ) -> dict | None:
        """
        Check if a domain is running Google Ads via Ads Transparency endpoint.
        Endpoint: /v3/serp/google/ads_search/live/advanced
        Cost: $0.002/call.
        Status 40102 = no ads found (not an error).
        Returns dict with is_running_ads, ad_count, formats, first_shown, last_shown
        or None on error.
        """
        try:
            result = await self._post(
                endpoint="/v3/serp/google/ads_search/live/advanced",
                payload=[
                    {
                        "target": domain,
                        "location_name": location_name,
                        "language_name": "English",
                    }
                ],
                cost_per_call=Decimal("0.002"),
                cost_attr="_cost_ads_search_by_domain",
            )
        except Exception as exc:
            logger.warning("ads_search_by_domain error for %s: %s", domain, exc)
            return None

        items = result.get("items") or []
        if not items:
            return {
                "is_running_ads": False,
                "ad_count": 0,
                "formats": [],
                "first_shown": None,
                "last_shown": None,
            }

        dates = []
        formats = set()
        for item in items:
            formats.add(item.get("format") or item.get("type") or "unknown")
            for dk in ("first_shown", "date_from"):
                if item.get(dk):
                    dates.append(item[dk])
        # last_shown from first item (highest rank)
        last_shown = items[0].get("last_shown") or items[0].get("date_to")

        return {
            "is_running_ads": True,
            "ad_count": len(items),
            "formats": sorted(formats),
            "first_shown": min(dates) if dates else None,
            "last_shown": last_shown,
        }

    # ============================================
    # ENDPOINT 9b: search_linkedin_people  (Directive #287 — DM waterfall T-DM1)
    # ============================================

    async def search_linkedin_people(
        self,
        company_name: str,
        location_name: str = "Australia",
    ) -> list[dict]:
        """
        Search Google SERP for LinkedIn people profiles at a company.
        Query: site:linkedin.com/in "{company_name}"
        Cost: $0.01/call.
        Returns list of {"name": str, "title": str, "linkedin_url": str, "snippet": str}.
        """
        import re

        query = f'site:linkedin.com/in "{company_name}"'

        result = await self._post(
            endpoint="/v3/serp/google/organic/live/advanced",
            payload=[
                {
                    "keyword": query,
                    "location_name": location_name,
                    "language_name": "English",
                    "depth": 10,
                }
            ],
            cost_per_call=Decimal("0.01"),
            cost_attr="_cost_search_linkedin_people",
        )
        items = result.get("items") or []
        results = []
        for item in items:
            url = item.get("url") or ""
            if "linkedin.com/in/" not in url:
                continue
            title_raw = item.get("title") or ""
            snippet = item.get("description") or ""

            # LinkedIn profile titles: "Name - Job Title | LinkedIn"
            name = ""
            job_title = ""
            m = re.match(r"^([^|\u2013\-]+?)(?:\s*[-\u2013]\s*(.+?))?(?:\s*\|\s*LinkedIn.*)?$", title_raw.strip())
            if m:
                name = m.group(1).strip()
                job_title = (m.group(2) or "").strip()

            results.append(
                {
                    "name": name,
                    "title": job_title,
                    "linkedin_url": url,
                    "snippet": snippet,
                }
            )
        return results

    # ============================================
    # ENDPOINT 10: domains_by_html_terms  (Directive #272 — Layer 2)
    # ============================================

    async def domains_by_html_terms(
        self,
        include_term: str,
        exclude_term: str | None = None,
        location_name: str = "Australia",
    ) -> list[dict]:
        """
        Find domains that contain include_term but NOT exclude_term in their HTML.
        Cost: ~$0.01/call.
        Returns list of {"domain": str}.
        TODO: verify payload format against DFS API docs before live run.
        """
        payload_item: dict = {
            "include": [include_term],
            "location_name": location_name,
            "language_name": "English",
            "limit": 100,
        }
        if exclude_term:
            payload_item["exclude"] = [exclude_term]

        result = await self._post(
            endpoint="/v3/domain_analytics/technologies/domains_by_html_terms/live",
            payload=[payload_item],
            cost_per_call=Decimal("0.01"),
            cost_attr="_cost_domains_by_html_terms",
        )
        items = result.get("items") or []
        return [{"domain": item["domain"]} for item in items if item.get("domain")]

    # ============================================
    # ENDPOINT 11: google_jobs_advertisers  (Directive #272 — Layer 2)
    # ============================================

    async def google_jobs_advertisers(
        self,
        keyword: str,
        location_name: str = "Australia",
    ) -> list[dict]:
        """
        Find employers posting jobs for a keyword (growth signal — they have budget).
        Cost: ~$0.006/call.
        Returns list of {"domain": str, "employer_name": str}.
        TODO: verify payload format against DFS API docs before live run.
        """
        from urllib.parse import urlparse

        result = await self._post(
            endpoint="/v3/serp/google/jobs/live/advanced",
            payload=[
                {
                    "keyword": keyword,
                    "location_name": location_name,
                    "language_name": "English",
                    "depth": 100,
                }
            ],
            cost_per_call=Decimal("0.006"),
            cost_attr="_cost_google_jobs_advertisers",
        )
        items = result.get("items") or []
        results = []
        for item in items:
            url = item.get("url") or item.get("apply_link") or ""
            employer = item.get("employer_name") or item.get("company") or ""
            if not url and not employer:
                continue
            domain = ""
            if url:
                parsed = urlparse(url)
                domain = (parsed.netloc or "").removeprefix("www.").lower().rstrip("/")
            results.append({"domain": domain, "employer_name": employer})
        return [r for r in results if r["domain"]]

    # ============================================
    # ENDPOINT 12: bulk_domain_metrics  (Directive #274 — Layer 3)
    # ============================================

    async def bulk_domain_metrics(
        self,
        domains: list[str],
    ) -> list[dict]:
        """
        Fetch traffic + authority metrics for up to 1,000 domains in one call.
        Used by Layer 3 cheap filter to eliminate dead/parked domains.

        Cost: ~$0.001/domain (TBD — verify against DFS pricing).
        Batching: caller is responsible for passing ≤1000 domains per call.

        NOTE: Pricing TBD — directive says $0.02/batch-of-1000; Manual says $0.001/domain.
        Using $0.001/domain in cost tracking until verified against DFS API pricing page.

        Returns list of:
        {
            "domain": str,
            "organic_etv": float,      # estimated organic traffic value USD
            "paid_etv": float,         # estimated paid traffic value USD
            "backlinks_count": int,    # total backlinks
            "domain_rank": int,        # DFS domain rank score (0-100)
        }
        Missing fields default to 0.
        """
        if not domains:
            return []

        # TODO: verify exact endpoint path against DFS Labs API docs
        # Most likely: /v3/dataforseo_labs/google/bulk_traffic_estimation/live
        # Fallback if above fails: /v3/domain_analytics/whois/overview/live
        result = await self._post(
            endpoint="/v3/dataforseo_labs/google/bulk_traffic_estimation/live",
            payload=[
                {"targets": domains, "location_name": "Australia", "language_name": "English"}
            ],
            cost_per_call=Decimal("0.10")
            + Decimal(str(len(domains))) * Decimal("0.001"),  # $0.10/task + $0.001/domain
            cost_attr="_cost_bulk_domain_metrics",
        )
        items = result.get("items") or []
        results = []
        for item in items:
            metrics = item.get("metrics", {})
            organic = metrics.get("organic") or {}
            paid = metrics.get("paid") or {}
            results.append(
                {
                    "domain": item.get("target") or item.get("domain", ""),
                    "organic_etv": float(organic.get("etv") or 0),
                    "paid_etv": float(paid.get("etv") or 0),
                    "backlinks_count": int(
                        item.get("backlinks") or item.get("backlinks_count") or 0
                    ),
                    "domain_rank": int(item.get("domain_rank") or 0),
                }
            )
        return results

    # ============================================
    # Utility
    # ============================================

    @staticmethod
    def canonicalize_domain(domain: str) -> str:
        """
        Canonicalize a domain for storage.

        Strips protocol (https://, http://), trailing slashes, and www. prefix.
        Returns lowercase bare domain.

        Used for storage. API calls may add www. as needed
        (see domain_technologies fallback).

        Examples:
            "https://www.example.com.au/" → "example.com.au"
            "http://example.com" → "example.com"
            "example.com" → "example.com"
            "WWW.EXAMPLE.COM.AU" → "example.com.au"
        """
        domain = domain.strip().lower()
        # Strip protocol
        for prefix in ("https://", "http://"):
            if domain.startswith(prefix):
                domain = domain[len(prefix) :]
        # Strip trailing slashes
        domain = domain.rstrip("/")
        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain


# ============================================
# Module-level Singleton
# ============================================

_client: DFSLabsClient | None = None


def get_dfs_labs_client() -> DFSLabsClient:
    """Get or create the module-level DFSLabsClient singleton."""
    global _client
    if _client is None:
        _client = DFSLabsClient(
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
        )
    return _client


async def close_dfs_labs_client() -> None:
    """Close and clear the module-level DFSLabsClient singleton."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
