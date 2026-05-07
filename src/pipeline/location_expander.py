"""
Location Expander — City to Suburbs

Converts city names into suburb arrays for Maps SERP pagination.
Uses curated lookup table with SERP fallback for unknown cities.
"""

import structlog

from src.integrations.supabase import get_async_supabase_service_client

logger = structlog.get_logger()


class LocationExpander:
    """
    Expands city locations into suburb arrays for Google Maps queries.

    Primary: Lookup from location_suburbs Supabase table
    Fallback: Google SERP for "{city} suburbs" (for unlisted cities)
    """

    def __init__(self, supabase_client=None, bright_data_client=None):
        self.supabase = supabase_client
        self.bd = bright_data_client
        self._cache: dict = {}

    async def expand(self, city: str, state: str) -> list[str]:
        """Get suburbs for a city, with caching."""
        cache_key = f"{city}:{state}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try database lookup
        suburbs = await self._lookup_db(city, state)

        if not suburbs and self.bd:
            # Fallback to SERP search
            logger.info("suburb_fallback_to_serp", city=city, state=state)
            suburbs = await self._expand_with_serp(city, state)

        if not suburbs:
            # Ultimate fallback: just use city name
            suburbs = [city]

        self._cache[cache_key] = suburbs
        return suburbs

    async def _lookup_db(self, city: str, state: str) -> list[str]:
        """Lookup suburbs from location_suburbs table."""
        try:
            supabase = await get_async_supabase_service_client()
            result = (
                await supabase.table("location_suburbs")
                .select("suburb")
                .eq("city", city)
                .eq("state", state)
                .execute()
            )

            if result.data:
                return [r["suburb"] for r in result.data]
        except Exception as e:
            logger.warning("suburb_db_lookup_failed", error=str(e))

        return []

    async def _expand_with_serp(self, city: str, state: str) -> list[str]:
        """Use Google SERP to find suburbs for unlisted city."""
        try:
            results = await self.bd.search_google(f"{city} {state} suburbs list")

            # Parse suburbs from search results
            # This is heuristic - look for suburb names in snippets
            suburbs = []

            for result in results.get("organic", [])[:5]:
                snippet = result.get("snippet", "")
                # Extract potential suburb names (capitalized words)
                import re

                words = re.findall(r"\b[A-Z][a-z]+\b", snippet)
                suburbs.extend(words[:5])

            # Deduplicate and limit
            seen = set()
            unique = []
            for s in suburbs:
                if s.lower() not in seen and s.lower() != city.lower():
                    seen.add(s.lower())
                    unique.append(s)
                    if len(unique) >= 20:
                        break

            return unique if unique else [city]

        except Exception as e:
            logger.error("serp_suburb_expansion_failed", error=str(e))
            return [city]

    def get_state_from_city(self, city: str) -> str:
        """Infer state from city name."""
        city_states = {
            "sydney": "NSW",
            "melbourne": "VIC",
            "brisbane": "QLD",
            "perth": "WA",
            "adelaide": "SA",
            "hobart": "TAS",
            "darwin": "NT",
            "canberra": "ACT",
            "gold coast": "QLD",
            "newcastle": "NSW",
            "wollongong": "NSW",
            "geelong": "VIC",
            "cairns": "QLD",
            "townsville": "QLD",
            "toowoomba": "QLD",
        }
        return city_states.get(city.lower(), "NSW")
