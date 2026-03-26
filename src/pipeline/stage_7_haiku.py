"""
Stage 7 Haiku Message Generation — Architecture v5
Directive #264

Generates personalised outreach messages for each confirmed channel
using Claude Haiku. Messages reference specific prospect signals.
No templates. No AI mentions. Human voice throughout.

Model: claude-haiku-4-5-20251001
Gate: propensity_score >= min_score_to_outreach (65)
Stores messages in outreach_messages JSONB on BU.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import asyncpg

from src.enrichment.signal_config import SignalConfigRepository

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S7 = 7
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Haiku 4.5 pricing (USD per token)
HAIKU_INPUT_COST_PER_TOKEN = 0.0000008    # $0.80 per million input tokens
HAIKU_OUTPUT_COST_PER_TOKEN = 0.000004    # $4.00 per million output tokens

_CHANNEL_PROMPTS = {
    "email": (
        "Write a 3-line cold email. Line 1: one specific observation about their business (use the tech stack, "
        "ad spend, or GMB data provided). Line 2: one question about their situation. Line 3: soft CTA — "
        "ask if they're open to a quick chat, not to buy anything. Sign off with the agency founder's name. "
        "Under 100 words. No 'I hope this email finds you well'. No mention of AI or automation. "
        "Sound like a curious peer, not a salesperson."
    ),
    "linkedin": (
        "Write a LinkedIn connection request note. Max 300 characters. Reference one shared context or "
        "specific observation about their business. Do not pitch. Ask to connect. No mention of AI. "
        "Sound like a genuine professional reaching out."
    ),
    "voice": (
        "Write a structured voice call knowledge card as JSON with these fields: "
        '{"trigger": "one-sentence reason for calling", "talking_point": "one specific business observation", '
        '"objective": "book a 15-minute discovery call", "fallback": "offer to send a short email instead", '
        '"company_name": "the business name"}. '
        "This is a briefing card, not a script. Fill in real values from the prospect data."
    ),
    "sms": (
        "Write a single SMS message. One sentence. Direct. Reference their business by name. "
        "Offer a specific value observation, not a generic pitch. Max 160 characters. No mention of AI."
    ),
}

_SYSTEM_PROMPT = """You are a senior business development consultant writing personalised outreach for a digital marketing agency.

