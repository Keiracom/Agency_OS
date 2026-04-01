"""
Contract: src/pipeline/intelligence.py
Purpose: Hybrid Sonnet/Haiku intelligence layer — replaces regex/rule-based website
         analysis and intent classification with LLM comprehension.
Layer: 3 - pipeline (called after free enrichment, before scoring gates)
Directive: #296

Five async stages:
  1. comprehend_website   — Sonnet, website HTML → structured signals
  2. classify_intent      — Sonnet, signals + gmb + ads → band + evidence
  3. analyse_reviews      — Sonnet, GMB reviews → sentiment + pain themes
  4. judge_affordability  — Haiku, ABN + website → score + hard gate
  5. refine_evidence      — Haiku, intent + reviews + website → final card copy

All calls:
  - Use GLOBAL_SEM_SONNET / GLOBAL_SEM_HAIKU from pipeline_orchestrator
  - System prompt (static, cacheable) first; variable content last
  - Return parsed JSON; on parse failure return safe fallback dict
  - Log input/output token counts for cost tracking
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Semaphores — defined here and re-exported; pipeline_orchestrator imports these ──
# Defined in intelligence.py to avoid circular import with pipeline_orchestrator.
GLOBAL_SEM_SONNET = asyncio.Semaphore(55)   # Sonnet concurrent calls (prompt caching reduces ITPM)
GLOBAL_SEM_HAIKU  = asyncio.Semaphore(55)   # Haiku concurrent calls


async def ramp_semaphore(
    sem: asyncio.Semaphore,
    target: int,
    start: int = 5,
    step: int = 5,
    interval: float = 2.0,
) -> None:
    """
    Gradually release a semaphore from `start` slots up to `target`.
    Call as a background task before launching parallel Sonnet work.
    The caller must initialise the semaphore with `start` slots (not target).
    Adds `step` slots every `interval` seconds until `target` is reached.
    """
    current = start
    while current < target:
        await asyncio.sleep(interval)
        add = min(step, target - current)
        for _ in range(add):
            sem.release()
        current += add

# ── Model constants ───────────────────────────────────────────────────────────
_MODEL_SONNET = "claude-sonnet-4-5"
_MODEL_HAIKU  = "claude-haiku-4-5"
_ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"

# Prompt caching beta header
_CACHE_BETA = "prompt-caching-2024-07-31"

# Max HTML chars sent to model — trim to avoid token blowout
_HTML_MAX_CHARS = 12_000
_REVIEW_MAX_CHARS = 6_000


def _get_api_key() -> str:
    """Resolve Anthropic API key from environment or settings."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            from src.config.settings import settings
            key = settings.anthropic_api_key
        except Exception:
            pass
    return key


def _trim_html(html: str) -> str:
    """Strip script/style blocks and trim HTML to max chars."""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html).strip()
    return html[:_HTML_MAX_CHARS]


def _parse_json_response(text: str, fallback: dict) -> dict:
    """Extract JSON from model response; return fallback on failure."""
    # Try to find JSON block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    logger.warning("intelligence: failed to parse JSON response, using fallback")
    return fallback


async def _call_anthropic(
    model: str,
    system_blocks: list[dict],
    user_content: str,
    max_tokens: int = 1024,
) -> tuple[str, int, int]:
    """
    POST to Anthropic Messages API.
    Returns (response_text, input_tokens, output_tokens).
    system_blocks: list of content blocks, first block marked cache_control for caching.
    """
    api_key = _get_api_key()
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "anthropic-beta": _CACHE_BETA,
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_blocks,
        "messages": [{"role": "user", "content": user_content}],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(_ANTHROPIC_API, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    text = data["content"][0]["text"] if data.get("content") else ""
    usage = data.get("usage", {})
    in_tok  = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)
    return text, in_tok, out_tok


# ── Stage 1: Website comprehension (Sonnet) ───────────────────────────────────

_WEBSITE_SYSTEM = """You are a business intelligence analyst specialising in Australian SMBs. \
Analyse the website content provided and extract structured signals about the business.

Return ONLY valid JSON with these exact keys:
{
  "services": ["list of services offered"],
  "team_size_indicator": "solo|small(2-5)|medium(6-20)|large(20+)|unknown",
  "technology_signals": {
    "has_analytics": true/false,
    "has_ads_tag": true/false,
    "has_meta_pixel": true/false,
    "has_booking_system": true/false,
    "has_conversion_tracking": true/false,
    "cms": "wordpress|wix|squarespace|webflow|shopify|custom|unknown",
    "analytics_tools": ["list of analytics tools detected"]
  },
  "contact_methods": ["phone","email","contact_form","live_chat","booking"],
  "content_freshness": "current|stale|no_content",
  "business_maturity": "startup|growing|established|unknown",
  "location_signals": ["list of AU states/cities mentioned"],
  "pain_indicators": ["list of business problems the site hints at"],
  "emails_found": [
    {"email": "address@example.com", "owner": "owner|office|reception|person_name|generic", "location": "header|footer|contact_page|about_page|other"}
  ]
}

For emails_found: extract ALL email addresses visible in the content. Identify who each likely belongs to and where on the site it appears. Return an empty array if none found."""

