"""
Contract: src/agents/skills/industry_researcher.py
Purpose: Web search skill to supplement weak ICP data with industry research
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, integrations
Consumers: campaign generation agent, ICP discovery agent

FILE: src/agents/skills/industry_researcher.py
TASK: CAM-008
PHASE: 12B (Campaign Enhancement)
PURPOSE: Web search skill to supplement weak ICP data with industry research

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/integrations/serper.py
- src/integrations/anthropic.py

EXPORTS:
- IndustryResearcherSkill: Skill for researching industry pain points and trends
- IndustryResearcherInput: Input model
- IndustryResearcherOutput: Output model

Triggered when:
- ICP confidence < 0.6
- Website scraping yields insufficient data
- Manual industry research requested
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillResult
from src.integrations.serper import SerperClient, get_serper_client

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class IndustryResearcherInput(BaseModel):
    """Input model for Industry Researcher skill."""

    # Required
    industry: str = Field(
        ...,
        description="Primary industry to research (e.g., 'healthcare', 'SaaS', 'legal')"
    )

    # Optional context
    agency_services: list[str] = Field(
        default_factory=list,
        description="Services the agency offers (helps focus research)"
    )
    target_titles: list[str] = Field(
        default_factory=list,
        description="Target job titles (helps identify relevant pain points)"
    )
    location: str = Field(
        default="Australia",
        description="Geographic focus for research"
    )

    # Search parameters
    search_depth: Literal["quick", "standard", "deep"] = Field(
        default="standard",
        description="How thorough the research should be"
    )


class DiscoveredPainPoint(BaseModel):
    """A discovered pain point with evidence."""

    pain_point: str = Field(
        ...,
        description="The pain point statement"
    )
    evidence: str = Field(
        ...,
        description="Where this was discovered (source URL or search result)"
    )
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How relevant to the agency's services (0-1)"
    )
    outreach_angle: str = Field(
        default="",
        description="Suggested angle for cold outreach messaging"
    )


class IndustryInsight(BaseModel):
    """An industry insight or trend."""

    insight: str = Field(
        ...,
        description="The insight or trend"
    )
    source: str = Field(
        ...,
        description="Source URL or reference"
    )
    implication: str = Field(
        default="",
        description="What this means for outreach strategy"
    )


class CompetitorInfo(BaseModel):
    """Information about a key industry player."""

    name: str
    description: str
    relevance: str = Field(
        default="",
        description="Why this competitor matters for prospecting"
    )


class IndustryResearcherOutput(BaseModel):
    """Output model for Industry Researcher skill."""

    # Core outputs
    industry: str
    pain_points: list[DiscoveredPainPoint] = Field(default_factory=list)
    industry_insights: list[IndustryInsight] = Field(default_factory=list)
    key_players: list[CompetitorInfo] = Field(default_factory=list)

    # ICP enhancement suggestions
    suggested_titles: list[str] = Field(
        default_factory=list,
        description="Additional job titles to target"
    )
    suggested_company_sizes: list[str] = Field(
        default_factory=list,
        description="Ideal company size ranges"
    )
    messaging_angles: list[str] = Field(
        default_factory=list,
        description="Suggested angles for cold outreach"
    )

    # Metadata
    sources_searched: int = 0
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the research quality"
    )
    search_queries_used: list[str] = Field(default_factory=list)


class IndustryResearcherSkill(BaseSkill[IndustryResearcherInput, IndustryResearcherOutput]):
    """
    Skill to research industry pain points and trends via web search.

    Used when ICP extraction yields insufficient data (confidence < 0.6).
    Searches Google via Serper API, then uses Claude to synthesize findings.

    Flow:
    1. Run industry-specific searches via Serper
    2. Collect pain points, trends, key players
    3. Use Claude to analyze and structure findings
    4. Return enhanced ICP data suggestions
    """

    name: str = "industry_researcher"
    description: str = (
        "Research industry pain points, trends, and key players via web search. "
        "Use when ICP confidence is low or website scraping yields insufficient data."
    )

    # Nested type aliases for generic base class
    Input = IndustryResearcherInput
    Output = IndustryResearcherOutput

    system_prompt: str = """You are an expert B2B market researcher specializing in identifying pain points and opportunities for outreach campaigns.

Given web search results about an industry, your task is to:

1. IDENTIFY PAIN POINTS: Extract specific, actionable pain points that businesses in this industry face. Focus on problems that could be solved by the agency's services.

2. FIND INSIGHTS: Identify industry trends, challenges, and opportunities that could inform outreach messaging.

3. SUGGEST OUTREACH ANGLES: For each pain point, suggest how it could be used in cold outreach messaging.

4. RECOMMEND TARGETS: Suggest job titles and company sizes most likely to feel these pain points.

