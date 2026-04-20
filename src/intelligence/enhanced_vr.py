"""Stage 10 — VR+MSG: Vulnerability Report + Outreach Messaging.

Two Gemini calls:
  1. VR Report: structured vulnerability analysis with strengths, gaps, GMB health,
     recommended services, urgency.
  2. Outreach Messaging: email (timeline hook first), LinkedIn note, phone knowledge
     base, SMS — all personalised to DM posts and signals.

Write outreach on behalf of "Agency OS". Use "Agency OS" as the agency name and "the Agency OS team" as the contact name. Do NOT use placeholder tokens like {{agency_name}} or {{agency_contact_name}} — write the actual name inline.
Do NOT invent numbers — only cite data from signals.
Facebook deferred to post-launch.

Pipeline F v2.1. Ratified: 2026-04-15.
"""
from __future__ import annotations

import json
import logging
import os

from src.intelligence.gemini_retry import gemini_call_with_retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_VR_SYSTEM_PROMPT = """You are a senior digital strategist producing a structured vulnerability
report for an Australian SMB prospect.

You will receive signals from pipeline stages 2-8. Your task: produce a concise,
evidence-based vulnerability report that a sales rep can read in 90 seconds.

Return ONLY valid JSON with this exact structure:
{
  "summary": "2-3 sentences — bottom-line assessment of where they sit digitally",
  "strengths": ["bullet 1", "bullet 2"],
  "vulnerabilities": [
    {
      "area": "e.g. Organic Search",
      "finding": "specific finding with numbers from signals",
      "impact": "business impact (lost leads, revenue leak, etc.)",
      "recommendation": "one concrete action we can take"
    }
  ],
  "gmb_health": {
    "rating": null,
    "review_count": null,
    "assessment": "healthy|needs_work|critical|unknown"
  },
  "recommended_services": ["service1", "service2"],
  "urgency": "high|medium|low",
  "urgency_reason": "one sentence"
}

Rules:
- Only cite numbers that appear in the signal data. Do NOT invent metrics.
- Maximum 3 vulnerabilities. Quality over quantity.
- recommended_services must map to real digital marketing services."""

