"""
Contract: src/agents/skills/value_prop_extractor.py
Purpose: Extract agency value proposition, taglines, and differentiators
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, agents.skills.website_parser, integrations
Consumers: ICP discovery agent

FILE: src/agents/skills/value_prop_extractor.py
TASK: ICP-005
PHASE: 11 (ICP Discovery System)
PURPOSE: Extract agency value proposition, taglines, and differentiators

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/website_parser.py (for PageContent)
- src/integrations/anthropic.py

EXPORTS:
- ValuePropExtractorSkill
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.website_parser import PageContent

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class ValuePropExtractorSkill(
    BaseSkill["ValuePropExtractorSkill.Input", "ValuePropExtractorSkill.Output"]
):
    """
    Extract agency's value proposition and key messaging.

    This skill analyzes website content to identify:
    - Core value proposition
    - Taglines and slogans
    - Key differentiators
    - Unique selling points
    - Brand promises

    The output helps understand how the agency positions
    itself and what makes them different from competitors.
    """

    name = "extract_value_prop"
    description = "Find the agency's value proposition and key messaging"

    class Input(BaseModel):
        """Input for value proposition extraction."""

        pages: list[PageContent] = Field(description="Parsed page content from website")
        company_name: str = Field(default="", description="Company name for context")
        services: list[str] = Field(default_factory=list, description="Known services for context")

    class Output(BaseModel):
        """Output from value proposition extraction."""

        value_proposition: str = Field(description="Core value proposition (1-2 sentences)")
        taglines: list[str] = Field(
            default_factory=list, description="Taglines, slogans, and headlines"
        )
        differentiators: list[str] = Field(
            default_factory=list, description="Key differentiators and unique selling points"
        )
        brand_promises: list[str] = Field(
            default_factory=list, description="Promises or guarantees made"
        )
        target_audience_hints: list[str] = Field(
            default_factory=list, description="Hints about who they target (from messaging)"
        )
        tone: str = Field(
            default="professional",
            description="Brand tone: professional, friendly, bold, creative, technical, casual",
        )
        confidence: float = Field(default=0.0, description="Confidence in extraction (0.0-1.0)")

    system_prompt = """You are a brand strategist analyzing marketing agency websites.
Extract the value proposition and key messaging.

EXTRACTION GUIDELINES:

1. VALUE PROPOSITION:
   - Look for hero section headlines, "About" page openings
   - Should answer: "What do they do and why does it matter?"
   - Extract as 1-2 sentences, not just taglines

2. TAGLINES:
   - Short, punchy phrases (usually 3-8 words)
   - Found in headers, footers, logos
   - Examples: "Results that speak", "Your growth partner"

3. DIFFERENTIATORS:
   - What makes them unique vs competitors
   - Specializations, methodologies, guarantees
   - Examples: "Data-driven approach", "20+ years experience"

4. BRAND PROMISES:
   - Explicit or implicit guarantees
   - ROI claims, timeline promises
   - Examples: "30-day results", "100% satisfaction"

5. TARGET AUDIENCE HINTS:
   - Clues about who they serve from messaging
   - Industry references, company size mentions
   - Examples: "For ambitious startups", "Enterprise solutions"

6. TONE:
   - professional: Formal, corporate
   - friendly: Warm, approachable
   - bold: Confident, assertive
   - creative: Artistic, innovative
   - technical: Data-focused, precise
   - casual: Relaxed, conversational

OUTPUT FORMAT:
Return valid JSON:
{
    "value_proposition": "We help B2B companies grow through data-driven digital marketing that delivers measurable ROI.",
    "taglines": [
        "Growth that matters",
        "Your digital partner"
    ],
    "differentiators": [
        "Proprietary analytics platform",
        "Industry specialists",
        "Transparent reporting"
    ],
    "brand_promises": [
        "Monthly performance reports",
        "No long-term contracts"
    ],
    "target_audience_hints": [
        "B2B companies",
        "Growth-stage businesses",
        "Marketing directors"
    ],
    "tone": "professional",
    "confidence": 0.85
}"""

    default_max_tokens = 1536
    default_temperature = 0.4

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for value proposition extraction."""
        pages_text = []
        for page in input_data.pages:
            page_info = f"""
PAGE: {page.page_type.upper()}
Title: {page.title}
Headings: {", ".join(page.headings)}
Summary: {page.content_summary}
Key Points: {", ".join(page.key_points)}
CTAs: {", ".join(page.ctas)}
"""
            pages_text.append(page_info)

        context = f"Company: {input_data.company_name}\n" if input_data.company_name else ""
        if input_data.services:
            context += f"Known Services: {', '.join(input_data.services)}\n"

        return f"""{context}
Analyze the following website content and extract the value proposition and messaging:

{"---".join(pages_text)}

Focus on identifying what makes this agency unique. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute value proposition extraction.

        Args:
            input_data: Validated input with parsed pages
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing extracted value proposition
        """
        if not input_data.pages:
            return SkillResult.fail(
                error="No pages provided for value proposition extraction",
                metadata={"pages_count": 0},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            output = self.Output(
                value_proposition=parsed.get("value_proposition", ""),
                taglines=parsed.get("taglines", []),
                differentiators=parsed.get("differentiators", []),
                brand_promises=parsed.get("brand_promises", []),
                target_audience_hints=parsed.get("target_audience_hints", []),
                tone=parsed.get("tone", "professional"),
                confidence=parsed.get("confidence", 0.7),
            )

            return SkillResult.ok(
                data=output,
                confidence=output.confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "taglines_found": len(output.taglines),
                    "differentiators_found": len(output.differentiators),
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Value proposition extraction failed: {str(e)}",
                metadata={"pages_analyzed": len(input_data.pages)},
            )


# Register skill instance
SkillRegistry.register(ValuePropExtractorSkill())


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
- [x] Tone categories defined
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
"""
