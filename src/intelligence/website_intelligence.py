"""
Contract: src/intelligence/website_intelligence.py
Purpose: LLM-powered website and GMB intelligence — supplements regex pipeline
Layer: 3 - engines (imports: models, integrations only)
Imports: src.integrations.anthropic
Consumers: src.pipeline.pipeline_orchestrator (injected as dependency)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from src.exceptions import AISpendLimitError, APIError, IntegrationError
from src.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)

# ── Cacheable system prompts ───────────────────────────────────────────────────

_COMPREHEND_SYSTEM = (
    "You are a business analyst classifying Australian small businesses for digital marketing "
    "agency prospecting.\n"
    "Analyze the website text provided and return a JSON object with exactly the fields specified.\n"
    "Be concise. Do not explain your reasoning outside the JSON."
)

_INTENT_SYSTEM = (
    "You are a senior sales strategist at an Australian digital marketing agency.\n"
    "Your job is to classify whether a local business prospect is HOT, WARM, or COLD — meaning "
    "how urgently they need marketing help and how likely they are to convert.\n\n"
    "HOT: Business is clearly trying to do marketing but getting poor results. Strong buying signals: "
    "running Google Ads without conversion tracking, poor GMB rating despite many reviews, booking "
    "system without analytics, no analytics on a WordPress/Webflow site with an active social presence.\n\n"
    "WARM: Business has some digital presence and marketing effort but significant untapped gaps. "
    "They're doing something right but leaving money on the table.\n\n"
    "COLD: Business is either very sophisticated (doesn't need help) or has almost no digital "
    "presence/intent signals. Either not a buyer or not ready.\n\n"
    "Return only a JSON object. One sentence for reasoning. Be direct and commercial in your language."
)

_GMB_SYSTEM = (
    "You are analyzing Google My Business signals for Australian small businesses to identify "
    "marketing pain points.\n"
    "Score how urgently this business needs marketing help, based on their GMB presence.\n"
    "Return only JSON. No explanation outside JSON."
)


# ── Output schema ──────────────────────────────────────────────────────────────


@dataclass
class WebsiteIntelligence:
    # ── Haiku-powered: website comprehension ──────────────────────────
    services: list[str]
    business_type: str  # "agency" | "freelancer" | "in-house" | "unknown"
    team_size_signal: str  # "solo" | "small" | "medium" | "large" | "unknown"
    is_actively_marketing: bool
    comprehension_confidence: float  # 0.0-1.0

    # ── Sonnet-powered: intent classification ─────────────────────────
    intent_grade: str  # "HOT" | "WARM" | "COLD"
    intent_reasoning: str  # 1-sentence explanation

    # ── Haiku-powered: GMB review intelligence ────────────────────────
    gmb_pain_themes: list[str]
    gmb_opportunity_score: int  # 0-100

    # ── Meta ──────────────────────────────────────────────────────────
    haiku_cost_aud: float = 0.0
    sonnet_cost_aud: float = 0.0
    fallback_used: bool = False


# ── Engine ─────────────────────────────────────────────────────────────────────


class WebsiteIntelligenceEngine:
    HAIKU_MODEL = "claude-haiku-4-5-20251001"
    SONNET_MODEL = "claude-sonnet-4-20250514"
    HTML_TEXT_MAX_CHARS = 3000
    HAIKU_MAX_TOKENS = 250
    SONNET_MAX_TOKENS = 100
    GMB_MAX_TOKENS = 150

    def __init__(self, anthropic_client: AnthropicClient) -> None:
        """Inject AnthropicClient — do not instantiate internally."""
        self._client = anthropic_client

    async def analyze(
        self,
        domain: str,
        html: str,
        intent_signals: dict,
        gmb_data: dict | None = None,
        ads_data: dict | None = None,
    ) -> WebsiteIntelligence:
        """
        Full three-call analysis pipeline:
        1. Haiku: website comprehension (parallel-safe — call first)
        2. Haiku: GMB analysis (can run parallel with step 1)
        3. Sonnet: intent grade (waits for steps 1+2 — needs their output)

        Steps 1 and 2 run concurrently via asyncio.gather().
        Returns WebsiteIntelligence with fallback_used=True on any API failure.
        """
        try:

            async def _empty_gmb() -> dict:
                return {}

            comprehension, gmb_result = await asyncio.gather(
                self.comprehend_website(domain, html),
                self.analyze_gmb(domain, gmb_data) if gmb_data else _empty_gmb(),
            )

            intent_result = await self.grade_intent(
                domain, comprehension, intent_signals, gmb_result, ads_data
            )

            haiku_cost = comprehension.get("_cost_aud", 0.0) + gmb_result.get("_cost_aud", 0.0)
            sonnet_cost = intent_result.get("_cost_aud", 0.0)

            return WebsiteIntelligence(
                services=comprehension.get("services", []),
                business_type=comprehension.get("business_type", "unknown"),
                team_size_signal=comprehension.get("team_size_signal", "unknown"),
                is_actively_marketing=comprehension.get("is_actively_marketing", False),
                comprehension_confidence=comprehension.get("comprehension_confidence", 0.0),
                intent_grade=intent_result.get("intent_grade", "WARM"),
                intent_reasoning=intent_result.get("intent_reasoning", ""),
                gmb_pain_themes=gmb_result.get("gmb_pain_themes", []),
                gmb_opportunity_score=gmb_result.get("gmb_opportunity_score", 50),
                haiku_cost_aud=haiku_cost,
                sonnet_cost_aud=sonnet_cost,
                fallback_used=False,
            )
        except AISpendLimitError:
            logger.warning(
                "intelligence_spend_limit_hit domain=%s — skipping LLM for this run", domain
            )
            return self._fallback_intelligence("spend_limit")
        except (APIError, IntegrationError, Exception):
            logger.warning("intelligence_api_error domain=%s", domain, exc_info=True)
            return self._fallback_intelligence("api_unavailable")

    async def comprehend_website(
        self,
        domain: str,
        html: str,
    ) -> dict:
        """
        Haiku call: extracts services, business_type, team_size_signal,
        is_actively_marketing, comprehension_confidence.

        Returns dict with those keys. On failure, returns safe defaults.
        Records spend via AnthropicClient._record_spend().
        """
        extracted_text = self._extract_visible_text(html, self.HTML_TEXT_MAX_CHARS)
        prompt = (
            f"Domain: {domain}\n\n"
            "Website content:\n"
            "---\n"
            f"{extracted_text}\n"
            "---\n\n"
            "Return ONLY this JSON (no markdown, no explanation):\n"
            "{\n"
            '  "services": [],\n'
            '  "business_type": "unknown",\n'
            '  "team_size_signal": "unknown",\n'
            '  "is_actively_marketing": false,\n'
            '  "comprehension_confidence": 0.0\n'
            "}\n\n"
            "Field definitions:\n"
            "- services: What the business sells or does. Max 6 items. Use plain English labels "
            '(e.g. "dental services", "Google Ads management", "plumbing repairs"). Empty array if unclear.\n'
            '- business_type: "agency" if they sell marketing/design/digital services to other businesses. '
            '"freelancer" if solo consultant or contractor. "in-house" if corporate internal team. '
            '"unknown" if none apply.\n'
            '- team_size_signal: "solo" if only 1 person mentioned. "small" if 2-10 people. '
            '"medium" if 10-50. "large" if 50+. "unknown" if no people mentioned.\n'
            "- is_actively_marketing: true if website mentions running ads, promotions, Google Ads, "
            "social media campaigns, or if advertising tags are present.\n"
            "- comprehension_confidence: 0.0 if page was a bot wall or error page. "
            "0.5 if partial content only. 1.0 if clear, readable homepage."
        )

        expected_keys = [
            "services",
            "business_type",
            "team_size_signal",
            "is_actively_marketing",
            "comprehension_confidence",
        ]
        defaults: dict[str, Any] = {
            "services": [],
            "business_type": "unknown",
            "team_size_signal": "unknown",
            "is_actively_marketing": False,
            "comprehension_confidence": 0.0,
        }

        try:
            result = await self._client.complete(
                prompt=prompt,
                system=_COMPREHEND_SYSTEM,
                max_tokens=self.HAIKU_MAX_TOKENS,
                temperature=0.1,
                model=self.HAIKU_MODEL,
                enable_caching=True,
            )
            parsed = self._parse_haiku_json(result["content"], expected_keys)
            parsed["_cost_aud"] = result.get("cost_aud", 0.0)
            for k, v in defaults.items():
                if k not in parsed:
                    parsed[k] = v
            return parsed
        except (AISpendLimitError, APIError, IntegrationError):
            raise
        except Exception:
            logger.debug("comprehend_website_failed domain=%s", domain, exc_info=True)
            return {**defaults, "_cost_aud": 0.0}

    async def grade_intent(
        self,
        domain: str,
        comprehension: dict,
        intent_signals: dict,
        gmb_result: dict | None = None,
        ads_data: dict | None = None,
    ) -> dict:
        """
        Sonnet call: classifies HOT/WARM/COLD.

        Requires comprehension dict output from comprehend_website().
        intent_signals is the ProspectScorer IntentResult dict (has 'evidence', 'signals').
        Returns {"intent_grade": str, "intent_reasoning": str}.
        """
        services = comprehension.get("services", [])
        business_type = comprehension.get("business_type", "unknown")
        team_size_signal = comprehension.get("team_size_signal", "unknown")
        is_actively_marketing = comprehension.get("is_actively_marketing", False)

        evidence_list = intent_signals.get("evidence", [])
        has_analytics = intent_signals.get("has_analytics", False)
        has_ads_tag = intent_signals.get("has_ads_tag", False)
        has_conversion = intent_signals.get("has_conversion", False)

        gmb_rating = None
        gmb_review_count = 0
        gmb_opportunity_score = 50
        if gmb_result:
            gmb_rating = gmb_result.get("gmb_rating")
            gmb_review_count = gmb_result.get("gmb_review_count", 0) or 0
            gmb_opportunity_score = gmb_result.get("gmb_opportunity_score", 50)
        if ads_data:
            gmb_rating = gmb_rating or ads_data.get("gmb_rating")
            gmb_review_count = gmb_review_count or (ads_data.get("gmb_review_count") or 0)

        evidence_str = (
            "\n".join(f"- {e}" for e in evidence_list)
            if evidence_list
            else "- No intent signals detected"
        )
        services_str = ", ".join(services) if services else "unknown"
        ads_without_conversion = has_ads_tag and not has_conversion

        prompt = (
            f"Domain: {domain}\n"
            f"Services they offer: {services_str}\n"
            f"Business type: {business_type}\n"
            f"Team size: {team_size_signal}\n\n"
            "Intent signals detected:\n"
            f"{evidence_str}\n\n"
            "Key facts:\n"
            f"- Has website analytics: {has_analytics}\n"
            f"- Running Google Ads: {has_ads_tag}\n"
            f"- Conversion tracking set up: {has_conversion}\n"
            f"- GMB rating: {gmb_rating or 'unknown'} ({gmb_review_count} reviews)\n"
            f"- GMB opportunity score: {gmb_opportunity_score}/100\n"
            f"- Actively marketing: {is_actively_marketing}\n"
            f"- Business actively marketing but lacking conversion tracking: {ads_without_conversion}\n\n"
            "Return ONLY this JSON:\n"
            '{"intent_grade": "HOT", "intent_reasoning": "one sentence"}'
        )

        defaults: dict[str, Any] = {
            "intent_grade": "WARM",
            "intent_reasoning": "LLM analysis unavailable — fallback scoring applied",
        }

        try:
            result = await self._client.complete(
                prompt=prompt,
                system=_INTENT_SYSTEM,
                max_tokens=self.SONNET_MAX_TOKENS,
                temperature=0.2,
                model=self.SONNET_MODEL,
                enable_caching=True,
            )
            parsed = self._parse_haiku_json(result["content"], ["intent_grade", "intent_reasoning"])
            parsed["_cost_aud"] = result.get("cost_aud", 0.0)
            # Enforce valid enum values
            if parsed.get("intent_grade") not in ("HOT", "WARM", "COLD"):
                parsed["intent_grade"] = "WARM"
            for k, v in defaults.items():
                if k not in parsed:
                    parsed[k] = v
            return parsed
        except (AISpendLimitError, APIError, IntegrationError):
            raise
        except Exception:
            logger.debug("grade_intent_failed domain=%s", domain, exc_info=True)
            return {**defaults, "_cost_aud": 0.0}

    async def analyze_gmb(
        self,
        domain: str,
        gmb_data: dict,
    ) -> dict:
        """
        Haiku call: identifies GMB pain themes and opportunity score.

        gmb_data keys used: gmb_rating, gmb_review_count, gmb_review_snippets (optional).
        Returns {"gmb_pain_themes": list[str], "gmb_opportunity_score": int}.
        """
        if not gmb_data:
            return {"gmb_pain_themes": [], "gmb_opportunity_score": 50, "_cost_aud": 0.0}

        gmb_rating = gmb_data.get("gmb_rating")
        gmb_review_count = gmb_data.get("gmb_review_count", 0) or 0
        review_snippets: list[str] = gmb_data.get("gmb_review_snippets") or []

        if review_snippets:
            snippets_str = "\n".join(f'- "{s}"' for s in review_snippets[:5])
            review_section = f"Review snippets:\n{snippets_str}"
        else:
            review_section = "Review text: not available"

        prompt = (
            f"Domain: {domain}\n"
            f"GMB Rating: {gmb_rating or 'not available'}\n"
            f"Review Count: {gmb_review_count or 0}\n"
            f"{review_section}\n\n"
            "Pain theme definitions:\n"
            '- "slow response": business is slow to respond to customers\n'
            '- "poor quality": service quality complaints visible\n'
            '- "inconsistent service": highly variable quality mentioned\n'
            '- "missing digital presence": very few reviews for what appears to be an established '
            "business (e.g. <10 reviews but clearly operational)\n"
            '- "reputation risk": low rating (under 4.0) with high review count (20+) — '
            "urgent intervention needed\n"
            '- "no reviews": zero reviews — invisible online despite being operational\n\n'
            "gmb_opportunity_score rules:\n"
            "- 0-20: Sophisticated business, good reputation, doesn't need help\n"
            "- 21-50: Decent but gaps exist\n"
            "- 51-75: Clear pain signals, likely receptive\n"
            "- 76-100: Urgent — reputation damage, missing presence, or obvious neglect\n\n"
            "Return ONLY this JSON:\n"
            '{"gmb_pain_themes": [], "gmb_opportunity_score": 0}'
        )

        expected_keys = ["gmb_pain_themes", "gmb_opportunity_score"]
        defaults: dict[str, Any] = {"gmb_pain_themes": [], "gmb_opportunity_score": 50}

        try:
            result = await self._client.complete(
                prompt=prompt,
                system=_GMB_SYSTEM,
                max_tokens=self.GMB_MAX_TOKENS,
                temperature=0.1,
                model=self.HAIKU_MODEL,
                enable_caching=True,
            )
            parsed = self._parse_haiku_json(result["content"], expected_keys)
            parsed["_cost_aud"] = result.get("cost_aud", 0.0)
            # Pass through GMB raw data for grade_intent to use
            parsed["gmb_rating"] = gmb_rating
            parsed["gmb_review_count"] = gmb_review_count
            for k, v in defaults.items():
                if k not in parsed:
                    parsed[k] = v
            return parsed
        except (AISpendLimitError, APIError, IntegrationError):
            raise
        except Exception:
            logger.debug("analyze_gmb_failed domain=%s", domain, exc_info=True)
            return {
                **defaults,
                "_cost_aud": 0.0,
                "gmb_rating": gmb_rating,
                "gmb_review_count": gmb_review_count,
            }

    @staticmethod
    def _extract_visible_text(html: str, max_chars: int = 3000) -> str:
        """
        Strip scripts, styles, head (except title), HTML tags.
        Extract title, meta description, first h1 as prefix.
        Truncate body text to max_chars.
        Returns formatted string ready to inject into prompt.
        """
        if not html:
            return ""

        # Extract title before stripping head
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Extract meta description
        meta_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
            html,
            re.IGNORECASE,
        )
        if not meta_match:
            meta_match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
                html,
                re.IGNORECASE,
            )
        meta_description = meta_match.group(1).strip() if meta_match else ""

        # Extract first h1
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        first_h1 = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip() if h1_match else ""

        # Strip script, style, head blocks
        clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<head[^>]*>.*?</head>", "", clean, flags=re.DOTALL | re.IGNORECASE)

        # Strip remaining HTML tags and collapse whitespace
        clean = re.sub(r"<[^>]+>", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        body_text = clean[:max_chars]

        parts: list[str] = []
        if title:
            parts.append(f"Title: {title}")
        if meta_description:
            parts.append(f"Description: {meta_description}")
        if first_h1:
            parts.append(f"H1: {first_h1}")
        parts.append("")
        parts.append("Page text:")
        parts.append(body_text)
        return "\n".join(parts)

    @staticmethod
    def _parse_haiku_json(content: str, expected_keys: list[str]) -> dict:
        """
        Parse JSON from Haiku response. Handles markdown code fences.
        Returns dict with only expected_keys; fills missing keys with safe defaults.
        Does NOT raise on malformed JSON — returns empty dict instead.
        """
        if not content:
            return {}

        text = content.strip()

        # Strip markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Find JSON object in text (handles prose before/after)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return {}
            return {k: data[k] for k in expected_keys if k in data}
        except (json.JSONDecodeError, ValueError):
            return {}

    @staticmethod
    def _fallback_intelligence(reason: str) -> WebsiteIntelligence:
        """Return safe-default WebsiteIntelligence with fallback_used=True."""
        return WebsiteIntelligence(
            services=[],
            business_type="unknown",
            team_size_signal="unknown",
            is_actively_marketing=False,
            comprehension_confidence=0.0,
            intent_grade="WARM",
            intent_reasoning="LLM analysis unavailable — fallback scoring applied",
            gmb_pain_themes=[],
            gmb_opportunity_score=50,
            fallback_used=True,
        )


# ── Factory ────────────────────────────────────────────────────────────────────


def get_website_intelligence_engine() -> WebsiteIntelligenceEngine:
    """Get singleton WebsiteIntelligenceEngine using global AnthropicClient."""
    from src.integrations.anthropic import get_anthropic_client

    return WebsiteIntelligenceEngine(get_anthropic_client())
