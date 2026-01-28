"""
Contract: src/agents/skills/research_skills.py
Purpose: Deep research skills for Hot Lead enrichment (ALS > 85)
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, integrations
Consumers: scout engine, SDK agents

FILE: src/agents/skills/research_skills.py
PURPOSE: Deep research skills for Hot Lead enrichment (ALS > 85)
PHASE: 21 (Deep Research & UI)
TASK: SKILL-021
DEPENDENCIES:
  - src/agents/skills/base_skill.py
  - src/integrations/apify.py
  - src/integrations/anthropic.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines
"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.integrations.anthropic import AnthropicClient
from src.integrations.apify import ApifyClient, get_apify_client


class DeepResearchSkill(BaseSkill):
    """
    Deep Research skill for Hot Leads (ALS > 85).

    Uses Apify to scrape LinkedIn posts and Claude to generate
    personalized icebreaker hooks for outreach.
    """

    name: ClassVar[str] = "deep_research"
    description: ClassVar[str] = (
        "Scrape LinkedIn posts and generate icebreaker hooks for hot leads. "
        "Use when ALS score > 85 and linkedin_url is available."
    )

    class Input(BaseModel):
        """Input for deep research skill."""

        linkedin_url: str = Field(
            ...,
            description="LinkedIn profile URL to research",
        )
        first_name: str = Field(
            ...,
            description="Lead's first name for personalization",
        )
        last_name: str = Field(
            default="",
            description="Lead's last name for personalization",
        )
        company: str = Field(
            default="",
            description="Lead's company for context",
        )
        title: str = Field(
            default="",
            description="Lead's job title for context",
        )
        max_posts: int = Field(
            default=3,
            description="Maximum number of posts to analyze",
        )

    class Output(BaseModel):
        """Output from deep research skill."""

        linkedin_url: str = Field(..., description="The researched LinkedIn URL")
        posts_found: int = Field(default=0, description="Number of posts found")
        posts: list[dict[str, Any]] = Field(
            default_factory=list,
            description="List of scraped posts with content and dates",
        )
        icebreaker_hook: str = Field(
            default="",
            description="AI-generated 1-sentence icebreaker",
        )
        profile_summary: str = Field(
            default="",
            description="Brief summary of the profile",
        )
        recent_activity: str = Field(
            default="",
            description="Summary of recent professional activity",
        )

    system_prompt: ClassVar[str] = """You are a sales research assistant specializing in crafting personalized outreach.

Your task is to analyze LinkedIn posts and generate a compelling, natural-sounding icebreaker hook.

Guidelines for the icebreaker:
- Keep it to 1 sentence (max 25 words)
- Reference something specific from their recent posts
- Be genuine and conversational, not salesy
- Show you've done your research
- Make it easy to transition into a business conversation

Example good hooks:
- "Loved your take on AI adoption in marketing - especially the point about starting small."
- "Your post about leadership lessons resonated - curious how that shapes your approach at [Company]."
- "Saw your insights on remote team culture - we've been navigating similar challenges."

