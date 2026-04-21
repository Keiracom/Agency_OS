"""
Stage 10 Message Generator — Phase 1
Directive #339.1

Split-model architecture: Sonnet for email (quality), Haiku for LinkedIn/SMS/Voice (speed+cost).
Prompt caching on system prompt + agency brief (80%+ cache hit rate after first call).
Writes one dm_messages row per channel per DM.

Cost target: $0.030 AUD per DM across 4 channels.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import asyncpg

from src.enrichment.signal_config import SignalConfigRepository
from src.utils.domain_blocklist import BLOCKED_DOMAINS

logger = logging.getLogger(__name__)

SONNET_MODEL = "claude-sonnet-4-20250514"
HAIKU_MODEL = "claude-haiku-4-5-20251001"
PIPELINE_STAGE_S10 = 10

# Concurrency ceilings
SONNET_CONCURRENCY = 12
HAIKU_CONCURRENCY = 15

# USD pricing per token
SONNET_INPUT_COST = 0.000003    # $3/M input
SONNET_OUTPUT_COST = 0.000015   # $15/M output
HAIKU_INPUT_COST = 0.0000008    # $0.80/M input
HAIKU_OUTPUT_COST = 0.000004    # $4/M output

_CHANNEL_PROMPTS = {
    "email": (
        "Write a 3-line cold email. Line 1: one specific observation about their business (use the tech stack, "
        "ad spend, or GMB data provided). Line 2: one question about their situation. Line 3: soft CTA — "
        "ask if they're open to a quick chat, not to buy anything. Sign off with the agency founder's name. "
        "Under 100 words. No 'I hope this email finds you well'. No mention of AI or automation. "
        "Sound like a curious peer, not a salesperson. "
        "Prepend one line: SUBJECT: <subject line>, then blank line, then the email body."
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


class Stage10MessageGenerator:
    """
    Split-model outreach message generator.

    Sonnet 4 for email (quality), Haiku 4.5 for LinkedIn/SMS/Voice (cost).
    Prompt caching enabled. Writes to dm_messages table.

    Usage:
        stage = Stage10MessageGenerator(anthropic_client, signal_repo, conn)
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
        self._sonnet_sem = asyncio.Semaphore(SONNET_CONCURRENCY)
        self._haiku_sem = asyncio.Semaphore(HAIKU_CONCURRENCY)
        self._stats: dict[str, Any] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "cost_usd": 0.0,
            "per_channel": {
                "email": {"count": 0, "cost_usd": 0.0},
                "linkedin": {"count": 0, "cost_usd": 0.0},
                "sms": {"count": 0, "cost_usd": 0.0},
                "voice": {"count": 0, "cost_usd": 0.0},
            },
        }

    async def run(
        self,
        vertical_slug: str,
        agency_profile: dict[str, Any],
        batch_size: int = 10,
    ) -> dict[str, Any]:
        """Generate messages for S9-completed businesses with a confirmed BDM."""
        config = await self.signal_repo.get_config(vertical_slug)
        outreach_gate = config.enrichment_gates.get("min_score_to_outreach", 65)

        rows = await self.conn.fetch(
            """
            SELECT
                bu.id, bu.domain, bu.display_name, bu.gmb_category, bu.state, bu.suburb,
                bu.dm_name, bu.dm_title, bu.best_match_service, bu.score_reason,
                bu.tech_stack, bu.tech_gaps, bu.dfs_paid_keywords, bu.gmb_rating,
                bu.gmb_review_count, bu.outreach_channels, bu.vulnerability_report,
                bdm.id           AS bdm_id,
                bdm.headline     AS bdm_headline,
                bdm.experience_json AS bdm_experience,
                bdm.skills       AS bdm_skills,
                bdm.education    AS bdm_education
            FROM business_universe bu
            LEFT JOIN business_decision_makers bdm
                ON bdm.business_universe_id = bu.id AND bdm.is_current = TRUE
            WHERE bu.pipeline_stage = 9
              AND bu.propensity_score >= $1
              AND bu.domain NOT IN (SELECT unnest($3::text[]))
            ORDER BY bu.propensity_score DESC
            LIMIT $2
            """,
            outreach_gate,
            batch_size,
            list(BLOCKED_DOMAINS),
        )

        messages_generated = 0
        dms_processed = 0
        skipped_no_bdm = 0

        for row in rows:
            business = dict(row)
            if not business.get("bdm_id"):
                skipped_no_bdm += 1
                continue

            channels = list(business.get("outreach_channels") or list(_CHANNEL_PROMPTS.keys()))
            active_channels = [c for c in channels if c in _CHANNEL_PROMPTS]
            if not active_channels:
                skipped_no_bdm += 1
                continue

            prospect_brief = self._build_prospect_brief(business)
            agency_brief = self._build_agency_brief(agency_profile)

            # Email runs with Sonnet; LinkedIn+SMS+Voice run concurrently with Haiku
            haiku_channels = [c for c in active_channels if c != "email"]
            tasks = []
            if "email" in active_channels:
                tasks.append(
                    self._generate_for_channel("email", business, prospect_brief, agency_brief)
                )
            for ch in haiku_channels:
                tasks.append(
                    self._generate_for_channel(ch, business, prospect_brief, agency_brief)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            channel_messages: list[tuple[str, str, str | None, dict[str, Any]]] = []
            for res in results:
                if isinstance(res, Exception):
                    logger.warning("Channel generation failed for %s: %s", business.get("domain"), res)
                    continue
                channel_messages.append(res)  # type: ignore[arg-type]

            if channel_messages:
                await self._write_messages(
                    business["id"], business["bdm_id"], channel_messages
                )
                messages_generated += len(channel_messages)
                dms_processed += 1

        total_non_cached = max(
            0, self._stats["input_tokens"] - self._stats["cached_tokens"]
        )
        total_seen = total_non_cached + self._stats["cached_tokens"]
        cache_hit_rate = (
            round(self._stats["cached_tokens"] / total_seen, 4) if total_seen > 0 else 0.0
        )

        return {
            "messages_generated": messages_generated,
            "dms_processed": dms_processed,
            "skipped_no_bdm": skipped_no_bdm,
            "cost_usd": round(self._stats["cost_usd"], 6),
            "cost_aud": round(self._stats["cost_usd"] * 1.55, 4),
            "cache_hit_rate": cache_hit_rate,
            "per_channel": self._stats["per_channel"],
        }

    async def _generate_for_channel(
        self,
        channel: str,
        business: dict[str, Any],
        prospect_brief: str,
        agency_brief: str,
    ) -> tuple[str, str, str | None, dict[str, Any]]:
        """Call AI for one channel. Returns (channel, body, subject|None, cost_info)."""
        model = SONNET_MODEL if channel == "email" else HAIKU_MODEL
        sem = self._sonnet_sem if channel == "email" else self._haiku_sem
        max_tokens = 500 if channel == "email" else 300
        prompt_text = _CHANNEL_PROMPTS[channel]

        user_prompt = (
            f"PROSPECT BRIEF:\n{prospect_brief}\n\n"
            f"AGENCY BRIEF:\n{agency_brief}\n\n"
            f"TASK:\n{prompt_text}"
        )

        async with sem:
            response = await self.ai.complete(
                prompt=user_prompt,
                system=_SYSTEM_PROMPT,
                model=model,
                max_tokens=max_tokens,
                temperature=0.7,
                enable_caching=True,
            )

        content = response.get("content", "") if isinstance(response, dict) else str(response)
        in_tok = response.get("input_tokens", 0) if isinstance(response, dict) else 0
        out_tok = response.get("output_tokens", 0) if isinstance(response, dict) else 0
        cached = response.get("cached_tokens", 0) if isinstance(response, dict) else 0

        if model == SONNET_MODEL:
            cost_usd = in_tok * SONNET_INPUT_COST + out_tok * SONNET_OUTPUT_COST
        else:
            cost_usd = in_tok * HAIKU_INPUT_COST + out_tok * HAIKU_OUTPUT_COST

        self._stats["input_tokens"] += in_tok
        self._stats["output_tokens"] += out_tok
        self._stats["cached_tokens"] += cached
        self._stats["cost_usd"] += cost_usd
        self._stats["per_channel"][channel]["count"] += 1
        self._stats["per_channel"][channel]["cost_usd"] += cost_usd

        subject: str | None = None
        body = content.strip()
        if channel == "email" and body.startswith("SUBJECT:"):
            lines = body.split("\n", 2)
            subject = lines[0].replace("SUBJECT:", "").strip()
            body = lines[2].strip() if len(lines) > 2 else body

        return (channel, body, subject, {"input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": cost_usd})

    async def _write_messages(
        self,
        bu_id: str,
        bdm_id: str,
        channel_messages: list[tuple[str, str, str | None, dict[str, Any]]],
        critic_results: dict[str, dict] | None = None,
    ) -> None:
        """Insert dm_messages rows and advance pipeline_stage to 10.

        Args:
            bu_id: Business universe ID.
            bdm_id: Business decision-maker ID.
            channel_messages: List of (channel, body, subject, cost_info) tuples.
            critic_results: Optional dict keyed by channel name containing
                {"score": int, "feedback": str, "needs_review": bool}.
                When None, critic columns default to NULL/FALSE.
        """
        now = datetime.now(UTC)
        for channel, body, subject, cost_info in channel_messages:
            model_name = SONNET_MODEL if channel == "email" else HAIKU_MODEL
            critic = (critic_results or {}).get(channel, {})
            critic_score = critic.get("score")
            critic_feedback = critic.get("feedback")
            needs_review = critic.get("needs_review", False)
            await self.conn.execute(
                """
                INSERT INTO dm_messages
                    (business_universe_id, business_decision_makers_id, channel,
                     subject, body, model, cost_usd, status, generated_at,
                     critic_score, critic_feedback, needs_review)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'draft', $8,
                        $9, $10, $11)
                """,
                bu_id, bdm_id, channel,
                subject, body, model_name,
                cost_info["cost_usd"], now,
                critic_score, critic_feedback, needs_review,
            )

        await self.conn.execute(
            """
            UPDATE business_universe
            SET pipeline_stage = $1, pipeline_updated_at = $2
            WHERE id = $3
            """,
            PIPELINE_STAGE_S10, now, bu_id,
        )

    def _build_prospect_brief(self, business: dict[str, Any]) -> str:
        tech_stack = list(business.get("tech_stack") or [])[:5]
        tech_gaps = list(business.get("tech_gaps") or [])[:3]
        paid_kw = business.get("dfs_paid_keywords") or 0
        location = ", ".join(filter(None, [business.get("suburb"), business.get("state")]))

        bdm_headline = business.get("bdm_headline") or ""
        bdm_experience = business.get("bdm_experience") or []
        top_role = ""
        if bdm_experience and isinstance(bdm_experience, list) and bdm_experience:
            top = bdm_experience[0]
            top_role = f"{top.get('title', '')} at {top.get('company', '')}".strip(" at")

        bdm_skills = list(business.get("bdm_skills") or [])[:3]
        vuln = business.get("vulnerability_report") or {}
        vuln_summary = ""
        if vuln and isinstance(vuln, dict):
            grades = {k: v.get("grade") for k, v in vuln.items() if isinstance(v, dict) and "grade" in v}
            if grades:
                vuln_summary = ", ".join(f"{k}:{g}" for k, g in grades.items())

        lines = [
            f"Business: {business.get('display_name') or business.get('domain')}",
            f"Domain: {business.get('domain')}",
            f"Category: {business.get('gmb_category') or 'Unknown'}",
            f"Location: {location or 'Australia'}",
            f"Decision maker: {business.get('dm_name') or 'Unknown'} ({business.get('dm_title') or 'Unknown title'})",
            f"BDM headline: {bdm_headline or 'N/A'}",
            f"BDM recent role: {top_role or 'N/A'}",
            f"BDM skills: {', '.join(bdm_skills) or 'N/A'}",
            f"Best service match: {business.get('best_match_service') or 'Unknown'}",
            f"Score reason: {business.get('score_reason') or 'N/A'}",
            f"Tech stack (top 5): {', '.join(tech_stack) or 'Unknown'}",
            f"Technology gaps: {', '.join(tech_gaps) or 'None detected'}",
            f"Active paid keywords: {paid_kw}",
            f"GMB rating: {business.get('gmb_rating') or 'N/A'} ({business.get('gmb_review_count') or 0} reviews)",
        ]
        if vuln_summary:
            lines.append(f"Vulnerability grades: {vuln_summary}")
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