Rules:
- Never use "I hope this email finds you well" or any equivalent
- Never mention AI, automation, or that you used technology to find them
- Reference exactly ONE specific signal from the prospect data
- Match the agency's communication style described in the agency brief
- Keep email under 100 words, LinkedIn note under 300 characters
- Every message must pass: "Would I reply to this if I received it?"
- Sound like a curious, intelligent human — not a salesperson
- Do not fabricate specific numbers or claims not in the data provided"""


class Stage7Haiku:
    """
    Haiku-powered personalised outreach message generator.

    Usage:
        stage = Stage7Haiku(anthropic_client, signal_repo, conn)
        result = await stage.run("marketing_agency", agency_profile, batch_size=10)
    """

    def __init__(
        self,
        anthropic_client: Any,
        signal_repo: SignalConfigRepository,
        conn: asyncpg.Connection,
    ) -> None:
        self.ai = anthropic_client
        self.signal_repo = signal_repo
        self.conn = conn
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    @property
    def total_cost_usd(self) -> float:
        return (
            self._total_input_tokens * HAIKU_INPUT_COST_PER_TOKEN
            + self._total_output_tokens * HAIKU_OUTPUT_COST_PER_TOKEN
        )

    async def run(
        self,
        vertical_slug: str,
        agency_profile: dict[str, Any],
        batch_size: int = 10,
    ) -> dict[str, Any]:
        """
        Generate personalised outreach messages for S6-completed businesses.
        Gate: propensity_score >= min_score_to_outreach.
        """
        config = await self.signal_repo.get_config(vertical_slug)
        outreach_gate = config.enrichment_gates.get("min_score_to_outreach", 65)

        rows = await self.conn.fetch(
            """
            SELECT id, domain, display_name, gmb_category, state, suburb,
                   dm_name, dm_title, best_match_service, score_reason,
                   tech_stack, tech_gaps, dfs_paid_keywords, gmb_rating,
                   gmb_review_count, outreach_channels
            FROM business_universe
            WHERE pipeline_stage = 6
              AND propensity_score >= $1
            ORDER BY propensity_score DESC
            LIMIT $2
            """,
            outreach_gate,
            batch_size,
        )

        messages_generated = 0

        for row in rows:
            business = dict(row)
            channels = list(business.get("outreach_channels") or [])
            if not channels:
                continue

            messages = await self._generate_messages(business, agency_profile, channels)
            await self._write_messages(business["id"], messages)
            messages_generated += len(messages)

        return {
            "messages_generated": messages_generated,
            "cost_usd": self.total_cost_usd,
            "cost_aud": round(self.total_cost_usd * 1.55, 4),
        }

    async def _generate_messages(
        self,
        business: dict[str, Any],
        agency_profile: dict[str, Any],
        channels: list[str],
    ) -> dict[str, str]:
        """Generate messages for each confirmed channel."""
        prospect_brief = self._build_prospect_brief(business)
        agency_brief = self._build_agency_brief(agency_profile)
        messages: dict[str, str] = {}

        for channel in channels:
            if channel == "physical":
                continue  # No message type for physical channel
            prompt = _CHANNEL_PROMPTS.get(channel)
            if not prompt:
                continue

            user_prompt = (
                f"PROSPECT BRIEF:\n{prospect_brief}\n\n"
                f"AGENCY BRIEF:\n{agency_brief}\n\n"
                f"TASK:\n{prompt}"
            )

            try:
                response = await self.ai.complete(
                    prompt=user_prompt,
                    system=_SYSTEM_PROMPT,
                    model=HAIKU_MODEL,
                    max_tokens=400,
                    temperature=0.7,
                )
                content = response.get("content", "") if isinstance(response, dict) else str(response)
                self._total_input_tokens += response.get("input_tokens", 0) if isinstance(response, dict) else 0
                self._total_output_tokens += response.get("output_tokens", 0) if isinstance(response, dict) else 0
                messages[channel] = content.strip()
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.warning(f"Haiku call failed for {business.get('domain')} channel={channel}: {e}")

        return messages

    def _build_prospect_brief(self, business: dict[str, Any]) -> str:
        tech_stack = list(business.get("tech_stack") or [])[:5]
        tech_gaps = list(business.get("tech_gaps") or [])[:3]
        paid_kw = business.get("dfs_paid_keywords") or 0
        location = ", ".join(filter(None, [business.get("suburb"), business.get("state")]))

        lines = [
            f"Business: {business.get('display_name') or business.get('domain')}",
            f"Domain: {business.get('domain')}",
            f"Category: {business.get('gmb_category') or 'Unknown'}",
            f"Location: {location or 'Australia'}",
            f"Decision maker: {business.get('dm_name') or 'Unknown'} ({business.get('dm_title') or 'Unknown title'})",
            f"Best service match: {business.get('best_match_service') or 'Unknown'}",
            f"Score reason: {business.get('score_reason') or 'N/A'}",
            f"Tech stack (top 5): {', '.join(tech_stack) or 'Unknown'}",
            f"Technology gaps: {', '.join(tech_gaps) or 'None detected'}",
            f"Active paid keywords: {paid_kw}",
            f"GMB rating: {business.get('gmb_rating') or 'N/A'} ({business.get('gmb_review_count') or 0} reviews)",
        ]
        return "\n".join(lines)

    def _build_agency_brief(self, agency_profile: dict[str, Any]) -> str:
        lines = [
            f"Agency: {agency_profile.get('name', 'the agency')}",
            f"Services: {', '.join(agency_profile.get('services', []))}",
            f"Tone: {agency_profile.get('tone', 'professional, direct, results-focused')}",
            f"Founder: {agency_profile.get('founder_name', 'the founder')}",
        ]
        if agency_profile.get("case_study"):
            lines.append(f"Relevant case study: {agency_profile['case_study']}")
        return "\n".join(lines)

    async def _write_messages(self, row_id: str, messages: dict[str, str]) -> None:
        """Store messages in outreach_messages JSONB and advance pipeline."""
        now = datetime.now(timezone.utc)
        await self.conn.execute(
            """
            UPDATE business_universe SET
                outreach_messages = $1,
                pipeline_stage = $2,
                pipeline_updated_at = $3
            WHERE id = $4
            """,
            json.dumps(messages),
            PIPELINE_STAGE_S7,
            now,
            row_id,
        )
