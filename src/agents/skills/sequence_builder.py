"""
Contract: src/agents/skills/sequence_builder.py
Purpose: Build optimal multi-channel touch sequences for campaigns
Layer: 4 - agents/skills
Imports: agents.skills.base_skill
Consumers: campaign generation agent

FILE: src/agents/skills/sequence_builder.py
TASK: CAM-001, 16C-002, 16D-002
PHASE: 12A (Campaign Generation - Core), modified Phase 16 for Conversion Intelligence
PURPOSE: Build optimal multi-channel touch sequences for campaigns

DEPENDENCIES:
- src/agents/skills/base_skill.py

EXPORTS:
- SequenceBuilderSkill: Skill for building campaign sequences
- SequenceTouch: Model for a single touch in sequence
- SequenceBuilderOutput: Complete sequence output

PHASE 16 CHANGES:
- Added optional when_patterns and how_patterns fields to Input
- Uses WHEN patterns for optimal timing (best days, hours, touch gaps)
- Uses HOW patterns for channel prioritization (effectiveness, multi-channel lift)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class SequenceTouch(BaseModel):
    """A single touch in the campaign sequence."""

    day: int = Field(..., ge=1, description="Day of the touch (1-based)")
    channel: Literal["email", "linkedin", "sms", "voice", "mail"] = Field(
        ..., description="Channel for this touch"
    )
    purpose: Literal[
        "intro", "connect", "value_add", "pattern_interrupt", "breakup", "discovery"
    ] = Field(..., description="Purpose of this touch")
    condition: str | None = Field(
        None, description="Condition for sending (e.g., 'no_reply', 'als_score >= 85')"
    )
    skip_if: str | None = Field(
        None, description="Skip condition (e.g., 'phone_missing', 'linkedin_url_missing')"
    )
    messaging_key: str = Field(..., description="Key for looking up generated messaging content")


class SequenceBuilderSkill(BaseSkill["SequenceBuilderSkill.Input", "SequenceBuilderSkill.Output"]):
    """
    Build optimal multi-channel touch sequences for campaigns.

    This skill creates the "Growth Engine" sequence - a proven 6-touch
    multi-channel approach that adapts based on:
    - Available channels
    - Industry norms
    - Lead engagement
    - ALS score thresholds

    The sequence is designed to maximize response rates while
    respecting lead preferences and data availability.
    """

    name: ClassVar[str] = "sequence_builder"
    description: ClassVar[str] = (
        "Build multi-channel touch sequences for campaigns. "
        "Creates the optimal timing, channel mix, and conditions for outreach."
    )

    class Input(BaseModel):
        """Input for sequence building."""

        icp_profile: dict[str, Any] = Field(..., description="Full ICPProfile as dictionary")
        available_channels: list[Literal["email", "linkedin", "sms", "voice", "mail"]] = Field(
            ..., description="Channels available for this campaign"
        )
        sequence_days: int = Field(14, ge=7, le=30, description="Total sequence duration in days")
        aggressive: bool = Field(False, description="Use faster timing for hot leads")

        # Phase 16: Pattern insights (optional)
        when_patterns: dict[str, Any] | None = Field(
            None,
            description="WHEN pattern insights from Conversion Intelligence. "
            "Includes best days, best hours, optimal touch gaps.",
        )
        how_patterns: dict[str, Any] | None = Field(
            None,
            description="HOW pattern insights from Conversion Intelligence. "
            "Includes channel effectiveness, multi-channel lift, winning sequences.",
        )

    class Output(BaseModel):
        """Complete campaign sequence output."""

        sequence_name: str = Field(..., description="Name for the sequence")
        total_days: int = Field(..., description="Total duration in days")
        total_touches: int = Field(..., description="Number of touches")
        touches: list[SequenceTouch] = Field(..., description="Ordered list of touches")
        adaptive_rules: list[str] = Field(
            ..., description="Runtime behavior rules for the sequence"
        )
        channel_summary: dict[str, int] = Field(..., description="Count of touches per channel")

    system_prompt: ClassVar[
        str
    ] = """You are a sales sequence strategist. Given an ICP profile and available channels,
build an optimal touch sequence following the "Growth Engine" pattern.

The Growth Engine sequence is:
1. Email intro (Day 1) - Personalized, hint at pain point, no pitch
2. LinkedIn connect (Day 3) - Brief, professional, mutual benefit
3. Email value add (Day 5) - Share insight, not just follow-up
4. SMS pattern interrupt (Day 8) - Short, direct, conversational
5. Email breakup (Day 12) - Last chance, soft close
6. Voice discovery (Day 14) - For hot leads only (ALS >= 85)

Adjust timing based on:
- Industry norms (B2B SaaS = faster, Healthcare = slower)
- aggressive flag (if True, compress to 10 days)
- Available channels (skip unavailable)

SKIP CONDITIONS:
- linkedin: skip_if = "linkedin_url_missing"
- sms: skip_if = "phone_missing"
- voice: skip_if = "phone_missing"
- mail: skip_if = "address_missing"