Return JSON with this structure:
{
    "icebreaker_hook": "Your 1-sentence hook here",
    "profile_summary": "2-3 sentence summary of who this person is professionally",
    "recent_activity": "Brief note on what they've been posting about recently"
}"""

    default_model: ClassVar[str] = "claude-sonnet-4-20250514"
    default_max_tokens: ClassVar[int] = 500
    default_temperature: ClassVar[float] = 0.7

    def __init__(
        self,
        apify_client: ApifyClient | None = None,
        **kwargs,
    ):
        """
        Initialize with optional Apify client.

        Args:
            apify_client: Optional Apify client (uses singleton if not provided)
        """
        super().__init__(**kwargs)
        self._apify = apify_client

    @property
    def apify(self) -> ApifyClient:
        """Get Apify client."""
        if self._apify is None:
            self._apify = get_apify_client()
        return self._apify

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute deep research on a LinkedIn profile.

        Args:
            input_data: Validated input with LinkedIn URL
            anthropic: Anthropic client for AI analysis

        Returns:
            SkillResult with posts and icebreaker hook
        """
        posts: list[dict[str, Any]] = []
        profile_data: dict[str, Any] = {}

        # Step 1: Scrape LinkedIn profile
        try:
            profiles = await self.apify.scrape_linkedin_profiles(
                [input_data.linkedin_url]
            )
            if profiles:
                profile_data = profiles[0]
                # Extract posts if available in profile data
                raw_posts = profile_data.get("posts", []) or profile_data.get("activity", [])
                for _i, post in enumerate(raw_posts[:input_data.max_posts]):
                    posts.append({
                        "content": post.get("text") or post.get("content", ""),
                        "date": post.get("date") or post.get("posted_date"),
                        "engagement": post.get("likes", 0) + post.get("comments", 0),
                    })
        except Exception:
            # Log but continue - we can still generate based on profile info
            pass

        # Step 2: If no posts found, try to get activity from profile
        if not posts and profile_data:
            # Use about/summary and recent experience as fallback context
            about = profile_data.get("about", "")
            headline = profile_data.get("title") or profile_data.get("headline", "")
            experience = profile_data.get("experience", [])

            if about or headline or experience:
                # Create synthetic "activity" from profile info
                posts.append({
                    "content": f"Profile headline: {headline}. About: {about[:500] if about else 'N/A'}",
                    "date": None,
                    "engagement": 0,
                    "type": "profile_summary",
                })

        # Step 3: Generate icebreaker hook using Claude
        if posts or profile_data:
            prompt = self._build_analysis_prompt(input_data, posts, profile_data)

            try:
                parsed, tokens, cost = await self._call_ai(anthropic, prompt)

                return SkillResult.ok(
                    data=self.Output(
                        linkedin_url=input_data.linkedin_url,
                        posts_found=len([p for p in posts if p.get("type") != "profile_summary"]),
                        posts=posts,
                        icebreaker_hook=parsed.get("icebreaker_hook", ""),
                        profile_summary=parsed.get("profile_summary", ""),
                        recent_activity=parsed.get("recent_activity", ""),
                    ),
                    confidence=0.85 if posts else 0.6,
                    tokens_used=tokens,
                    cost_aud=cost,
                    metadata={
                        "profile_found": bool(profile_data),
                        "posts_scraped": len(posts),
                    },
                )
            except Exception as e:
                return SkillResult.fail(
                    error=f"AI analysis failed: {str(e)}",
                    metadata={"posts_found": len(posts)},
                )

        # No data found
        return SkillResult.fail(
            error="Could not retrieve LinkedIn data",
            metadata={"linkedin_url": input_data.linkedin_url},
        )

    def _build_analysis_prompt(
        self,
        input_data: Input,
        posts: list[dict[str, Any]],
        profile_data: dict[str, Any],
    ) -> str:
        """Build prompt for Claude analysis."""
        prompt_parts = [
            "Analyze this LinkedIn profile and generate an icebreaker hook.\n",
            "\n## Target Person",
            f"- Name: {input_data.first_name} {input_data.last_name}".strip(),
            f"- Company: {input_data.company}" if input_data.company else "",
            f"- Title: {input_data.title}" if input_data.title else "",
        ]

        if profile_data:
            prompt_parts.extend([
                "\n## Profile Data",
                f"- Headline: {profile_data.get('title', profile_data.get('headline', 'N/A'))}",
                f"- Location: {profile_data.get('location', 'N/A')}",
                f"- Connections: {profile_data.get('connections', 'N/A')}",
            ])

            about = profile_data.get("about", "")
            if about:
                prompt_parts.append(f"- About: {about[:500]}...")

        if posts:
            prompt_parts.append("\n## Recent Posts/Activity")
            for i, post in enumerate(posts[:3], 1):
                content = post.get("content", "")[:400]
                date_str = post.get("date", "Unknown date")
                prompt_parts.append(f"\n### Post {i} ({date_str})\n{content}")

        prompt_parts.append(
            "\n\nGenerate a natural icebreaker hook based on this research. "
            "Return ONLY valid JSON, no other text."
        )

        return "\n".join(filter(None, prompt_parts))


# Register the skill
SkillRegistry.register(DeepResearchSkill())


