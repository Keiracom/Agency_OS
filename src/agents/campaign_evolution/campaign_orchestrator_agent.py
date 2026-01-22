"""
Contract: src/agents/campaign_evolution/campaign_orchestrator_agent.py
Purpose: Orchestrate analyzer outputs into actionable campaign suggestions
Layer: 3 - agents
Imports: models, integrations (sdk_brain)
Consumers: campaign_evolution_flow
Phase: Phase D - Item 18

The Orchestrator Agent combines WHO, WHAT, and HOW analyzer outputs
to generate prioritized, actionable campaign suggestions that require
client approval before being applied.

CRITICAL: Suggestions are NEVER auto-applied. They require explicit client approval.
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


class CampaignSuggestion(BaseModel):
    """A single actionable campaign suggestion."""

    # Identification
    suggestion_type: str = Field(
        description="Type: create_campaign, pause_campaign, adjust_allocation, refine_targeting, change_channel_mix, update_content, adjust_timing"
    )
    title: str = Field(description="Short, actionable title (e.g., 'Pause Low-Performing Tech Campaign')")

    # Details
    description: str = Field(description="Detailed explanation of the suggestion (2-4 sentences)")
    rationale: dict[str, Any] = Field(
        description="Which patterns support this suggestion (pattern_type -> key findings)"
    )

    # Action
    recommended_action: dict[str, Any] = Field(
        description="Specific action to take (varies by suggestion_type)"
    )

    # For create_campaign
    new_campaign_spec: dict[str, Any] | None = Field(
        default=None,
        description="For create_campaign: {name, targeting, channels, messaging_angle}"
    )

    # For existing campaign actions
    target_campaign_criteria: dict[str, Any] | None = Field(
        default=None,
        description="Criteria to identify which campaign(s) this applies to"
    )

    # Confidence and priority
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in this suggestion (0.0-1.0)"
    )
    priority: int = Field(
        ge=1,
        le=100,
        description="Priority score (100 = highest priority)"
    )

    # Impact projections
    projected_improvement: dict[str, float] = Field(
        default_factory=dict,
        description="Expected improvements (e.g., {'reply_rate': 1.3, 'conversion_rate': 1.2})"
    )

    # Pattern sources
    pattern_types: list[str] = Field(
        default_factory=list,
        description="Which patterns informed this (who, what, how, when)"
    )

    # Risk assessment
    risk_level: str = Field(
        default="low",
        description="Risk level: low, medium, high"
    )
    risk_notes: str = Field(
        default="",
        description="Notes on potential risks or considerations"
    )


class CampaignSuggestionOutput(BaseModel):
    """Output from the campaign orchestrator."""

    # Summary
    executive_summary: str = Field(
        description="2-3 sentence summary for the client dashboard"
    )

    # Suggestions (prioritized)
    suggestions: list[CampaignSuggestion] = Field(
        default_factory=list,
        description="Prioritized list of campaign suggestions"
    )

    # Overall health assessment
    campaign_health_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall campaign health (0-100)"
    )
    health_assessment: str = Field(
        description="Brief health assessment (1-2 sentences)"
    )

    # Quick wins
    quick_wins: list[str] = Field(
        default_factory=list,
        description="Low-effort, high-impact suggestions (bullet points)"
    )

    # Strategic recommendations
    strategic_recommendations: list[str] = Field(
        default_factory=list,
        description="Longer-term strategic recommendations"
    )

    # Data gaps
    data_gaps: list[str] = Field(
        default_factory=list,
        description="Areas where more data is needed"
    )

    # Overall confidence
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in this analysis"
    )

    # Cost tracking
    total_analysis_cost_aud: float = Field(
        default=0.0,
        description="Total cost of WHO + WHAT + HOW + Orchestrator analysis"
    )


# ============================================
# SYSTEM PROMPT
# ============================================

ORCHESTRATOR_SYSTEM_PROMPT = """You are a senior B2B campaign strategist synthesizing insights from multiple data sources.

Your role is to combine WHO, WHAT, and HOW pattern analyses into prioritized, actionable campaign suggestions.

## CRITICAL RULES