OUTPUT FORMAT:
- Be specific and actionable
- Cite sources where possible
- Prioritize pain points by relevance to the agency's services
- Focus on problems, not features or solutions
- Use language that resonates with the target industry

QUALITY CRITERIA:
- Pain points should be specific, not generic (e.g., "struggling to generate qualified leads from digital channels" not "need more leads")
- Insights should be current (2024-2025 relevant)
- Suggestions should be practical for cold outreach"""

    def __init__(self, serper_client: SerperClient | None = None):
        """
        Initialize Industry Researcher skill.

        Args:
            serper_client: Optional Serper client (uses singleton if not provided)
        """
        self._serper = serper_client or get_serper_client()

    async def execute(
        self,
        input_data: IndustryResearcherInput,
        anthropic: AnthropicClient,
    ) -> SkillResult[IndustryResearcherOutput]:
        """
        Execute industry research via web search and AI analysis.

        Args:
            input_data: Research parameters
            anthropic: Anthropic client for AI analysis

        Returns:
            SkillResult with industry research findings
        """
        try:
            # Determine search depth
            num_results = {
                "quick": 5,
                "standard": 10,
                "deep": 20,
            }.get(input_data.search_depth, 10)

            # Step 1: Run industry searches via Serper
            search_results = await self._serper.search_industry(
                industry=input_data.industry,
                location=input_data.location,
                num_results=num_results,
            )

            # Step 2: Run pain point specific searches
            pain_point_queries = [
                f"{input_data.industry} business challenges 2025",
                f"{input_data.industry} companies struggle with",
                f"why {input_data.industry} businesses fail",
            ]

            if input_data.agency_services:
                services_str = " ".join(input_data.agency_services[:3])
                pain_point_queries.append(
                    f"{input_data.industry} {services_str} problems"
                )

            pain_point_results = []
            for query in pain_point_queries:
                result = await self._serper.search(query, num_results)
                pain_point_results.append({
                    "query": query,
                    "results": [
                        {"title": r.title, "snippet": r.snippet, "link": r.link}
                        for r in result.organic[:5]
                    ],
                    "people_also_ask": result.people_also_ask[:3],
                })

            # Step 3: Compile search data for Claude analysis
            search_data = {
                "industry": input_data.industry,
                "location": input_data.location,
                "agency_services": input_data.agency_services,
                "target_titles": input_data.target_titles,
                "trends_search": [
                    {"title": r.title, "snippet": r.snippet}
                    for r in search_results.get("trends", []).organic[:5]
                ] if "trends" in search_results else [],
                "pain_point_searches": pain_point_results,
                "key_players": [
                    {"title": r.title, "snippet": r.snippet}
                    for r in search_results.get("key_players", []).organic[:5]
                ] if "key_players" in search_results else [],
                "news": [
                    {"title": r.title, "snippet": r.snippet}
                    for r in search_results.get("news", []).organic[:3]
                ] if "news" in search_results else [],
            }

            # Step 4: Use Claude to analyze and structure findings
            analysis_prompt = f"""Analyze these web search results about the {input_data.industry} industry and extract actionable insights for B2B outreach.

SEARCH DATA:
{self._format_search_data(search_data)}

AGENCY CONTEXT:
- Services: {', '.join(input_data.agency_services) if input_data.agency_services else 'General marketing/growth services'}
- Target Titles: {', '.join(input_data.target_titles) if input_data.target_titles else 'Decision makers'}
- Location: {input_data.location}

Please provide:

1. TOP 5 PAIN POINTS (specific, actionable problems)
For each:
- Pain point statement
- Evidence/source
- Relevance score (0.0-1.0) based on agency services fit
- Suggested outreach angle

2. TOP 3 INDUSTRY INSIGHTS/TRENDS
For each:
- The insight
- Source
- Implication for outreach

3. KEY PLAYERS (top 3 companies to know about)

4. RECOMMENDATIONS
- 3 additional job titles to target
- Ideal company size ranges
- 3 messaging angles for cold outreach

