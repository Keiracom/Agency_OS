"""
Contract: src/agents/skills/messaging_generator.py
Purpose: Generate channel-specific messaging content for campaign touches
Layer: 4 - agents/skills
Imports: agents.skills.base_skill
Consumers: campaign generation agent

FILE: src/agents/skills/messaging_generator.py
TASK: CAM-002, 16B-004
PHASE: 12A (Campaign Generation - Core), modified Phase 16 for Conversion Intelligence
PURPOSE: Generate channel-specific messaging content for campaign touches

DEPENDENCIES:
- src/agents/skills/base_skill.py

EXPORTS:
- MessagingGeneratorSkill: Skill for generating outreach copy
- MessagingGeneratorOutput: Generated messaging content

PHASE 16 CHANGES:
- Added optional what_patterns field to Input
- Uses WHAT pattern insights in prompt (subject patterns, CTAs, personalization lift)
- Prioritizes historically effective content patterns
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import BaseModel, Field, field_validator

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class MessagingGeneratorSkill(BaseSkill["MessagingGeneratorSkill.Input", "MessagingGeneratorSkill.Output"]):
    """
    Generate channel-specific messaging content for campaign touches.

    This skill creates personalized outreach copy for:
    - Email (subject lines + body)
    - SMS (160 char limit)
    - LinkedIn (connection notes + InMail)
    - Voice (talking points + objection handlers)

    All content uses placeholders for runtime personalization:
    {first_name}, {company}, {title}, {industry}, {pain_point}, etc.
    """

    name: ClassVar[str] = "messaging_generator"
    description: ClassVar[str] = (
        "Generate channel-specific outreach copy for campaign touches. "
        "Creates emails, SMS, LinkedIn messages, and voice scripts."
    )

    class Input(BaseModel):
        """Input for messaging generation."""

        # From ICP Profile
        icp_pain_points: list[str] = Field(
            ..., min_length=1, description="Target pain points from ICP"
        )
        icp_titles: list[str] = Field(
            ..., description="Target job titles from ICP"
        )
        agency_value_prop: str = Field(
            ..., min_length=10, description="Agency's value proposition"
        )
        agency_name: str = Field(
            ..., min_length=1, description="Agency name"
        )
        agency_services: list[str] = Field(
            ..., description="Services offered by the agency"
        )
        industry: str = Field(
            ..., min_length=1, description="Target industry"
        )

        # Generation parameters
        channel: Literal["email", "sms", "linkedin", "voice"] = Field(
            ..., description="Channel for this message"
        )
        touch_number: int = Field(
            ..., ge=1, le=10, description="Touch number in sequence (1-10)"
        )
        touch_purpose: Literal[
            "intro", "connect", "value_add", "pattern_interrupt", "follow_up", "breakup", "discovery"
        ] = Field(..., description="Purpose of this touch")
        tone: Literal["professional", "casual", "direct", "friendly", "formal"] = Field(
            "professional", description="Tone for the messaging"
        )

        # Phase 16: WHAT pattern insights (optional)
        what_patterns: dict[str, Any] | None = Field(
            None,
            description="WHAT pattern insights from Conversion Intelligence. "
            "Includes winning subject patterns, top CTAs, optimal length, personalization lift."
        )

    class Output(BaseModel):
        """Generated messaging output."""

        channel: str = Field(..., description="Channel for this message")
        touch_number: int = Field(..., description="Touch number")

        # Email fields (if channel == "email")
        subject_options: list[str] | None = Field(
            None, description="3 subject line variants (under 50 chars each)"
        )
        email_body: str | None = Field(
            None, description="Email body with {placeholders}"
        )

        # SMS fields (if channel == "sms")
        sms_message: str | None = Field(
            None, description="SMS message (under 160 chars)"
        )

        # LinkedIn fields (if channel == "linkedin")
        connection_note: str | None = Field(
            None, description="Connection request note (under 300 chars)"
        )
        inmail_body: str | None = Field(
            None, description="InMail message body"
        )

        # Voice fields (if channel == "voice")
        voice_script_points: list[str] | None = Field(
            None, description="Talking points for voice call"
        )
        voice_objection_handlers: dict[str, str] | None = Field(
            None, description="Common objections and responses"
        )

        # Metadata
        placeholders_used: list[str] = Field(
            default_factory=list, description="List of placeholders in the content"
        )
        pain_point_addressed: str = Field(
            "", description="Primary pain point addressed"
        )

        @field_validator("sms_message")
        @classmethod
        def validate_sms_length(cls, v: str | None) -> str | None:
            """Ensure SMS is under 160 characters."""
            if v and len(v) > 160:
                # Truncate if too long
                return v[:157] + "..."
            return v

        @field_validator("connection_note")
        @classmethod
        def validate_connection_note_length(cls, v: str | None) -> str | None:
            """Ensure LinkedIn connection note is under 300 characters."""
            if v and len(v) > 300:
                return v[:297] + "..."
            return v

    system_prompt: ClassVar[str] = """You are an expert cold outreach copywriter. Generate messaging for a specific
