"""
Keyword Expander — Industry to Search Keywords

Converts industry slugs to arrays of ABN/Maps search keywords.
Uses curated lookup table with Claude API fallback for unknown verticals.
"""

import os

import anthropic
import structlog

logger = structlog.get_logger()


class KeywordExpander:
    """
    Expands industry verticals into search keywords.

    Primary: Lookup from industry_keywords Supabase table
    Fallback: Claude API for unlisted verticals ($0.01 per call)
    """

    CLAUDE_PROMPT = """List 8-12 ABN search keywords for "{industry}" businesses in Australia.
Return ONLY a JSON array of strings, no explanation.
Example: ["keyword1", "keyword2", "keyword3"]"""

    def __init__(self, supabase_client=None, anthropic_api_key: str = None):
        self.supabase = supabase_client
        self.anthropic_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._cache: dict = {}

    async def expand(self, industry_slug: str) -> list[str]:
        """Get keywords for an industry, with caching."""
        if industry_slug in self._cache:
            return self._cache[industry_slug]

        # Try database lookup first
        keywords = await self._lookup_db(industry_slug)

        if not keywords:
            # Fallback to Claude
            logger.info("keyword_fallback_to_claude", industry=industry_slug)
            keywords = await self._expand_with_claude(industry_slug)

        self._cache[industry_slug] = keywords
        return keywords

    async def _lookup_db(self, industry_slug: str) -> list[str] | None:
        """Lookup keywords from industry_keywords table."""
        if not self.supabase:
            return None

        try:
            result = (
                await self.supabase.table("industry_keywords")
                .select("keywords")
                .eq("industry_slug", industry_slug)
                .single()
                .execute()
            )

            if result.data:
                return result.data.get("keywords", [])
        except Exception as e:
            logger.warning("keyword_db_lookup_failed", error=str(e))

        return None

    async def _expand_with_claude(self, industry: str) -> list[str]:
        """Use Claude to generate keywords for unlisted industry."""
        if not self.anthropic_key:
            logger.warning("no_anthropic_key_for_fallback")
            return [industry]  # Return industry name as single keyword

        try:
            client = anthropic.Anthropic(api_key=self.anthropic_key)

            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model
                max_tokens=200,
                messages=[
                    {"role": "user", "content": self.CLAUDE_PROMPT.format(industry=industry)}
                ],
            )

            # Parse JSON array from response
            import json

            text = response.content[0].text.strip()
            keywords = json.loads(text)

            if isinstance(keywords, list) and len(keywords) > 0:
                return keywords

        except Exception as e:
            logger.error("claude_keyword_expansion_failed", error=str(e))

        return [industry]

    def get_discovery_mode(self, industry_slug: str) -> str:
        """Get recommended discovery mode for an industry."""
        # This would query the database, but for sync access we cache it
        # during expand() call
        return "both"  # Default fallback

    async def get_maps_categories(self, industry_slug: str) -> list[str]:
        """Get Google Maps category terms for an industry."""
        if not self.supabase:
            return []

        try:
            result = (
                await self.supabase.table("industry_keywords")
                .select("maps_categories")
                .eq("industry_slug", industry_slug)
                .single()
                .execute()
            )

            if result.data:
                return result.data.get("maps_categories", [])
        except Exception:
            pass

        return []
