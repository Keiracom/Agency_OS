"""
Contract: src/agents/campaign_evolution/who_analyzer_agent.py
Purpose: Analyze WHO patterns to generate targeting suggestions
Layer: 3 - agents
Imports: models, integrations (sdk_brain)
Consumers: campaign_orchestrator_agent, campaign_evolution_flow
Phase: Phase D - Item 18

WHO Analyzer examines lead attribute patterns (title, industry, company size)
and generates targeting refinement suggestions.
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


class TargetingRefinement(BaseModel):
    """A specific targeting refinement suggestion."""

    attribute: str = Field(description="The attribute to refine (title, industry, company_size, seniority)")
    current_value: str = Field(description="Current targeting value or range")
    suggested_value: str = Field(description="Suggested new value or range")
    reason: str = Field(description="Why this change is recommended based on patterns")
    expected_lift: float = Field(description="Expected conversion lift (e.g., 1.5 = 50% improvement)")


class SegmentOpportunity(BaseModel):
    """An untapped segment opportunity."""

    segment_name: str = Field(description="Name for this segment (e.g., 'Tech CTOs at Growth-Stage')")
    description: str = Field(description="Description of the segment")
    attributes: dict[str, str] = Field(description="Key attributes defining this segment")
    conversion_rate: float = Field(description="Observed conversion rate for this segment")
    sample_size: int = Field(description="Number of leads analyzed in this segment")
    recommendation: str = Field(description="Specific action to take")


class WHOAnalysis(BaseModel):
    """Output from WHO pattern analysis."""

    # High-level summary
    summary: str = Field(description="1-2 sentence summary of WHO pattern findings")

    # Targeting refinements
    targeting_refinements: list[TargetingRefinement] = Field(
        default_factory=list,
        description="Specific targeting changes recommended",
    )

    # Segment opportunities
    segment_opportunities: list[SegmentOpportunity] = Field(
        default_factory=list,
        description="Untapped segments worth targeting",
    )

    # Underperforming segments
    underperforming_segments: list[str] = Field(
        default_factory=list,
        description="Segments that should be deprioritized or excluded",
    )

    # Key insights
    key_insights: list[str] = Field(
        default_factory=list,
        description="Top 3-5 actionable insights from WHO patterns",
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

WHO_ANALYZER_SYSTEM_PROMPT = """You are a B2B targeting optimization expert analyzing conversion patterns.

Your role is to examine WHO patterns (which lead attributes convert best) and generate actionable targeting suggestions.

## Input Data You'll Receive

1. **WHO Patterns** from CIS (Conversion Intelligence System):
   - title_rankings: Job titles ranked by conversion rate
   - industry_rankings: Industries ranked by conversion rate
   - size_analysis: Company size sweet spots
   - timing_signals: Lift from new role, hiring, funding signals
   - objection_patterns: Common objections by segment

2. **Current Campaign Targeting**:
   - Current ICP criteria (industries, titles, company sizes)
   - Current campaign performance metrics

3. **Business Context**:
   - Client's value proposition
   - Target market constraints

## Your Analysis Tasks

1. **Identify Targeting Refinements**
   - Compare current targeting to what actually converts
   - Suggest specific changes (add/remove titles, narrow industries, etc.)
   - Quantify expected improvement

2. **Find Segment Opportunities**
   - Identify high-converting segments not currently targeted
   - Look for "sweet spots" in the data
   - Suggest new campaigns for untapped segments

3. **Flag Underperformers**
   - Identify segments with poor conversion rates
   - Suggest exclusions or deprioritization

## Output Guidelines

- Be SPECIFIC: "Add 'VP of Engineering' to title targeting" not "target more technical roles"
- Be DATA-DRIVEN: Always cite the pattern data that supports your recommendation
- Be CONSERVATIVE: Only suggest changes with sufficient sample size (30+ leads)
- Be REALISTIC: Projected lifts should be based on observed data, not assumptions

## Confidence Scoring

- 0.9+: Strong patterns with 100+ sample size
- 0.7-0.9: Good patterns with 50-100 sample size
- 0.5-0.7: Emerging patterns with 30-50 sample size
- <0.5: Insufficient data for confident recommendations