touch in a multi-channel sequence.

RULES:
1. Never use {company} in subject lines (spam trigger)
2. Subject lines under 50 characters
3. Email body under 150 words
4. SMS under 160 characters (CRITICAL - never exceed)
5. LinkedIn connection note under 300 characters
6. Voice scripts as bullet points, not full scripts
7. Always sound human, never robotic or salesy
8. Focus on THEIR problem, not your solution
9. One clear CTA per message
10. Use placeholders for personalization

PLACEHOLDER REFERENCE (use exactly as shown):
- {first_name} - Lead's first name
- {company} - Lead's company name
- {title} - Lead's job title
- {industry} - Lead's industry
- {pain_point} - Selected pain point
- {agency_name} - Your agency name
- {sender_name} - Sender's name

TONE BY INDUSTRY:
- Healthcare: Professional, trustworthy, patient-focused
- SaaS/Tech: Casual, direct, metrics-focused
- Professional Services: Formal, consultative
- Trades/Home Services: Straightforward, practical
- Ecommerce: Energetic, results-focused

TOUCH PURPOSE GUIDELINES:
- intro: Pattern interrupt, hint at pain, no pitch
- connect: LinkedIn connection - brief, professional
- value_add: Give something useful, build credibility
- pattern_interrupt: SMS - quick, direct, different
- follow_up: Quick check-in, reference previous touch
- breakup: Last attempt, acknowledge their time
- discovery: Voice talking points for initial call

Return JSON with the exact structure for the requested channel:

For EMAIL:
{
    "channel": "email",
    "touch_number": 1,
    "subject_options": ["Subject 1", "Subject 2", "Subject 3"],
    "email_body": "Hi {first_name},\\n\\nBody text...\\n\\nBest,\\n{sender_name}",
    "placeholders_used": ["first_name", "sender_name"],
    "pain_point_addressed": "inconsistent lead flow"
}

For SMS:
{
    "channel": "sms",
    "touch_number": 4,
    "sms_message": "Hi {first_name}, quick question about...",
    "placeholders_used": ["first_name"],
    "pain_point_addressed": "pain point here"
}

For LINKEDIN:
{
    "channel": "linkedin",
    "touch_number": 2,
    "connection_note": "Hi {first_name}, noticed your work at {company}...",
    "inmail_body": "Longer message for InMail...",
    "placeholders_used": ["first_name", "company"],
    "pain_point_addressed": "pain point here"
}

For VOICE:
{
    "channel": "voice",
    "touch_number": 6,
    "voice_script_points": ["Introduction", "Value prop", "Question", "CTA"],
    "voice_objection_handlers": {
        "too busy": "I understand. When would be better?",
        "not interested": "No problem. Mind if I ask what you're currently using?"
    },
    "placeholders_used": ["first_name", "company"],
    "pain_point_addressed": "pain point here"
}"""

    default_model: ClassVar[str] = "claude-3-5-sonnet-20241022"
    default_max_tokens: ClassVar[int] = 2048
    default_temperature: ClassVar[float] = 0.7

    def build_prompt(self, input_data: Input) -> str:
        """Build prompt from input data."""
        # Select primary pain point to address
        pain_point = input_data.icp_pain_points[0] if input_data.icp_pain_points else "business growth"

        prompt = f"""Generate {input_data.channel.upper()} messaging for touch #{input_data.touch_number}.

