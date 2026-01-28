"""
Contract: src/agents/skills/social_profile_discovery.py
Purpose: Search Google to find agency social profiles when not found on website
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, integrations
Consumers: ICP discovery agent

FILE: src/agents/skills/social_profile_discovery.py
TASK: ICP-FALLBACK-001
PHASE: 21 (Portfolio Fallback Discovery)
PURPOSE: Search Google to find agency social profiles when not found on website

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/integrations/apify.py (search_google)

EXPORTS:
- SocialProfileDiscoverySkill
- DiscoveredProfiles (output model)

WHEN USED:
- Triggered when website scrape returns empty social_links
- Part of Portfolio Fallback Discovery pipeline (Tier F2)
- Uses Google search to find LinkedIn/Instagram/Facebook company pages
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)


class DiscoveredProfile(BaseModel):
    """A social profile discovered via Google search."""

    platform: str = Field(description="Platform: linkedin, instagram, facebook")
    url: str = Field(description="Profile URL")
    confidence: float = Field(default=0.8, description="Confidence this is the correct profile (0.0-1.0)")


class SocialProfileDiscoverySkill(BaseSkill["SocialProfileDiscoverySkill.Input", "SocialProfileDiscoverySkill.Output"]):
    """
    Search Google to find agency social profiles when not found on website.

    This skill:
    1. Searches Google for "[company_name]" site:linkedin.com/company
    2. Searches Google for "[company_name]" site:instagram.com
    3. Searches Google for "[company_name]" site:facebook.com
    4. Parses results to extract profile URLs
    5. Returns discovered URLs for subsequent scraping

    Cost: ~$0.02 (1 Apify Google search batch with 3 queries)
    """

    name = "discover_social_profiles"
    description = "Find agency social profiles via Google search when not found on website"

    class Input(BaseModel):
        """Input for social profile discovery."""

        company_name: str = Field(description="Agency/company name to search for")
        website_domain: str = Field(default="", description="Website domain (to filter out own site)")

    class Output(BaseModel):
        """Output from social profile discovery."""

        linkedin_url: str | None = Field(default=None, description="LinkedIn company page URL")
        instagram_url: str | None = Field(default=None, description="Instagram profile URL")
        facebook_url: str | None = Field(default=None, description="Facebook page URL")
        profiles_found: int = Field(default=0, description="Number of profiles discovered")
        search_queries_used: list[str] = Field(default_factory=list, description="Search queries executed")

    # No Claude call needed - this skill uses Apify Google search + regex parsing
    system_prompt = ""
    default_max_tokens = 0
    default_temperature = 0.0

    def build_prompt(self, input_data: Input) -> str:
        """Not used - this skill doesn't use Claude."""
        return ""

    def parse_response(self, response: str) -> Output:
        """Not used - this skill doesn't use Claude."""
        return self.Output()

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute social profile discovery via Google search.

        Args:
            input_data: Validated input with company_name and website_domain
            anthropic: Anthropic client (not used but required by interface)

        Returns:
            SkillResult with discovered profile URLs
        """
        from src.integrations.apify import get_apify_client

        company_name = input_data.company_name

        logger.info(f"Discovering social profiles for: {company_name}")

        # Build search queries
        queries = [
            f'"{company_name}" site:linkedin.com/company',
            f'"{company_name}" site:instagram.com',
            f'"{company_name}" site:facebook.com/pages OR site:facebook.com/',
        ]

        apify = get_apify_client()

        # Execute Google search
        try:
            search_results = await apify.search_google(queries, results_per_query=5)
        except Exception as e:
            logger.warning(f"Google search failed: {e}")
            return SkillResult.fail(
                error=f"Google search failed: {e}",
            )

        # Parse results to extract profile URLs
        linkedin_url = None
        instagram_url = None
        facebook_url = None

        for result in search_results:
            url = result.get("url", "").lower()
            title = result.get("title", "").lower()
            company_lower = company_name.lower()

            # LinkedIn company page
            if "linkedin.com/company/" in url and not linkedin_url:
                # Verify it's likely the correct company
                if company_lower in title or company_lower in url:
                    linkedin_url = result.get("url")
                    logger.debug(f"Found LinkedIn: {linkedin_url}")

            # Instagram profile
            elif "instagram.com/" in url and not instagram_url:
                # Filter out generic instagram.com results
                if "/p/" not in url and "/reel/" not in url:
                    if company_lower in title or self._fuzzy_match(company_name, url):
                        instagram_url = result.get("url")
                        logger.debug(f"Found Instagram: {instagram_url}")

            # Facebook page
            elif "facebook.com/" in url and not facebook_url:
                # Filter out generic Facebook results
                if "/posts/" not in url and "/photos/" not in url:
                    if company_lower in title or self._fuzzy_match(company_name, url):
                        facebook_url = result.get("url")
                        logger.debug(f"Found Facebook: {facebook_url}")

        profiles_found = sum([
            1 if linkedin_url else 0,
            1 if instagram_url else 0,
            1 if facebook_url else 0,
        ])

        output = self.Output(
            linkedin_url=linkedin_url,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            profiles_found=profiles_found,
            search_queries_used=queries,
        )

        logger.info(f"Social profile discovery found {profiles_found} profiles for {company_name}")

        return SkillResult.ok(
            data=output,
            confidence=0.8 if profiles_found > 0 else 0.0,
            tokens_used=0,  # No Claude tokens used
            cost_aud=0.02,  # Apify Google search cost estimate
            metadata={"profiles_found": profiles_found},
        )

    def _fuzzy_match(self, company_name: str, url: str) -> bool:
        """
        Check if company name fuzzy-matches URL path.

        Examples:
            "Sparro by Brainlabs" matches "instagram.com/sparroagency"
            "Digital Edge" matches "facebook.com/digitaledgeagency"
        """
        # Extract words from company name (lowercase, alphanumeric only)
        words = re.findall(r'[a-z0-9]+', company_name.lower())
        url_lower = url.lower()

        # Check if any significant word appears in URL
        significant_words = [w for w in words if len(w) > 3]
        return any(word in url_lower for word in significant_words)


# Register skill
SkillRegistry.register(SocialProfileDiscoverySkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill
- [x] Registered with SkillRegistry
- [x] Input/Output Pydantic models
- [x] Error handling
- [x] Logging at appropriate levels
"""
