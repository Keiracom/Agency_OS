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
import logging
from datetime import UTC, datetime
from typing import Any

import asyncpg

from src.pipeline.signal_config import SignalConfigRepository

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S7 = 7
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# Haiku 4.5 pricing (USD per token)
HAIKU_INPUT_COST_PER_TOKEN = 0.0000008  # $0.80 per million input tokens
HAIKU_OUTPUT_COST_PER_TOKEN = 0.000004  # $4.00 per million output tokens

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
            SELECT bu.id, bu.domain, bu.display_name, bu.gmb_category, bu.state, bu.suburb,
                   bu.best_match_service, bu.score_reason,
                   bu.tech_stack, bu.tech_gaps, bu.dfs_paid_keywords, bu.gmb_rating,
                   bu.gmb_review_count, bu.outreach_channels, bu.vulnerability_report,
                   bdm.id AS bdm_id, bdm.name AS dm_name, bdm.title AS dm_title,
                   bdm.linkedin_url AS dm_linkedin_url, bdm.email AS dm_email,
                   bdm.headline AS dm_headline,
                   bdm.experience_json AS dm_experience,
                   bdm.skills AS dm_skills,
                   bdm.education AS dm_education
            FROM business_universe bu
            LEFT JOIN business_decision_makers bdm
                ON bdm.business_universe_id = bu.id AND bdm.is_current = TRUE
            WHERE bu.pipeline_stage = 6
              AND bu.propensity_score >= $1
            ORDER BY bu.propensity_score DESC
            LIMIT $2
            """,
            outreach_gate,
            batch_size,
        )

        messages_generated = 0

        for row in rows:
            business = dict(row)
            bdm_id = business.get("bdm_id")
            if not bdm_id:
                logger.warning("stage7_skip domain=%s reason=no_bdm", business.get("domain"))
                continue
            channels = list(business.get("outreach_channels") or [])
            if not channels:
                continue

            messages, channel_costs = await self._generate_messages(
                business, agency_profile, channels
            )
            await self._write_messages(business["id"], bdm_id, messages, channel_costs)
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
    ) -> tuple[dict[str, str], dict[str, dict]]:
        """Generate messages for each confirmed channel."""
        prospect_brief = self._build_prospect_brief(business)
        agency_brief = self._build_agency_brief(agency_profile)
        messages: dict[str, str] = {}
        channel_costs: dict[str, dict] = {}

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
                content = (
                    response.get("content", "") if isinstance(response, dict) else str(response)
                )
                input_toks = response.get("input_tokens", 0) if isinstance(response, dict) else 0
                output_toks = response.get("output_tokens", 0) if isinstance(response, dict) else 0
                self._total_input_tokens += input_toks
                self._total_output_tokens += output_toks
                channel_costs[channel] = {"input_tokens": input_toks, "output_tokens": output_toks}
                messages[channel] = content.strip()
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.warning(
                    f"Haiku call failed for {business.get('domain')} channel={channel}: {e}"
                )

        return (messages, channel_costs)

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

        # BDM context (from business_decision_makers JOIN)
        if business.get("dm_headline"):
            lines.append(f"DM headline: {business['dm_headline']}")

        experience = business.get("dm_experience")
        if experience and isinstance(experience, list):
            recent = experience[:2]
            exp_lines = [f"  - {r.get('title', '?')} at {r.get('company', '?')}" for r in recent]
            lines.append("DM recent experience:\n" + "\n".join(exp_lines))

        skills = business.get("dm_skills")
        if skills and isinstance(skills, list):
            lines.append(f"DM skills: {', '.join(skills[:5])}")

        education = business.get("dm_education")
        if education and isinstance(education, list) and education:
            edu = education[0]
            lines.append(f"DM education: {edu.get('degree', '')} — {edu.get('institution', '')}")

        vr = business.get("vulnerability_report")
        if vr and isinstance(vr, dict):
            vulns = vr.get("vulnerabilities", [])
            if vulns:
                top_vulns = [v.get("title", "?") for v in vulns[:3]]
                lines.append(f"Key vulnerabilities: {', '.join(top_vulns)}")

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

    async def _write_messages(
        self,
        row_id: str,
        bdm_id: str,
        messages: dict[str, str],
        channel_costs: dict[str, dict],
    ) -> None:
        """Insert messages into dm_messages and advance pipeline stage."""
        now = datetime.now(UTC)
        for channel, body in messages.items():
            costs = channel_costs.get(channel, {})
            cost_usd = (
                costs.get("input_tokens", 0) * HAIKU_INPUT_COST_PER_TOKEN
                + costs.get("output_tokens", 0) * HAIKU_OUTPUT_COST_PER_TOKEN
            )
            await self.conn.execute(
                """
                INSERT INTO dm_messages (
                    business_universe_id, business_decision_makers_id,
                    channel, body, model, cost_usd, status, generated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, 'draft', $7)
                """,
                row_id,
                bdm_id,
                channel,
                body,
                HAIKU_MODEL,
                round(cost_usd, 6),
                now,
            )
        await self.conn.execute(
            """
            UPDATE business_universe SET
                pipeline_stage = $1, pipeline_updated_at = $2
            WHERE id = $3
            """,
            PIPELINE_STAGE_S7,
            now,
            row_id,
        )