AGENCY INFO:
- Name: {input_data.agency_name}
- Value Proposition: {input_data.agency_value_prop}
- Services: {', '.join(input_data.agency_services)}

TARGET ICP:
- Industry: {input_data.industry}
- Titles: {', '.join(input_data.icp_titles)}
- Pain Points: {', '.join(input_data.icp_pain_points)}

GENERATION PARAMETERS:
- Channel: {input_data.channel}
- Touch Number: {input_data.touch_number}
- Touch Purpose: {input_data.touch_purpose}
- Tone: {input_data.tone}
- Primary Pain Point to Address: {pain_point}"""

        # Phase 16: Add WHAT pattern insights if available
        if input_data.what_patterns:
            patterns = input_data.what_patterns
            prompt += "\n\nCONVERSION INTELLIGENCE INSIGHTS (use these to optimize copy):"

            # Subject patterns
            subject_patterns = patterns.get("subject_patterns", {})
            if subject_patterns.get("winning_patterns"):
                winners = subject_patterns["winning_patterns"][:3]
                prompt += f"\n- Winning subject patterns: {', '.join([p.get('pattern', '') for p in winners])}"

            # CTAs
            ctas = patterns.get("ctas", {})
            if ctas.get("top_ctas"):
                top_ctas = [c.get("cta", "") for c in ctas["top_ctas"][:3]]
                prompt += f"\n- Most effective CTAs: {', '.join(top_ctas)}"

            # Optimal length
            optimal_length = patterns.get("optimal_length", {})
            if optimal_length.get("email"):
                prompt += f"\n- Optimal email length: {optimal_length['email'].get('optimal_word_count', 100)} words"

            # Personalization
            personalization = patterns.get("personalization_lift", {})
            if personalization.get("uses_name_lift", 1.0) > 1.1:
                prompt += "\n- Use first name (high personalization lift)"
            if personalization.get("uses_company_lift", 1.0) > 1.1:
                prompt += "\n- Reference company name (high conversion lift)"

            # Pain points that convert
            if patterns.get("pain_points", {}).get("top_pain_points"):
                top_pains = [p.get("pain_point", "") for p in patterns["pain_points"]["top_pain_points"][:2]]
                prompt += f"\n- High-converting pain points: {', '.join(top_pains)}"

        prompt += "\n\nGenerate the messaging content as JSON. Focus on the pain point and use appropriate placeholders."

        return prompt

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute the skill to generate messaging content.

        Args:
            input_data: Validated input with ICP and channel info
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing the messaging or error
        """
        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Validate output
            output = self.validate_output(parsed)

            # Calculate confidence based on content completeness
            confidence = self._calculate_confidence(output, input_data.channel)

            return SkillResult.ok(
                data=output,
                confidence=confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "channel": input_data.channel,
                    "touch_number": input_data.touch_number,
                    "industry": input_data.industry,
                    "placeholders": output.placeholders_used,
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Failed to generate messaging: {str(e)}",
                metadata={
                    "channel": input_data.channel,
                    "touch_number": input_data.touch_number,
                },
            )

    def _calculate_confidence(self, output: Output, channel: str) -> float:
        """Calculate confidence based on content completeness."""
        confidence = 0.7  # Base confidence

        if channel == "email":
            if output.subject_options and len(output.subject_options) >= 3:
                confidence += 0.1
            if output.email_body and len(output.email_body) > 50:
                confidence += 0.1
            if output.placeholders_used:
                confidence += 0.05

        elif channel == "sms":
            if output.sms_message:
                if len(output.sms_message) <= 160:
                    confidence += 0.2
                if output.placeholders_used:
                    confidence += 0.05

        elif channel == "linkedin":
            if output.connection_note and len(output.connection_note) <= 300:
                confidence += 0.1
            if output.inmail_body:
                confidence += 0.1
            if output.placeholders_used:
                confidence += 0.05

        elif channel == "voice":
            if output.voice_script_points and len(output.voice_script_points) >= 3:
                confidence += 0.1
            if output.voice_objection_handlers and len(output.voice_objection_handlers) >= 2:
                confidence += 0.1

        return min(0.95, confidence)

    def get_default_messaging(
        self,
        channel: str,
        touch_number: int,
        touch_purpose: str,
        agency_name: str = "Our Agency",
    ) -> Output:
        """
        Get default messaging without AI call.

        Useful for testing or when AI is unavailable.

        Args:
            channel: Channel type
            touch_number: Touch number
            touch_purpose: Purpose of the touch
            agency_name: Agency name for placeholders

        Returns:
            Default messaging output
        """
        if channel == "email":
            return self.Output(
                channel="email",
                touch_number=touch_number,
                subject_options=[
                    "Quick question for you",
                    "Idea for {company}",
                    "Thoughts?",
                ],
                email_body=f"""Hi {{first_name}},

I noticed {{company}} is in the {{industry}} space and thought you might be dealing with {{pain_point}}.

We've helped similar companies solve this - would love to share how.

Worth a quick chat?

Best,
{{sender_name}}
{agency_name}""",
                placeholders_used=["first_name", "company", "industry", "pain_point", "sender_name"],
                pain_point_addressed="general business challenges",
            )

        elif channel == "sms":
            return self.Output(
                channel="sms",
                touch_number=touch_number,
                sms_message="Hi {first_name}, sent you an email about {pain_point}. Worth 5 mins? -{sender_name}",
                placeholders_used=["first_name", "pain_point", "sender_name"],
                pain_point_addressed="general business challenges",
            )

        elif channel == "linkedin":
            return self.Output(
                channel="linkedin",
                touch_number=touch_number,
                connection_note="Hi {first_name}, noticed your work at {company}. Would love to connect and share some ideas.",
                inmail_body="""Hi {first_name},

I came across your profile and was impressed by what {company} is doing in {industry}.

We specialize in helping companies like yours with {pain_point}. Would you be open to a brief conversation?

Best,
{sender_name}""",
                placeholders_used=["first_name", "company", "industry", "pain_point", "sender_name"],
                pain_point_addressed="general business challenges",
            )

        else:  # voice
            return self.Output(
                channel="voice",
                touch_number=touch_number,
                voice_script_points=[
                    "Introduce yourself and agency briefly",
                    "Reference the emails you've sent",
                    "Ask about their current approach to {pain_point}",
                    "Listen for pain points and buying signals",
                    "If interested, suggest a brief meeting",
                ],
                voice_objection_handlers={
                    "too busy": "I understand. When would be a better time to call back?",
                    "not interested": "No problem at all. Mind if I ask what you're currently using for this?",
                    "send info": "Happy to. What's the best email? I'll include some case studies too.",
                    "in a meeting": "Apologies for the interruption. I'll try again tomorrow - what time works?",
                },
                placeholders_used=["pain_point"],
                pain_point_addressed="general business challenges",
            )


# Register the skill
SkillRegistry.register(MessagingGeneratorSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12) - only imports from base_skill
- [x] Uses dependency injection (AnthropicClient passed as argument)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output models defined as nested classes
- [x] System prompt present with detailed instructions
- [x] Registered with SkillRegistry
- [x] SkillResult used for return values
- [x] Confidence scoring based on output quality
- [x] Token/cost tracking passed through
- [x] Default fallback method for testing
- [x] Field validators for SMS/LinkedIn length limits
- [x] Placeholder reference documented
- [x] Docstrings on class and all methods
--- Phase 16 Additions ---
- [x] Optional what_patterns field in Input
- [x] WHAT pattern insights integrated into prompt
- [x] Subject patterns, CTAs, personalization lift used
"""
