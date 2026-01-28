"""
Contract: src/agents/campaign_evolution/how_analyzer_agent.py
Purpose: Analyze HOW patterns to generate channel optimization suggestions
Layer: 3 - agents
Imports: models, integrations (sdk_brain)
Consumers: campaign_orchestrator_agent, campaign_evolution_flow
Phase: Phase D - Item 18

HOW Analyzer examines channel patterns (email vs voice vs LinkedIn)
and generates channel mix optimization suggestions.
"""

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.integrations.sdk_brain import SDKBrainResult, create_sdk_brain

logger = logging.getLogger(__name__)


# ============================================
# OUTPUT SCHEMA
# ============================================


class ChannelRecommendation(BaseModel):
    """A specific channel optimization recommendation."""

    channel: str = Field(description="The channel (email, voice, linkedin, sms)")
    current_allocation: float = Field(description="Current percentage allocation (0-100)")
    suggested_allocation: float = Field(description="Suggested percentage allocation (0-100)")
    reason: str = Field(description="Why this change is recommended based on patterns")
    expected_lift: float = Field(description="Expected improvement (e.g., 1.2 = 20% better)")


class SequenceRecommendation(BaseModel):
    """A recommended multi-channel sequence."""

    sequence_name: str = Field(description="Name for this sequence pattern")
    channels: list[str] = Field(
        description="Ordered list of channels (e.g., ['email', 'linkedin', 'email'])"
    )
    description: str = Field(description="Why this sequence works")
    conversion_rate: float = Field(description="Observed conversion rate for this pattern")
    sample_size: int = Field(description="Number of leads that followed this sequence")


class TierChannelStrategy(BaseModel):
    """Channel strategy for a specific lead tier."""

    tier: str = Field(description="Lead tier (hot, warm, cool, cold)")
    primary_channel: str = Field(description="Best performing channel for this tier")
    secondary_channel: str = Field(description="Second best channel")
    avoid_channel: str | None = Field(description="Channel to avoid for this tier", default=None)
    rationale: str = Field(description="Why this strategy works for this tier")


class HOWAnalysis(BaseModel):
    """Output from HOW pattern analysis."""

    # High-level summary
    summary: str = Field(description="1-2 sentence summary of HOW pattern findings")

    # Channel recommendations
    channel_recommendations: list[ChannelRecommendation] = Field(
        default_factory=list,
        description="Specific channel allocation changes recommended",
    )

    # Sequence recommendations
    sequence_recommendations: list[SequenceRecommendation] = Field(
        default_factory=list,
        description="Multi-channel sequence patterns to adopt",
    )

    # Tier-specific strategies
    tier_strategies: list[TierChannelStrategy] = Field(
        default_factory=list,
        description="Channel strategies by lead tier",
    )

    # Multi-channel insights
    multi_channel_recommendation: str = Field(
        default="",
        description="Whether to use single or multi-channel approach",
    )
    multi_channel_lift: float = Field(
        default=1.0,
        description="Observed lift from multi-channel vs single-channel",
    )

    # Key insights
    key_insights: list[str] = Field(
        default_factory=list,
        description="Top 3-5 actionable channel insights",
    )

    # Timing considerations
    optimal_timing: dict[str, str] = Field(
        default_factory=dict,
        description="Optimal timing by channel (e.g., {'email': 'Tuesday 10AM'})",
    )

    # Confidence
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in this analysis (0.0-1.0)",
    )

    # Data quality notes
    data_quality_notes: str = Field(
        default="",
        description="Notes on data quality or limitations",
    )


# ============================================
# SYSTEM PROMPT
# ============================================