Return your analysis in the specified JSON format."""


# ============================================
# CORE FUNCTION
# ============================================


async def run_who_analyzer(
    who_patterns: dict[str, Any],
    current_targeting: dict[str, Any],
    campaign_metrics: dict[str, Any] | None = None,
    business_context: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Run WHO pattern analysis to generate targeting suggestions.

    Args:
        who_patterns: CIS WHO detector output (title_rankings, industry_rankings, etc.)
        current_targeting: Current ICP/targeting criteria
        campaign_metrics: Current campaign performance (optional)
        business_context: Client business context (optional)
        client_id: Client UUID for cost tracking

    Returns:
        SDKBrainResult with WHOAnalysis data
    """
    # Build context prompt
    prompt_parts = []

    # WHO patterns
    prompt_parts.append("## WHO Patterns (from CIS)\n")
    prompt_parts.append(f"```json\n{_format_patterns(who_patterns)}\n```\n")

    # Current targeting
    prompt_parts.append("\n## Current Targeting Criteria\n")
    prompt_parts.append(f"- Industries: {current_targeting.get('industries', [])}\n")
    prompt_parts.append(f"- Titles: {current_targeting.get('titles', [])}\n")
    prompt_parts.append(f"- Company Sizes: {current_targeting.get('company_sizes', [])}\n")
    prompt_parts.append(f"- Locations: {current_targeting.get('locations', [])}\n")

    # Campaign metrics
    if campaign_metrics:
        prompt_parts.append("\n## Current Campaign Performance\n")
        prompt_parts.append(f"- Reply Rate: {campaign_metrics.get('reply_rate', 'N/A')}%\n")
        prompt_parts.append(f"- Conversion Rate: {campaign_metrics.get('conversion_rate', 'N/A')}%\n")
        prompt_parts.append(f"- Leads Contacted: {campaign_metrics.get('leads_contacted', 'N/A')}\n")

    # Business context
    if business_context:
        prompt_parts.append("\n## Business Context\n")
        prompt_parts.append(f"- Value Proposition: {business_context.get('value_proposition', 'N/A')}\n")
        prompt_parts.append(f"- Target Market: {business_context.get('target_market', 'N/A')}\n")

    # Instructions
    prompt_parts.append("\n## Your Task\n")
    prompt_parts.append(
        "Analyze the WHO patterns and current targeting. "
        "Generate specific, data-driven targeting refinements. "
        "Identify any untapped high-converting segments. "
        "Flag underperforming segments that should be deprioritized."
    )

    user_prompt = "".join(prompt_parts)

    # Create brain and run
    brain = create_sdk_brain("campaign_evolution_who")

    result = await brain.run(
        prompt=user_prompt,
        tools=[],  # No tools needed - analyzing provided data
        output_schema=WHOAnalysis,
        system=WHO_ANALYZER_SYSTEM_PROMPT,
    )

    logger.info(
        f"WHO analyzer complete: confidence={result.data.confidence if result.success else 'N/A'}, "
        f"cost=${result.cost_aud:.4f}"
    )

    return result


# ============================================
# HELPER FUNCTIONS
# ============================================


def _format_patterns(patterns: dict[str, Any]) -> str:
    """Format patterns for prompt, handling large data."""
    import json

    # Limit size of pattern data to avoid token bloat
    formatted = {}

    # Title rankings - top 10
    if "title_rankings" in patterns:
        formatted["title_rankings"] = patterns["title_rankings"][:10]

    # Industry rankings - top 10
    if "industry_rankings" in patterns:
        formatted["industry_rankings"] = patterns["industry_rankings"][:10]

    # Size analysis - keep as-is (usually small)
    if "size_analysis" in patterns:
        formatted["size_analysis"] = patterns["size_analysis"]

    # Timing signals - keep as-is
    if "timing_signals" in patterns:
        formatted["timing_signals"] = patterns["timing_signals"]

    # Baseline conversion rate
    if "baseline_conversion_rate" in patterns:
        formatted["baseline_conversion_rate"] = patterns["baseline_conversion_rate"]

    # Objection patterns - summary only
    if "objection_patterns" in patterns:
        obj = patterns["objection_patterns"]
        formatted["objection_patterns_summary"] = {
            "top_objections": obj.get("overall_distribution", [])[:5],
        }

    return json.dumps(formatted, indent=2, default=str)


# ============================================
# CONVENIENCE WRAPPER
# ============================================


async def analyze_who_patterns(
    who_patterns: dict[str, Any],
    current_targeting: dict[str, Any],
    campaign_metrics: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience wrapper for WHO analysis.

    Returns dict with analysis results or None if failed.
    """
    result = await run_who_analyzer(
        who_patterns=who_patterns,
        current_targeting=current_targeting,
        campaign_metrics=campaign_metrics,
        client_id=client_id,
    )

    if result.success and result.data:
        analysis = result.data.model_dump() if hasattr(result.data, "model_dump") else result.data
        return {
            **analysis,
            "source": "sdk_who_analyzer",
            "cost_aud": result.cost_aud,
        }

    logger.warning(f"WHO analysis failed: {result.error}")
    return None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Pydantic output schema (WHOAnalysis)
# [x] Detailed system prompt
# [x] Core async function (run_who_analyzer)
# [x] Uses create_sdk_brain pattern
# [x] No tools needed (analyzes provided data)
# [x] Convenience wrapper
# [x] Helper functions for data formatting
# [x] Logging
# [x] Type hints throughout
