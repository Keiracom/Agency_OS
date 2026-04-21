"""Stage 10 Critic — Gemini Flash quality scoring for outreach drafts."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from src.intelligence.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

CRITIC_PASS_THRESHOLD = 70
MAX_REVISIONS = 2

_CRITIC_SYSTEM_PROMPT = """You are a quality reviewer for B2B outreach messages targeting Australian SMBs.
Score the draft on 5 criteria. Return ONLY valid JSON, no markdown."""

_CRITERIA_RUBRIC = """
Score the message on these 5 criteria:

1. prospect_data (0-25): Does the message reference specific data about THIS prospect
   (tech stack, GMB rating, paid keywords, VR findings)? Generic messages score 0.

2. channel_format (0-20): Channel-appropriate format:
   - email: 3 lines + subject line
   - linkedin: under 300 chars, conversational
   - sms: under 160 chars, clear value
   - voice: natural cadence with question hooks

3. cta_quality (0-20): Soft ask ("open to a chat?") scores high.
   Hard sell ("buy now", "book a demo") scores 0. No CTA at all scores 5.

4. no_hallucination (0-20): Message only cites data from the prospect brief.
   Any fabricated statistics, made-up service offerings, or invented competitor
   references = 0 on this criterion.

5. australian_voice (0-15): Natural, casual, peer-to-peer. Not American corporate
   ("I hope this finds you well", "synergy", "leverage"). Not too informal either.

Return ONLY this JSON structure, no markdown:
{
  "score": <total 0-100>,
  "criteria": {
    "prospect_data": <0-25>,
    "channel_format": <0-20>,
    "cta_quality": <0-20>,
    "no_hallucination": <0-20>,
    "australian_voice": <0-15>
  },
  "feedback": "<one sentence: the most important thing to fix>"
}
"""


def _build_critic_prompt(
    channel: str,
    body: str,
    subject: str | None,
    prospect_brief: str,
) -> str:
    """Build the scoring prompt with the 5 criteria rubric."""
    lines = [
        f"Channel: {channel}",
    ]
    if subject:
        lines.append(f"Subject: {subject}")
    lines += [
        f"Message body:\n{body}",
        "",
        "Prospect brief (source of truth — only facts in here are valid to cite):",
        prospect_brief,
        "",
        _CRITERIA_RUBRIC,
    ]
    return "\n".join(lines)


async def critique_draft(
    gemini: GeminiClient,
    channel: str,
    body: str,
    subject: str | None,
    prospect_brief: str,
) -> dict[str, Any]:
    """Score a draft message.

    Returns:
        {
            "score": int,
            "feedback": str,
            "criteria": dict,
            "pass": bool,
        }
    On timeout or error returns needs_review=True with critic_feedback="critic_timeout".
    """
    user_prompt = _build_critic_prompt(channel, body, subject, prospect_brief)

    try:
        result = await asyncio.wait_for(
            gemini.comprehend(
                system_prompt=_CRITIC_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                enable_grounding=False,
                enable_url_context=False,
            ),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Critic timed out after 15s — shipping unreviewed")
        return {
            "score": 0,
            "feedback": "critic_timeout",
            "criteria": {},
            "pass": False,
            "needs_review": True,
        }
    except Exception as exc:
        logger.warning("Critic error: %s — shipping unreviewed", exc)
        return {
            "score": 0,
            "feedback": "critic_timeout",
            "criteria": {},
            "pass": False,
            "needs_review": True,
        }

    content = result.get("content")

    # content may come back as a dict (already parsed) or a string
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Critic returned unparseable JSON: %s", content[:200])
            return {
                "score": 0,
                "feedback": "critic_parse_error",
                "criteria": {},
                "pass": False,
                "needs_review": True,
            }

    if not isinstance(content, dict):
        logger.warning("Critic returned unexpected type: %s", type(content))
        return {
            "score": 0,
            "feedback": "critic_parse_error",
            "criteria": {},
            "pass": False,
            "needs_review": True,
        }

    score = int(content.get("score", 0))
    feedback = content.get("feedback", "")
    criteria = content.get("criteria", {})

    return {
        "score": score,
        "feedback": feedback,
        "criteria": criteria,
        "pass": score >= CRITIC_PASS_THRESHOLD,
        "needs_review": False,
    }


async def critique_and_revise(
    gemini: GeminiClient,
    writer_fn,  # async callable(feedback: str) -> {"body": str, "subject": str | None}
    channel: str,
    prospect_brief: str,
    initial_body: str,
    initial_subject: str | None,
) -> dict[str, Any]:
    """Run the critic loop: score → revise if needed (max 2 retries) → return best draft.

    Returns:
        {
            "body": str,
            "subject": str | None,
            "critic_score": int,
            "critic_feedback": str,
            "needs_review": bool,
            "revision_count": int,
        }
    """
    body = initial_body
    subject = initial_subject
    best: dict[str, Any] = {}
    revision_count = 0

    for attempt in range(MAX_REVISIONS + 1):
        result = await critique_draft(gemini, channel, body, subject, prospect_brief)

        # On critic failure (timeout/parse error) ship immediately
        if result.get("needs_review") and result["score"] == 0 and attempt == 0:
            return {
                "body": body,
                "subject": subject,
                "critic_score": 0,
                "critic_feedback": result["feedback"],
                "needs_review": True,
                "revision_count": 0,
            }

        # Track best scored draft
        if not best or result["score"] > best.get("critic_score", -1):
            best = {
                "body": body,
                "subject": subject,
                "critic_score": result["score"],
                "critic_feedback": result["feedback"],
                "needs_review": result.get("needs_review", False),
                "revision_count": revision_count,
            }

        if result["pass"]:
            best["needs_review"] = False
            return best

        # Last attempt exhausted — ship best seen
        if attempt == MAX_REVISIONS:
            best["needs_review"] = True
            return best

        # Revise and try again
        logger.info(
            "Critic score %d < %d on attempt %d — requesting revision: %s",
            result["score"],
            CRITIC_PASS_THRESHOLD,
            attempt + 1,
            result["feedback"],
        )
        try:
            revised = await writer_fn(result["feedback"])
        except Exception as exc:
            logger.warning("writer_fn failed on revision %d: %s", attempt + 1, exc)
            best["needs_review"] = True
            return best

        body = revised.get("body", body)
        subject = revised.get("subject", subject)
        revision_count += 1

    # Should not reach here
    best["needs_review"] = True
    return best
