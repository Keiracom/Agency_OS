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

VERIFIED: January 4, 2026
- Labs API: Working (domain_rank_overview endpoint)
- Backlinks API: Working (14-day trial active until Jan 18, 2026)
- Response structures validated against live API
"""

import base64
from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class DataForSEOClient:
    """
    DataForSEO API client for SEO metrics enrichment.

    Used to enhance ALS (Agency Lead Score) with:
    - Domain Rank (authority) - from Backlinks API
    - Organic Traffic ETV (presence) - from Labs API
    - Organic Keywords Count - from Labs API
    - Backlinks Count - from Backlinks API
    - Referring Domains - from Backlinks API
    - Spam Score - from Backlinks API

    API Costs (verified Jan 2026):
    - Labs domain_rank_overview: $0.0101/request
    - Backlinks summary: $0.02003/request
    - Combined per lead: ~$0.03
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
        Get domain SEO metrics from DataForSEO Labs API.

        Endpoint: /dataforseo_labs/google/domain_rank_overview/live
        Cost: $0.0101 per request

        Args:
            domain: Target domain (e.g., "example.com.au")
            location_code: Country code (2036 = Australia)
            language_code: Language code

        Returns:
            Dict with organic metrics:
            - organic_etv: Estimated Traffic Value
            - organic_count: Number of ranking keywords
            - organic_pos_1: Keywords in position 1
            - organic_pos_2_3: Keywords in positions 2-3
            - organic_pos_4_10: Keywords in positions 4-10
            - estimated_paid_traffic_cost: Value in paid equivalent
        """
        clean_domain = self._clean_domain(domain)

        if not clean_domain:
            return self._empty_labs_result()

        data = [
            {
                "target": clean_domain,
                "location_code": location_code,
                "language_code": language_code,
            }
        ]

        response = await self._request(
            method="POST",
            endpoint="/dataforseo_labs/google/domain_rank_overview/live",
            data=data,
        )

        return self._parse_labs_response(response)

    async def get_backlinks_summary(
        self,
        domain: str,
        include_subdomains: bool = True,
    ) -> dict[str, Any]:
        """
        Get backlink metrics from DataForSEO Backlinks API.

        Endpoint: /backlinks/summary/live
        Cost: $0.02003 per request

        Args:
            domain: Target domain (e.g., "example.com.au")
            include_subdomains: Include subdomains in count

        Returns:
            Dict with backlink metrics:
            - rank: Domain Rank (0-1000+ scale, higher = more authoritative)
            - backlinks: Total backlink count
            - referring_domains: Unique referring domains
            - referring_ips: Unique referring IPs
            - referring_subnets: Unique referring subnets
            - spam_score: Spam score (0-100, lower = better)
        """
        clean_domain = self._clean_domain(domain)

        if not clean_domain:
            return self._empty_backlinks_result()

        data = [
            {
                "target": clean_domain,
                "include_subdomains": include_subdomains,
            }
        ]

        response = await self._request(
            method="POST",
            endpoint="/backlinks/summary/live",
            data=data,
        )

        return self._parse_backlinks_response(response)

    async def get_full_domain_metrics(
        self,
        domain: str,
        location_code: int = 2036,
        language_code: str = "en",
    ) -> dict[str, Any]:
        """
        Get comprehensive domain metrics from both Labs and Backlinks APIs.

        Combined cost: ~$0.03 per request

        Args:
            domain: Target domain
            location_code: Country code for Labs API
            language_code: Language code for Labs API

        Returns:
            Combined dict with all metrics from both APIs
        """
        # Run both API calls
        labs_result = await self.get_domain_overview(
            domain=domain,
            location_code=location_code,
            language_code=language_code,
        )

        backlinks_result = await self.get_backlinks_summary(
            domain=domain,
            include_subdomains=True,
        )

        # Merge results
        return {
            # From Labs API
            "organic_etv": labs_result.get("organic_etv"),
            "organic_count": labs_result.get("organic_count"),
            "organic_pos_1": labs_result.get("organic_pos_1"),
            "organic_pos_2_3": labs_result.get("organic_pos_2_3"),
            "organic_pos_4_10": labs_result.get("organic_pos_4_10"),
            "estimated_paid_traffic_cost": labs_result.get("estimated_paid_traffic_cost"),
            # From Backlinks API
            "domain_rank": backlinks_result.get("rank"),
            "backlinks": backlinks_result.get("backlinks"),
            "referring_domains": backlinks_result.get("referring_domains"),
            "referring_ips": backlinks_result.get("referring_ips"),
            "spam_score": backlinks_result.get("spam_score"),
            # Meta
            "enriched_at": datetime.utcnow().isoformat(),
        }

    async def health_check(self) -> dict[str, Any]:
        """
        Check API connectivity and account status.

        Returns:
            Dict with status, balance, and any errors
        """
        try:
            response = await self._request(
                method="GET",
                endpoint="/appendix/user_data",
            )

            if response.get("tasks") and len(response["tasks"]) > 0:
                task = response["tasks"][0]
                if task.get("result"):
                    result = (
                        task["result"][0] if isinstance(task["result"], list) else task["result"]
                    )
                    money = result.get("money", {})
                    return {
                        "status": "healthy",
                        "balance": money.get("balance"),
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

        domain = domain.lower().strip()
        domain = domain.replace("https://", "").replace("http://", "")

        if domain.startswith("www."):
            domain = domain[4:]

        domain = domain.split("/")[0]
        domain = domain.split(":")[0]

        return domain

    def _parse_labs_response(self, response: dict) -> dict[str, Any]:
        """
        Parse Labs API domain_rank_overview response.

        Response structure (verified Jan 2026):
        {
            "tasks": [{
                "result": [{
                    "items": [{
                        "metrics": {
                            "organic": {
                                "etv": 149.89,
                                "count": 99,
                                "pos_1": 2,
                                "pos_2_3": 0,
                                "pos_4_10": 5,
                                "estimated_paid_traffic_cost": 434.26
                            }
                        }
                    }]
                }]
            }]
        }
        """
        if not response.get("tasks"):
            return self._empty_labs_result()

        task = response["tasks"][0]

        if task.get("status_code") != 20000:
            return self._empty_labs_result()

        if not task.get("result") or len(task["result"]) == 0:
            return self._empty_labs_result()

        result = task["result"][0]
        items = result.get("items", [])

        if not items:
            return self._empty_labs_result()

        item = items[0]
        organic = item.get("metrics", {}).get("organic", {})

        return {
            "organic_etv": organic.get("etv"),
            "organic_count": organic.get("count"),
            "organic_pos_1": organic.get("pos_1"),
            "organic_pos_2_3": organic.get("pos_2_3"),
            "organic_pos_4_10": organic.get("pos_4_10"),
            "estimated_paid_traffic_cost": organic.get("estimated_paid_traffic_cost"),
            "enriched_at": datetime.utcnow().isoformat(),
        }

    def _parse_backlinks_response(self, response: dict) -> dict[str, Any]:
        """
        Parse Backlinks API summary response.

        Response structure (verified Jan 2026):
        {
            "tasks": [{
                "result": [{
                    "rank": 337,
                    "backlinks": 19578,
                    "referring_domains": 1429,
                    "referring_ips": 864,
                    "referring_subnets": 693,
                    "backlinks_spam_score": 28
                }]
            }]
        }
        """
        if not response.get("tasks"):
            return self._empty_backlinks_result()

        task = response["tasks"][0]

        if task.get("status_code") != 20000:
            return self._empty_backlinks_result()

        if not task.get("result") or len(task["result"]) == 0:
            return self._empty_backlinks_result()

        result = task["result"][0]

        return {
            "rank": result.get("rank"),
            "backlinks": result.get("backlinks"),
            "referring_domains": result.get("referring_domains"),
            "referring_ips": result.get("referring_ips"),
            "referring_subnets": result.get("referring_subnets"),
            "spam_score": result.get("backlinks_spam_score"),
            "enriched_at": datetime.utcnow().isoformat(),
        }

    def _empty_labs_result(self) -> dict[str, Any]:
        """Return empty Labs result structure."""
        return {
            "organic_etv": None,
            "organic_count": None,
            "organic_pos_1": None,
            "organic_pos_2_3": None,
            "organic_pos_4_10": None,
            "estimated_paid_traffic_cost": None,
            "enriched_at": datetime.utcnow().isoformat(),
        }

    def _empty_backlinks_result(self) -> dict[str, Any]:
        """Return empty Backlinks result structure."""
        return {
            "rank": None,
            "backlinks": None,
            "referring_domains": None,
            "referring_ips": None,
            "referring_subnets": None,
            "spam_score": None,
            "enriched_at": datetime.utcnow().isoformat(),
        }

    # ============================================
    # ALS Scoring Helper Methods
    # ============================================

    def score_domain_rank(self, domain_rank: int | None) -> int:
        """
        Score domain rank for ALS Company Fit component.

        NOTE: DataForSEO Backlinks API returns rank on 0-1000+ scale
        (not 0-100 like Moz DA). Higher = more authoritative.

        Scoring rubric (0-5 points):
        - 0-50: 0 points (new/invisible)
        - 51-150: 1 point (small local presence)
        - 151-300: 2 points (established local agency)
        - 301-500: 3 points (strong regional agency)
        - 501-800: 4 points (well-known agency)
        - 801+: 5 points (industry leader)
        """
        if domain_rank is None or domain_rank <= 50:
            return 0
        elif domain_rank <= 150:
            return 1
        elif domain_rank <= 300:
            return 2
        elif domain_rank <= 500:
            return 3
        elif domain_rank <= 800:
            return 4
        else:
            return 5

    def score_organic_traffic(self, organic_etv: float | None) -> int:
        """
        Score organic traffic (ETV) for ALS Company Fit component.

        ETV = Estimated Traffic Value (monthly)

        Scoring rubric (0-5 points):
        - 0-50: 0 points (no presence)
        - 51-200: 1 point (minimal)
        - 201-1,000: 2 points (growing)
        - 1,001-5,000: 3 points (solid)
        - 5,001-20,000: 4 points (strong)
        - 20,001+: 5 points (dominant)
        """
        if organic_etv is None or organic_etv <= 50:
            return 0
        elif organic_etv <= 200:
            return 1
        elif organic_etv <= 1000:
            return 2
        elif organic_etv <= 5000:
            return 3
        elif organic_etv <= 20000:
            return 4
        else:
            return 5

    def score_seo_competence(self, metrics: dict[str, Any]) -> int:
        """
        Score overall SEO competence for marketing agencies.

        Combines multiple signals to assess if agency
        "practices what they preach".

        Scoring (0-5 points):
        - Has top 10 rankings: +2
        - Has position 1 rankings: +1
        - Has 50+ ranking keywords: +1
        - Has 500+ referring domains: +1
        """
        score = 0

        # Top 10 rankings (pos 1 + pos 2-3 + pos 4-10)
        pos_1 = metrics.get("organic_pos_1") or 0
        pos_2_3 = metrics.get("organic_pos_2_3") or 0
        pos_4_10 = metrics.get("organic_pos_4_10") or 0
        top_10_keywords = pos_1 + pos_2_3 + pos_4_10

        if top_10_keywords > 0:
            score += 2

        if pos_1 > 0:
            score += 1

        keyword_count = metrics.get("organic_count") or 0
        if keyword_count >= 50:
            score += 1

        referring_domains = metrics.get("referring_domains") or 0
        if referring_domains >= 500:
            score += 1

        return min(score, 5)  # Cap at 5

    def calculate_risk_deductions(self, metrics: dict[str, Any]) -> int:
        """
        Calculate risk deductions based on DataForSEO metrics.

        Deductions:
        - Domain Rank 0 or None: -5 (no web presence)
        - No organic traffic: -3 (doesn't practice what they preach)
        - High spam score (>50): -3 (low quality backlinks)
        """
        deductions = 0

        domain_rank = metrics.get("domain_rank") or metrics.get("rank")
        organic_etv = metrics.get("organic_etv")
        spam_score = metrics.get("spam_score")

        # No domain rank = suspicious for a marketing agency
        if domain_rank is None or domain_rank == 0:
            deductions -= 5

        # No organic traffic = red flag for marketing agency
        if organic_etv is None or organic_etv == 0:
            deductions -= 3

        # High spam score = low quality link building
        if spam_score is not None and spam_score > 50:
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
# [x] Labs API endpoint verified (domain_rank_overview)
# [x] Backlinks API endpoint verified (summary)
# [x] Response parsing matches live API structure
# [x] ALS scoring helper methods
# [x] Empty result handling
# [x] Factory function pattern
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Combined metrics method for full enrichment