_MSG_SYSTEM_PROMPT = """You are writing outreach copy for a high-propensity Australian SMB prospect.

You have the vulnerability report, DM posts, and contact details.
Your task: write four outreach assets that feel human, specific, and low-pressure.

BANNED WORDS/PHRASES (instant fail if used):
"I hope this finds you well", "reaching out", "touch base", "low-hanging fruit",
"leverage", "synergy", "unlock potential", "game-changer", "circle back",
"just wanted to", "quick question", "hope you're well"

FORMAT RULES:
- Email: 50-100 words. Lead with a TIMELINE HOOK (something the DM did/said/posted recently).
  Then credibility + insight (acknowledge a strength, then name a specific gap with numbers).
  Close with a low-pressure personal question. Sign off as "the Agency OS team" from "Agency OS".
- LinkedIn note: <300 chars. Reference something from their posts or company news. Sign off as "the Agency OS team".
- Phone knowledge base: NOT a script to read verbatim. Provide:
    pattern_interrupt (first 5 seconds — something specific to THEM),
    key_insight (the one number or finding that will make them lean in),
    permission_question (soft ask to continue),
    objection_handle (for "not interested" or "happy with current provider").
- SMS: <160 chars. Specific to the vulnerability. Include "the Agency OS team" as the sender name.

TONE:
- Match the DM's apparent tone from their posts (formal vs casual, technical vs plain).
- If no posts available, default to warm-professional Australian tone.
- Never over-promise. Cite only data from the signals.

Return ONLY valid JSON:
{
  "email": {
    "subject": "under 60 chars, specific not generic",
    "body": "50-100 words, timeline hook first, credibility + gap with numbers, low-pressure close"
  },
  "linkedin_note": "under 300 chars",
  "phone_kb": {
    "pattern_interrupt": "first 5 seconds",
    "key_insight": "the one number or finding",
    "permission_question": "soft ask",
    "objection_handle": "for not interested / happy with current"
  },
  "sms": "under 160 chars",
  "dm_post_reference": "the specific post or activity referenced, or null"
}"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_stage10_vr_and_messaging(
    stage3_identity: dict,
    stage4_signals: dict,
    stage5_scores: dict,
    stage7_analyse: dict,
    stage8_contacts: dict,
    stage9_social: dict,
    stage6_enrich: dict | None = None,
    api_key: str | None = None,
    max_retries: int = 4,
) -> dict:
    """Stage 10 VR+MSG: vulnerability report + outreach messaging.

    Makes two Gemini calls — VR report then outreach. Both use gemini_call_with_retry
    with enable_grounding=False.

    Args:
        stage3_identity: Stage 3 IDENTIFY parsed output.
        stage4_signals: Stage 4 signal bundle dict.
        stage5_scores: Stage 5 scoring output dict.
        stage7_analyse: Stage 7 ANALYSE parsed output (intent, affordability, etc.).
        stage8_contacts: Stage 8 contact waterfall results.
        stage9_social: Stage 9 SOCIAL output (dm_posts, company_posts).
        stage6_enrich: Stage 6 ENRICH output (optional, historical_rank).
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var).
        max_retries: Retry count per Gemini call.

    Returns:
        {
            "vr_report": dict | None,
            "outreach": dict | None,
            "cost_usd": float,
            "f_status": str,   # "success" | "partial" | "failed"
        }
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        logger.error("run_stage10_vr_and_messaging: GEMINI_API_KEY not set")
        return {"vr_report": None, "outreach": None, "cost_usd": 0.0, "f_status": "failed"}

    # Build shared signal context
    signal_ctx = json.dumps(
        {
            "identity": stage3_identity,
            "signals": stage4_signals,
            "scores": stage5_scores,
            "analyse": stage7_analyse,
            "contacts": stage8_contacts,
            "enrich": stage6_enrich,
        },
        indent=2,
    )

    # --- Call 1: VR Report ---
    vr_user_prompt = (
        f"Signal data:\n{signal_ctx}\n\n"
        "Produce the vulnerability report as specified."
    )
    vr_result = await gemini_call_with_retry(
        api_key=key,
        system_prompt=_VR_SYSTEM_PROMPT,
        user_prompt=vr_user_prompt,
        enable_grounding=False,
        max_retries=max_retries,
    )
    total_cost = vr_result.get("cost_usd", 0.0)
    vr_report = vr_result.get("content")

    # --- Call 2: Outreach Messaging ---
    dm_posts = stage9_social.get("dm_posts") or []
    company_posts = stage9_social.get("company_posts") or []
    msg_user_prompt = (
        f"Vulnerability report:\n{json.dumps(vr_report, indent=2)}\n\n"
        f"DM posts ({len(dm_posts)} posts):\n{json.dumps(dm_posts, indent=2)}\n\n"
        f"Company posts ({len(company_posts)} posts):\n{json.dumps(company_posts, indent=2)}\n\n"
        f"Contact details:\n{json.dumps(stage8_contacts, indent=2)}\n\n"
        f"DM identity:\n{json.dumps(stage3_identity.get('dm_candidate'), indent=2)}\n\n"
        "Write the outreach assets as specified."
    )
    msg_result = await gemini_call_with_retry(
        api_key=key,
        system_prompt=_MSG_SYSTEM_PROMPT,
        user_prompt=msg_user_prompt,
        enable_grounding=False,
        max_retries=max_retries,
    )
    total_cost += msg_result.get("cost_usd", 0.0)
    outreach = msg_result.get("content")

    # Determine composite status
    if vr_report and outreach:
        f_status = "success"
    elif vr_report or outreach:
        f_status = "partial"
    else:
        f_status = "failed"

    return {
        "vr_report": vr_report,
        "outreach": outreach,
        "cost_usd": round(total_cost, 6),
        "f_status": f_status,
    }
