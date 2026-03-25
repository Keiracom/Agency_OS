# FILE: src/clients/dfs_serp_client.py
# PURPOSE: DataForSEO SERP Organic client for Stage 4 DM identification
# PHASE: Pipeline Stage 4 — Decision Maker Identification
# DEPENDENCIES: httpx, tenacity, src.config.settings
# DIRECTIVE: #250

import logging
from decimal import Decimal

import httpx
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ============================================
# Module-level Constants
# ============================================

DFS_BASE_URL = "https://api.dataforseo.com/v3"
DFS_SERP_LIVE_ENDPOINT = "/serp/google/organic/live/advanced"

DFS_STATUS_SUCCESS = 20000
DFS_STATUS_AUTH_FAILURE = 40200

COST_PER_SERP_AUD = Decimal("0.00930")  # $0.006 USD * 1.55 AUD/USD

DFS_SERP_LOCATION_AU = 2036
DFS_LINKEDIN_IN_PATTERN = "linkedin.com/in/"


# ============================================
# Custom Exceptions
# ============================================


class DFSSerpAuthError(Exception):
    pass


class DFSSerpError(Exception):
    pass


# ============================================
# Client
# ============================================


class DFSSerpClient:
    def __init__(self, login: str, password: str) -> None:
        import base64
        self._auth_header = "Basic " + base64.b64encode(f"{login}:{password}".encode()).decode()
        self._client: httpx.AsyncClient | None = None
        self.queries_made: int = 0

    async def _get_client(self) -> httpx.AsyncClient:
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
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    @property
    def estimated_cost_aud(self) -> Decimal:
        return self.queries_made * COST_PER_SERP_AUD

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def find_decision_maker(
        self,
        business_name: str,
        suburb: str | None,
        state: str | None,
    ) -> dict | None:
        """Search DFS SERP for DM LinkedIn profile. Returns mapped dict or None."""
        # Build search query
        location_parts = " ".join(filter(None, [suburb, state]))
        query = f'"{business_name}" {location_parts} site:linkedin.com/in/'

        # Single POST to live endpoint — synchronous, no polling
        client = await self._get_client()
        resp = await client.post(DFS_SERP_LIVE_ENDPOINT, json=[{
            "keyword": query,
            "location_code": DFS_SERP_LOCATION_AU,
            "language_code": "en",
            "device": "desktop",
            "os": "windows",
            "depth": 10,
        }])
        resp.raise_for_status()
        data = resp.json()

        task = data["tasks"][0]
        status_code = task["status_code"]
        if status_code == DFS_STATUS_AUTH_FAILURE:
            raise DFSSerpAuthError("DFS SERP authentication failed")
        if status_code != DFS_STATUS_SUCCESS:
            raise DFSSerpError(
                f"DFS SERP error {status_code}: {task.get('status_message', '')}"
            )

        self.queries_made += 1

        # Parse results directly
        result = task.get("result") or []
        items = result[0].get("items") or [] if result else []
        return self._extract_dm(items)

    def _extract_dm(self, items: list[dict]) -> dict | None:
        """Find first linkedin.com/in/ result and extract DM fields."""
        for item in items:
            url = item.get("url", "")
            if DFS_LINKEDIN_IN_PATTERN not in url:
                continue
            # Extract name and title from LinkedIn result title
            # LinkedIn format: "FirstName LastName - Title - Company | LinkedIn"
            title_raw = item.get("title", "")
            name, job_title = self._parse_linkedin_title(title_raw)
            position = item.get("rank_group", 10)
            # dm_confidence: position 1=high, degrades with position
            confidence = max(
                Decimal("0.90") - Decimal("0.08") * (position - 1),
                Decimal("0.10"),
            )
            return {
                "dm_linkedin_url": url.split("?")[0],  # strip query params
                "dm_name": name,
                "dm_title": job_title,
                "dm_source": "dfs_serp",
                "dm_confidence": confidence,
            }
        return None

    def _parse_linkedin_title(self, title: str) -> tuple[str | None, str | None]:
        """Parse 'FirstName LastName - Title - Company | LinkedIn' format."""
        # Strip trailing ' | LinkedIn' or ' - LinkedIn'
        for suffix in [" | LinkedIn", " - LinkedIn", "| LinkedIn"]:
            if suffix in title:
                title = title[:title.rfind(suffix)]
        parts = [p.strip() for p in title.split(" - ")]
        name = parts[0] if parts else None
        job_title = parts[1] if len(parts) > 1 else None
        return name, job_title


# ============================================
# Module-level Singleton
# ============================================

_serp_client: DFSSerpClient | None = None


def get_dfs_serp_client() -> DFSSerpClient:
    global _serp_client
    if _serp_client is None:
        _serp_client = DFSSerpClient(
            login=settings.dataforseo_login,
            password=settings.dataforseo_password,
        )
    return _serp_client


async def close_dfs_serp_client() -> None:
    global _serp_client
    if _serp_client is not None:
        await _serp_client.close()
        _serp_client = None