1. **NEVER suggest auto-applying changes** - All suggestions require client approval
2. **Be conservative** - Only suggest changes with sufficient confidence (0.7+)
3. **Prioritize ruthlessly** - Maximum 5-7 suggestions, ranked by impact × confidence
4. **Be specific** - Vague suggestions are useless
5. **Show your work** - Always cite which patterns support each suggestion

## Input Data You'll Receive

1. **WHO Analysis**: Targeting refinements, segment opportunities, underperforming segments
2. **WHAT Analysis**: Messaging refinements, A/B test recommendations, winning/losing patterns
3. **HOW Analysis**: Channel recommendations, sequence recommendations, tier strategies

4. **Current Campaign State**: Active campaigns, their performance, current configurations
5. **Client Context**: Tier, budget constraints, preferences

## Suggestion Types

| Type | Trigger | Confidence Required |
|------|---------|---------------------|
| `create_campaign` | Clear untapped segment with 0.15+ conversion rate | 0.8+ |
| `pause_campaign` | <1% reply rate after 100+ leads, trending down | 0.7+ |
| `adjust_allocation` | One campaign outperforming by 2x+ | 0.7+ |
| `refine_targeting` | Clear WHO pattern with 1.5x+ lift | 0.7+ |
| `change_channel_mix` | Clear channel winner with 1.5x+ lift | 0.8+ |
| `update_content` | Clear WHAT pattern with 1.3x+ lift | 0.7+ |
| `adjust_timing` | Clear WHEN pattern with 1.3x+ lift | 0.7+ |

## Priority Scoring (1-100)

- **90-100**: Critical - immediate action needed (e.g., pause failing campaign)
- **70-89**: High - strong pattern, high confidence, significant impact
- **50-69**: Medium - good pattern, moderate confidence
- **30-49**: Low - emerging pattern, worth testing
- **1-29**: Watch - interesting but insufficient data

## Output Guidelines

1. **Executive Summary**: Start with 2-3 sentences a busy client can scan
2. **Quick Wins**: 2-3 low-effort, high-impact actions
3. **Suggestions**: Maximum 7, sorted by priority descending
4. **Data Gaps**: What would make the analysis stronger

## Risk Assessment

- **Low**: Well-supported by data, reversible, minimal downside
- **Medium**: Good data but some uncertainty, moderate effort to reverse
- **High**: Limited data or significant effort/cost to reverse