class PersonalizationAnalysisSkill(BaseSkill):
    """
    Personalization Analysis skill for hyper-personalized outreach.

    Analyzes LinkedIn data (person + company) to identify:
    - Pain points
    - Personalization angles
    - Icebreaker hooks for all 5 channels
    - Topics to avoid
    - Best channel recommendation
    """

    name: ClassVar[str] = "personalization_analysis"
    description: ClassVar[str] = (
        "Analyze LinkedIn data to generate pain points, personalization angles, "
        "and icebreaker hooks for Email, SMS, LinkedIn, Voice, and Direct Mail."
    )

    class Input(BaseModel):
        """Input for personalization analysis."""

        # Lead info
        first_name: str = Field(..., description="Lead's first name")
        last_name: str = Field(default="", description="Lead's last name")
        title: str = Field(default="", description="Lead's job title")
        company_name: str = Field(default="", description="Lead's company")
        industry: str = Field(default="", description="Company industry")

        # LinkedIn person data
        person_headline: str = Field(default="", description="LinkedIn headline")
        person_about: str = Field(default="", description="LinkedIn about/summary")
        person_posts: list[dict[str, Any]] = Field(
            default_factory=list,
            description="Person's recent LinkedIn posts",
        )

        # LinkedIn company data
        company_description: str = Field(default="", description="Company description")
        company_specialties: list[str] = Field(default_factory=list, description="Company specialties")
        company_posts: list[dict[str, Any]] = Field(
            default_factory=list,
            description="Company's recent LinkedIn posts",
        )

        # Agency context (for relevance)
        agency_services: str = Field(default="", description="What the agency offers")

    class Output(BaseModel):
        """Output from personalization analysis."""

        pain_points: list[str] = Field(
            default_factory=list,
            description="Identified pain points based on role, posts, company stage",
        )
        personalization_angles: list[str] = Field(
            default_factory=list,
            description="Specific things to reference from their content",
        )
        icebreaker_hooks: dict[str, str] = Field(
            default_factory=dict,
            description="Per-channel hooks: email, linkedin, sms, voice, direct_mail",
        )
        topics_to_avoid: list[str] = Field(
            default_factory=list,
            description="Topics that could backfire",
        )
        common_ground: list[str] = Field(
            default_factory=list,
            description="Shared interests or experiences",
        )
        best_channel: str = Field(
            default="email",
            description="Recommended best channel for outreach",
        )
        best_timing: str = Field(
            default="",
            description="Recommended timing for outreach",
        )
        confidence: float = Field(
            default=0.5,
            description="Confidence in the analysis (0-1)",
        )

    system_prompt: ClassVar[str] = """You are a sales research analyst specializing in personalized B2B outreach.

Your task is to analyze LinkedIn data to create hyper-personalized outreach for 5 channels.

## Guidelines

### Pain Points
- Infer challenges from their role, company stage, and post topics
- Look for complaints, questions, or frustrations in posts
- Consider industry-specific challenges

### Personalization Angles
- Reference specific posts or achievements
- Note career milestones or transitions
- Identify shared interests or connections

### Icebreaker Hooks (per channel)
- **Email**: 1-2 sentences, can include specific reference
- **LinkedIn**: Short (300 char limit for connection requests)
- **SMS**: Very brief, casual tone, <100 chars
- **Voice**: Conversational opener for phone call
- **Direct Mail**: Headline that would grab attention

### Topics to Avoid
- Competitors mentioned positively
- Controversial opinions
- Personal/sensitive topics

### Best Channel
- LinkedIn: If they're active on LinkedIn (regular posts)
- Email: If they're executives or less active on social
- SMS: If in sales/customer-facing role
- Voice: If senior decision-maker

Return ONLY valid JSON matching the output schema."""

    default_model: ClassVar[str] = "claude-sonnet-4-20250514"
    default_max_tokens: ClassVar[int] = 1500
    default_temperature: ClassVar[float] = 0.7

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute personalization analysis on LinkedIn data.

        Args:
            input_data: Validated input with LinkedIn data
            anthropic: Anthropic client for AI analysis

        Returns:
            SkillResult with pain points, angles, and hooks
        """
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Calculate confidence based on data availability
            confidence = self._calculate_confidence(input_data, parsed)

            return SkillResult.ok(
                data=self.Output(
                    pain_points=parsed.get("pain_points", []),
                    personalization_angles=parsed.get("personalization_angles", []),
                    icebreaker_hooks=parsed.get("icebreaker_hooks", {}),
                    topics_to_avoid=parsed.get("topics_to_avoid", []),
                    common_ground=parsed.get("common_ground", []),
                    best_channel=parsed.get("best_channel", "email"),
                    best_timing=parsed.get("best_timing", ""),
                    confidence=confidence,
                ),
                confidence=confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "person_posts_analyzed": len(input_data.person_posts),
                    "company_posts_analyzed": len(input_data.company_posts),
                },
            )
        except Exception as e:
            return SkillResult.fail(
                error=f"Personalization analysis failed: {str(e)}",
                metadata={"input_name": f"{input_data.first_name} {input_data.last_name}"},
            )

    def _build_analysis_prompt(self, input_data: Input) -> str:
        """Build prompt for Claude analysis."""
        parts = [
            "Analyze this lead for personalized outreach.\n",
            "\n## Lead Profile",
            f"- Name: {input_data.first_name} {input_data.last_name}",
            f"- Title: {input_data.title}" if input_data.title else "",
            f"- Company: {input_data.company_name}" if input_data.company_name else "",
            f"- Industry: {input_data.industry}" if input_data.industry else "",
        ]

        # Person LinkedIn data
        if input_data.person_headline or input_data.person_about:
            parts.append("\n## Their LinkedIn Profile")
            if input_data.person_headline:
                parts.append(f"Headline: {input_data.person_headline}")
            if input_data.person_about:
                parts.append(f"About: {input_data.person_about[:800]}")

        # Person posts
        if input_data.person_posts:
            parts.append("\n## Their Recent Posts")
            for i, post in enumerate(input_data.person_posts[:5], 1):
                content = post.get("content", "")[:400]
                date_str = post.get("date", "")
                likes = post.get("likes", 0)
                parts.append(f"\n**Post {i}** ({date_str}, {likes} likes):\n{content}")

        # Company data
        if input_data.company_description or input_data.company_specialties:
            parts.append("\n## Their Company")
            if input_data.company_description:
                parts.append(f"Description: {input_data.company_description[:500]}")
            if input_data.company_specialties:
                parts.append(f"Specialties: {', '.join(input_data.company_specialties[:5])}")

        # Company posts
        if input_data.company_posts:
            parts.append("\n## Company's Recent Posts")
            for i, post in enumerate(input_data.company_posts[:3], 1):
                content = post.get("content", "")[:300]
                parts.append(f"\n**Company Post {i}**:\n{content}")

        # Agency context
        if input_data.agency_services:
            parts.append(f"\n## What We Offer\n{input_data.agency_services}")

        parts.append(
            "\n\nAnalyze this lead and generate personalized outreach data. "
            "Return ONLY valid JSON."
        )

        return "\n".join(filter(None, parts))

    def _calculate_confidence(self, input_data: Input, parsed: dict) -> float:
        """Calculate confidence based on data availability and output quality."""
        score = 0.3  # Base confidence

        # Data availability
        if input_data.person_headline:
            score += 0.1
        if input_data.person_about:
            score += 0.1
        if input_data.person_posts:
            score += 0.15
        if input_data.company_description:
            score += 0.05
        if input_data.company_posts:
            score += 0.1

        # Output quality
        if len(parsed.get("pain_points", [])) >= 2:
            score += 0.1
        if len(parsed.get("personalization_angles", [])) >= 2:
            score += 0.1

        return min(0.95, score)


# Register the skill
SkillRegistry.register(PersonalizationAnalysisSkill())


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Follows BaseSkill pattern
# [x] Input/Output Pydantic models
# [x] Uses ApifyIntegration for LinkedIn scraping
# [x] Uses AnthropicIntegration for icebreaker generation
# [x] Handles missing posts gracefully
# [x] Returns SkillResult with confidence and cost
# [x] Registered with SkillRegistry
# [x] No imports from engines (Rule 12)
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] PersonalizationAnalysisSkill for hyper-personalization (Phase 24A+)
# [x] Generates pain points, angles, hooks for all 5 channels
# [x] Analyzes person + company LinkedIn data
