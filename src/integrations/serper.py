"""
FILE: src/integrations/serper.py
PURPOSE: Serper API integration for web search (Google Search API)
PHASE: 12B (Campaign Enhancement)
TASK: CAM-007
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70

Serper provides Google Search API access for:
- Industry research when ICP data is weak
- Competitor analysis
- Pain point discovery
- Market validation
"""

from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class SerperSearchResult(BaseModel):
    """A single search result from Serper."""
    title: str
    link: str
    snippet: str
    position: int


class SerperOrganicResults(BaseModel):
    """Organic search results container."""
    results: list[SerperSearchResult] = Field(default_factory=list)
    total_results: int = 0
    search_time: float = 0.0


class SerperKnowledgeGraph(BaseModel):
    """Knowledge graph data if available."""
    title: str | None = None
    type: str | None = None
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class SerperResponse(BaseModel):
    """Complete Serper API response."""
    query: str
    organic: list[SerperSearchResult] = Field(default_factory=list)
    knowledge_graph: SerperKnowledgeGraph | None = None
    related_searches: list[str] = Field(default_factory=list)
    people_also_ask: list[dict[str, str]] = Field(default_factory=list)


class SerperClient:
    """
    Serper API client for Google Search.

    Used to supplement ICP discovery when:
    - Website scraping yields insufficient data
    - ICP confidence < 0.6
    - Industry research needed

    Serper provides:
    - Google Search results
    - Knowledge graph data
    - Related searches
    - People Also Ask questions
    """

    BASE_URL = "https://google.serper.dev"

    def __init__(self, api_key: str | None = None):
        """
        Initialize Serper client.

        Args:
            api_key: Serper API key (falls back to settings)
        """
        self.api_key = api_key or getattr(settings, 'serper_api_key', None)
        if not self.api_key:
            raise IntegrationError(
                service="serper",
                message="Serper API key is required. Set SERPER_API_KEY env var.",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "X-API-KEY": self.api_key,
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

    async def __aenter__(self) -> "SerperClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        endpoint: str,
        data: dict,
    ) -> dict:
        """
        Make API request with retry logic.

        Args:
            endpoint: API endpoint path
            data: Request payload

        Returns:
            API response as dict

        Raises:
            APIError: On HTTP errors
            IntegrationError: On connection errors
        """
        client = await self._get_client()

        try:
            response = await client.post(endpoint, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                service="serper",
                status_code=e.response.status_code,
                response=e.response.text,
                message=f"Serper API error: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="serper",
                message=f"Serper request failed: {str(e)}",
            )

    async def search(
        self,
        query: str,
        num_results: int = 10,
        country: str = "au",
        language: str = "en",
    ) -> SerperResponse:
        """
        Perform Google search via Serper API.

        Args:
            query: Search query string
            num_results: Number of results (default 10, max 100)
            country: Country code for localized results (default "au")
            language: Language code (default "en")

        Returns:
            SerperResponse with organic results and metadata
        """
        data = {
            "q": query,
            "num": min(num_results, 100),
            "gl": country,
            "hl": language,
        }

        response = await self._request("/search", data)

        # Parse organic results
        organic = []
        for idx, item in enumerate(response.get("organic", []), start=1):
            organic.append(SerperSearchResult(
                title=item.get("title", ""),
                link=item.get("link", ""),
                snippet=item.get("snippet", ""),
                position=idx,
            ))

        # Parse knowledge graph if present
        kg = response.get("knowledgeGraph")
        knowledge_graph = None
        if kg:
            knowledge_graph = SerperKnowledgeGraph(
                title=kg.get("title"),
                type=kg.get("type"),
                description=kg.get("description"),
                attributes=kg.get("attributes", {}),
            )

        # Parse related searches
        related = [rs.get("query", "") for rs in response.get("relatedSearches", [])]

        # Parse People Also Ask
        paa = response.get("peopleAlsoAsk", [])

        return SerperResponse(
            query=query,
            organic=organic,
            knowledge_graph=knowledge_graph,
            related_searches=related,
            people_also_ask=paa,
        )

    async def search_news(
        self,
        query: str,
        num_results: int = 10,
        country: str = "au",
    ) -> SerperResponse:
        """
        Search Google News via Serper API.

        Args:
            query: Search query string
            num_results: Number of results
            country: Country code

        Returns:
            SerperResponse with news articles
        """
        data = {
            "q": query,
            "num": min(num_results, 100),
            "gl": country,
            "type": "news",
        }

        response = await self._request("/news", data)

        organic = []
        for idx, item in enumerate(response.get("news", []), start=1):
            organic.append(SerperSearchResult(
                title=item.get("title", ""),
                link=item.get("link", ""),
                snippet=item.get("snippet", ""),
                position=idx,
            ))

        return SerperResponse(
            query=query,
            organic=organic,
            related_searches=[],
            people_also_ask=[],
        )

    async def search_industry(
        self,
        industry: str,
        location: str = "Australia",
        num_results: int = 20,
    ) -> dict[str, SerperResponse]:
        """
        Perform comprehensive industry research.

        Runs multiple searches to gather:
        - Industry trends
        - Pain points
        - Key players
        - Recent news

        Args:
            industry: Industry name (e.g., "healthcare", "SaaS")
            location: Geographic focus
            num_results: Results per search

        Returns:
            Dict with categorized search results
        """
        searches = {
            "trends": f"{industry} industry trends {location} 2025",
            "pain_points": f"{industry} business challenges problems {location}",
            "key_players": f"top {industry} companies {location}",
            "news": f"{industry} industry news {location}",
        }

        results = {}
        for category, query in searches.items():
            if category == "news":
                results[category] = await self.search_news(query, num_results // 2)
            else:
                results[category] = await self.search(query, num_results)

        return results

    async def discover_pain_points(
        self,
        industry: str,
        business_type: str | None = None,
        num_results: int = 15,
    ) -> list[str]:
        """
        Discover common pain points for an industry.

        Args:
            industry: Industry name
            business_type: Optional business type (e.g., "agency", "startup")
            num_results: Number of search results

        Returns:
            List of discovered pain points/challenges
        """
        queries = [
            f"{industry} business challenges 2025",
            f"{industry} common problems businesses face",
            f"why {industry} businesses fail",
        ]

        if business_type:
            queries.append(f"{business_type} {industry} struggles")

        pain_points = set()

        for query in queries:
            response = await self.search(query, num_results)

            # Extract pain points from snippets
            for result in response.organic:
                snippet = result.snippet.lower()
                # Simple extraction - in production, use AI to parse
                pain_points.add(result.snippet[:200])

            # Extract from People Also Ask
            for paa in response.people_also_ask:
                if question := paa.get("question"):
                    if any(word in question.lower() for word in ["problem", "challenge", "struggle", "fail", "why"]):
                        pain_points.add(question)

        return list(pain_points)[:10]


# Singleton getter
_serper_client: SerperClient | None = None


def get_serper_client() -> SerperClient:
    """Get singleton Serper client instance."""
    global _serper_client
    if _serper_client is None:
        _serper_client = SerperClient()
    return _serper_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Follows integration pattern (like apollo.py)
# [x] Uses dependency injection pattern
# [x] Retry logic with tenacity
# [x] Proper error handling with APIError/IntegrationError
# [x] Type hints on all functions
# [x] Pydantic models for responses
# [x] Async context manager support
# [x] Multiple search methods (search, news, industry)
# [x] Pain point discovery method
# [x] No hardcoded secrets
# [x] Singleton getter pattern
