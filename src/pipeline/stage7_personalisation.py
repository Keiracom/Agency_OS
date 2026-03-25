# FILE: src/pipeline/stage7_personalisation.py
# PURPOSE: Stage 7 — Haiku batch personalisation for campaign_leads
# PIPELINE STAGE: campaign_leads.status never_touched → personalised
# DEPENDENCIES: src.integrations.anthropic, asyncpg
# DIRECTIVE: #252

from __future__ import annotations

import asyncio
import json
import logging
import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from src.integrations.anthropic import AnthropicClient, get_anthropic_client

logger = logging.getLogger(__name__)

# Haiku pricing (AUD) — input/output per token
HAIKU_INPUT_COST_PER_TOKEN = Decimal("0.00000124")   # $1.24 AUD / 1M tokens
HAIKU_OUTPUT_COST_PER_TOKEN = Decimal("0.00000620")  # $6.20 AUD / 1M tokens
HAIKU_MODEL = "claude-haiku-4-5-20251001"
BATCH_DELAY_SECONDS = 0.5  # 500ms between Haiku calls (rate limit buffer)

SYSTEM_PROMPT = """You are a B2B outreach specialist writing on behalf of an Australian marketing agency. Generate personalised outreach messages for a specific prospect business.

Rules:
- Reference specific signals about the prospect (their actual business situation, not generic pain points)
- Match the agency's communication style and service offerings
- Each channel has different constraints: email (subject + body, <150 words), LinkedIn (connection note, <300 chars), SMS (<160 chars), voice (conversation opener + key talking point, <100 words)
- Never fabricate information — only reference signals provided in the prospect data
- Be direct and specific. No filler. No "I hope this finds you well."
- Australian English spelling and conventions

Respond with ONLY a JSON object, no markdown, no explanation:
{
  "outreach_angle": "one sentence summary of why this prospect is being contacted",
  "email": {"subject": "...", "body": "..."},
  "linkedin": {"note": "..."},
  "sms": {"body": "..."},
  "voice": {"opener": "...", "talking_point": "..."}
}
Only include channels that are listed as available. Omit channels not available."""


