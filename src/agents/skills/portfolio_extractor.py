"""
FILE: src/agents/skills/portfolio_extractor.py
TASK: ICP-006
PHASE: 11 (ICP Discovery System)
PURPOSE: Extract client logos, case studies, and testimonials from agency website

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/website_parser.py (for PageContent)
- src/integrations/anthropic.py

EXPORTS:
- PortfolioExtractorSkill
- PortfolioCompany (output model)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.website_parser import PageContent

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class PortfolioCompany(BaseModel):
    """
    Information about a client company from portfolio.

    Represents a company mentioned in case studies,
    client logos, or testimonials.
    """

    company_name: str = Field(description="Company name")
    company_domain: str | None = Field(
        default=None,
        description="Company website domain if identifiable"
    )
    source: str = Field(
        description="How discovered: logo, case_study, testimonial, client_list"
    )
    industry_hint: str | None = Field(
        default=None,
        description="Industry if mentioned or inferable"
    )
    testimonial_person: str | None = Field(
        default=None,
        description="Person who gave testimonial (if applicable)"
    )
    testimonial_title: str | None = Field(
        default=None,
        description="Title of testimonial person"
    )
    testimonial_text: str | None = Field(
        default=None,
        description="Testimonial content (if available)"
    )
    case_study_summary: str | None = Field(
        default=None,
        description="Brief summary of case study (if applicable)"
    )
    results_mentioned: list[str] = Field(
        default_factory=list,
        description="Results or metrics mentioned"
    )


class PortfolioExtractorSkill(BaseSkill["PortfolioExtractorSkill.Input", "PortfolioExtractorSkill.Output"]):
    """
    Extract client portfolio from website content.

    This skill identifies:
    - Client logos displayed
    - Case studies with company names
    - Testimonials with company/person info
    - Results and metrics mentioned

    The portfolio data is crucial for deriving ICP,
    as existing clients reveal the agency's ideal targets.
    """

    name = "extract_portfolio"
    description = "Find client logos, case studies, and testimonials from website"

    class Input(BaseModel):
        """Input for portfolio extraction."""

        pages: list[PageContent] = Field(
            description="Parsed page content from website"
        )
        company_name: str = Field(
            default="",
            description="Agency name for context"
        )

    class Output(BaseModel):
        """Output from portfolio extraction."""

        companies: list[PortfolioCompany] = Field(
            default_factory=list,
            description="Companies identified from portfolio"
        )
        total_clients_claimed: int | None = Field(
            default=None,
            description="Number of clients claimed (if mentioned, e.g., '100+ clients')"
        )
        notable_brands: list[str] = Field(
            default_factory=list,
            description="Well-known brand names identified"
        )
        industries_represented: list[str] = Field(
            default_factory=list,
            description="Industries found in portfolio"
        )
        source_distribution: dict = Field(
            default_factory=dict,
            description="Count by source: {logo: X, case_study: Y, testimonial: Z}"
        )
        confidence: float = Field(
            default=0.0,
            description="Confidence in extraction (0.0-1.0)"
        )

    system_prompt = """You are a portfolio analyst extracting client information from agency websites.

EXTRACTION GUIDELINES:

1. CLIENT LOGOS:
   - Look for "Our Clients", "Trusted by", logo grids
   - Note company names from image descriptions
   - Source: "logo"

2. CASE STUDIES:
   - Look for "Work", "Portfolio", "Case Studies" pages
   - Extract company name, industry, results
   - Source: "case_study"

3. TESTIMONIALS:
   - Look for quotes with attribution
   - Note: person name, title, company
   - Extract the testimonial text
   - Source: "testimonial"

4. INDUSTRIES:
   - Infer industry from company names/context
   - Common: tech, ecommerce, healthcare, finance, manufacturing, professional_services, retail, real_estate, education

5. NOTABLE BRANDS:
   - Flag well-known companies (Fortune 500, household names)
   - These validate agency credibility