Format your response as structured data that can be parsed."""

            # Call Claude for analysis
            response = await anthropic.complete(
                system=self.system_prompt,
                prompt=analysis_prompt,
                max_tokens=2000,
            )

            # Step 5: Parse Claude's response into structured output
            output = await self._parse_analysis(
                response.content,
                input_data.industry,
                pain_point_queries,
                anthropic,
            )

            # Calculate confidence based on search quality
            total_results = sum(
                len(search_results.get(key, []).organic if hasattr(search_results.get(key, []), 'organic') else [])
                for key in ["trends", "key_players", "news"]
            )
            confidence = min(0.9, 0.5 + (total_results / 50))

            output.confidence = confidence
            output.sources_searched = total_results + len(pain_point_results) * 5
            output.search_queries_used = pain_point_queries

            return SkillResult.ok(
                data=output,
                confidence=confidence,
                tokens_used=response.usage.total_tokens if hasattr(response, 'usage') else 0,
                cost_aud=response.cost_aud if hasattr(response, 'cost_aud') else 0.0,
                metadata={
                    "industry": input_data.industry,
                    "search_depth": input_data.search_depth,
                    "sources_searched": output.sources_searched,
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Industry research failed: {str(e)}",
                metadata={"industry": input_data.industry},
            )

    def _format_search_data(self, data: dict) -> str:
        """Format search data for Claude prompt."""
        lines = []

        if data.get("trends_search"):
            lines.append("=== INDUSTRY TRENDS ===")
            for item in data["trends_search"]:
                lines.append(f"- {item['title']}: {item['snippet']}")

        if data.get("pain_point_searches"):
            lines.append("\n=== PAIN POINT SEARCHES ===")
            for search in data["pain_point_searches"]:
                lines.append(f"\nQuery: {search['query']}")
                for result in search["results"]:
                    lines.append(f"- {result['title']}: {result['snippet']}")
                if search.get("people_also_ask"):
                    lines.append("People Also Ask:")
                    for paa in search["people_also_ask"]:
                        if q := paa.get("question"):
                            lines.append(f"  ? {q}")

        if data.get("key_players"):
            lines.append("\n=== KEY PLAYERS ===")
            for item in data["key_players"]:
                lines.append(f"- {item['title']}: {item['snippet']}")

        if data.get("news"):
            lines.append("\n=== RECENT NEWS ===")
            for item in data["news"]:
                lines.append(f"- {item['title']}: {item['snippet']}")

        return "\n".join(lines)

    async def _parse_analysis(
        self,
        analysis_text: str,
        industry: str,
        queries: list[str],
        anthropic: AnthropicClient,
    ) -> IndustryResearcherOutput:
        """
        Parse Claude's analysis into structured output.

        Uses a second Claude call to ensure structured extraction.
        """
        extraction_prompt = f"""Extract structured data from this industry analysis.

ANALYSIS:
{analysis_text}

Return a JSON object with this exact structure:
{{
    "pain_points": [
        {{
            "pain_point": "specific pain point",
            "evidence": "source or evidence",
            "relevance_score": 0.8,
            "outreach_angle": "suggested messaging angle"
        }}
    ],
    "industry_insights": [
        {{
            "insight": "the trend or insight",
            "source": "source reference",
            "implication": "what it means for outreach"
        }}
    ],
    "key_players": [
        {{
            "name": "Company Name",
            "description": "brief description",
            "relevance": "why they matter"
        }}
    ],
    "suggested_titles": ["Title 1", "Title 2"],
    "suggested_company_sizes": ["11-50", "51-200"],
    "messaging_angles": ["angle 1", "angle 2"]
}}

Extract ONLY what's in the analysis. If something is missing, use empty arrays."""

        try:
            response = await anthropic.complete(
                system="You are a JSON extraction assistant. Return only valid JSON, no markdown.",
                prompt=extraction_prompt,
                max_tokens=1500,
            )

            import json
            # Clean response - remove markdown if present
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            data = json.loads(content)

            # Build output from parsed data
            pain_points = [
                DiscoveredPainPoint(**pp)
                for pp in data.get("pain_points", [])[:5]
            ]

            insights = [
                IndustryInsight(**ins)
                for ins in data.get("industry_insights", [])[:3]
            ]

            players = [
                CompetitorInfo(**p)
                for p in data.get("key_players", [])[:3]
            ]

            return IndustryResearcherOutput(
                industry=industry,
                pain_points=pain_points,
                industry_insights=insights,
                key_players=players,
                suggested_titles=data.get("suggested_titles", [])[:5],
                suggested_company_sizes=data.get("suggested_company_sizes", [])[:3],
                messaging_angles=data.get("messaging_angles", [])[:3],
            )

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: return minimal output
            return IndustryResearcherOutput(
                industry=industry,
                pain_points=[
                    DiscoveredPainPoint(
                        pain_point="Unable to parse detailed pain points - manual review recommended",
                        evidence="Web search completed but AI parsing failed",
                        relevance_score=0.5,
                        outreach_angle="Focus on general industry challenges",
                    )
                ],
                messaging_angles=["Focus on solving industry-specific challenges"],
            )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
# [x] Extends BaseSkill with proper generics
# [x] Input model with all required fields
# [x] Output model with structured results
# [x] system_prompt defined
# [x] execute() method implemented
# [x] Uses Serper integration for web search
# [x] Uses Anthropic for AI analysis
# [x] Proper error handling with SkillResult.fail()
# [x] Confidence calculation based on data quality
# [x] Type hints on all functions
# [x] No hardcoded secrets
# [x] No placeholder code
