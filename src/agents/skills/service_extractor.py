"""
Contract: src/agents/skills/service_extractor.py
Purpose: Extract and categorize services offered by a marketing agency
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, agents.skills.website_parser, integrations
Consumers: ICP discovery agent

FILE: src/agents/skills/service_extractor.py
TASK: ICP-004
PHASE: 11 (ICP Discovery System)
PURPOSE: Extract and categorize services offered by a marketing agency

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/website_parser.py (for PageContent)
- src/integrations/anthropic.py

EXPORTS:
- ServiceExtractorSkill
- ServiceInfo (output model)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.website_parser import PageContent

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class ServiceInfo(BaseModel):
    """
    Information about a single service offered.

    Captures service name, category, and details
    for understanding agency capabilities.
    """

    name: str = Field(description="Service name")
    category: str = Field(
        description="Category: digital_marketing, branding, web_development, content, social_media, seo, ppc, email_marketing, analytics, consulting, design, video, pr, other"
    )
    description: str = Field(default="", description="Brief description of the service")
    is_primary: bool = Field(
        default=False, description="Whether this appears to be a primary/flagship service"
    )
    mentioned_on_pages: list[str] = Field(
        default_factory=list, description="Page types where this service is mentioned"
    )


class ServiceExtractorSkill(
    BaseSkill["ServiceExtractorSkill.Input", "ServiceExtractorSkill.Output"]
):
    """
    Identify and categorize services a marketing agency offers.

    This skill analyzes parsed website content to:
    - Identify all services mentioned
    - Categorize them into standard marketing categories
    - Determine primary vs secondary services
    - Note which pages mention each service

    The output helps understand what the agency does
    and informs ICP derivation (what industries they serve).
    """

    name = "extract_services"
    description = "Identify services a marketing agency offers from website content"

    class Input(BaseModel):
        """Input for service extraction."""

        pages: list[PageContent] = Field(description="Parsed page content from website")
        company_name: str = Field(default="", description="Company name for context")

    class Output(BaseModel):
        """Output from service extraction."""

        services: list[ServiceInfo] = Field(
            default_factory=list, description="List of services identified"
        )
        primary_categories: list[str] = Field(
            default_factory=list, description="Primary service categories (top 3)"
        )
        service_focus: str = Field(
            default="", description="Brief description of agency's service focus"
        )
        confidence: float = Field(default=0.0, description="Confidence in extraction (0.0-1.0)")
        source_pages: list[str] = Field(
            default_factory=list, description="Page types used for extraction"
        )

    system_prompt = """You are a marketing agency analyst. Extract services from website content.

SERVICE CATEGORIES (use these exact values):
- digital_marketing: General digital marketing services
- branding: Brand strategy, identity, positioning
- web_development: Website design and development
- content: Content marketing, copywriting, blogs
- social_media: Social media management and marketing
- seo: Search engine optimization
- ppc: Paid advertising (Google Ads, Meta Ads)
- email_marketing: Email campaigns and automation
- analytics: Data analytics, reporting, insights
- consulting: Strategy consulting, audits
- design: Graphic design, creative services
- video: Video production, animation
- pr: Public relations, media
- other: Services not fitting above categories

EXTRACTION GUIDELINES:
1. Identify all services mentioned across all pages
2. Use the exact category names listed above
3. Mark services prominently featured on home/services pages as primary
4. Note which page types mention each service
5. Identify the top 3 primary categories
6. Write a brief service focus summary (1-2 sentences)

OUTPUT FORMAT:
Return valid JSON:
{
    "services": [
        {
            "name": "SEO Strategy",
            "category": "seo",
            "description": "Comprehensive SEO audits and optimization",
            "is_primary": true,
            "mentioned_on_pages": ["home", "services"]
        }
    ],
    "primary_categories": ["seo", "content", "web_development"],
    "service_focus": "Full-service digital agency specializing in SEO and content marketing for B2B companies.",
    "confidence": 0.9,
    "source_pages": ["home", "services", "about"]
}"""

    default_max_tokens = 2048
    default_temperature = 0.3

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for service extraction."""
        pages_text = []
        for page in input_data.pages:
            page_info = f"""
PAGE: {page.page_type.upper()} ({page.url})
Title: {page.title}
Headings: {", ".join(page.headings)}
Summary: {page.content_summary}
Key Points: {", ".join(page.key_points)}
CTAs: {", ".join(page.ctas)}
"""
            pages_text.append(page_info)

        company_context = (
            f"Company: {input_data.company_name}\n\n" if input_data.company_name else ""
        )

        return f"""{company_context}Analyze the following website content and extract all services offered:

{"---".join(pages_text)}

Identify all services, categorize them, and determine which are primary services. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute service extraction.

        Args:
            input_data: Validated input with parsed pages
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing extracted services
        """
        if not input_data.pages:
            return SkillResult.fail(
                error="No pages provided for service extraction",
                metadata={"pages_count": 0},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Convert services to ServiceInfo objects
            services = []
            for service_data in parsed.get("services", []):
                services.append(ServiceInfo(**service_data))

            output = self.Output(
                services=services,
                primary_categories=parsed.get("primary_categories", [])[:3],
                service_focus=parsed.get("service_focus", ""),
                confidence=parsed.get("confidence", 0.7),
                source_pages=parsed.get("source_pages", []),
            )

            return SkillResult.ok(
                data=output,
                confidence=output.confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "services_found": len(services),
                    "primary_services": len([s for s in services if s.is_primary]),
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Service extraction failed: {str(e)}",
                metadata={"pages_analyzed": len(input_data.pages)},
            )


# Register skill instance
SkillRegistry.register(ServiceExtractorSkill())


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
- [x] Standard service categories defined
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
- [x] ServiceInfo model exported for other components
"""
