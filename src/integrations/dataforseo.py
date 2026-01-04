"""
FILE: src/integrations/dataforseo.py
PURPOSE: DataForSEO API integration for SEO metrics enrichment
PHASE: 17 (Launch Prerequisites)
TASK: INT-015
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
SPEC: docs/specs/phase17/DATAFORSEO_ALS_ENHANCEMENT_SPEC.md
"""

import base64
from datetime import datetime, timedelta
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class DataForSEOClient:
    """
    DataForSEO API client for SEO metrics enrichment.
    
    Used to enhance ALS (Agency Lead Score) with:
    - Domain Rank (authority)
    - Organic Traffic (presence)
    - Traffic Trend (timing signal)
    - Backlinks (quality indicator)
    """

    BASE_URL = "https://api.dataforseo.com/v3"

    def __init__(
        self,
        login: str | None = None,
        password: str | None = None,
    ):
        self.login = login or settings.dataforseo_login
        self.password = password or settings.dataforseo_password
        
        if not self.login or not self.password:
            raise IntegrationError(
                service="dataforseo",
                message="DataForSEO login and password are required",
            )
        
        # Create Basic Auth header
        credentials = f"{self.login}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        self._auth_header = f"Basic {encoded}"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: list[dict] | None = None,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise APIError(
                service="dataforseo",
                status_code=e.response.status_code,
                message=f"DataForSEO API error: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="dataforseo",
                message=f"Request failed: {str(e)}",
            )

    async def get_domain_overview(
        self,
        domain: str,
        location_code: int = 2036,  # Australia
        language_code: str = "en",
    ) -> dict[str, Any]:
        """
        Get domain SEO metrics from DataForSEO Labs.
        
        Args:
            domain: Target domain (e.g., "example.com.au")
            location_code: Country code (2036 = Australia)
            language_code: Language code
            
        Returns:
            Dict with domain_rank, organic_traffic, backlinks, referring_domains
        """
        # Clean domain (remove protocol, www, trailing slash)
        clean_domain = self._clean_domain(domain)
        
        if not clean_domain:
            return self._empty_result()

        data = [{
            "target": clean_domain,
            "location_code": location_code,
            "language_code": language_code,
        }]

        response = await self._request(
            method="POST",
            endpoint="/dataforseo_labs/google/domain_overview/live",
            data=data,
        )

        return self._parse_domain_overview(response)

    async def get_domain_metrics_batch(
        self,
        domains: list[str],
        location_code: int = 2036,
        language_code: str = "en",
    ) -> dict[str, dict[str, Any]]:
        """
        Get domain metrics for multiple domains in one request.
        
        Args:
            domains: List of domains to check
            location_code: Country code
            language_code: Language code
            
        Returns:
            Dict mapping domain -> metrics
        """
        results = {}
        
        # DataForSEO allows up to 100 tasks per request
        # Process in batches
        batch_size = 100
        
        for i in range(0, len(domains), batch_size):
            batch = domains[i:i + batch_size]
            
            data = [
                {
                    "target": self._clean_domain(domain),
                    "location_code": location_code,
                    "language_code": language_code,
                }
                for domain in batch
                if self._clean_domain(domain)
            ]
            
            if not data:
                continue

            response = await self._request(
                method="POST",
                endpoint="/dataforseo_labs/google/domain_overview/live",
                data=data,
            )

            # Parse each task result
            if response.get("tasks"):
                for task in response["tasks"]:
                    if task.get("result") and len(task["result"]) > 0:
                        result = task["result"][0]
                        target = result.get("target", "")
                        results[target] = self._extract_metrics(result)
                    elif task.get("data", {}).get("target"):
                        # No result, store empty
                        target = task["data"]["target"]
                        results[target] = self._empty_result()

        return results

    async def health_check(self) -> dict[str, Any]:
        """
        Check API connectivity and account status.
        
        Returns:
            Dict with status, balance, and any errors
        """
        try:
            # Use a simple endpoint to check connectivity
            response = await self._request(
                method="GET",
                endpoint="/appendix/user_data",
            )
            
            if response.get("tasks") and len(response["tasks"]) > 0:
                task = response["tasks"][0]
                if task.get("result"):
                    result = task["result"][0] if isinstance(task["result"], list) else task["result"]
                    return {
                        "status": "healthy",
                        "balance": result.get("money", {}).get("balance"),
                        "login": result.get("login"),
                    }
            
            return {
                "status": "healthy",
                "message": "Connected but no user data returned",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _clean_domain(self, domain: str) -> str:
        """Clean domain for API request."""
        if not domain:
            return ""
        
        # Remove protocol
        domain = domain.lower().strip()
        domain = domain.replace("https://", "").replace("http://", "")
        
        # Remove www
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Remove trailing slash and path
        domain = domain.split("/")[0]
        
        # Remove port
        domain = domain.split(":")[0]
        
        return domain

    def _parse_domain_overview(self, response: dict) -> dict[str, Any]:
        """Parse domain overview API response."""
        if not response.get("tasks"):
            return self._empty_result()

        task = response["tasks"][0]
        
        if task.get("status_code") != 20000:
            # API returned an error for this task
            return self._empty_result()

        if not task.get("result") or len(task["result"]) == 0:
            return self._empty_result()

        result = task["result"][0]
        return self._extract_metrics(result)

    def _extract_metrics(self, result: dict) -> dict[str, Any]:
        """Extract relevant metrics from API result."""
        metrics = result.get("metrics", {}).get("organic", {})
        
        return {
            "domain_rank": result.get("rank"),
            "organic_traffic": metrics.get("etv"),  # Estimated Traffic Value
            "organic_count": metrics.get("count"),  # Number of keywords
            "backlinks": result.get("backlinks_info", {}).get("backlinks"),
            "referring_domains": result.get("backlinks_info", {}).get("referring_domains"),
            "domain_age": None,  # Not available in this endpoint
            "enriched_at": datetime.utcnow().isoformat(),
        }

    def _empty_result(self) -> dict[str, Any]:
        """Return empty result structure."""
        return {
            "domain_rank": None,
            "organic_traffic": None,
            "organic_count": None,
            "backlinks": None,
            "referring_domains": None,
            "domain_age": None,
            "enriched_at": datetime.utcnow().isoformat(),
        }

    # ============================================
    # ALS Scoring Helper Methods
    # ============================================

    def score_domain_rank(self, domain_rank: int | None) -> int:
        """
        Score domain rank for ALS Company Fit component.
        
        Scoring rubric (0-5 points):
        - 0-10: 0 points (new/invisible)
        - 11-25: 1 point (small local presence)
        - 26-40: 2 points (established local agency)
        - 41-55: 3 points (strong regional agency)
        - 56-70: 4 points (well-known agency)
        - 71+: 5 points (industry leader)
        """
        if domain_rank is None or domain_rank <= 10:
            return 0
        elif domain_rank <= 25:
            return 1
        elif domain_rank <= 40:
            return 2
        elif domain_rank <= 55:
            return 3
        elif domain_rank <= 70:
            return 4
        else:
            return 5

    def score_organic_traffic(self, organic_traffic: int | None) -> int:
        """
        Score organic traffic for ALS Company Fit component.
        
        Scoring rubric (0-5 points):
        - 0-100: 0 points (no presence)
        - 101-500: 1 point (minimal)
        - 501-2,000: 2 points (growing)
        - 2,001-10,000: 3 points (solid)
        - 10,001-50,000: 4 points (strong)
        - 50,001+: 5 points (dominant)
        """
        if organic_traffic is None or organic_traffic <= 100:
            return 0
        elif organic_traffic <= 500:
            return 1
        elif organic_traffic <= 2000:
            return 2
        elif organic_traffic <= 10000:
            return 3
        elif organic_traffic <= 50000:
            return 4
        else:
            return 5

    def score_traffic_trend(
        self,
        current_traffic: int | None,
        previous_traffic: int | None,
    ) -> int:
        """
        Score traffic trend for ALS Timing component.
        
        Scoring rubric (0-3 points):
        - Declining >20%: 3 points (pain point)
        - Declining 5-20%: 2 points (slight concern)
        - Stable (±5%): 1 point (maintaining)
        - Growing 5-20%: 2 points (healthy)
        - Growing >20%: 3 points (rapid growth)
        
        Note: Both declining AND growing get high scores
        for different reasons (pain vs. opportunity).
        """
        if current_traffic is None or previous_traffic is None:
            return 1  # Default to stable if no trend data
        
        if previous_traffic == 0:
            return 3 if current_traffic > 0 else 0
        
        change_pct = ((current_traffic - previous_traffic) / previous_traffic) * 100
        
        if change_pct <= -20:
            return 3  # Significant decline = pain point
        elif change_pct <= -5:
            return 2  # Slight decline
        elif change_pct <= 5:
            return 1  # Stable
        elif change_pct <= 20:
            return 2  # Healthy growth
        else:
            return 3  # Rapid growth = has budget

    def calculate_risk_deductions(self, metrics: dict[str, Any]) -> int:
        """
        Calculate risk deductions based on DataForSEO metrics.
        
        Deductions:
        - Domain Rank 0 or None: -5 (no web presence)
        - No organic traffic: -3 (doesn't practice what they preach)
        """
        deductions = 0
        
        domain_rank = metrics.get("domain_rank")
        organic_traffic = metrics.get("organic_traffic")
        
        # No domain rank = suspicious for a marketing agency
        if domain_rank is None or domain_rank == 0:
            deductions -= 5
        
        # No organic traffic = red flag for marketing agency
        if organic_traffic is None or organic_traffic == 0:
            deductions -= 3
        
        return deductions


# ============================================
# Factory Function
# ============================================

_dataforseo_client: DataForSEOClient | None = None


def get_dataforseo_client() -> DataForSEOClient:
    """Get or create DataForSEO client instance."""
    global _dataforseo_client
    if _dataforseo_client is None:
        _dataforseo_client = DataForSEOClient()
    return _dataforseo_client


async def close_dataforseo_client() -> None:
    """Close DataForSEO client."""
    global _dataforseo_client
    if _dataforseo_client is not None:
        await _dataforseo_client.close()
        _dataforseo_client = None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Basic Auth implementation
# [x] Retry logic with tenacity
# [x] Domain cleaning/normalization
# [x] Batch request support
# [x] Health check endpoint
# [x] ALS scoring helper methods
# [x] Empty result handling
# [x] Factory function pattern
# [x] All functions have type hints
# [x] All functions have docstrings