Return your analysis in the specified JSON format."""


# ============================================
# CONFIDENCE THRESHOLDS
# ============================================

CONFIDENCE_THRESHOLDS = {
    "create_campaign": 0.80,
    "pause_campaign": 0.70,
    "adjust_allocation": 0.70,
    "refine_targeting": 0.70,
    "change_channel_mix": 0.80,
    "update_content": 0.70,
    "adjust_timing": 0.70,
}


# ============================================
# CORE FUNCTION
# ============================================


async def run_campaign_orchestrator(
    who_analysis: dict[str, Any],
    what_analysis: dict[str, Any],
    how_analysis: dict[str, Any],
    current_campaigns: list[dict[str, Any]],
    client_context: dict[str, Any],
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Orchestrate analyzer outputs into campaign suggestions.

    Args:
        who_analysis: Output from WHO analyzer
        what_analysis: Output from WHAT analyzer
        how_analysis: Output from HOW analyzer
        current_campaigns: List of active campaign data
        client_context: Client tier, preferences, constraints
        client_id: Client UUID for cost tracking

    Returns:
        SDKBrainResult with CampaignSuggestionOutput data
    """
    # Build comprehensive prompt
    prompt_parts = []

    # WHO Analysis Summary
    prompt_parts.append("## WHO Analysis (Targeting Patterns)\n")
    prompt_parts.append(f"- Summary: {who_analysis.get('summary', 'N/A')}\n")
    prompt_parts.append(f"- Confidence: {who_analysis.get('confidence', 0)}\n")
    if who_analysis.get("targeting_refinements"):
        prompt_parts.append(f"- Targeting Refinements: {len(who_analysis['targeting_refinements'])} recommendations\n")
        for ref in who_analysis["targeting_refinements"][:3]:
            prompt_parts.append(f"  - {ref.get('attribute')}: {ref.get('suggested_value')} (lift: {ref.get('expected_lift', 1.0)}x)\n")
    if who_analysis.get("segment_opportunities"):
        prompt_parts.append(f"- Segment Opportunities: {len(who_analysis['segment_opportunities'])} found\n")
    if who_analysis.get("underperforming_segments"):
        prompt_parts.append(f"- Underperforming Segments: {who_analysis['underperforming_segments']}\n")

    # WHAT Analysis Summary
    prompt_parts.append("\n## WHAT Analysis (Content Patterns)\n")
    prompt_parts.append(f"- Summary: {what_analysis.get('summary', 'N/A')}\n")
    prompt_parts.append(f"- Confidence: {what_analysis.get('confidence', 0)}\n")
    if what_analysis.get("messaging_refinements"):
        prompt_parts.append(f"- Messaging Refinements: {len(what_analysis['messaging_refinements'])} recommendations\n")
        for ref in what_analysis["messaging_refinements"][:3]:
            prompt_parts.append(f"  - {ref.get('element')}: {ref.get('suggested_approach')[:50]}...\n")
    if what_analysis.get("winning_patterns"):
        prompt_parts.append(f"- Winning Patterns: {what_analysis['winning_patterns'][:3]}\n")
    if what_analysis.get("losing_patterns"):
        prompt_parts.append(f"- Losing Patterns: {what_analysis['losing_patterns'][:3]}\n")

    # HOW Analysis Summary
    prompt_parts.append("\n## HOW Analysis (Channel Patterns)\n")
    prompt_parts.append(f"- Summary: {how_analysis.get('summary', 'N/A')}\n")
    prompt_parts.append(f"- Confidence: {how_analysis.get('confidence', 0)}\n")
    if how_analysis.get("channel_recommendations"):
        prompt_parts.append(f"- Channel Recommendations: {len(how_analysis['channel_recommendations'])} changes\n")
        for rec in how_analysis["channel_recommendations"][:3]:
            prompt_parts.append(f"  - {rec.get('channel')}: {rec.get('current_allocation')}% -> {rec.get('suggested_allocation')}%\n")
    if how_analysis.get("multi_channel_lift"):
        prompt_parts.append(f"- Multi-Channel Lift: {how_analysis['multi_channel_lift']}x\n")

    # Current Campaigns
    prompt_parts.append("\n## Current Campaigns\n")
    for i, campaign in enumerate(current_campaigns[:5], 1):
        prompt_parts.append(f"\n### Campaign {i}: {campaign.get('name', 'Unnamed')}\n")
        prompt_parts.append(f"- Status: {campaign.get('status', 'unknown')}\n")
        prompt_parts.append(f"- Leads: {campaign.get('lead_count', 0)}\n")
        prompt_parts.append(f"- Reply Rate: {campaign.get('reply_rate', 0)}%\n")
        prompt_parts.append(f"- Conversion Rate: {campaign.get('conversion_rate', 0)}%\n")
        prompt_parts.append(f"- Allocation: {campaign.get('lead_allocation_pct', 0)}%\n")

    # Client Context
    prompt_parts.append("\n## Client Context\n")
    prompt_parts.append(f"- Tier: {client_context.get('tier', 'ignition')}\n")
    prompt_parts.append(f"- Monthly Lead Budget: {client_context.get('monthly_leads', 1250)}\n")
    prompt_parts.append(f"- Active Months: {client_context.get('active_months', 1)}\n")
    if client_context.get("preferences"):
        prompt_parts.append(f"- Preferences: {client_context['preferences']}\n")

    # Instructions
    prompt_parts.append("\n## Your Task\n")
    prompt_parts.append(
        "Synthesize the WHO, WHAT, and HOW analyses into actionable campaign suggestions. "
        "Prioritize by impact × confidence. Maximum 7 suggestions. "
        "Be specific about what to change and why. "
        "Remember: ALL suggestions require client approval - never auto-apply."
    )

    user_prompt = "".join(prompt_parts)

    # Create brain and run
    brain = create_sdk_brain("campaign_evolution_orchestrator")

    result = await brain.run(
        prompt=user_prompt,
        tools=[],
        output_schema=CampaignSuggestionOutput,
        system=ORCHESTRATOR_SYSTEM_PROMPT,
    )

    # Post-process: Filter suggestions below confidence threshold
    if result.success and result.data:
        filtered_suggestions = []
        for suggestion in result.data.suggestions:
            threshold = CONFIDENCE_THRESHOLDS.get(suggestion.suggestion_type, 0.7)
            if suggestion.confidence >= threshold:
                filtered_suggestions.append(suggestion)
            else:
                logger.info(
                    f"Filtered suggestion '{suggestion.title}' - "
                    f"confidence {suggestion.confidence} < threshold {threshold}"
                )
        result.data.suggestions = filtered_suggestions

    logger.info(
        f"Orchestrator complete: {len(result.data.suggestions) if result.success else 0} suggestions, "
        f"confidence={result.data.overall_confidence if result.success else 'N/A'}, "
        f"cost=${result.cost_aud:.4f}"
    )

    return result


