"""F6 — Enhanced Vulnerability Report with DM LinkedIn post context.

Second Gemini call for qualified prospects where DM LinkedIn posts are available.
Personalises the VR and outreach messages using post content.

Ratified: 2026-04-14. Pipeline F architecture.
"""
from __future__ import annotations

import logging

from src.intelligence.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

ENHANCED_VR_PROMPT = """You are regenerating the vulnerability report and outreach messages for a prospect.
You now have the decision maker's recent LinkedIn posts as additional context.
Use these posts to personalise the messages — reference something they recently wrote or shared.

Return JSON with:
{
  "enhanced_vulnerability_report": {
    "top_vulnerabilities": ["..."],
    "what_agency_could_fix": "..."
  },
  "enhanced_messages": {
    "email_subject": "...",
    "email_body": "...",
    "linkedin_connection_note": "...",
    "sms_if_mobile_found": "..." or null,
    "voice_ai_opening_script": "..."
  },
  "personalisation_used": "what specific post/insight was referenced"
}

Rules:
- email_body must be under 150 words
- linkedin_connection_note must be under 300 characters
- sms_if_mobile_found must be under 160 characters or null if no mobile context
- voice_ai_opening_script: 2-3 sentences maximum
- Always reference an actual post detail — never invent generic flattery"""


class EnhancedVR:
    """F6 stage: enhanced vulnerability report using DM LinkedIn post context."""

    def __init__(self, gemini_client: GeminiClient) -> None:
        self.gemini = gemini_client

    async def regenerate(
        self,
        f3_payload: dict,
        dm_posts: list[str],
    ) -> dict | None:
        """
        Regenerate VR + outreach messages with DM LinkedIn post context.

        Only called when dm_posts is non-empty (gated by caller).

        Args:
            f3_payload: original F3 Gemini output dict
            dm_posts: list of raw post text strings (most recent first)

        Returns:
            Enhanced payload dict with enhanced_vulnerability_report,
            enhanced_messages, and personalisation_used — or None on failure.
        """
        if not dm_posts:
            return None

        identity = f3_payload.get("s2_identity", {}) or {}
        vr = f3_payload.get("s5_5_vulnerability_report", {}) or {}
        buyer = f3_payload.get("s6_5_buyer_reasoning", {}) or {}
        dm = (f3_payload.get("s6_dm_identification", {}) or {}).get("primary_dm", {}) or {}

        # Cap posts: max 10, max 500 chars each
        posts_text = "\n".join(
            f"Post {i + 1}: {p[:500]}" for i, p in enumerate(dm_posts[:10])
        )

        business_name = identity.get("canonical_business_name", "Unknown")
        location = identity.get("primary_location", "")
        dm_name = dm.get("name", "")
        vulnerabilities = vr.get("top_vulnerabilities", [])
        best_angle = buyer.get("best_angle_for_marketing_agency", "")

        user_prompt = (
            f"Business: {business_name}"
            + (f" ({location})" if location else "")
            + f"\nDecision Maker: {dm_name}" if dm_name else ""
            + f"\nCurrent top vulnerabilities: {vulnerabilities}"
            + f"\nBest agency angle: {best_angle}"
            + f"\n\nDM's recent LinkedIn posts:\n{posts_text}"
            + "\n\nRegenerate the vulnerability report and outreach messages "
              "using the post context for personalisation."
        )

        result = await self.gemini.comprehend(
            system_prompt=ENHANCED_VR_PROMPT,
            user_prompt=user_prompt,
            enable_grounding=False,
            enable_url_context=False,
        )

        if result.get("f3_status") != "success":
            logger.warning(
                "F6 enhanced VR failed for %s: %s",
                business_name,
                result.get("f3_failure_reason"),
            )
            return None

        content = result.get("content")
        if not isinstance(content, dict):
            logger.warning("F6 enhanced VR returned non-dict content for %s", business_name)
            return None

        # Validate required keys present
        if not content.get("enhanced_vulnerability_report") or not content.get("enhanced_messages"):
            logger.warning(
                "F6 enhanced VR missing required keys for %s: got %s",
                business_name,
                list(content.keys()),
            )
            return None

        logger.info(
            "F6 enhanced VR OK for %s — personalisation: %s",
            business_name,
            content.get("personalisation_used", "")[:80],
        )
        return content