_WEBSITE_SYSTEM_BLOCK = {
    "type": "text",
    "text": _WEBSITE_SYSTEM,
    "cache_control": {"type": "ephemeral"},
}


async def comprehend_website(domain: str, html: str, url: str) -> dict:
    """
    Stage 1 — Sonnet. Extract structured business signals from website HTML.
    Replaces regex-based extraction in free_enrichment.py.
    """
    fallback = {
        "services": [], "team_size_indicator": "unknown",
        "technology_signals": {
            "has_analytics": False, "has_ads_tag": False, "has_meta_pixel": False,
            "has_booking_system": False, "has_conversion_tracking": False,
            "cms": "unknown", "analytics_tools": [],
        },
        "contact_methods": [], "content_freshness": "unknown",
        "business_maturity": "unknown", "location_signals": [], "pain_indicators": [],
        "emails_found": [],
    }
    async with GLOBAL_SEM_SONNET:
        try:
            trimmed = _trim_html(html)
            user_content = f"Domain: {domain}\nURL: {url}\n\nWebsite content:\n{trimmed}"
            text, in_tok, out_tok = await _call_anthropic(
                model=_MODEL_SONNET,
                system_blocks=[_WEBSITE_SYSTEM_BLOCK],
                user_content=user_content,
                max_tokens=1024,
            )
            logger.info("comprehend_website domain=%s tokens=%d/%d", domain, in_tok, out_tok)
            return _parse_json_response(text, fallback)
        except Exception as exc:
            logger.warning("comprehend_website failed domain=%s: %s", domain, exc)
            return fallback


# ── Stage 2: Intent classification (Sonnet) ──────────────────────────────────

_INTENT_SYSTEM = """You are a sales intelligence analyst for a digital marketing agency. \
Your job is to classify an Australian SMB's digital marketing intent based on observable signals.

Intent bands:
- NOT_TRYING: No digital marketing activity. No website analytics, no ads, no online presence effort.
- DABBLING: Some effort but inconsistent. Has a website but no tracking, or ran ads but stopped.
- TRYING: Active digital marketing with clear gaps. Running ads without conversion tracking, \
  has analytics but no optimisation, spending money without measuring results.
- STRUGGLING: Heavy investment with obvious problems. High ad spend, poor landing pages, \
  negative reviews, losing market share. Urgent need for help.

Return ONLY valid JSON:
{
  "band": "NOT_TRYING|DABBLING|TRYING|STRUGGLING",
  "score": 0-18,
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence": [
    {"effort": "what the business is doing", "gap": "what they're missing or doing wrong"}
  ],
  "primary_signal": "the single strongest signal that defines this classification",
  "recommended_entry_point": "the most compelling opening for outreach"
}"""

_INTENT_SYSTEM_BLOCK = {
    "type": "text",
    "text": _INTENT_SYSTEM,
    "cache_control": {"type": "ephemeral"},
}


async def classify_intent(
    domain: str,
    website_data: dict,
    gmb_data: dict | None,
    ads_data: dict | None,
    category_name: str | None = None,
) -> dict:
    """
    Stage 2 — Sonnet. Classify digital marketing intent from aggregated signals.
    Replaces point-counting in prospect_scorer.py score_intent_full().
    """
    fallback = {
        "band": "NOT_TRYING", "score": 0, "confidence": "LOW",
        "evidence": [], "primary_signal": "", "recommended_entry_point": "",
    }
    async with GLOBAL_SEM_SONNET:
        try:
            system_text = _INTENT_SYSTEM
            if category_name:
                system_text = system_text + f"\n\nThis business operates in the {category_name} industry. Do not reference other industries in evidence statements."

            system_block = {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }

            signals_summary = {
                "website": website_data,
                "gmb": {
                    "review_count": (gmb_data or {}).get("gmb_review_count", 0),
                    "rating": (gmb_data or {}).get("gmb_rating"),
                    "found": (gmb_data or {}).get("gmb_found", False),
                },
                "ads": {
                    "running": (ads_data or {}).get("is_running_ads", False),
                    "ad_count": (ads_data or {}).get("ad_count", 0),
                },
            }
            user_content = (
                f"Domain: {domain}\n\n"
                f"Signals:\n{json.dumps(signals_summary, indent=2)}"
            )
            text, in_tok, out_tok = await _call_anthropic(
                model=_MODEL_SONNET,
                system_blocks=[system_block],
                user_content=user_content,
                max_tokens=600,
            )
            logger.info("classify_intent domain=%s tokens=%d/%d", domain, in_tok, out_tok)
            return _parse_json_response(text, fallback)
        except Exception as exc:
            logger.warning("classify_intent failed domain=%s: %s", domain, exc)
            return fallback


