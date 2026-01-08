"""
FILE: src/agents/skills/portfolio_fallback.py
TASK: ICP-FALLBACK-002
PHASE: 21 (Portfolio Fallback Discovery)
PURPOSE: Extract client names from Apollo descriptions and Google search results

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/integrations/anthropic.py

EXPORTS:
- PortfolioFallbackSkill
- FallbackPortfolioCompany (output model)

WHEN USED:
- Triggered when website scrape returns empty portfolio_companies
- Part of Portfolio Fallback Discovery pipeline (Tier F1 + F3)
- Uses Claude to extract client mentions from Apollo data and Google search snippets
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.portfolio_extractor import PortfolioCompany

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)


class FallbackPortfolioCompany(BaseModel):
    """A portfolio company discovered via fallback methods."""

    company_name: str = Field(description="Company/client name")
    source: str = Field(description="Where found: fallback:apollo, fallback:google, fallback:linkedin")
    context: str = Field(default="", description="Context where it was mentioned")
    confidence: float = Field(default=0.7, description="Confidence this is a real client (0.0-1.0)")


class PortfolioFallbackSkill(BaseSkill["PortfolioFallbackSkill.Input", "PortfolioFallbackSkill.Output"]):
    """
    Extract client names from Apollo descriptions and Google search results.

    This skill:
    1. Parses Apollo company description for client mentions
    2. Parses Google search snippets for client mentions
    3. Uses Claude to intelligently extract company names
    4. Deduplicates against existing portfolio

    Cost: ~$0.01 (1 Claude Haiku call)
    """

    name = "portfolio_fallback"
    description = "Extract client names from Apollo/Google when website has no portfolio"

    class Input(BaseModel):
        """Input for portfolio fallback extraction."""

        company_name: str = Field(description="Agency name (to exclude from results)")
        apollo_description: Optional[str] = Field(
            default=None,
            description="Apollo company description (may mention clients)"
        )
        apollo_keywords: list[str] = Field(
            default_factory=list,
            description="Apollo keywords/tags"
        )
        linkedin_description: Optional[str] = Field(
            default=None,
            description="LinkedIn company description (may mention clients)"
        )
        linkedin_specialties: list[str] = Field(
            default_factory=list,
            description="LinkedIn specialties list"
        )
        google_search_results: list[dict] = Field(
            default_factory=list,
            description="Google search results for '[company] clients case study'"
        )
        existing_portfolio: list[str] = Field(
            default_factory=list,
            description="Already known portfolio companies (to avoid duplicates)"
        )

    class Output(BaseModel):
        """Output from portfolio fallback extraction."""

        companies: list[FallbackPortfolioCompany] = Field(
            default_factory=list,
            description="Client companies extracted from fallback sources"
        )
        sources_used: list[str] = Field(
            default_factory=list,
            description="Which sources had data: apollo, linkedin, google"
        )
        total_extracted: int = Field(default=0, description="Total companies extracted")

    system_prompt = """You are extracting CLIENT/CUSTOMER company names from agency descriptions and search results.

TASK: Find company names that are CLIENTS of the agency, NOT:
- The agency itself
- Software/tools they use (e.g., HubSpot, Salesforce)
- Industry categories (e.g., "retail", "e-commerce")
- Generic terms (e.g., "leading businesses", "major brands")

EXTRACTION GUIDELINES:

1. FROM APOLLO/LINKEDIN DESCRIPTIONS:
   - Look for: "worked with X", "clients include Y", "helped Z achieve", "proud to partner with"
   - Extract specific company names mentioned
   - Example: "We've helped brands like Nike, Coca-Cola..." → Extract: Nike, Coca-Cola

2. FROM GOOGLE SEARCH RESULTS:
   - Look for case study mentions, press releases, award entries
   - Extract company names from titles and snippets
   - Example: "Sparro wins gold for Telstra campaign" → Extract: Telstra

3. WHAT TO EXTRACT:
   - Specific company names (proper nouns)
   - Both large brands (Nike, Google) and smaller companies
   - Australian companies are particularly valuable

4. WHAT NOT TO EXTRACT:
   - The agency's own name
   - Tool/platform names (Shopify, HubSpot, Google Ads)
   - Industry terms (SMBs, enterprise, retail)
   - Generic phrases (leading brands, major clients)

