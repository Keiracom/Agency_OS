"""
Contract: src/agents/campaign_evolution/what_analyzer_agent.py
Purpose: Analyze WHAT patterns to generate content/messaging suggestions
Layer: 3 - agents
Imports: models, integrations (sdk_brain)
Consumers: campaign_orchestrator_agent, campaign_evolution_flow
Phase: Phase D - Item 18

WHAT Analyzer examines content patterns (subjects, pain points, CTAs)
and generates messaging optimization suggestions.
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


class MessagingRefinement(BaseModel):
    """A specific messaging/content refinement."""

    element: str = Field(description="The element to refine (subject_line, pain_point, cta, angle, length)")
    current_approach: str = Field(description="Current approach being used")
    suggested_approach: str = Field(description="Suggested new approach")
    example: str = Field(description="Concrete example of the suggested approach")
    reason: str = Field(description="Why this change is recommended based on patterns")
    expected_lift: float = Field(description="Expected improvement (e.g., 1.3 = 30% better)")


class ABTestRecommendation(BaseModel):
    """Recommended A/B test based on patterns."""

    test_name: str = Field(description="Name for this test")
    hypothesis: str = Field(description="What we're testing and why")
    variant_a: str = Field(description="Control variant description")
    variant_b: str = Field(description="Test variant description")
    success_metric: str = Field(description="How to measure success (reply_rate, conversion_rate)")
    confidence_required: float = Field(description="Statistical confidence needed (typically 0.95)")


class ContentInsight(BaseModel):
    """A key insight about content performance."""

    insight: str = Field(description="The insight")
    supporting_data: str = Field(description="Data supporting this insight")
    action: str = Field(description="Recommended action based on this insight")


class WHATAnalysis(BaseModel):
    """Output from WHAT pattern analysis."""

    # High-level summary
    summary: str = Field(description="1-2 sentence summary of WHAT pattern findings")

    # Messaging refinements
    messaging_refinements: list[MessagingRefinement] = Field(
        default_factory=list,
        description="Specific content/messaging changes recommended",
    )

    # A/B test recommendations
    ab_test_recommendations: list[ABTestRecommendation] = Field(
        default_factory=list,
        description="Recommended A/B tests to run",
    )

    # Winning patterns to amplify
    winning_patterns: list[str] = Field(
        default_factory=list,
        description="Content patterns that work well - use more",
    )

    # Losing patterns to avoid
    losing_patterns: list[str] = Field(
        default_factory=list,
        description="Content patterns that underperform - use less",
    )

    # Key insights
    key_insights: list[ContentInsight] = Field(
        default_factory=list,
        description="Top 3-5 actionable content insights",
    )

    # Optimal parameters
    optimal_length: dict[str, int] = Field(
        default_factory=dict,
        description="Optimal message length by channel (words)",
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

WHAT_ANALYZER_SYSTEM_PROMPT = """You are a B2B content optimization expert analyzing messaging patterns.

Your role is to examine WHAT patterns (which content resonates) and generate actionable content suggestions.

## Input Data You'll Receive

1. **WHAT Patterns** from CIS (Conversion Intelligence System):
   - subject_patterns: Subject lines that work/don't work
   - pain_points: Which pain points resonate
   - ctas: Which calls-to-action convert
   - angles: Which messaging angles work
   - optimal_length: Ideal message length by channel
   - personalization_lift: Value of different personalization elements
   - template_performance: Which templates perform best
   - ab_test_insights: Results from A/B tests

2. **Current Content Strategy**:
   - Current subject line patterns
   - Current pain points used
   - Current CTA approach
   - Current message templates

3. **Business Context**:
   - Client's value proposition
   - Target audience characteristics

## Your Analysis Tasks

1. **Identify Messaging Refinements**
   - Compare current content to what actually converts
   - Suggest specific changes with examples
   - Quantify expected improvement

2. **Recommend A/B Tests**
   - Identify testable hypotheses from patterns
   - Design clear test variants
   - Define success metrics

3. **Catalog Winners and Losers**
   - Document patterns to amplify
   - Document patterns to avoid

## Output Guidelines

- Be SPECIFIC: Provide actual example text, not abstract suggestions
- Be DATA-DRIVEN: Always cite the pattern data that supports your recommendation
- Be ACTIONABLE: "Change CTA from 'Learn more' to 'See how [Company] did it'"
- Be TESTABLE: Frame suggestions as hypotheses when data is limited

## Confidence Scoring

- 0.9+: Clear patterns with 100+ sample size, consistent results
- 0.7-0.9: Good patterns with 50-100 sample size
- 0.5-0.7: Emerging patterns, worth testing
- <0.5: Insufficient data, flag for future testing

