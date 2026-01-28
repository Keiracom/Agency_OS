"""
Contract: src/agents/sdk_agents/icp_agent.py
Purpose: SDK Agent for intelligent ICP extraction during client onboarding
Layer: Agents
Consumers: icp_scraper.py, icp_extraction_flow.py

This agent uses Claude with tools to:
- Analyze scraped website data and portfolio companies
- Research additional context via web_search
- Build a comprehensive Ideal Customer Profile
- Self-review and refine until confident
"""

from __future__ import annotations

import logging
from uuid import UUID

from pydantic import BaseModel, Field

from src.agents.sdk_agents.sdk_tools import ICP_TOOLS
from src.integrations.sdk_brain import SDKBrain, SDKBrainResult, create_sdk_brain

logger = logging.getLogger(__name__)


# ============================================
# INPUT/OUTPUT SCHEMAS
# ============================================


class TargetIndustry(BaseModel):
    """A target industry with weight and reasoning."""

    name: str = Field(description="Industry name (e.g., 'healthcare', 'technology')")
    weight: float = Field(description="Weight 0.0-1.0 indicating priority", ge=0.0, le=1.0)
    reasoning: str = Field(description="Why this industry is a good fit")


class CompanySizeRange(BaseModel):
    """Target company size specifications."""

    min_employees: int = Field(description="Minimum employee count", ge=1)
    max_employees: int = Field(description="Maximum employee count")
    sweet_spot: int = Field(description="Ideal/most common employee count")
    reasoning: str = Field(description="Why this size range")


class TargetTitle(BaseModel):
    """A target job title with priority."""

    title: str = Field(description="Job title (e.g., 'Marketing Director')")
    priority: int = Field(description="Priority 1-5, where 1 is highest", ge=1, le=5)
    reasoning: str = Field(description="Why target this title")


class PainPoint(BaseModel):
    """A specific pain point the agency can address."""

    pain_point: str = Field(description="The pain point description")
    how_agency_helps: str = Field(description="How the agency solves this")
    evidence: str = Field(description="Evidence from research supporting this")


class BuyingSignal(BaseModel):
    """A signal indicating purchase readiness."""

    signal: str = Field(description="The buying signal to look for")
    where_to_find: str = Field(description="Where/how to detect this signal")
    urgency: str = Field(description="How urgent: 'high', 'medium', 'low'")


class ICPInput(BaseModel):
    """Input data for ICP extraction."""

    client_name: str = Field(description="Agency/client name")
    website_url: str = Field(description="Agency website URL")
    website_content: str = Field(description="Scraped website text content")
    portfolio_companies: list[dict] = Field(
        default_factory=list,
        description="List of enriched portfolio companies with industry, size, etc.",
    )
    social_links: dict = Field(
        default_factory=dict, description="Social media URLs (linkedin, instagram, etc.)"
    )
    existing_icp: dict | None = Field(default=None, description="Any existing ICP data to refine")


class ICPOutput(BaseModel):
    """Complete Ideal Customer Profile output."""

    # Core ICP
    target_industries: list[TargetIndustry] = Field(description="Priority-ranked target industries")
    company_size_range: CompanySizeRange = Field(description="Target company size specifications")
    target_titles: list[TargetTitle] = Field(description="Priority-ranked decision maker titles")
    target_locations: list[str] = Field(
        default_factory=list, description="Target geographic locations"
    )

    # Messaging intelligence
    pain_points: list[PainPoint] = Field(description="Specific pain points the agency addresses")
    buying_signals: list[BuyingSignal] = Field(description="Signals indicating purchase readiness")

    # Agency positioning
    agency_strengths: list[str] = Field(description="Key differentiators and strengths")
    services_offered: list[str] = Field(description="Main services the agency provides")

    # Confidence
    confidence_score: float = Field(description="Confidence in this ICP 0.0-1.0", ge=0.0, le=1.0)
    data_gaps: list[str] = Field(
        default_factory=list, description="Areas where more data would help"
    )

    # Metadata
    sources_used: list[str] = Field(
        default_factory=list, description="Sources consulted during research"
    )


# ============================================
# SYSTEM PROMPT
# ============================================

ICP_SYSTEM_PROMPT = """You are an expert B2B sales strategist specializing in Ideal Customer Profile (ICP) development for marketing and digital agencies.

Your task is to analyze the provided agency data and build a comprehensive ICP that will help the agency identify and target their best-fit prospects.

## Your Capabilities
- **web_search**: Search for additional context about industries, market trends, or the agency
- **web_fetch**: Read specific web pages for detailed information

## Analysis Process

1. **Understand the Agency**
   - What services do they offer?
   - What industries do they specialize in?
   - What's their positioning/unique value?

2. **Analyze Portfolio Companies**
   - What industries are represented?
   - What company sizes?
   - What patterns emerge?

3. **Research & Validate** (use tools!)
   - Search for industry trends relevant to their services
   - Validate assumptions about target markets
   - Find pain points specific to their target industries

4. **Build the ICP**
   - Identify 3-5 primary target industries with weights
   - Define company size sweet spot
   - List decision maker titles in priority order
   - Document specific, actionable pain points
   - Identify buying signals

5. **Self-Review**
   - Is this ICP specific enough to be actionable?
   - Are the pain points evidence-based, not generic?
   - Would a salesperson know exactly who to target?
   - Confidence score: be honest about data gaps

## Quality Standards

**Good Pain Point:**
"Mid-size healthcare clinics (50-200 employees) struggle with HIPAA-compliant patient communication, often using outdated systems that frustrate patients and staff."

**Bad Pain Point:**
"Companies need better marketing." (Too generic)

**Good Target:**
"Healthcare Operations Directors at multi-location clinics in Australia with 50-200 employees"

**Bad Target:**
"Business owners" (Too broad)

## Output Format

Return your analysis as a JSON object matching the ICPOutput schema. Be specific, actionable, and evidence-based."""


