# FILE: src/clients/dfs_gmaps_client.py
# PURPOSE: DataForSEO Google Maps API client for Stage 0 GMB discovery
# PHASE: Pipeline Stage 0 — Business Discovery
# DEPENDENCIES: httpx, tenacity, src.config.settings, src.exceptions
# DIRECTIVE: #248

import asyncio
import base64
import logging
from decimal import Decimal
from urllib.parse import urlparse

import httpx
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError

logger = logging.getLogger(__name__)

# ============================================
# Module-level Constants
# ============================================

COST_PER_SEARCH_AUD = Decimal("0.003")  # $0.002 USD * ~1.55 AUD/USD

DFS_GMAPS_BASE_URL = "https://api.dataforseo.com/v3"
DFS_TASK_POST_ENDPOINT = "/serp/google/maps/task_post"
DFS_TASK_GET_ENDPOINT = "/serp/google/maps/task_get/advanced"

# DFS status codes
DFS_STATUS_SUCCESS = 20000
DFS_STATUS_IN_QUEUE = 20100
DFS_STATUS_AUTH_FAILURE = 40200
DFS_STATUS_INVALID_LOCATION = 40501

# Poll settings
TASK_POLL_MAX_ATTEMPTS = 10
TASK_POLL_INITIAL_WAIT_S = 2.0


# ============================================
# Custom Exceptions
# ============================================


class DFSInvalidLocationError(Exception):
    """Raised when DataForSEO rejects the location coordinates."""
    pass


class DFSAuthError(Exception):
    """Raised when DataForSEO authentication fails."""
    pass


# ============================================
# Client
# ============================================


class DFSGMapsClient:
    """
    Async client for the DataForSEO Google Maps SERP API.

    Used for Stage 0 business discovery — finding GMB listings
    by geographic coordinates and business category.

    API Costs (AUD):
    - Google Maps task_post + task_get: ~$0.003 AUD per search
    """

    def __init__(self, login: str, password: str) -> None:
        self.login = login
        self.password = password
        self._client: httpx.AsyncClient | None = None
        self.queries_made: int = 0

        # Pre-compute Basic Auth header
        credentials = f"{self.login}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init httpx.AsyncClient with Basic Auth header."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=DFS_GMAPS_BASE_URL,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def estimated_cost_aud(self) -> Decimal:
        """Estimated total API cost in AUD for this client instance."""
        return self.queries_made * COST_PER_SEARCH_AUD

    # --------------------------------------------------
    # Core discovery method
    # --------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def discover_by_coordinates(
        self,
        lat: float,
        lng: float,
        category: str,
        zoom: int = 14,
        depth: int = 100,
    ) -> list[dict]:
        """
        Discover GMB listings near a coordinate point for a given category.

        Posts a task to the DFS Google Maps SERP API and fetches results.

        Args:
            lat: Latitude of search centre
            lng: Longitude of search centre
            category: Business category keyword (e.g. "dentist")
            zoom: Google Maps zoom level (default 14)
            depth: Max results to retrieve (default 100)

        Returns:
            List of business dicts mapped to business_universe schema columns.

        Raises:
            DFSInvalidLocationError: DFS status 40501 — bad coordinates
            DFSAuthError: DFS status 40200 — auth failure
            APIError: Any other DFS non-success status
            httpx.HTTPStatusError: HTTP 429/500/502/503 (retried by tenacity)
        """
        client = await self._get_client()

        payload = [
            {
                "keyword": category,
                "location_coordinate": f"{lat},{lng},{zoom}z",
                "depth": depth,
                "language_code": "en",
                "os": "windows",
            }
        ]

        response = await client.post(DFS_TASK_POST_ENDPOINT, json=payload)

        if response.status_code in (429, 500, 502, 503):
            response.raise_for_status()  # triggers tenacity retry

        response.raise_for_status()
        data = response.json()

        # Validate DFS-level status
        tasks = data.get("tasks", [])
        if not tasks:
            raise APIError(
                service="dfs_gmaps",
                status_code=0,
                message="DFS task_post returned no tasks",
            )

        task = tasks[0]
        dfs_status = task.get("status_code")
        dfs_message = task.get("status_message", "")

        if dfs_status == DFS_STATUS_INVALID_LOCATION:
            raise DFSInvalidLocationError(f"Invalid location coordinates: {lat},{lng}")

        if dfs_status == DFS_STATUS_AUTH_FAILURE:
            raise DFSAuthError("DataForSEO authentication failed")

        if dfs_status not in (DFS_STATUS_SUCCESS, DFS_STATUS_IN_QUEUE):
            raise APIError(
                service="dfs_gmaps",
                status_code=dfs_status,
                message=f"DFS error {dfs_status}: {dfs_message}",
            )

        # Extract task_id
        task_data = (task.get("data") or {})
        task_id = task_data.get("id") or (
            (task.get("result") or [{}])[0].get("id")
        )

        # Fallback: id may sit directly on the task
        if not task_id:
            task_id = task.get("id")

        if not task_id:
            raise APIError(
                service="dfs_gmaps",
                status_code=dfs_status,
                message="DFS task_post did not return a task_id",
            )

        # Fetch results
        raw_items = await self.fetch_task_results(task_id)
        self.queries_made += 1

        results = [self.map_to_bu_columns(item) for item in raw_items]

        cost = self.estimated_cost_aud
        logger.info(
            f"DFS GMaps: {category} @ {lat},{lng} → {len(results)} results, cost AUD {cost}"
        )

        return results

    # --------------------------------------------------
    # Task result fetcher
    # --------------------------------------------------

    async def fetch_task_results(self, task_id: str) -> list[dict]:
        """
        Fetch results for a submitted DFS Google Maps task.

        Polls with exponential backoff if the task is still queued
        (DFS status 20100).

        Args:
            task_id: Task ID returned by task_post

        Returns:
            List of raw DFS item dicts, or [] if no results.
        """
        client = await self._get_client()
        wait_s = TASK_POLL_INITIAL_WAIT_S

        for attempt in range(1, TASK_POLL_MAX_ATTEMPTS + 1):
            response = await client.get(f"{DFS_TASK_GET_ENDPOINT}/{task_id}")
            response.raise_for_status()
            data = response.json()

            tasks = data.get("tasks", [])
            if not tasks:
                return []

            task = tasks[0]
            dfs_status = task.get("status_code")
            dfs_message = task.get("status_message", "")

            if dfs_status == DFS_STATUS_IN_QUEUE:
                if attempt < TASK_POLL_MAX_ATTEMPTS:
                    logger.debug(
                        f"DFS task {task_id} still queued (attempt {attempt}/{TASK_POLL_MAX_ATTEMPTS}), "
                        f"waiting {wait_s:.1f}s"
                    )
                    await asyncio.sleep(wait_s)
                    wait_s = min(wait_s * 2, 30.0)
                    continue
                else:
                    logger.warning(
                        f"DFS task {task_id} still queued after {TASK_POLL_MAX_ATTEMPTS} attempts"
                    )
                    return []

            if dfs_status != DFS_STATUS_SUCCESS:
                raise APIError(
                    service="dfs_gmaps",
                    status_code=dfs_status,
                    message=f"DFS error {dfs_status}: {dfs_message}",
                )

            result_list = task.get("result") or []
            if not result_list:
                return []

            items = result_list[0].get("items") or []
            return items

        return []

    # --------------------------------------------------
    # Field mapper
    # --------------------------------------------------

    def map_to_bu_columns(self, raw_item: dict) -> dict:
        """
        Map a raw DFS Google Maps item to business_universe schema columns.

        All fields are optional via .get() except gmb_place_id.
        Only non-None values are included in the returned dict.

        Args:
            raw_item: Raw dict from DFS task result items

        Returns:
            Dict of business_universe column → value (None values excluded).
        """
        url = raw_item.get("url")
        domain: str | None = None
        if url:
            parsed = urlparse(url)
            domain = parsed.netloc or None
            if domain and domain.startswith("www."):
                domain = domain[4:]

        mapping: dict = {
            "gmb_place_id": raw_item.get("place_id"),
            "display_name": raw_item.get("title"),
            "address": raw_item.get("address"),
            "phone": raw_item.get("phone"),
            "website": url,
            "domain": domain,
            "lat": raw_item.get("latitude"),
            "lng": raw_item.get("longitude"),
            "gmb_cid": raw_item.get("cid"),
            "gmb_rating": raw_item.get("rating", {}).get("value"),
            "gmb_review_count": raw_item.get("rating", {}).get("votes_count"),
            "gmb_category": raw_item.get("category"),
            "gmb_additional_categories": raw_item.get("additional_categories", []),
            "gmb_work_hours": raw_item.get("work_hours"),
            "gmb_total_photos": raw_item.get("total_photos"),
            "gmb_maps_url": raw_item.get("maps_url"),
            "discovery_source": "dfs_gmaps",
            "pipeline_stage": 0,
            "pipeline_status": "discovered",
        }

        # Exclude None values (but keep falsy non-None values like 0, [], "")
        return {k: v for k, v in mapping.items() if v is not None}