HOW_ANALYZER_SYSTEM_PROMPT = """You are a B2B channel optimization expert analyzing outreach patterns.

Your role is to examine HOW patterns (which channels and sequences convert best) and generate actionable channel strategy suggestions.

## Input Data You'll Receive

1. **HOW Patterns** from CIS (Conversion Intelligence System):
   - channel_effectiveness: Performance by channel (email, voice, linkedin, sms)
   - sequence_patterns: Multi-channel sequences that work
   - tier_channel_effectiveness: Channel performance by lead tier (hot/warm/cool/cold)
   - multi_channel_lift: Single vs multi-channel comparison
   - email_engagement_correlation: How email engagement predicts conversion
   - channel_conversation_quality: Conversation depth by channel

2. **WHEN Patterns** (timing data):
   - best_days: Best days of week by channel
   - best_hours: Best hours by channel
   - optimal_sequence_gaps: Time between touches

3. **Current Channel Strategy**:
   - Current channel allocation percentages
   - Current sequence patterns
   - Current timing rules

## Your Analysis Tasks

1. **Optimize Channel Allocation**
   - Compare current allocation to what actually converts
   - Suggest reallocation with expected lift
   - Consider cost-effectiveness (voice is expensive)

2. **Recommend Sequences**
   - Identify winning multi-channel sequences
   - Suggest new sequences to test
   - Define optimal sequence gaps

3. **Tier-Specific Strategies**
   - Define optimal channels by lead tier
   - Hot leads may need voice; cold leads may need email first

## Output Guidelines

- Be SPECIFIC: "Increase LinkedIn from 15% to 25%" not "use more LinkedIn"
- Be DATA-DRIVEN: Always cite the pattern data that supports your recommendation
- Be COST-AWARE: Voice costs ~$2/call, email ~$0.01, LinkedIn ~$0.05
- Be TIER-AWARE: Different tiers may need different channel strategies

## Confidence Scoring

- 0.9+: Clear patterns with 100+ sample per channel
- 0.7-0.9: Good patterns with 50-100 sample per channel
- 0.5-0.7: Emerging patterns, worth testing
- <0.5: Insufficient data, recommend testing

Return your analysis in the specified JSON format."""


# ============================================
# CORE FUNCTION
# ============================================


