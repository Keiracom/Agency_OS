"""
Contract: src/engines/campaign_suggester.py
Purpose: AI-powered campaign suggestion engine based on client ICP
Layer: 3 - engines
Imports: models, integrations, config
Consumers: orchestration, API routes

FILE: src/engines/campaign_suggester.py
PURPOSE: AI-powered campaign suggestion engine based on client ICP
PHASE: 37 (Lead/Campaign Architecture)
DEPENDENCIES:
  - src/engines/base.py
  - src/integrations/anthropic.py
  - src/config/tiers.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines

This engine analyzes a client's ICP (Ideal Customer Profile) and suggests
optimal campaign segments. Each suggestion includes:
- Campaign name and target segment
- Recommended lead allocation percentage
- AI reasoning for the segment
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.tiers import get_campaign_slots
from src.engines.base import BaseEngine, EngineResult
from src.integrations.anthropic import get_anthropic_client
from src.models.client import Client

logger = logging.getLogger(__name__)


@dataclass
class CampaignSuggestion:
    """A suggested campaign from ICP analysis."""

    name: str
    description: str
    target_industries: list[str]
    target_titles: list[str]
    target_company_sizes: list[str]
    target_locations: list[str]
    lead_allocation_pct: int
    ai_reasoning: str
    priority: int  # 1 = highest priority


CAMPAIGN_SUGGESTION_PROMPT = """You are an expert B2B sales strategist. Analyze this client's Ideal Customer Profile (ICP) and suggest optimal campaign segments.

## Client Information
Company: {company_name}
Industry: {client_industry}
Services: {services}
Value Proposition: {value_prop}

## Client's ICP Data
Target Industries: {icp_industries}
Target Titles: {icp_titles}
Target Company Sizes: {icp_company_sizes}
Target Locations: {icp_locations}
Pain Points: {icp_pain_points}
Keywords: {icp_keywords}
Exclusions: {icp_exclusions}

## Campaign Constraints
- Maximum AI-suggested campaigns: {max_ai_campaigns}
- Lead allocation must sum to exactly 100%
- Minimum allocation per campaign: 10%
- Each campaign should target a distinct segment

## Your Task
Suggest {max_ai_campaigns} distinct campaign segments. For each campaign:
1. Identify a specific, actionable segment (combine industry + title + company size)
2. Explain WHY this segment is valuable (pain point alignment, conversion potential)
3. Assign lead allocation percentage based on expected ROI

Prioritize segments where:
- Decision-makers have budget authority
- Pain points align with client's services
- Industry/company size suggests good fit

## Output Format (JSON)
Return a JSON array with exactly {max_ai_campaigns} campaigns:
```json
[
  {{
    "name": "C-Suite Tech Leaders",
    "description": "CTOs and CIOs at mid-market SaaS companies",
    "target_industries": ["SaaS", "Technology"],
    "target_titles": ["CTO", "CIO", "VP Engineering"],
    "target_company_sizes": ["51-200", "201-500"],
    "target_locations": ["Australia"],
    "lead_allocation_pct": 40,
    "ai_reasoning": "Highest decision-making authority with direct budget control. Tech companies have fastest sales cycles.",
    "priority": 1
  }},
  ...
]
```

IMPORTANT:
- Allocations MUST sum to exactly 100%
- Return ONLY valid JSON, no markdown or explanation
- Each campaign must be distinct (no overlapping segments)

