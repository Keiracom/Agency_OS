"""Stage 10 — VR+MSG (ENHANCED_VR): Enhanced Vulnerability Report.

Second Gemini call for prospects that pass the candidacy gate.
Regenerates vulnerability report and outreach messages with DM post context.

Uses gemini_retry helper (not inline retry).
Sender fields use {{agency_contact_name}} and {{agency_name}} placeholders.

Ratified: 2026-04-14. Pipeline F architecture refactor.
"""
from __future__ import annotations

import json
import logging
import os

from src.intelligence.gemini_retry import gemini_call_with_retry

logger = logging.getLogger(__name__)

ENHANCED_VR_SYSTEM_PROMPT = """You are generating an enhanced vulnerability report and outreach
for a high-propensity Australian SMB prospect. You have:
1. The Stage 7 ANALYSE output (vulnerability report + initial outreach drafts)
2. Recent LinkedIn posts by the decision-maker
3. Contact details (email, mobile if found)

Your task: regenerate the outreach to reference the DM's actual LinkedIn activity.
Make the email feel like it was written by a human who read their posts.

CRITICAL:
- Use {{agency_contact_name}} and {{agency_name}} as sender placeholders.
- Do NOT hardcode any agency or sender names.
- Do NOT modify the vulnerability analysis — only improve the outreach copy.

Return ONLY valid JSON:
{
  "enhanced_email": {
    "subject": "under 60 chars",
    "body": "3-5 sentences, references DM's LinkedIn post or activity, signs off as {{agency_contact_name}} from {{agency_name}}"
  },
  "enhanced_linkedin_note": "under 300 chars, references something they posted, signs off as {{agency_contact_name}}",
  "enhanced_voice_script": "2-3 sentences mentioning {{agency_name}}, references specific vulnerability",
  "dm_post_reference": "the specific post or activity referenced in outreach, or null if no posts available"
}"""


async def run_enhanced_vr(
    f3b_output: dict,
    dm_posts: list[dict],
    contact_details: dict,
    api_key: str | None = None,
    max_retries: int = 4,
) -> dict:
    """Stage 10 VR+MSG: enhanced VR + outreach using DM post context.

    Args:
        f3b_output: Parsed Stage 7 ANALYSE JSON dict.
            NOTE: param name retained for caller compatibility.
        dm_posts: Filtered list of DM LinkedIn posts (may be empty).
        contact_details: Contact waterfall result (email, mobile).
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var).
        max_retries: Retry count for gemini_call_with_retry.

    Returns:
        gemini_retry result dict with content = enhanced VR JSON or None on failure.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        logger.error("run_enhanced_vr: GEMINI_API_KEY not set")
        return {
            "content": None,
            "f_status": "failed",
            "f_failure_reason": "no_api_key",
            "cost_usd": 0.0,
        }

    user_prompt = (
        f"Stage 7 ANALYSE output:\n{json.dumps(f3b_output, indent=2)}\n\n"
        f"DM recent posts ({len(dm_posts)} posts):\n"
        f"{json.dumps(dm_posts, indent=2)}\n\n"
        f"Contact details:\n{json.dumps(contact_details, indent=2)}\n\n"
        "Generate the enhanced outreach as specified."
    )

    result = await gemini_call_with_retry(
        api_key=key,
        system_prompt=ENHANCED_VR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        enable_grounding=False,
        max_retries=max_retries,
    )
    return result