# ============================================
# Module-level Singleton
# ============================================

_client: DFSGMapsClient | None = None


def get_dfs_gmaps_client() -> DFSGMapsClient:
    """Get or create the module-level DFSGMapsClient singleton."""
    global _client
    if _client is None:
        _client = DFSGMapsClient(
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
        )
    return _client


async def close_dfs_gmaps_client() -> None:
    """Close and clear the module-level DFSGMapsClient singleton."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] File header comment block (matches dataforseo.py style)
# [x] DFSGMapsClient.__init__: stores creds, lazy client, queries_made counter
# [x] _get_client(): lazy init with Basic Auth header
# [x] close(): aclose httpx client
# [x] discover_by_coordinates(): POST task_post, extract task_id, fetch results
# [x] fetch_task_results(): GET task_get with poll+backoff (max 10, 2s initial)
# [x] map_to_bu_columns(): 19 fields mapped, None values excluded
# [x] estimated_cost_aud property: queries_made * COST_PER_SEARCH_AUD
# [x] COST_PER_SEARCH_AUD = Decimal("0.003")
# [x] Retry on 429/500/502/503 (tenacity, 3 attempts, exp backoff min 2s max 30s)
# [x] DFS 40501 → DFSInvalidLocationError
# [x] DFS 40200 → DFSAuthError
# [x] Other non-success DFS codes → APIError
# [x] logger.info per discovery call with count + cost
# [x] Module-level singleton: get_dfs_gmaps_client / close_dfs_gmaps_client
# [x] settings.dataforseo_login / settings.dataforseo_password
# [x] No modifications to src/integrations/dataforseo.py
