"""Stage 10 Critic — Gemini Flash quality scoring for outreach drafts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.intelligence.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

CRITIC_PASS_THRESHOLD = 70
MAX_REVISIONS = 2

_CRITIC_SYSTEM_PROMPT = """You are a quality reviewer for B2B outreach messages targeting Australian SMBs.
Score the draft on 6 scored criteria plus 1 binary gate criterion. Return ONLY valid JSON, no markdown."""

_CRITERIA_RUBRIC = """
Score the message on these 6 criteria (sum = 0-100 total):

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

5. australian_voice (0-10): Natural, casual, peer-to-peer. Not American corporate
   ("I hope this finds you well", "synergy", "leverage"). Not too informal either.

6. hook_relevance (0-5): Does the opening hook connect to a specific signal from
   the prospect brief (a real data point, not a generic observation)? If the hook
   could apply to any business, score 0.

Then evaluate this SEVENTH binary gate (NOT added to the 0-100 total — hard-fail only):

7. social_proof_sourced (0 or 1): Does the message make any claim of past client
   work, past results, track record, customer references, or social proof? If YES,
   does EVERY such claim trace to a non-null field in the Agency Profile block?
   - 0 = message contains at least one unsourced past-work claim → HARD-FAIL
   - 1 = message makes no past-work claims, OR every such claim maps to a present
         agency_profile field

   PARAPHRASE WATCHLIST — any of these phrasings triggers the source check:
   • "we helped", "we've worked with", "we've delivered", "we've built"
   • "our clients", "past clients", "existing customers", "customer base"
   • "past results", "track record", "history of", "results speak for"
   • "similar businesses", "other companies like yours", "businesses in your space"
   • "in our experience", "we typically see", "we've seen"
   • case-study references ("helped X achieve Y%", "grew N by M%")
   • industry-specialisation claims ("we specialise in <vertical>",
     "experience in <industry>", "dental/legal/trades expertise")
   • specific past-work statistics ("40% uplift", "3x ROI", "saved $X")

   HARD-FAIL EXAMPLES (score 0):
   • "We've helped dental practices increase bookings" — when agency_profile
     has no case_study or clients field → UNSOURCED
   • "Our clients in the legal space saw 30% growth" — no clients field → UNSOURCED
   • "Similar businesses to yours achieved X" — comparative claim with no
     supporting agency_profile data → UNSOURCED
   • "We typically see 40% uplift for dental practices" — unsourced stat → UNSOURCED

   PASS EXAMPLES (score 1):
   • Message references only prospect data, no past-work claims at all → pass 1
   • "We help Australian dental practices with local SEO" where
     agency_profile.case_study contains a real dental engagement → pass 1
   • "Our services include SEO and Google Ads" where agency_profile.services
     lists those (offering ≠ past result) → pass 1
   • "We're an Australian agency" where agency_profile.name is present and
     the claim is factual → pass 1