Return your analysis in the specified JSON format."""


# ============================================
# CORE FUNCTION
# ============================================


async def run_what_analyzer(
    what_patterns: dict[str, Any],
    current_content: dict[str, Any],
    campaign_metrics: dict[str, Any] | None = None,
    business_context: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> SDKBrainResult:
    """
    Run WHAT pattern analysis to generate content suggestions.

    Args:
        what_patterns: CIS WHAT detector output
        current_content: Current content strategy/templates
        campaign_metrics: Current campaign performance (optional)
        business_context: Client business context (optional)
        client_id: Client UUID for cost tracking

    Returns:
        SDKBrainResult with WHATAnalysis data
    """
    # Build context prompt
    prompt_parts = []

    # WHAT patterns
    prompt_parts.append("## WHAT Patterns (from CIS)\n")
    prompt_parts.append(f"```json\n{_format_patterns(what_patterns)}\n```\n")

    # Current content strategy
    prompt_parts.append("\n## Current Content Strategy\n")
    if current_content.get("subject_patterns"):
        prompt_parts.append(f"- Subject Patterns: {current_content['subject_patterns']}\n")
    if current_content.get("pain_points"):
        prompt_parts.append(f"- Pain Points Used: {current_content['pain_points']}\n")
    if current_content.get("ctas"):
        prompt_parts.append(f"- CTAs Used: {current_content['ctas']}\n")
    if current_content.get("templates"):
        prompt_parts.append(f"- Active Templates: {len(current_content['templates'])} templates\n")

    # Campaign metrics
    if campaign_metrics:
        prompt_parts.append("\n## Current Campaign Performance\n")
        prompt_parts.append(f"- Open Rate: {campaign_metrics.get('open_rate', 'N/A')}%\n")
        prompt_parts.append(f"- Reply Rate: {campaign_metrics.get('reply_rate', 'N/A')}%\n")
        prompt_parts.append(f"- Conversion Rate: {campaign_metrics.get('conversion_rate', 'N/A')}%\n")

    # Business context
    if business_context:
        prompt_parts.append("\n## Business Context\n")
        prompt_parts.append(f"- Value Proposition: {business_context.get('value_proposition', 'N/A')}\n")
        prompt_parts.append(f"- Target Audience: {business_context.get('target_audience', 'N/A')}\n")
        prompt_parts.append(f"- Tone: {business_context.get('tone', 'professional')}\n")

    # Instructions
    prompt_parts.append("\n## Your Task\n")
    prompt_parts.append(
        "Analyze the WHAT patterns and current content strategy. "
        "Generate specific, data-driven messaging refinements with examples. "
        "Recommend A/B tests for uncertain areas. "
        "Document winning patterns to amplify and losing patterns to avoid."
    )

    user_prompt = "".join(prompt_parts)

    # Create brain and run
    brain = create_sdk_brain("campaign_evolution_what")

    result = await brain.run(
        prompt=user_prompt,
        tools=[],  # No tools needed - analyzing provided data
        output_schema=WHATAnalysis,
        system=WHAT_ANALYZER_SYSTEM_PROMPT,
    )

    logger.info(
        f"WHAT analyzer complete: confidence={result.data.confidence if result.success else 'N/A'}, "
        f"cost=${result.cost_aud:.4f}"
    )

    return result


# ============================================
# HELPER FUNCTIONS
# ============================================


def _format_patterns(patterns: dict[str, Any]) -> str:
    """Format patterns for prompt, handling large data."""
    import json

    formatted = {}

    # Subject patterns - winning only
    if "subject_patterns" in patterns:
        sp = patterns["subject_patterns"]
        formatted["subject_patterns"] = {
            "winning": sp.get("winning", [])[:5],
        }

    # Pain points - effective only
    if "pain_points" in patterns:
        pp = patterns["pain_points"]
        formatted["pain_points"] = {
            "effective": pp.get("effective", [])[:5],
            "ineffective": pp.get("ineffective", [])[:3],
        }

    # CTAs - effective only
    if "ctas" in patterns:
        formatted["ctas"] = {
            "effective": patterns["ctas"].get("effective", [])[:5],
        }

    # Optimal length
    if "optimal_length" in patterns:
        formatted["optimal_length"] = patterns["optimal_length"]

    # Personalization lift
    if "personalization_lift" in patterns:
        formatted["personalization_lift"] = patterns["personalization_lift"]

    # Template performance - top/bottom only
    if "template_performance" in patterns:
        tp = patterns["template_performance"]
        formatted["template_performance"] = {
            "top_templates": tp.get("top_templates", [])[:3],
            "bottom_templates": tp.get("bottom_templates", [])[:2],
        }

    # Baseline
    if "baseline_conversion_rate" in patterns:
        formatted["baseline_conversion_rate"] = patterns["baseline_conversion_rate"]

    return json.dumps(formatted, indent=2, default=str)


# ============================================
# CONVENIENCE WRAPPER
# ============================================


async def analyze_what_patterns(
    what_patterns: dict[str, Any],
    current_content: dict[str, Any],
    campaign_metrics: dict[str, Any] | None = None,
    client_id: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Convenience wrapper for WHAT analysis.

    Returns dict with analysis results or None if failed.
    """
    result = await run_what_analyzer(
        what_patterns=what_patterns,
        current_content=current_content,
        campaign_metrics=campaign_metrics,
        client_id=client_id,
    )

    if result.success and result.data:
        analysis = result.data.model_dump() if hasattr(result.data, "model_dump") else result.data
        return {
            **analysis,
            "source": "sdk_what_analyzer",
            "cost_aud": result.cost_aud,
        }

    logger.warning(f"WHAT analysis failed: {result.error}")
    return None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Pydantic output schema (WHATAnalysis)
# [x] Detailed system prompt
# [x] Core async function (run_what_analyzer)
# [x] Uses create_sdk_brain pattern
# [x] No tools needed (analyzes provided data)
# [x] Convenience wrapper
# [x] Helper functions for data formatting
# [x] Logging
# [x] Type hints throughout
