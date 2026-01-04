"""
FILE: src/agents/skills/icp_deriver.py
TASK: ICP-009
PHASE: 11 (ICP Discovery System)
PURPOSE: Derive Ideal Customer Profile from enriched portfolio data

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/industry_classifier.py (for IndustryMatch)
- src/integrations/anthropic.py

EXPORTS:
- ICPDeriverSkill
- EnrichedCompany (input model)
- DerivedICP (output model)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.industry_classifier import IndustryMatch

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class EnrichedCompany(BaseModel):
    """
    Enriched company data from Apollo/LinkedIn.

    Represents a portfolio company with full enrichment data.
    """

    company_name: str = Field(description="Company name")
    domain: str | None = Field(default=None, description="Company domain")
    industry: str | None = Field(default=None, description="Industry classification")
    employee_count: int | None = Field(default=None, description="Number of employees")
    employee_range: str | None = Field(default=None, description="Employee range (e.g., '11-50')")
    annual_revenue: str | None = Field(default=None, description="Annual revenue range")
    location: str | None = Field(default=None, description="Headquarters location")
    country: str | None = Field(default=None, description="Country")
    founded_year: int | None = Field(default=None, description="Year founded")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")
    is_hiring: bool | None = Field(default=None, description="Currently hiring")
    linkedin_url: str | None = Field(default=None, description="LinkedIn company URL")
    source: str = Field(default="portfolio", description="How this company was found")


class DerivedICP(BaseModel):
    """
    Derived Ideal Customer Profile.

    The ICP pattern extracted from analyzing portfolio companies.
    """

    # Industry targeting
    icp_industries: list[str] = Field(
        default_factory=list,
        description="Target industries (top 3-5)"
    )
    industry_pattern: str = Field(
        default="",
        description="Description of industry pattern"
    )

    # Company size targeting
    icp_company_sizes: list[str] = Field(
        default_factory=list,
        description="Target company sizes (ranges)"
    )
    size_pattern: str = Field(
        default="",
        description="Description of size pattern"
    )

    # Revenue targeting
    icp_revenue_ranges: list[str] = Field(
        default_factory=list,
        description="Target revenue ranges"
    )

    # Geographic targeting
    icp_locations: list[str] = Field(
        default_factory=list,
        description="Target locations/regions"
    )
    location_pattern: str = Field(
        default="",
        description="Description of geographic focus"
    )

    # Technology/signals
    icp_technologies: list[str] = Field(
        default_factory=list,
        description="Common technologies among clients"
    )
    icp_signals: list[str] = Field(
        default_factory=list,
        description="Buying signals (hiring, growth, etc.)"
    )

    # Decision maker targeting
    icp_titles: list[str] = Field(
        default_factory=list,
        description="Target job titles"
    )

    # Pain points/needs
    icp_pain_points: list[str] = Field(
        default_factory=list,
        description="Common pain points addressed"
    )

    # Overall pattern
    pattern_description: str = Field(
        default="",
        description="1-2 sentence description of ideal customer"
    )
    pattern_confidence: float = Field(
        default=0.0,
        description="Confidence in derived pattern (0.0-1.0)"
    )


class ICPDeriverSkill(BaseSkill["ICPDeriverSkill.Input", "ICPDeriverSkill.Output"]):
    """
    Derive ICP pattern from enriched portfolio companies.

    This is the core ICP derivation skill that:
    - Analyzes enriched portfolio company data
    - Identifies common patterns (industry, size, location)
    - Determines targeting criteria
    - Suggests pain points and signals

    The output directly informs campaign targeting and
    custom ALS weight configuration.
    """

    name = "derive_icp"
    description = "Analyze portfolio companies to derive ICP pattern"

    class Input(BaseModel):
        """Input for ICP derivation."""

        enriched_portfolio: list[EnrichedCompany] = Field(
            description="Enriched portfolio companies"
        )
        classified_industries: list[IndustryMatch] = Field(
            default_factory=list,
            description="Pre-classified industries"
        )
        services_offered: list[str] = Field(
            default_factory=list,
            description="Agency services for context"
        )
        value_proposition: str = Field(
            default="",
            description="Agency value proposition for context"
        )
        company_name: str = Field(
            default="",
            description="Agency name"
        )

    class Output(BaseModel):
        """Output from ICP derivation."""

        icp: DerivedICP = Field(description="Derived ICP profile")
        sample_size: int = Field(default=0, description="Number of companies analyzed")
        data_quality: str = Field(
            default="low",
            description="Data quality: high, medium, low"
        )
        recommendations: list[str] = Field(
            default_factory=list,
            description="Recommendations for targeting"
        )

    system_prompt = """You are an ICP strategist deriving ideal customer profiles from portfolio data.

ANALYSIS FRAMEWORK:

1. INDUSTRY PATTERNS:
   - Which industries appear most frequently?
   - Are there adjacent/related industries?
   - What's the primary vertical focus?

2. COMPANY SIZE PATTERNS:
   - Use ranges: 1-10, 11-50, 51-200, 201-500, 500+
   - What's the "sweet spot" range?
   - Any size they explicitly avoid?