# ============================================
# ICP AGENT
# ============================================


class ICPAgent:
    """
    SDK Agent for intelligent ICP extraction.

    Uses Claude with web_search and web_fetch tools to:
    - Analyze website and portfolio data
    - Research additional context
    - Build evidence-based ICP
    - Self-review for quality
    """

    def __init__(self, brain: SDKBrain | None = None):
        """
        Initialize ICP Agent.

        Args:
            brain: Optional SDKBrain instance (creates one if not provided)
        """
        self.brain = brain or create_sdk_brain("icp_extraction")

    async def extract(
        self,
        input_data: ICPInput,
        client_id: UUID | None = None,
    ) -> SDKBrainResult:
        """
        Extract ICP from input data using SDK Brain.

        Args:
            input_data: ICPInput with website content and portfolio data
            client_id: Optional client ID for tracking

        Returns:
            SDKBrainResult with ICPOutput data if successful
        """
        # Build context from input
        context = self._build_context(input_data)

        # Build prompt
        prompt = self._build_prompt(input_data)

        logger.info(f"Starting ICP extraction for {input_data.client_name}")

        # Run SDK Brain with tools
        result = await self.brain.run(
            prompt=prompt,
            tools=ICP_TOOLS,
            output_schema=ICPOutput,
            system=ICP_SYSTEM_PROMPT,
            context=context,
            cache_context=True,  # Cache the website content
        )

        if result.success:
            logger.info(
                f"ICP extraction complete for {input_data.client_name}: "
                f"confidence={result.data.confidence_score:.2f}, "
                f"cost=${result.cost_aud:.4f}, turns={result.turns_used}"
            )
        else:
            logger.warning(f"ICP extraction failed for {input_data.client_name}: {result.error}")

        return result

    def _build_context(self, input_data: ICPInput) -> str:
        """Build context string from input data."""
        sections = []

        # Agency info
        sections.append(f"## Agency: {input_data.client_name}")
        sections.append(f"Website: {input_data.website_url}")

        # Social links
        if input_data.social_links:
            links = ", ".join(f"{k}: {v}" for k, v in input_data.social_links.items() if v)
            if links:
                sections.append(f"Social: {links}")

        # Website content
        sections.append("\n## Website Content (Scraped)")
        # Truncate if very long
        content = input_data.website_content
        if len(content) > 15000:
            content = content[:15000] + "\n\n[Content truncated...]"
        sections.append(content)

        # Portfolio companies
        if input_data.portfolio_companies:
            sections.append(
                f"\n## Portfolio Companies ({len(input_data.portfolio_companies)} total)"
            )
            for i, company in enumerate(input_data.portfolio_companies[:20], 1):  # Max 20
                name = company.get("company_name", "Unknown")
                industry = company.get("industry", "Unknown")
                size = company.get("employee_range") or company.get("employee_count", "Unknown")
                location = company.get("location") or company.get("country", "")

                sections.append(
                    f"{i}. **{name}** - {industry}, {size} employees{', ' + location if location else ''}"
                )

        # Existing ICP (if refining)
        if input_data.existing_icp:
            sections.append("\n## Existing ICP Data (for refinement)")
            for key, value in input_data.existing_icp.items():
                if value:
                    sections.append(f"- {key}: {value}")

        return "\n".join(sections)

    def _build_prompt(self, input_data: ICPInput) -> str:
        """Build the user prompt."""
        if input_data.existing_icp:
            return (
                f"Refine and improve the ICP for {input_data.client_name}. "
                f"Use the existing data as a starting point, but validate and enhance it "
                f"with additional research. Focus on making pain points more specific "
                f"and evidence-based."
            )
        else:
            return (
                f"Build a comprehensive Ideal Customer Profile for {input_data.client_name}. "
                f"Analyze their website content and portfolio to understand who they serve best. "
                f"Use web_search to research industry trends and validate your assumptions. "
                f"Be specific and actionable - a salesperson should know exactly who to target."
            )


# ============================================
# FACTORY FUNCTION
# ============================================


def get_icp_agent() -> ICPAgent:
    """Get ICP Agent instance."""
    return ICPAgent()


async def extract_icp(
    client_name: str,
    website_url: str,
    website_content: str,
    portfolio_companies: list[dict] | None = None,
    social_links: dict | None = None,
    existing_icp: dict | None = None,
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Convenience function to extract ICP.

    Args:
        client_name: Agency name
        website_url: Agency website
        website_content: Scraped website text
        portfolio_companies: Enriched portfolio data
        social_links: Social media URLs
        existing_icp: Existing ICP to refine
        client_id: Client ID for tracking

    Returns:
        SDKBrainResult with ICPOutput
    """
    agent = get_icp_agent()

    input_data = ICPInput(
        client_name=client_name,
        website_url=website_url,
        website_content=website_content,
        portfolio_companies=portfolio_companies or [],
        social_links=social_links or {},
        existing_icp=existing_icp,
    )

    return await agent.extract(input_data, client_id=client_id)