CONDITIONS:
- All touches after first: condition = "no_reply"
- Voice: condition = "als_score >= 85 AND no_reply"

ADAPTIVE RULES (always include):
1. "Stop sequence immediately if reply detected"
2. "Classify reply intent (interested, not_interested, meeting_request)"
3. "Accelerate next touch by 1 day if email opened 3+ times"
4. "Skip channel if required data missing (don't fail)"

Return JSON with this exact structure:
{
    "sequence_name": "Growth Engine - [Industry]",
    "total_days": 14,
    "total_touches": 6,
    "touches": [
        {
            "day": 1,
            "channel": "email",
            "purpose": "intro",
            "condition": null,
            "skip_if": null,
            "messaging_key": "touch_1_email"
        }
    ],
    "adaptive_rules": ["..."],
    "channel_summary": {"email": 3, "linkedin": 1}
}"""

    default_model: ClassVar[str] = "claude-3-5-sonnet-20241022"
    default_max_tokens: ClassVar[int] = 2048
    default_temperature: ClassVar[float] = 0.5

    def build_prompt(self, input_data: Input) -> str:
        """Build prompt from input data."""
        icp = input_data.icp_profile

        # Extract key ICP fields
        industries = icp.get("icp_industries", [])
        primary_industry = industries[0] if industries else "general"

        prompt = f"""Build a campaign sequence for the following:

ICP PROFILE:
- Primary Industry: {primary_industry}
- All Industries: {", ".join(industries) if industries else "Not specified"}
- Target Titles: {", ".join(icp.get("icp_titles", [])) if icp.get("icp_titles") else "Not specified"}
- Pain Points: {", ".join(icp.get("icp_pain_points", [])) if icp.get("icp_pain_points") else "Not specified"}

AVAILABLE CHANNELS: {", ".join(input_data.available_channels)}
SEQUENCE DURATION: {input_data.sequence_days} days
AGGRESSIVE MODE: {input_data.aggressive}"""

        # Phase 16: Add WHEN pattern insights if available
        if input_data.when_patterns:
            patterns = input_data.when_patterns
            prompt += "\n\nTIMING INTELLIGENCE (optimize based on historical data):"

            # Best days
            if patterns.get("best_days"):
                days = [d.get("day", "") for d in patterns["best_days"][:3]]
                prompt += f"\n- Best days for outreach: {', '.join(days)}"

            # Best hours
            if patterns.get("best_hours"):
                hours = [str(h.get("hour", "")) for h in patterns["best_hours"][:3]]
                prompt += f"\n- Best hours: {', '.join(hours)}:00"

            # Optimal gaps
            gaps = patterns.get("optimal_sequence_gaps", {})
            if gaps:
                prompt += "\n- Optimal days between touches:"
                for gap_key, gap_days in gaps.items():
                    prompt += f"\n  - {gap_key.replace('_', ' ')}: {gap_days} days"

            # Converting touch
            if patterns.get("converting_touch_distribution"):
                dist = patterns["converting_touch_distribution"]
                if dist:
                    top_touch = max(dist.items(), key=lambda x: x[1])[0]
                    prompt += f"\n- Most conversions happen at: {top_touch.replace('_', ' ')}"

        # Phase 16: Add HOW pattern insights if available
        if input_data.how_patterns:
            patterns = input_data.how_patterns
            prompt += "\n\nCHANNEL INTELLIGENCE (prioritize based on conversion data):"

            # Channel effectiveness
            if patterns.get("channel_effectiveness"):
                channels = patterns["channel_effectiveness"][:3]
                rankings = [
                    f"{c.get('channel', '')}: {c.get('conversion_rate', 0):.1%}" for c in channels
                ]
                prompt += f"\n- Channel conversion rates: {', '.join(rankings)}"

            # Multi-channel recommendation
            multi = patterns.get("multi_channel_lift", {})
            if multi.get("recommendation") == "multi":
                lift = multi.get("multi_channel_lift", 1.0)
                prompt += f"\n- Multi-channel lift: {lift:.1f}x (use multiple channels)"
            elif multi.get("recommendation") == "single":
                prompt += "\n- Single channel performs well (focus on best channel)"

            # Winning sequences
            sequences = patterns.get("sequence_patterns", {}).get("winning_sequences", [])
            if sequences:
                top_seq = sequences[0].get("sequence", "")
                prompt += f"\n- High-converting channel sequence: {top_seq}"

        prompt += """