3. REVENUE PATTERNS:
   - Common ranges: <$1M, $1M-$10M, $10M-$50M, $50M-$100M, $100M+
   - What's the typical client revenue tier?

4. GEOGRAPHIC PATTERNS:
   - Primary locations/regions
   - Any international vs domestic focus?
   - Local, national, or global clients?

5. TECHNOLOGY/SIGNALS:
   - Common tech stack (Shopify, HubSpot, Salesforce, etc.)
   - Growth signals (hiring, recent funding)

6. DECISION MAKER PATTERNS:
   - Common titles: CEO, CMO, VP Marketing, Marketing Director
   - What level do they typically sell to?

7. PAIN POINTS:
   - Based on services + client mix, what problems do they solve?

OUTPUT FORMAT:
Return valid JSON:
{
    "icp": {
        "icp_industries": ["saas", "technology", "ecommerce"],
        "industry_pattern": "Primarily B2B SaaS with some ecommerce clients",
        "icp_company_sizes": ["11-50", "51-200"],
        "size_pattern": "Growth-stage companies past seed but pre-enterprise",
        "icp_revenue_ranges": ["$1M-$10M", "$10M-$50M"],
        "icp_locations": ["Australia", "United States"],
        "location_pattern": "Primarily Australian with some US expansion",
        "icp_technologies": ["HubSpot", "Salesforce", "Shopify"],
        "icp_signals": ["Recently funded", "Hiring marketing roles", "New product launch"],
        "icp_titles": ["CMO", "VP Marketing", "Head of Growth", "Marketing Director"],
        "icp_pain_points": [
            "Scaling lead generation",
            "Brand awareness in new markets",
            "Converting traffic to revenue"
        ],
        "pattern_description": "Growth-stage B2B SaaS companies ($1-50M revenue) in Australia seeking to scale marketing operations",
        "pattern_confidence": 0.85
    },
    "sample_size": 15,
    "data_quality": "high",
    "recommendations": [
        "Focus on Series A-B funded SaaS companies",
        "Target marketing leaders actively hiring",
        "Prioritize Australia before US expansion"
    ]
}"""

    default_max_tokens = 3072
    default_temperature = 0.4

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for ICP derivation."""
        context = f"Agency: {input_data.company_name}\n" if input_data.company_name else ""

        if input_data.services_offered:
            context += f"Services: {', '.join(input_data.services_offered)}\n"

        if input_data.value_proposition:
            context += f"Value Prop: {input_data.value_proposition}\n"

        # Format enriched companies
        companies_text = []
        for c in input_data.enriched_portfolio:
            company_info = f"""
- {c.company_name}
  Industry: {c.industry or 'Unknown'}
  Employees: {c.employee_count or c.employee_range or 'Unknown'}
  Revenue: {c.annual_revenue or 'Unknown'}
  Location: {c.location or c.country or 'Unknown'}
  Founded: {c.founded_year or 'Unknown'}
  Technologies: {', '.join(c.technologies[:5]) if c.technologies else 'Unknown'}
  Hiring: {c.is_hiring if c.is_hiring is not None else 'Unknown'}
  Source: {c.source}"""
            companies_text.append(company_info)

        # Add industry classification if available
        industry_text = ""
        if input_data.classified_industries:
            primary = [i.industry for i in input_data.classified_industries if i.is_primary]
            secondary = [i.industry for i in input_data.classified_industries if not i.is_primary][:3]
            industry_text = f"""
PRE-CLASSIFIED INDUSTRIES:
Primary: {', '.join(primary)}
Secondary: {', '.join(secondary)}
"""

        return f"""{context}
{industry_text}
Analyze these portfolio companies to derive ICP:

ENRICHED PORTFOLIO ({len(input_data.enriched_portfolio)} companies):
{''.join(companies_text)}

Identify patterns across industries, sizes, locations, and signals. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute ICP derivation.

        Args:
            input_data: Validated input with enriched portfolio
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing derived ICP
        """
        if not input_data.enriched_portfolio:
            return SkillResult.fail(
                error="No enriched portfolio data provided for ICP derivation",
                metadata={"portfolio_count": 0},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Parse ICP data
            icp_data = parsed.get("icp", {})
            icp = DerivedICP(**icp_data)

            output = self.Output(
                icp=icp,
                sample_size=parsed.get("sample_size", len(input_data.enriched_portfolio)),
                data_quality=parsed.get("data_quality", "medium"),
                recommendations=parsed.get("recommendations", []),
            )

            return SkillResult.ok(
                data=output,
                confidence=icp.pattern_confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "companies_analyzed": len(input_data.enriched_portfolio),
                    "industries_derived": len(icp.icp_industries),
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"ICP derivation failed: {str(e)}",
                metadata={"portfolio_count": len(input_data.enriched_portfolio)},
            )


# Register skill instance
SkillRegistry.register(ICPDeriverSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output Pydantic models defined
- [x] EnrichedCompany model for structured input
- [x] DerivedICP model with comprehensive fields
- [x] System prompt with clear analysis framework
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
- [x] Models exported for use by other components
"""