CRITICAL: Respond with ONLY a valid JSON array. No explanation. No preamble. No markdown fences. No commentary before or after the JSON. Your entire response must be parseable by json.loads(). If any ICP field says 'Not specified', use your best judgment based on the other fields provided. Do not mention that data is missing.
"""


class CampaignSuggesterEngine(BaseEngine):
    """
    Campaign suggestion engine.

    Analyzes client ICP and suggests optimal campaign segments
    using Claude AI for intelligent segmentation.
    """

    @property
    def name(self) -> str:
        return "campaign_suggester"

    async def suggest_campaigns(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> EngineResult[dict[str, Any]]:
        """
        Generate AI-suggested campaigns for a client.

        Analyzes the client's ICP and creates campaign suggestions
        up to the tier's AI campaign limit.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            EngineResult with campaign suggestions
        """
        # Get client data
        client = await self._get_client(db, client_id)
        if not client:
            return EngineResult.fail(
                error=f"Client {client_id} not found",
                metadata={"client_id": str(client_id)},
            )

        # Check ICP data exists
        if not client.icp_industries and not client.icp_titles:
            return EngineResult.fail(
                error="Client has no ICP data. Complete onboarding first.",
                metadata={"client_id": str(client_id)},
            )

        # Get tier limits
        tier_name = client.tier.value if hasattr(client.tier, "value") else str(client.tier)
        try:
            ai_slots, custom_slots = get_campaign_slots(tier_name)
        except ValueError:
            ai_slots = 3  # Default to Ignition
            custom_slots = 2

        # Build prompt
        prompt = self._build_prompt(client, ai_slots)

        # Call Claude
        suggestions = await self._get_ai_suggestions(prompt, ai_slots)

        if not suggestions:
            return EngineResult.fail(
                error="Failed to generate campaign suggestions",
                metadata={"client_id": str(client_id)},
            )

        # Validate allocations sum to 100%
        total_allocation = sum(s.lead_allocation_pct for s in suggestions)
        if total_allocation != 100:
            # Adjust last campaign to make it sum to 100
            diff = 100 - total_allocation
            suggestions[-1].lead_allocation_pct += diff
            logger.warning(f"Adjusted allocation by {diff}% to sum to 100%")

        # Convert to dict for return
        result = {
            "client_id": str(client_id),
            "tier": tier_name,
            "ai_campaign_slots": ai_slots,
            "custom_campaign_slots": custom_slots,
            "suggestions": [self._suggestion_to_dict(s) for s in suggestions],
            "generated_at": datetime.now(UTC).isoformat(),
        }

        logger.info(f"Generated {len(suggestions)} campaign suggestions for client {client_id}")

        return EngineResult.ok(
            data=result,
            metadata={
                "engine": self.name,
                "suggestions_count": len(suggestions),
                "tier": tier_name,
            },
        )

    async def _get_client(self, db: AsyncSession, client_id: UUID) -> Client | None:
        """Get client by ID."""
        stmt = select(Client).where(Client.id == client_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _build_prompt(self, client: Client, max_campaigns: int) -> str:
        """Build the suggestion prompt with client ICP data."""
        # Count sparse fields to detect thin ICP
        sparse_sentinel = "Not specified"
        icp_fields = [
            client.icp_industries,
            client.services_offered,
            client.value_proposition,
            client.icp_titles,
            client.icp_company_sizes,
            client.icp_locations,
            client.icp_pain_points,
            client.icp_keywords,
            client.icp_exclusions,
        ]
        sparse_count = sum(1 for f in icp_fields if not f or (isinstance(f, list) and len(f) == 0))
        sparse_note = ""
        if sparse_count >= 5:
            sparse_note = (
                "\nThe agency has limited ICP data. Generate broad but sensible campaign "
                "suggestions based on their industry and location. Prioritise practical over specific."
            )

        prompt = CAMPAIGN_SUGGESTION_PROMPT.format(
            company_name=client.name,
            client_industry=", ".join(client.icp_industries or [sparse_sentinel]),
            services=", ".join(client.services_offered or [sparse_sentinel]),
            value_prop=client.value_proposition or sparse_sentinel,
            icp_industries=", ".join(client.icp_industries or ["Any"]),
            icp_titles=", ".join(client.icp_titles or ["Decision makers"]),
            icp_company_sizes=", ".join(client.icp_company_sizes or ["Any"]),
            icp_locations=", ".join(client.icp_locations or ["Australia"]),
            icp_pain_points=", ".join(client.icp_pain_points or [sparse_sentinel]),
            icp_keywords=", ".join(client.icp_keywords or [sparse_sentinel]),
            icp_exclusions=", ".join(client.icp_exclusions or ["None"]),
            max_ai_campaigns=max_campaigns,
        )
        return prompt + sparse_note

    async def _get_ai_suggestions(
        self,
        prompt: str,
        expected_count: int,
    ) -> list[CampaignSuggestion] | None:
        """
        Get campaign suggestions from Claude.

        Args:
            prompt: The formatted prompt
            expected_count: Expected number of campaigns

        Returns:
            List of CampaignSuggestion or None on failure
        """
        try:
            client = get_anthropic_client()

            response = await client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract content
            content = response.content[0].text if response.content else ""

            # Parse JSON — attempt 1
            suggestions = self._parse_suggestions(content, expected_count)
            if suggestions is not None:
                return suggestions

            # Attempt 2: retry with explicit nudge (~$0.001 extra)
            logger.warning(
                f"AI suggestion parse failed on first attempt. Raw response: {content!r:.500}. Retrying."
            )
            retry_prompt = (
                prompt + "\n\nYour previous response could not be parsed as JSON. "
                "Return ONLY a JSON array this time."
            )
            retry_response = await client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=2000,
                messages=[{"role": "user", "content": retry_prompt}],
            )
            retry_content = retry_response.content[0].text if retry_response.content else ""
            suggestions = self._parse_suggestions(retry_content, expected_count)
            if suggestions is None:
                logger.error(
                    f"AI suggestion parse failed on retry. Raw response: {retry_content!r:.500}"
                )
            return suggestions

        except Exception as e:
            logger.exception(f"AI suggestion error: {e}")
            return None

    def _parse_suggestions(
        self,
        content: str,
        expected_count: int,
    ) -> list[CampaignSuggestion] | None:
        """Parse Claude's response into CampaignSuggestion objects."""
        try:
            # Extract JSON from response
            json_str = content.strip()

            # Strip markdown fences
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            json_str = json_str.strip()

            # FIX 4: If response doesn't start with '[', find the array boundaries.
            # Handles Claude prepending explanatory text before the JSON array.
            if json_str and json_str[0] != "[":
                first_bracket = json_str.find("[")
                last_bracket = json_str.rfind("]")
                if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
                    logger.warning(
                        "Claude response contained non-JSON preamble — extracted array. "
                        "Prompt may not be working optimally."
                    )
                    json_str = json_str[first_bracket : last_bracket + 1]
                else:
                    logger.error("No JSON array found in Claude response")
                    return None

            data = json.loads(json_str)

            if not isinstance(data, list):
                logger.error("Response is not a list")
                return None

            suggestions = []
            for i, item in enumerate(data[:expected_count]):
                suggestion = CampaignSuggestion(
                    name=item.get("name", f"Campaign {i + 1}"),
                    description=item.get("description", ""),
                    target_industries=item.get("target_industries", []),
                    target_titles=item.get("target_titles", []),
                    target_company_sizes=item.get("target_company_sizes", []),
                    target_locations=item.get("target_locations", ["Australia"]),
                    lead_allocation_pct=int(item.get("lead_allocation_pct", 100 // expected_count)),
                    ai_reasoning=item.get("ai_reasoning", "AI-suggested segment"),
                    priority=item.get("priority", i + 1),
                )
                suggestions.append(suggestion)

            return suggestions

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.exception(f"Parse error: {e}")
            return None

    def _suggestion_to_dict(self, suggestion: CampaignSuggestion) -> dict[str, Any]:
        """Convert CampaignSuggestion to dict."""
        return {
            "name": suggestion.name,
            "description": suggestion.description,
            "target_industries": suggestion.target_industries,
            "target_titles": suggestion.target_titles,
            "target_company_sizes": suggestion.target_company_sizes,
            "target_locations": suggestion.target_locations,
            "lead_allocation_pct": suggestion.lead_allocation_pct,
            "ai_reasoning": suggestion.ai_reasoning,
            "priority": suggestion.priority,
        }

    async def create_suggested_campaigns(
        self,
        db: AsyncSession,
        client_id: UUID,
        suggestions: list[dict[str, Any]],
        auto_activate: bool = False,
    ) -> EngineResult[dict[str, Any]]:
        """
        Create actual Campaign records from suggestions.

        Args:
            db: Database session
            client_id: Client UUID
            suggestions: List of suggestion dicts from suggest_campaigns
            auto_activate: Whether to auto-activate campaigns (default: False = draft)

        Returns:
            EngineResult with created campaign IDs
        """
        from sqlalchemy import text

        from src.models.campaign import CampaignType

        created_campaigns = []
        total_allocation = 0

        for suggestion in suggestions:
            # Validate allocation doesn't exceed 100%
            allocation = suggestion.get("lead_allocation_pct", 0)
            if total_allocation + allocation > 100:
                allocation = 100 - total_allocation

            if allocation <= 0:
                continue

            total_allocation += allocation

            # Create campaign
            query = text("""
                INSERT INTO campaigns (
                    client_id, name, description, status,
                    campaign_type, lead_allocation_pct, ai_suggestion_reason,
                    target_industries, target_titles, target_company_sizes, target_locations
                ) VALUES (
                    :client_id, :name, :description, :status,
                    :campaign_type, :lead_allocation_pct, :ai_reason,
                    :industries, :titles, :company_sizes, :locations
                )
                RETURNING id, name
            """)

            result = await db.execute(
                query,
                {
                    "client_id": str(client_id),
                    "name": suggestion.get("name", "AI Campaign"),
                    "description": suggestion.get("description", ""),
                    "status": "active" if auto_activate else "draft",
                    "campaign_type": CampaignType.AI_SUGGESTED,
                    "lead_allocation_pct": allocation,
                    "ai_reason": suggestion.get("ai_reasoning", "AI-suggested segment"),
                    "industries": suggestion.get("target_industries", []),
                    "titles": suggestion.get("target_titles", []),
                    "company_sizes": suggestion.get("target_company_sizes", []),
                    "locations": suggestion.get("target_locations", []),
                },
            )

            row = result.fetchone()
            if row:
                created_campaigns.append(
                    {
                        "campaign_id": str(row.id),
                        "name": row.name,
                        "allocation_pct": allocation,
                    }
                )

        await db.commit()

        logger.info(f"Created {len(created_campaigns)} AI campaigns for client {client_id}")

        return EngineResult.ok(
            data={
                "client_id": str(client_id),
                "campaigns_created": len(created_campaigns),
                "total_allocation": total_allocation,
                "campaigns": created_campaigns,
            },
            metadata={
                "engine": self.name,
                "auto_activated": auto_activate,
            },
        )


# Singleton instance
_campaign_suggester: CampaignSuggesterEngine | None = None


def get_campaign_suggester() -> CampaignSuggesterEngine:
    """Get or create CampaignSuggester engine instance."""
    global _campaign_suggester
    if _campaign_suggester is None:
        _campaign_suggester = CampaignSuggesterEngine()
    return _campaign_suggester


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Uses Claude Haiku for cost efficiency
# [x] Respects tier campaign limits
# [x] Validates allocation sums to 100%
# [x] Returns structured suggestions
# [x] Can create campaigns from suggestions
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