# ── Stage 3: GMB review analysis (Sonnet) ────────────────────────────────────

_REVIEWS_SYSTEM = """You are analysing Google My Business reviews for an Australian SMB. \
Extract intelligence that would help a marketing agency understand the business's strengths, \
weaknesses, and the owner's engagement style.

Return ONLY valid JSON:
{
  "sentiment_trend": "improving|stable|declining|insufficient_data",
  "average_rating": 0.0,
  "pain_themes": ["list of recurring customer complaints or business problems"],
  "strength_themes": ["list of recurring customer praises"],
  "owner_responsiveness": "always|sometimes|rarely|never",
  "owner_tone": "professional|friendly|defensive|absent",
  "staff_mentions": ["staff names mentioned in reviews"],
  "decision_maker_signals": ["signals about who runs the business"],
  "marketing_opportunity": "one sentence on the strongest marketing angle based on reviews"
}"""

_REVIEWS_SYSTEM_BLOCK = {
    "type": "text",
    "text": _REVIEWS_SYSTEM,
    "cache_control": {"type": "ephemeral"},
}


async def analyse_reviews(domain: str, reviews: list[dict]) -> dict:
    """
    Stage 3 — Sonnet. Read actual GMB review text to extract intelligence.
    Only called when reviews are available from DFS GMB endpoint.
    """
    fallback = {
        "sentiment_trend": "insufficient_data", "average_rating": 0.0,
        "pain_themes": [], "strength_themes": [], "owner_responsiveness": "absent",
        "owner_tone": "absent", "staff_mentions": [], "decision_maker_signals": [],
        "marketing_opportunity": "",
    }
    if not reviews:
        return fallback

    async with GLOBAL_SEM_SONNET:
        try:
            # Trim reviews to stay within token budget
            review_text = json.dumps(reviews, ensure_ascii=False)[:_REVIEW_MAX_CHARS]
            user_content = f"Domain: {domain}\n\nReviews:\n{review_text}"
            text, in_tok, out_tok = await _call_anthropic(
                model=_MODEL_SONNET,
                system_blocks=[_REVIEWS_SYSTEM_BLOCK],
                user_content=user_content,
                max_tokens=600,
            )
            logger.info("analyse_reviews domain=%s reviews=%d tokens=%d/%d",
                        domain, len(reviews), in_tok, out_tok)
            return _parse_json_response(text, fallback)
        except Exception as exc:
            logger.warning("analyse_reviews failed domain=%s: %s", domain, exc)
            return fallback


# ── Stage 4: Affordability judgment (Haiku) ──────────────────────────────────

_AFFORD_SYSTEM = """You are assessing whether an Australian SMB can afford digital marketing services \
(typically $1,500–$5,000 AUD/month). Use ABN registry data and website signals to judge financial capacity.

Hard gates (return hard_gate=true if ANY apply):
- Sole trader (individual, not a company/trust/partnership)
- Not GST registered (turnover < $75K AUD)
- No website AND no ABN found (unreachable)

Score 0–10 based on: entity type, GST status, years trading, professional website, \
email domain, CMS quality, team size signals.

Return ONLY valid JSON:
{
  "score": 0-10,
  "hard_gate": true/false,
  "gate_reason": "sole_trader|no_gst|unreachable|none",
  "band": "LOW|MEDIUM|HIGH|VERY_HIGH",
  "judgment": "one sentence explaining the affordability assessment",
  "confidence": "HIGH|MEDIUM|LOW"
}"""

_AFFORD_SYSTEM_BLOCK = {
    "type": "text",
    "text": _AFFORD_SYSTEM,
    "cache_control": {"type": "ephemeral"},
}