OUTPUT FORMAT:
Return valid JSON array of objects:
[
    {"company_name": "Telstra", "source": "google", "context": "award-winning campaign", "confidence": 0.95},
    {"company_name": "Woolworths", "source": "linkedin", "context": "client partnership", "confidence": 0.85}
]

Return empty array [] if no specific clients found."""

    default_max_tokens = 1024
    default_temperature = 0.2

    def build_prompt(self, input_data: Input) -> str:
        """Build prompt with all available fallback data."""
        sections = []

        sections.append(f"AGENCY NAME (exclude this): {input_data.company_name}")

        if input_data.existing_portfolio:
            sections.append(f"ALREADY KNOWN CLIENTS (exclude duplicates): {', '.join(input_data.existing_portfolio)}")

        if input_data.apollo_description:
            sections.append(f"""
=== APOLLO DESCRIPTION ===
{input_data.apollo_description}
""")

        if input_data.apollo_keywords:
            sections.append(f"APOLLO KEYWORDS: {', '.join(input_data.apollo_keywords)}")

        if input_data.linkedin_description:
            sections.append(f"""
=== LINKEDIN DESCRIPTION ===
{input_data.linkedin_description}
""")

        if input_data.linkedin_specialties:
            sections.append(f"LINKEDIN SPECIALTIES: {', '.join(input_data.linkedin_specialties)}")

        if input_data.google_search_results:
            google_text = []
            for result in input_data.google_search_results[:10]:  # Limit to 10 results
                title = result.get("title", "")
                snippet = result.get("description", "") or result.get("snippet", "")
                if title or snippet:
                    google_text.append(f"- {title}: {snippet}")

            if google_text:
                sections.append(f"""
=== GOOGLE SEARCH RESULTS ===
{chr(10).join(google_text)}
""")

        return "\n\n".join(sections) + "\n\nExtract client company names as JSON array:"

    def parse_response(self, response: str) -> Output:
        """Parse Claude's JSON response into Output model."""
        import json

        companies = []
        sources_used = set()

        try:
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "company_name" in item:
                        company = FallbackPortfolioCompany(
                            company_name=item.get("company_name", ""),
                            source=item.get("source", "fallback:unknown"),
                            context=item.get("context", ""),
                            confidence=item.get("confidence", 0.7),
                        )
                        companies.append(company)
                        # Track source
                        source = item.get("source", "")
                        if "apollo" in source.lower():
                            sources_used.add("apollo")
                        elif "linkedin" in source.lower():
                            sources_used.add("linkedin")
                        elif "google" in source.lower():
                            sources_used.add("google")

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse fallback extraction response: {e}")

        return self.Output(
            companies=companies,
            sources_used=list(sources_used),
            total_extracted=len(companies),
        )

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute portfolio fallback extraction.

        Args:
            input_data: Validated input with Apollo/Google data
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing extracted clients
        """
        # Check if we have any data to extract from
        has_data = (
            input_data.apollo_description
            or input_data.linkedin_description
            or input_data.google_search_results
        )

        if not has_data:
            return SkillResult.ok(
                data=self.Output(companies=[], sources_used=[], total_extracted=0),
                confidence=0.0,
                tokens_used=0,
                cost_aud=0.0,
                metadata={"reason": "no_input_data"},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Parse expects a list, but _call_ai returns dict
            # Convert back to raw response for parse_response
            import json
            raw_response = json.dumps(parsed if isinstance(parsed, list) else [])
            output = self.parse_response(raw_response)

            return SkillResult.ok(
                data=output,
                confidence=0.8 if output.total_extracted > 0 else 0.3,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "companies_extracted": output.total_extracted,
                    "sources_used": output.sources_used,
                },
            )

        except Exception as e:
            logger.warning(f"Portfolio fallback extraction failed: {e}")
            return SkillResult.fail(
                error=f"Portfolio fallback extraction failed: {str(e)}",
                metadata={},
            )


# Register skill
SkillRegistry.register(PortfolioFallbackSkill())


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
- [x] Claude prompt for intelligent extraction
- [x] JSON parsing with error handling
"""