async def run_how_analyzer(
    how_patterns: dict[str, Any],
    when_patterns: dict[str, Any] | None,
    current_strategy: dict[str, Any],
    campaign_metrics: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Run HOW pattern analysis to generate channel suggestions.

    Args:
        how_patterns: CIS HOW detector output
        when_patterns: CIS WHEN detector output (optional, for timing)
        current_strategy: Current channel allocation and strategy
        campaign_metrics: Current campaign performance (optional)
        client_id: Client UUID for cost tracking

    Returns:
        SDKBrainResult with HOWAnalysis data
    """
    # Build context prompt
    prompt_parts = []

    # HOW patterns
    prompt_parts.append("## HOW Patterns (from CIS)\n")
    prompt_parts.append(f"```json\n{_format_how_patterns(how_patterns)}\n```\n")

    # WHEN patterns (timing)
    if when_patterns:
        prompt_parts.append("\n## WHEN Patterns (Timing)\n")
        prompt_parts.append(f"```json\n{_format_when_patterns(when_patterns)}\n```\n")

    # Current strategy
    prompt_parts.append("\n## Current Channel Strategy\n")
    if current_strategy.get("channel_allocation"):
        prompt_parts.append(f"- Channel Allocation: {current_strategy['channel_allocation']}\n")
    if current_strategy.get("sequence_pattern"):
        prompt_parts.append(f"- Sequence Pattern: {current_strategy['sequence_pattern']}\n")
    if current_strategy.get("tier_strategies"):
        prompt_parts.append(f"- Tier Strategies: {current_strategy['tier_strategies']}\n")

    # Campaign metrics
    if campaign_metrics:
        prompt_parts.append("\n## Current Campaign Performance\n")
        prompt_parts.append(f"- Overall Reply Rate: {campaign_metrics.get('reply_rate', 'N/A')}%\n")
        prompt_parts.append(
            f"- Email Reply Rate: {campaign_metrics.get('email_reply_rate', 'N/A')}%\n"
        )
        prompt_parts.append(
            f"- LinkedIn Reply Rate: {campaign_metrics.get('linkedin_reply_rate', 'N/A')}%\n"
        )
        prompt_parts.append(
            f"- Voice Connect Rate: {campaign_metrics.get('voice_connect_rate', 'N/A')}%\n"
        )

    # Instructions
    prompt_parts.append("\n## Your Task\n")
    prompt_parts.append(
        "Analyze the HOW patterns and current channel strategy. "
        "Generate specific channel allocation recommendations. "
        "Recommend winning sequences to adopt. "
        "Define tier-specific channel strategies."
    )

    user_prompt = "".join(prompt_parts)

    # Create brain and run
    brain = create_sdk_brain("campaign_evolution_how")

    result = await brain.run(
        prompt=user_prompt,
        tools=[],  # No tools needed - analyzing provided data
        output_schema=HOWAnalysis,
        system=HOW_ANALYZER_SYSTEM_PROMPT,
    )

    logger.info(
        f"HOW analyzer complete: confidence={result.data.confidence if result.success else 'N/A'}, "
        f"cost=${result.cost_aud:.4f}"
    )

    return result


# ============================================
# HELPER FUNCTIONS
# ============================================


def _format_how_patterns(patterns: dict[str, Any]) -> str:
    """Format HOW patterns for prompt."""
    import json

    formatted = {}

    # Channel effectiveness
    if "channel_effectiveness" in patterns:
        formatted["channel_effectiveness"] = patterns["channel_effectiveness"]

    # Sequence patterns - top 5
    if "sequence_patterns" in patterns:
        sp = patterns["sequence_patterns"]
        formatted["winning_sequences"] = sp.get("winning_sequences", [])[:5]

    # Tier effectiveness
    if "tier_channel_effectiveness" in patterns:
        formatted["tier_channel_effectiveness"] = patterns["tier_channel_effectiveness"]

    # Multi-channel lift
    if "multi_channel_lift" in patterns:
        formatted["multi_channel_lift"] = patterns["multi_channel_lift"]

    # Baseline
    if "baseline_conversion_rate" in patterns:
        formatted["baseline_conversion_rate"] = patterns["baseline_conversion_rate"]

    return json.dumps(formatted, indent=2, default=str)


def _format_when_patterns(patterns: dict[str, Any]) -> str:
    """Format WHEN patterns for prompt."""
    import json

    formatted = {}

    # Best days - top 3
    if "best_days" in patterns:
        formatted["best_days"] = patterns["best_days"][:3]

    # Best hours - top 3
    if "best_hours" in patterns:
        formatted["best_hours"] = patterns["best_hours"][:3]

    # Sequence gaps
    if "optimal_sequence_gaps" in patterns:
        formatted["optimal_sequence_gaps"] = patterns["optimal_sequence_gaps"]

    return json.dumps(formatted, indent=2, default=str)


# ============================================
# CONVENIENCE WRAPPER
# ============================================


async def analyze_how_patterns(
    how_patterns: dict[str, Any],
    when_patterns: dict[str, Any] | None,
    current_strategy: dict[str, Any],
    campaign_metrics: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience wrapper for HOW analysis.

    Returns dict with analysis results or None if failed.
    """
    result = await run_how_analyzer(
        how_patterns=how_patterns,
        when_patterns=when_patterns,
        current_strategy=current_strategy,
        campaign_metrics=campaign_metrics,
        client_id=client_id,
    )

    if result.success and result.data:
        analysis = result.data.model_dump() if hasattr(result.data, "model_dump") else result.data
        return {
            **analysis,
            "source": "sdk_how_analyzer",
            "cost_aud": result.cost_aud,
        }

    logger.warning(f"HOW analysis failed: {result.error}")
    return None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Pydantic output schema (HOWAnalysis)
# [x] Detailed system prompt
# [x] Core async function (run_how_analyzer)
# [x] Uses create_sdk_brain pattern
# [x] No tools needed (analyzes provided data)
# [x] Convenience wrapper
# [x] Helper functions for data formatting
# [x] Logging
# [x] Type hints throughout