async def judge_affordability(
    domain: str,
    abn_data: dict,
    website_data: dict,
) -> dict:
    """
    Stage 4 — Haiku. Assess whether SMB can afford agency services.
    Complements ProspectScorer.score_affordability() with LLM judgment.
    """
    fallback = {
        "score": 0, "hard_gate": False, "gate_reason": "none",
        "band": "MEDIUM", "judgment": "", "confidence": "LOW",
    }
    async with GLOBAL_SEM_HAIKU:
        try:
            context = {
                "domain": domain,
                "abn": {
                    "entity_type": abn_data.get("entity_type"),
                    "gst_registered": abn_data.get("gst_registered"),
                    "abn_matched": abn_data.get("abn_matched"),
                    "entity_name": abn_data.get("entity_name"),
                },
                "website": {
                    "cms": website_data.get("technology_signals", {}).get("cms"),
                    "team_size": website_data.get("team_size_indicator"),
                    "content_freshness": website_data.get("content_freshness"),
                    "business_maturity": website_data.get("business_maturity"),
                    "has_professional_email": "email" in (website_data.get("contact_methods") or []),
                },
            }
            user_content = f"SMB profile:\n{json.dumps(context, indent=2)}"
            text, in_tok, out_tok = await _call_anthropic(
                model=_MODEL_HAIKU,
                system_blocks=[_AFFORD_SYSTEM_BLOCK],
                user_content=user_content,
                max_tokens=300,
            )
            logger.info("judge_affordability domain=%s tokens=%d/%d", domain, in_tok, out_tok)
            return _parse_json_response(text, fallback)
        except Exception as exc:
            logger.warning("judge_affordability failed domain=%s: %s", domain, exc)
            return fallback


# ── Stage 5: Evidence refinement (Haiku) ─────────────────────────────────────

_EVIDENCE_SYSTEM = """You are writing prospect card copy for a digital marketing agency's CRM.
Given intent signals and website analysis for an Australian SMB, produce specific, compelling copy.

Rules:
- Be specific: name the actual signal, not generic statements
- Use plain Australian business English
- Each evidence statement = one observable fact + one implied opportunity
- Headline signal = the single most compelling reason to reach out NOW
- Recommended service = the most logical first service to offer (keep to 3-5 words max)
- Outreach angle = the emotional hook for the first message (problem-aware, not solution-first)
- Draft email subject: specific to THIS prospect's top signal, not generic
- Draft email body: 4-6 sentences. Reference ONE specific signal. Match to the service. End with ONE question. Sign off with {{agency_name}}.

The draft email body must feel like a human wrote it after researching this business for 20 minutes.
NOT: "I noticed you could improve your digital marketing."
YES: "I was looking at your Google Ads and noticed you're running 18 campaigns — but there's no conversion tracking installed, so there's no way to know which ones are actually booking patients."

Return ONLY valid JSON:
{
  "evidence_statements": ["list of 2-5 specific evidence strings"],
  "headline_signal": "single most compelling signal (one sentence)",
  "recommended_service": "most logical first service (3-5 words)",
  "outreach_angle": "emotional hook for first outreach message",
  "draft_email_subject": "specific subject line referencing this prospect's top signal",
  "draft_email_body": "4-6 sentence email body. References specific signal. No pitch. Ends with one question. Signed {{agency_name}}."
}"""

_EVIDENCE_SYSTEM_BLOCK = {
    "type": "text",
    "text": _EVIDENCE_SYSTEM,
    "cache_control": {"type": "ephemeral"},
}


async def refine_evidence(
    domain: str,
    intent_data: dict,
    review_data: dict,
    website_data: dict,
) -> dict:
    """
    Stage 5 — Haiku. Produce final prospect card copy from aggregated intelligence.
    Replaces hardcoded evidence strings in ProspectScorer.
    """
    fallback = {
        "evidence_statements": [],
        "headline_signal": "",
        "recommended_service": "",
        "outreach_angle": "",
        "draft_email_subject": "",
        "draft_email_body": "",
    }
    async with GLOBAL_SEM_HAIKU:
        try:
            context = {
                "domain": domain,
                "intent_band": intent_data.get("band", "UNKNOWN"),
                "intent_score": intent_data.get("score", 0),
                "primary_signal": intent_data.get("primary_signal", ""),
                "raw_evidence": intent_data.get("evidence", []),
                "review_summary": {
                    "sentiment_trend": review_data.get("sentiment_trend", "insufficient_data"),
                    "pain_themes": review_data.get("pain_themes", []),
                    "marketing_opportunity": review_data.get("marketing_opportunity", ""),
                    "owner_responsiveness": review_data.get("owner_responsiveness", "absent"),
                },
                "website_summary": {
                    "services": website_data.get("services", []),
                    "pain_indicators": website_data.get("pain_indicators", []),
                    "business_maturity": website_data.get("business_maturity", "unknown"),
                },
            }
            user_content = f"Prospect intelligence:\n{json.dumps(context, indent=2)}"
            text, in_tok, out_tok = await _call_anthropic(
                model=_MODEL_HAIKU,
                system_blocks=[_EVIDENCE_SYSTEM_BLOCK],
                user_content=user_content,
                max_tokens=700,
            )
            logger.info("refine_evidence domain=%s tokens=%d/%d", domain, in_tok, out_tok)
            return _parse_json_response(text, fallback)
        except Exception as exc:
            logger.warning("refine_evidence failed domain=%s: %s", domain, exc)
            return fallback