Return ONLY this JSON structure, no markdown:
{
  "score": <total 0-100 from criteria 1-6 only>,
  "criteria": {
    "prospect_data": <0-25>,
    "channel_format": <0-20>,
    "cta_quality": <0-20>,
    "no_hallucination": <0-20>,
    "australian_voice": <0-10>,
    "hook_relevance": <0-5>,
    "social_proof_sourced": <0 or 1>
  },
  "feedback": "<quote the specific problematic line from the draft> — <reason it fails> — <suggested replacement>"
}
"""

_AGENCY_PROFILE_FIELDS = ("name", "services", "tone", "founder_name", "case_study")


def _format_agency_profile_block(agency_profile: dict[str, Any]) -> str:
    """Render agency_profile as a structured 'present / missing' listing so the
    critic can tell which fields are available to source past-work claims from."""
    present_lines = []
    missing_lines = []
    for field in _AGENCY_PROFILE_FIELDS:
        value = agency_profile.get(field)
        if value:
            present_lines.append(f"  {field}: {value!r}")
        else:
            missing_lines.append(
                f"  {field}: MISSING — any claim relying on this field is UNSOURCED"
            )
    # Also surface any extra fields the caller supplied that aren't in our
    # canonical list, so a future schema addition doesn't go invisible.
    for field, value in agency_profile.items():
        if field in _AGENCY_PROFILE_FIELDS:
            continue
        if value:
            present_lines.append(f"  {field}: {value!r}")
    body = "\n".join(present_lines + missing_lines)
    return body or "  (empty — no agency profile fields supplied)"


def _build_critic_prompt(
    channel: str,
    body: str,
    subject: str | None,
    prospect_brief: str,
    agency_profile: dict[str, Any],
) -> str:
    """Build the scoring prompt with the 6 scored + 1 gate criteria rubric."""
    lines = [
        f"Channel: {channel}",
    ]
    if subject:
        lines.append(f"Subject: {subject}")
    lines += [
        f"Message body:\n{body}",
        "",
        "Prospect brief (source of truth for prospect-specific facts):",
        prospect_brief,
        "",
        "Agency profile (source of truth for ALL past-work / social-proof / "
        "track-record claims — fields marked MISSING below cannot be referenced):",
        _format_agency_profile_block(agency_profile),
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
    agency_profile: dict[str, Any],
) -> dict[str, Any]:
    """Score a draft message against prospect brief + agency profile.

    agency_profile is REQUIRED so the critic can gate social-proof claims —
    past-work / track-record references must trace to a non-null agency_profile
    field. Unsourced claims HARD-FAIL via criterion 7 (social_proof_sourced).

    Returns:
        {
            "score": int,
            "feedback": str,
            "criteria": dict,
            "pass": bool,
        }
    On timeout or error returns needs_review=True with critic_feedback="critic_timeout".
    """
    if agency_profile is None:
        raise ValueError(
            "critique_draft requires agency_profile (dict). Pass the customer's "
            "profile from onboarding/CRM. For tests use TEST_AGENCY_PROFILE fixture."
        )
    user_prompt = _build_critic_prompt(channel, body, subject, prospect_brief, agency_profile)

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
    except TimeoutError:
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

    # HARD-FAIL (prospect hallucination): fabricated prospect-specific claims
    if criteria.get("no_hallucination", 1) == 0:
        feedback = f"HARD-FAIL: hallucinated prospect claims detected — {feedback}"
        score = 0

    # HARD-FAIL (unsourced social proof): past-work / track-record claims that
    # don't trace to a non-null agency_profile field. Added 2026-04-21 via
    # AGENCY-PROFILE-TRUTH-AUDIT T4 — a pre-revenue agency with zero clients
    # cannot ship outreach claiming past-work unless Dave has populated the
    # relevant field. Criterion defaults to 1 (pass) when absent from the
    # critic response, so legacy responses remain backward compatible.
    if criteria.get("social_proof_sourced", 1) == 0:
        feedback = f"HARD-FAIL: unsourced social proof (claim not in agency_profile) — {feedback}"
        score = 0

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
    agency_profile: dict[str, Any],
) -> dict[str, Any]:
    """Run the critic loop: score → revise if needed (max 2 retries) → return best draft.

    agency_profile is threaded through to the critic so past-work / social-proof
    claims can be gated against populated agency fields (criterion 7 HARD-FAIL).

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
    if agency_profile is None:
        raise ValueError(
            "critique_and_revise requires agency_profile (dict). Production flow "
            "must supply the customer's profile; missing = hard-fail at entry."
        )
    body = initial_body
    subject = initial_subject
    best: dict[str, Any] = {}

    for attempt in range(MAX_REVISIONS + 1):
        result = await critique_draft(
            gemini, channel, body, subject, prospect_brief, agency_profile
        )

        # On critic failure (timeout/parse error) ship immediately — any attempt
        if result.get("needs_review") and result["feedback"] in (
            "critic_timeout",
            "critic_parse_error",
        ):
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
                "revision_count": attempt,
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

    # Should not reach here
    best["needs_review"] = True
    return best