OUTPUT FORMAT:
Return valid JSON:
{
    "companies": [
        {
            "company_name": "Acme Corp",
            "company_domain": "acme.com",
            "source": "case_study",
            "industry_hint": "manufacturing",
            "testimonial_person": null,
            "testimonial_title": null,
            "testimonial_text": null,
            "case_study_summary": "Increased lead generation by 200% in 6 months",
            "results_mentioned": ["200% lead increase", "6 month timeline"]
        },
        {
            "company_name": "TechStartup",
            "company_domain": null,
            "source": "testimonial",
            "industry_hint": "tech",
            "testimonial_person": "Jane Smith",
            "testimonial_title": "CMO",
            "testimonial_text": "They transformed our digital presence...",
            "case_study_summary": null,
            "results_mentioned": []
        }
    ],
    "total_clients_claimed": 150,
    "notable_brands": ["Microsoft", "Adobe"],
    "industries_represented": ["tech", "manufacturing", "retail"],
    "source_distribution": {
        "logo": 8,
        "case_study": 4,
        "testimonial": 6
    },
    "confidence": 0.85
}"""

    default_max_tokens = 3072
    default_temperature = 0.3

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for portfolio extraction."""
        pages_text = []
        for page in input_data.pages:
            # Include more detail for portfolio-relevant pages
            if page.page_type in ["portfolio", "case_studies", "home", "about"]:
                page_info = f"""
PAGE: {page.page_type.upper()} ({page.url})
Title: {page.title}
Headings: {', '.join(page.headings)}
Summary: {page.content_summary}
Key Points: {', '.join(page.key_points)}
Images: {', '.join(page.images_described)}
Has Client Logos: {page.has_client_logos}
Has Case Studies: {page.has_case_studies}
Has Testimonials: {page.has_testimonials}
"""
                pages_text.append(page_info)
            elif page.has_testimonials or page.has_client_logos or page.has_case_studies:
                page_info = f"""
PAGE: {page.page_type.upper()}
Summary: {page.content_summary}
Has Client Logos: {page.has_client_logos}
Has Case Studies: {page.has_case_studies}
Has Testimonials: {page.has_testimonials}
"""
                pages_text.append(page_info)

        if not pages_text:
            # Fallback to all pages if no relevant ones found
            for page in input_data.pages[:5]:
                pages_text.append(f"""
PAGE: {page.page_type.upper()}
Summary: {page.content_summary}
Key Points: {', '.join(page.key_points)}
""")

        context = f"Agency: {input_data.company_name}\n\n" if input_data.company_name else ""

        return f"""{context}Extract client portfolio information from this website content:

{'---'.join(pages_text)}

Identify all clients, case studies, and testimonials. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute portfolio extraction.

        Args:
            input_data: Validated input with parsed pages
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing extracted portfolio
        """
        if not input_data.pages:
            return SkillResult.fail(
                error="No pages provided for portfolio extraction",
                metadata={"pages_count": 0},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Convert companies to PortfolioCompany objects
            companies = []
            for company_data in parsed.get("companies", []):
                companies.append(PortfolioCompany(**company_data))

            output = self.Output(
                companies=companies,
                total_clients_claimed=parsed.get("total_clients_claimed"),
                notable_brands=parsed.get("notable_brands", []),
                industries_represented=parsed.get("industries_represented", []),
                source_distribution=parsed.get("source_distribution", {}),
                confidence=parsed.get("confidence", 0.7),
            )

            return SkillResult.ok(
                data=output,
                confidence=output.confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "companies_found": len(companies),
                    "case_studies": len([c for c in companies if c.source == "case_study"]),
                    "testimonials": len([c for c in companies if c.source == "testimonial"]),
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Portfolio extraction failed: {str(e)}",
                metadata={"pages_analyzed": len(input_data.pages)},
            )


# Register skill instance
SkillRegistry.register(PortfolioExtractorSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output Pydantic models defined
- [x] System prompt with clear instructions
- [x] Source types defined (logo, case_study, testimonial)
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
- [x] PortfolioCompany model exported
"""
