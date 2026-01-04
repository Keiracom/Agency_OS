"""
FILE: src/agents/skills/company_size_estimator.py
TASK: ICP-008
PHASE: 11 (ICP Discovery System)
PURPOSE: Estimate agency team size from website and LinkedIn data

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/website_parser.py (for PageContent)
- src/integrations/anthropic.py

EXPORTS:
- CompanySizeEstimatorSkill
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.website_parser import PageContent

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class LinkedInData(BaseModel):
    """LinkedIn company data for size estimation."""

    company_name: str = Field(default="", description="Company name on LinkedIn")
    employee_count: int | None = Field(default=None, description="Employee count from LinkedIn")
    employee_range: str | None = Field(default=None, description="Employee range (e.g., '11-50')")
    headquarters: str | None = Field(default=None, description="Headquarters location")
    founded_year: int | None = Field(default=None, description="Year founded")
    specialties: list[str] = Field(default_factory=list, description="Listed specialties")


class CompanySizeEstimatorSkill(BaseSkill["CompanySizeEstimatorSkill.Input", "CompanySizeEstimatorSkill.Output"]):
    """
    Estimate agency team size from available data.

    This skill uses:
    - About/Team page content
    - LinkedIn company data (if available)
    - Website indicators (office photos, team section)

    To estimate the agency's team size and operational scale.
    """

    name = "estimate_company_size"
    description = "Estimate agency team size from website and LinkedIn data"

    class Input(BaseModel):
        """Input for company size estimation."""

        about_page: PageContent | None = Field(
            default=None,
            description="About page content if available"
        )
        team_page: PageContent | None = Field(
            default=None,
            description="Team page content if available"
        )
        all_pages: list[PageContent] = Field(
            default_factory=list,
            description="All parsed pages for additional context"
        )
        linkedin_data: LinkedInData | None = Field(
            default=None,
            description="LinkedIn company data if available"
        )
        company_name: str = Field(
            default="",
            description="Company name for context"
        )

    class Output(BaseModel):
        """Output from company size estimation."""

        team_size: int = Field(
            description="Estimated team size (number of employees)"
        )
        size_range: str = Field(
            description="Size range: solo, micro (2-5), small (6-20), medium (21-50), large (51-200), enterprise (200+)"
        )
        confidence: float = Field(
            default=0.0,
            description="Confidence in estimate (0.0-1.0)"
        )
        evidence: list[str] = Field(
            default_factory=list,
            description="Evidence supporting the estimate"
        )
        years_in_business: int | None = Field(
            default=None,
            description="Years in business if determinable"
        )
        has_multiple_offices: bool = Field(
            default=False,
            description="Whether they have multiple office locations"
        )
        office_locations: list[str] = Field(
            default_factory=list,
            description="Office locations if mentioned"
        )

    system_prompt = """You are a business analyst estimating company size.

SIZE RANGES (use these exact values):
- solo: 1 person (freelancer/consultant)
- micro: 2-5 employees
- small: 6-20 employees
- medium: 21-50 employees
- large: 51-200 employees
- enterprise: 200+ employees

ESTIMATION INDICATORS:

1. DIRECT MENTIONS:
   - "Our team of X" → Direct count
   - Team page with photos → Count photos
   - LinkedIn employee count → Most reliable

2. INDIRECT INDICATORS:
   - Office photos (size of space)
   - Department mentions (HR, finance = larger)
   - Client volume ("100+ clients" suggests scale)
   - Founded year (older = potentially larger)
   - Multiple locations = at least medium

3. CONFIDENCE SCORING:
   - 0.9+: LinkedIn count or explicit mention
   - 0.7-0.9: Team photos countable
   - 0.5-0.7: Indirect indicators only
   - <0.5: Very limited data

OUTPUT FORMAT:
Return valid JSON:
{
    "team_size": 15,
    "size_range": "small",
    "confidence": 0.8,
    "evidence": [
        "Team page shows 12 employees",
        "Founded 2015 (8 years)",
        "Single office location"
    ],
    "years_in_business": 8,
    "has_multiple_offices": false,
    "office_locations": ["Sydney, Australia"]
}"""

    default_max_tokens = 1024
    default_temperature = 0.3

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for size estimation."""
        context = f"Company: {input_data.company_name}\n\n" if input_data.company_name else ""

        # Add LinkedIn data if available
        linkedin_text = ""
        if input_data.linkedin_data:
            ld = input_data.linkedin_data
            linkedin_text = f"""LINKEDIN DATA:
Employee Count: {ld.employee_count or 'Unknown'}
Employee Range: {ld.employee_range or 'Unknown'}
Headquarters: {ld.headquarters or 'Unknown'}
Founded: {ld.founded_year or 'Unknown'}
Specialties: {', '.join(ld.specialties) if ld.specialties else 'None listed'}
"""

        # Add about page
        about_text = ""
        if input_data.about_page:
            p = input_data.about_page
            about_text = f"""ABOUT PAGE:
Title: {p.title}
Summary: {p.content_summary}
Key Points: {', '.join(p.key_points)}
Images: {', '.join(p.images_described)}
"""

        # Add team page
        team_text = ""
        if input_data.team_page:
            p = input_data.team_page
            team_text = f"""TEAM PAGE:
Title: {p.title}
Summary: {p.content_summary}
Key Points: {', '.join(p.key_points)}
Images: {', '.join(p.images_described)}
"""

        # Add relevant info from other pages
        other_text = ""
        for page in input_data.all_pages[:3]:
            if page.page_type not in ["about", "team"] and page.content_summary:
                other_text += f"\n{page.page_type.upper()}: {page.content_summary[:200]}"

        return f"""{context}Estimate company size from this data:

{linkedin_text}
{about_text}
{team_text}

ADDITIONAL CONTEXT:{other_text}

Provide your best estimate with supporting evidence. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute company size estimation.

        Args:
            input_data: Validated input with page and LinkedIn data
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing size estimate
        """
        # Check if we have any useful data
        has_data = (
            input_data.about_page is not None or
            input_data.team_page is not None or
            input_data.linkedin_data is not None or
            len(input_data.all_pages) > 0
        )

        if not has_data:
            return SkillResult.fail(
                error="No data provided for size estimation",
                metadata={},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            output = self.Output(
                team_size=parsed.get("team_size", 10),
                size_range=parsed.get("size_range", "small"),
                confidence=parsed.get("confidence", 0.5),
                evidence=parsed.get("evidence", []),
                years_in_business=parsed.get("years_in_business"),
                has_multiple_offices=parsed.get("has_multiple_offices", False),
                office_locations=parsed.get("office_locations", []),
            )

            return SkillResult.ok(
                data=output,
                confidence=output.confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "had_linkedin_data": input_data.linkedin_data is not None,
                    "had_team_page": input_data.team_page is not None,
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Size estimation failed: {str(e)}",
                metadata={},
            )


# Register skill instance
SkillRegistry.register(CompanySizeEstimatorSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output Pydantic models defined
- [x] LinkedInData model for structured LinkedIn input
- [x] System prompt with clear instructions
- [x] Size ranges defined
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
"""
