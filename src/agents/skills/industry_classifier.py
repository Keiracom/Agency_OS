"""
Contract: src/agents/skills/industry_classifier.py
Purpose: Classify target industries from services and portfolio data
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, agents.skills.service_extractor, agents.skills.portfolio_extractor, integrations
Consumers: ICP discovery agent

FILE: src/agents/skills/industry_classifier.py
TASK: ICP-007
PHASE: 11 (ICP Discovery System)
PURPOSE: Classify target industries from services and portfolio data

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/service_extractor.py (for ServiceInfo)
- src/agents/skills/portfolio_extractor.py (for PortfolioCompany)
- src/integrations/anthropic.py

EXPORTS:
- IndustryClassifierSkill
- IndustryMatch (output model)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.portfolio_extractor import PortfolioCompany
from src.agents.skills.service_extractor import ServiceInfo

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class IndustryMatch(BaseModel):
    """
    Information about a target industry.

    Represents an industry the agency likely targets,
    with supporting evidence and confidence.
    """

    industry: str = Field(description="Industry name (standardized)")
    confidence: float = Field(
        description="Confidence this is a target industry (0.0-1.0)"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Evidence supporting this classification"
    )
    is_primary: bool = Field(
        default=False,
        description="Whether this is a primary target industry"
    )
    client_count: int = Field(
        default=0,
        description="Number of portfolio clients in this industry"
    )


# Standard industry categories
STANDARD_INDUSTRIES = [
    "technology",
    "saas",
    "ecommerce",
    "retail",
    "healthcare",
    "finance",
    "real_estate",
    "professional_services",
    "manufacturing",
    "construction",
    "hospitality",
    "education",
    "nonprofit",
    "legal",
    "automotive",
    "food_beverage",
    "media_entertainment",
    "travel",
    "energy",
    "agriculture",
    "logistics",
    "government",
    "b2b_general",
    "b2c_general",
]


class IndustryClassifierSkill(BaseSkill["IndustryClassifierSkill.Input", "IndustryClassifierSkill.Output"]):
    """
    Classify target industries from services and portfolio.

    This skill analyzes:
    - Services offered (industry-specific services)
    - Portfolio clients (actual client industries)
    - Value proposition hints

    To determine which industries the agency targets.
    """

    name = "classify_industries"
    description = "Determine target industries from services and portfolio analysis"

    class Input(BaseModel):
        """Input for industry classification."""

        services: list[ServiceInfo] = Field(
            default_factory=list,
            description="Services offered by the agency"
        )
        portfolio_companies: list[PortfolioCompany] = Field(
            default_factory=list,
            description="Companies from portfolio"
        )
        target_audience_hints: list[str] = Field(
            default_factory=list,
            description="Target audience hints from value prop"
        )
        company_name: str = Field(
            default="",
            description="Agency name for context"
        )

    class Output(BaseModel):
        """Output from industry classification."""

        industries: list[IndustryMatch] = Field(
            default_factory=list,
            description="Classified target industries"
        )
        primary_industries: list[str] = Field(
            default_factory=list,
            description="Top 3 primary industries"
        )
        industry_focus: str = Field(
            default="generalist",
            description="Focus type: specialist, niche, generalist"
        )
        focus_description: str = Field(
            default="",
            description="Description of industry focus"
        )
        confidence: float = Field(
            default=0.0,
            description="Overall confidence (0.0-1.0)"
        )

    system_prompt = f"""You are an industry analyst classifying agency target markets.

STANDARD INDUSTRIES (use these exact values):
{chr(10).join(f'- {ind}' for ind in STANDARD_INDUSTRIES)}

CLASSIFICATION GUIDELINES:

1. EVIDENCE SOURCES:
   - Portfolio clients: Strong evidence (actual clients)
   - Industry-specific services: Medium evidence
   - Target audience hints: Supporting evidence

2. PRIMARY vs SECONDARY:
   - Primary: 3+ clients OR explicit targeting
   - Secondary: 1-2 clients OR implied targeting

3. FOCUS TYPE:
   - specialist: 70%+ clients in one industry
   - niche: 50%+ clients in 2-3 related industries
   - generalist: Diverse client base

4. CONFIDENCE SCORING:
   - 0.9+: Multiple clients + explicit targeting
   - 0.7-0.9: Some clients or clear service alignment
   - 0.5-0.7: Implied from services/positioning
   - <0.5: Weak or no evidence

OUTPUT FORMAT:
Return valid JSON:
{{
    "industries": [
        {{
            "industry": "saas",
            "confidence": 0.9,
            "evidence": ["5 SaaS clients in portfolio", "Explicit B2B SaaS messaging"],
            "is_primary": true,
            "client_count": 5
        }},
        {{
            "industry": "ecommerce",
            "confidence": 0.7,
            "evidence": ["2 ecommerce case studies", "Shopify partner"],
            "is_primary": false,
            "client_count": 2
        }}
    ],
    "primary_industries": ["saas", "technology"],
    "industry_focus": "niche",
    "focus_description": "Specializes in B2B SaaS and technology companies with some ecommerce work",
    "confidence": 0.85
}}"""

    default_max_tokens = 2048
    default_temperature = 0.3

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for industry classification."""
        # Format services
        services_text = ""
        if input_data.services:
            services_list = [f"- {s.name} ({s.category})" for s in input_data.services]
            services_text = "\nSERVICES OFFERED:\n" + "\n".join(services_list)

        # Format portfolio with industry hints
        portfolio_text = ""
        if input_data.portfolio_companies:
            portfolio_list = []
            for c in input_data.portfolio_companies:
                industry = f" [{c.industry_hint}]" if c.industry_hint else ""
                portfolio_list.append(f"- {c.company_name}{industry} ({c.source})")
            portfolio_text = "\nPORTFOLIO COMPANIES:\n" + "\n".join(portfolio_list)

        # Format hints
        hints_text = ""
        if input_data.target_audience_hints:
            hints_text = "\nTARGET AUDIENCE HINTS:\n- " + "\n- ".join(input_data.target_audience_hints)

        context = f"Agency: {input_data.company_name}\n" if input_data.company_name else ""

        return f"""{context}Classify target industries based on this data:
{services_text}
{portfolio_text}
{hints_text}

Determine which industries this agency targets and why. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute industry classification.

        Args:
            input_data: Validated input with services and portfolio
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing classified industries
        """
        # Need at least some data to classify
        if not input_data.services and not input_data.portfolio_companies:
            return SkillResult.fail(
                error="No services or portfolio data provided for classification",
                metadata={},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Convert industries to IndustryMatch objects
            industries = []
            for ind_data in parsed.get("industries", []):
                industries.append(IndustryMatch(**ind_data))

            output = self.Output(
                industries=industries,
                primary_industries=parsed.get("primary_industries", [])[:3],
                industry_focus=parsed.get("industry_focus", "generalist"),
                focus_description=parsed.get("focus_description", ""),
                confidence=parsed.get("confidence", 0.7),
            )

            return SkillResult.ok(
                data=output,
                confidence=output.confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "industries_classified": len(industries),
                    "primary_count": len([i for i in industries if i.is_primary]),
                    "focus": output.industry_focus,
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Industry classification failed: {str(e)}",
                metadata={},
            )


# Register skill instance
SkillRegistry.register(IndustryClassifierSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output Pydantic models defined
- [x] Standard industries list defined
- [x] System prompt with clear instructions
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
- [x] IndustryMatch model exported
"""