Build the Growth Engine sequence using only the available channels.
If a channel is not available, skip that touch entirely (don't substitute).
Use the timing and channel intelligence to optimize the sequence when available.

Return the complete sequence as JSON."""

        return prompt

    async def execute(
        self,
        input_data: Input,
        anthropic: AnthropicClient,
    ) -> SkillResult[Output]:
        """
        Execute the skill to build a campaign sequence.

        Args:
            input_data: Validated input with ICP and channel info
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing the sequence or error
        """
        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Validate output
            output = self.validate_output(parsed)

            # Calculate confidence based on channel coverage
            available = set(input_data.available_channels)
            used = set(output.channel_summary.keys())
            coverage = len(used.intersection(available)) / len(available) if available else 0
            confidence = min(0.95, 0.7 + (coverage * 0.25))

            return SkillResult.ok(
                data=output,
                confidence=confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "primary_industry": input_data.icp_profile.get("icp_industries", ["unknown"])[0]
                    if input_data.icp_profile.get("icp_industries")
                    else "unknown",
                    "channels_used": list(used),
                    "aggressive_mode": input_data.aggressive,
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Failed to build sequence: {str(e)}",
                metadata={"input_channels": input_data.available_channels},
            )

    def get_default_sequence(
        self,
        available_channels: list[str],
        aggressive: bool = False,
    ) -> Output:
        """
        Get a default sequence without AI call.

        Useful for testing or when AI is unavailable.

        Args:
            available_channels: Available channels
            aggressive: Use faster timing

        Returns:
            Default sequence output
        """
        # Base timing (standard)
        timing = {
            "intro": 1,
            "connect": 3,
            "value_add": 5,
            "pattern_interrupt": 8,
            "breakup": 12,
            "discovery": 14,
        }

        # Aggressive timing (compressed)
        if aggressive:
            timing = {
                "intro": 1,
                "connect": 2,
                "value_add": 4,
                "pattern_interrupt": 6,
                "breakup": 8,
                "discovery": 10,
            }

        touches: list[SequenceTouch] = []
        channel_summary: dict[str, int] = {}

        # Touch 1: Email intro
        if "email" in available_channels:
            touches.append(
                SequenceTouch(
                    day=timing["intro"],
                    channel="email",
                    purpose="intro",
                    condition=None,
                    skip_if=None,
                    messaging_key="touch_1_email",
                )
            )
            channel_summary["email"] = channel_summary.get("email", 0) + 1

        # Touch 2: LinkedIn connect
        if "linkedin" in available_channels:
            touches.append(
                SequenceTouch(
                    day=timing["connect"],
                    channel="linkedin",
                    purpose="connect",
                    condition=None,
                    skip_if="linkedin_url_missing",
                    messaging_key="touch_2_linkedin",
                )
            )
            channel_summary["linkedin"] = channel_summary.get("linkedin", 0) + 1

        # Touch 3: Email value add
        if "email" in available_channels:
            touches.append(
                SequenceTouch(
                    day=timing["value_add"],
                    channel="email",
                    purpose="value_add",
                    condition="no_reply",
                    skip_if=None,
                    messaging_key="touch_3_email",
                )
            )
            channel_summary["email"] = channel_summary.get("email", 0) + 1

        # Touch 4: SMS pattern interrupt
        if "sms" in available_channels:
            touches.append(
                SequenceTouch(
                    day=timing["pattern_interrupt"],
                    channel="sms",
                    purpose="pattern_interrupt",
                    condition="no_reply",
                    skip_if="phone_missing",
                    messaging_key="touch_4_sms",
                )
            )
            channel_summary["sms"] = channel_summary.get("sms", 0) + 1

        # Touch 5: Email breakup
        if "email" in available_channels:
            touches.append(
                SequenceTouch(
                    day=timing["breakup"],
                    channel="email",
                    purpose="breakup",
                    condition="no_reply",
                    skip_if=None,
                    messaging_key="touch_5_email",
                )
            )
            channel_summary["email"] = channel_summary.get("email", 0) + 1

        # Touch 6: Voice discovery (hot leads only)
        if "voice" in available_channels:
            touches.append(
                SequenceTouch(
                    day=timing["discovery"],
                    channel="voice",
                    purpose="discovery",
                    condition="als_score >= 85 AND no_reply",
                    skip_if="phone_missing",
                    messaging_key="touch_6_voice",
                )
            )
            channel_summary["voice"] = channel_summary.get("voice", 0) + 1

        # Calculate total days
        total_days = max(t.day for t in touches) if touches else 0

        return self.Output(
            sequence_name="Growth Engine - Default",
            total_days=total_days,
            total_touches=len(touches),
            touches=touches,
            adaptive_rules=[
                "Stop sequence immediately if reply detected",
                "Classify reply intent (interested, not_interested, meeting_request)",
                "Accelerate next touch by 1 day if email opened 3+ times",
                "Skip channel if required data missing (don't fail)",
            ],
            channel_summary=channel_summary,
        )


# Register the skill
SkillRegistry.register(SequenceBuilderSkill())


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
- [x] Docstrings on class and all methods
--- Phase 16 Additions ---
- [x] Optional when_patterns field in Input
- [x] Optional how_patterns field in Input
- [x] WHEN pattern insights integrated (timing, gaps)
- [x] HOW pattern insights integrated (channel effectiveness)
"""