class Stage7Personalisation:
    def __init__(self, anthropic_client: AnthropicClient, db) -> None:
        self.ai = anthropic_client
        self.db = db
        self._total_cost = Decimal("0")

    async def run(self, campaign_id: UUID, batch_size: int = 20) -> dict:
        """
        Personalise campaign_leads at status='never_touched' for campaign_id.
        Returns: personalised, messages_generated, cost_aud, errors
        """
        personalised = 0
        messages_generated = 0
        errors: list[dict] = []

        # Fetch batch of campaign_leads + BU data
        rows = await self.db.fetch("""
            SELECT
                cl.id AS cl_id,
                cl.campaign_id,
                cl.client_id,
                bu.id AS bu_id,
                bu.display_name,
                bu.gmb_category,
                bu.suburb,
                bu.state,
                bu.gmb_rating,
                bu.gmb_review_count,
                bu.website,
                bu.domain,
                bu.phone,
                bu.dm_name,
                bu.dm_title,
                bu.dm_email,
                bu.dm_linkedin_url,
                bu.dm_mobile,
                bu.has_google_ads,
                bu.has_facebook_pixel,
                bu.listed_on_yp,
                bu.yp_advertiser,
                bu.site_copyright_year,
                bu.is_mobile_responsive,
                bu.propensity_score,
                bu.reachability_score,
                bu.propensity_reasons
            FROM campaign_leads cl
            JOIN business_universe bu ON cl.business_universe_id = bu.id
            WHERE cl.campaign_id = $1
              AND cl.status = 'never_touched'
            LIMIT $2
            FOR UPDATE OF cl SKIP LOCKED
        """, campaign_id, batch_size)

        if not rows:
            return {"personalised": 0, "messages_generated": 0, "cost_aud": 0.0, "errors": []}

        # Fetch agency context ONCE per batch (same client for all rows in campaign)
        client_id = rows[0]["client_id"]
        agency = await self._fetch_agency_context(client_id)

        for row in rows:
            try:
                available_channels = self._get_available_channels(row)
                if not available_channels:
                    await self.db.execute("""
                        UPDATE campaign_leads SET status = 'personalisation_failed', updated_at = NOW()
                        WHERE id = $1
                    """, row["cl_id"])
                    errors.append({"cl_id": str(row["cl_id"]), "error": "no_channels_available"})
                    continue

                user_prompt = self._build_user_prompt(row, agency, available_channels)

                # Call Haiku — retry once on failure
                response = await self._call_haiku_with_retry(user_prompt, row["cl_id"])
                if response is None:
                    await self.db.execute("""
                        UPDATE campaign_leads SET status = 'personalisation_failed', updated_at = NOW()
                        WHERE id = $1
                    """, row["cl_id"])
                    errors.append({"cl_id": str(row["cl_id"]), "error": "haiku_api_failure"})
                    continue

                parsed, input_tokens, output_tokens = response
                call_cost = self._calculate_cost(input_tokens, output_tokens)
                self._total_cost += call_cost

                # INSERT message rows — one per channel
                channel_count = 0
                outreach_angle = parsed.get("outreach_angle", "")
                tone_notes = outreach_angle  # store angle as tone_notes for transparency

                for channel in available_channels:
                    channel_data = parsed.get(channel)
                    if not channel_data:
                        continue

                    if channel == "email":
                        subject = channel_data.get("subject")
                        body = channel_data.get("body", "")
                    elif channel == "linkedin":
                        subject = None
                        body = channel_data.get("note", "")
                    elif channel == "sms":
                        subject = None
                        body = channel_data.get("body", "")
                    elif channel == "voice":
                        subject = None
                        opener = channel_data.get("opener", "")
                        talking = channel_data.get("talking_point", "")
                        body = f"{opener}\n\n{talking}".strip()
                    else:
                        continue

                    if not body:
                        continue

                    await self.db.execute("""
                        INSERT INTO campaign_lead_messages
                            (campaign_lead_id, channel, subject, body, tone_notes,
                             generation_model, generation_cost_aud, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, 'draft')
                        ON CONFLICT (campaign_lead_id, channel) DO UPDATE SET
                            body = EXCLUDED.body,
                            subject = EXCLUDED.subject,
                            tone_notes = EXCLUDED.tone_notes,
                            updated_at = NOW()
                    """, row["cl_id"], channel, subject, body, tone_notes,
                        HAIKU_MODEL, call_cost)
                    channel_count += 1

                # Update campaign_lead status
                await self.db.execute("""
                    UPDATE campaign_leads SET
                        status = 'personalised',
                        outreach_angle = $1,
                        updated_at = NOW()
                    WHERE id = $2
                """, outreach_angle, row["cl_id"])

                personalised += 1
                messages_generated += channel_count

                # Rate limit buffer
                await asyncio.sleep(BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error("Stage7 error for cl_id=%s: %s", row["cl_id"], e)
                errors.append({"cl_id": str(row["cl_id"]), "error": str(e)})
                try:
                    await self.db.execute("""
                        UPDATE campaign_leads SET status = 'personalisation_failed', updated_at = NOW()
                        WHERE id = $1
                    """, row["cl_id"])
                except Exception:
                    pass

        return {
            "personalised": personalised,
            "messages_generated": messages_generated,
            "cost_aud": float(self._total_cost),
            "errors": errors,
        }

    async def _fetch_agency_context(self, client_id: UUID) -> dict:
        """Fetch agency data from clients table."""
        row = await self.db.fetchrow("""
            SELECT name, company_description, value_proposition,
                   services_offered, website_url
            FROM clients WHERE id = $1
        """, client_id)
        if not row:
            return {}
        return dict(row)

    def _get_available_channels(self, row: dict) -> list[str]:
        channels = []
        if row.get("dm_email"):
            channels.append("email")
        if row.get("dm_linkedin_url"):
            channels.append("linkedin")
        if row.get("dm_mobile"):
            channels.append("sms")
        if row.get("dm_mobile") or row.get("phone"):
            channels.append("voice")
        return channels

    def _build_user_prompt(self, row: dict, agency: dict, channels: list[str]) -> str:
        agency_name = agency.get("name") or "Agency"
        services = agency.get("services_offered") or []
        if isinstance(services, list):
            services_str = ", ".join(services) if services else "Digital marketing services"
        else:
            services_str = str(services)
        value_prop = agency.get("value_proposition") or agency.get("company_description") or ""
        website = agency.get("website_url") or ""

        # Format propensity reasons
        reasons_raw = row.get("propensity_reasons") or []
        reasons_formatted = ""
        for r in reasons_raw:
            try:
                reason = json.loads(r) if isinstance(r, str) else r
                signal = reason.get("signal", "")
                cat = reason.get("category", "")
                if signal:
                    reasons_formatted += f"- {signal} ({cat})\n"
            except Exception:
                pass

        channels_str = ", ".join(channels)

        return f"""AGENCY:
Name: {agency_name}
Services: {services_str}
Website: {website}
Value proposition: {value_prop}

PROSPECT:
Business: {row.get('display_name', 'Unknown')}
Category: {row.get('gmb_category', 'Unknown')}
Location: {row.get('suburb', '')}, {row.get('state', '')}
Rating: {row.get('gmb_rating', 'N/A')} ({row.get('gmb_review_count', 0)} reviews)
Website: {row.get('website') or row.get('domain') or 'None'}
Decision Maker: {row.get('dm_name') or 'Unknown'}, {row.get('dm_title') or 'Unknown'}

SIGNALS:
{reasons_formatted}- Has Google Ads: {row.get('has_google_ads', False)}
- Has Facebook Pixel: {row.get('has_facebook_pixel', False)}
- GMB Rating: {row.get('gmb_rating', 'N/A')}
- Listed on Yellow Pages: {row.get('listed_on_yp', False)} (advertiser: {row.get('yp_advertiser', False)})
- Site copyright year: {row.get('site_copyright_year', 'Unknown')}
- Mobile responsive: {row.get('is_mobile_responsive', False)}

SCORES:
Propensity: {row.get('propensity_score', 0)}/100
Reachability: {row.get('reachability_score', 0)}/100

AVAILABLE CHANNELS: {channels_str}"""

    async def _call_haiku_with_retry(
        self, user_prompt: str, cl_id: UUID
    ) -> tuple[dict, int, int] | None:
        """Call Haiku with one retry. Returns (parsed_json, input_tokens, output_tokens) or None.

        AnthropicClient.complete() returns dict[str, Any] with keys:
            content (str), input_tokens (int), output_tokens (int), cost_aud (float), ...
        """
        for attempt in range(2):
            try:
                result = await self.ai.complete(
                    prompt=user_prompt,
                    system=SYSTEM_PROMPT,
                    max_tokens=600,
                    model=HAIKU_MODEL,
                )
                # result is a dict — content is the raw text string
                content: str = result["content"]
                input_tokens: int = result["input_tokens"]
                output_tokens: int = result["output_tokens"]

                # Strip markdown code fences — some model versions wrap JSON in ```json...```
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:\w+)?\n?", "", content)
                    content = re.sub(r"\n?```\s*$", "", content.strip())
                    content = content.strip()

                parsed = json.loads(content)
                return parsed, input_tokens, output_tokens

            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning("Stage7 JSON parse failure for cl_id=%s, retrying", cl_id)
                    continue
                return None
            except Exception as e:
                if attempt == 0:
                    logger.warning("Stage7 Haiku API error for cl_id=%s: %s, retrying", cl_id, e)
                    continue
                return None
        return None

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            Decimal(str(input_tokens)) * HAIKU_INPUT_COST_PER_TOKEN
            + Decimal(str(output_tokens)) * HAIKU_OUTPUT_COST_PER_TOKEN
        )