# ============================================
# CONVENIENCE WRAPPER
# ============================================


async def generate_campaign_suggestions(
    who_analysis: dict[str, Any],
    what_analysis: dict[str, Any],
    how_analysis: dict[str, Any],
    current_campaigns: list[dict[str, Any]],
    client_context: dict[str, Any],
    analyzer_costs: dict[str, float] | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience wrapper for generating campaign suggestions.

    Args:
        who_analysis: WHO analyzer output
        what_analysis: WHAT analyzer output
        how_analysis: HOW analyzer output
        current_campaigns: Active campaign data
        client_context: Client context
        analyzer_costs: Cost from each analyzer {who: X, what: Y, how: Z}
        client_id: Client UUID

    Returns:
        Dict with suggestions or None if failed
    """
    result = await run_campaign_orchestrator(
        who_analysis=who_analysis,
        what_analysis=what_analysis,
        how_analysis=how_analysis,
        current_campaigns=current_campaigns,
        client_context=client_context,
        client_id=client_id,
    )

    if result.success and result.data:
        output = result.data.model_dump() if hasattr(result.data, "model_dump") else result.data

        # Calculate total cost
        total_cost = result.cost_aud
        if analyzer_costs:
            total_cost += sum(analyzer_costs.values())
        output["total_analysis_cost_aud"] = total_cost

        output["source"] = "sdk_campaign_orchestrator"
        output["orchestrator_cost_aud"] = result.cost_aud

        return output

    logger.warning(f"Orchestrator failed: {result.error}")
    return None


# ============================================
# VALIDATION HELPERS
# ============================================


def validate_suggestion_for_storage(suggestion: dict[str, Any]) -> bool:
    """
    Validate a suggestion has all required fields for database storage.

    Args:
        suggestion: Suggestion dict from orchestrator

    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "suggestion_type",
        "title",
        "description",
        "confidence",
        "priority",
        "recommended_action",
    ]

    for field in required_fields:
        if field not in suggestion or suggestion[field] is None:
            logger.warning(f"Suggestion missing required field: {field}")
            return False

    # Validate suggestion_type
    valid_types = [
        "create_campaign",
        "pause_campaign",
        "adjust_allocation",
        "refine_targeting",
        "change_channel_mix",
        "update_content",
        "adjust_timing",
    ]
    if suggestion["suggestion_type"] not in valid_types:
        logger.warning(f"Invalid suggestion_type: {suggestion['suggestion_type']}")
        return False

    # Validate confidence range
    if not 0 <= suggestion["confidence"] <= 1:
        logger.warning(f"Invalid confidence: {suggestion['confidence']}")
        return False

    # Validate priority range
    if not 1 <= suggestion["priority"] <= 100:
        logger.warning(f"Invalid priority: {suggestion['priority']}")
        return False

    return True


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] CRITICAL rule: suggestions require client approval
# [x] Pydantic output schemas (CampaignSuggestion, CampaignSuggestionOutput)
# [x] Detailed system prompt with confidence thresholds
# [x] Core async function (run_campaign_orchestrator)
# [x] Confidence threshold filtering post-process
# [x] Convenience wrapper with cost aggregation
# [x] Validation helper for storage
# [x] Comprehensive logging
# [x] Type hints throughout
# [x] Risk assessment in suggestions
# [x] Priority scoring guidance
