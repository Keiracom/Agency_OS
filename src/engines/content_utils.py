"""
Contract: src/engines/content_utils.py
Purpose: Shared utilities for content extraction across channel engines
Layer: 3 - engines
Imports: models
Consumers: channel engines (email, sms, voice, linkedin)

FILE: src/engines/content_utils.py
PURPOSE: Shared utilities for content extraction across channel engines
PHASE: 16 (Conversion Intelligence)
TASK: 16E-001
DEPENDENCIES:
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from other engines
"""

import re
from datetime import datetime
from typing import Any

from src.models.lead import Lead

# =============================================================================
# VOCABULARIES (must match WHAT Detector keywords)
# =============================================================================

PAIN_POINT_KEYWORDS: dict[str, list[str]] = {
    "leads": [
        "leads", "pipeline", "prospects", "opportunities",
        "qualified", "mql", "sql", "inbound", "lead gen",
    ],
    "revenue": [
        "revenue", "sales", "growth", "roi", "profit",
        "income", "deals", "closed", "won", "booking",
    ],
    "time": [
        "time", "hours", "manual", "automate", "efficiency",
        "busy", "bandwidth", "overwhelmed", "tedious", "repetitive",
    ],
    "scaling": [
        "scale", "scaling", "growth", "capacity", "bandwidth",
        "hire", "team", "expand", "growing", "bottleneck",
    ],
    "competition": [
        "competitors", "competition", "market share", "behind",
        "catching up", "losing", "threat", "outpace",
    ],
    "cost": [
        "cost", "expensive", "budget", "waste", "spending",
        "save", "afford", "price", "investment", "roi",
    ],
    "quality": [
        "quality", "results", "performance", "outcomes",
        "better", "improve", "consistent", "reliable",
    ],
    "clients": [
        "clients", "customers", "retention", "churn",
        "satisfaction", "referrals", "testimonials", "reviews",
    ],
}

CTA_PATTERNS: list[str] = [
    "open to a quick chat",
    "worth 15 minutes",
    "worth a conversation",
    "free audit",
    "free analysis",
    "quick call",
    "schedule a call",
    "book a time",
    "interested in learning",
    "happy to share",
    "let me know",
    "thoughts?",
    "make sense to connect",
    "grab 15 minutes",
    "coffee chat",
    "worth exploring",
    "quick question",
]


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def extract_pain_points(text: str) -> list[str]:
    """
    Extract pain points mentioned in text.

    Returns list of pain point categories found (e.g., ["leads", "time"]).
    Each category is only counted once even if multiple keywords match.

    Args:
        text: Message content to analyze

    Returns:
        List of unique pain point categories found
    """
    if not text:
        return []

    text_lower = text.lower()
    found: list[str] = []

    for pain_point, keywords in PAIN_POINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found.append(pain_point)
                break  # Only count each pain point category once

    return found


def extract_cta(text: str) -> str | None:
    """
    Extract call-to-action phrase from text.

    Searches for common CTA patterns in the message.
    Returns the first matching CTA phrase, or None if not found.

    Args:
        text: Message content to analyze

    Returns:
        CTA phrase if found, None otherwise
    """
    if not text:
        return None

    text_lower = text.lower()

    for cta in CTA_PATTERNS:
        if cta in text_lower:
            return cta

    return None


def detect_personalization(text: str, lead: Lead) -> dict[str, bool]:
    """
    Detect personalization elements in message.

    Checks for:
    - Company name mention
    - First name mention
    - Recent news/event reference
    - Mutual connection reference
    - Industry-specific language

    Args:
        text: Message content to analyze
        lead: Lead object with personal/company info

    Returns:
        Dict of boolean flags for each personalization type
    """
    if not text:
        return {
            "has_company_mention": False,
            "has_first_name": False,
            "has_recent_news": False,
            "has_mutual_connection": False,
            "has_industry_specific": False,
        }

    text_lower = text.lower()

    # Company mention check
    has_company = False
    company_name = getattr(lead, "company", None) or getattr(lead, "company_name", None)
    if company_name:
        has_company = company_name.lower() in text_lower

    # First name check
    has_first_name = False
    first_name = getattr(lead, "first_name", None)
    if first_name:
        has_first_name = first_name.lower() in text_lower

    # Recent news patterns
    has_recent_news = bool(
        re.search(
            r"(noticed|saw|congrats|congratulations|just saw|read about|heard about)",
            text_lower,
        )
    )

    # Mutual connection patterns
    has_mutual_connection = any(
        phrase in text_lower
        for phrase in ["mutual", "connection", "referred", "introduced", "recommended"]
    )

    # Industry-specific check
    has_industry = False
    industry = getattr(lead, "organization_industry", None) or getattr(lead, "industry", None)
    if industry:
        has_industry = industry.lower() in text_lower

    return {
        "has_company_mention": has_company,
        "has_first_name": has_first_name,
        "has_recent_news": has_recent_news,
        "has_mutual_connection": has_mutual_connection,
        "has_industry_specific": has_industry,
    }


def build_content_snapshot(
    body: str,
    lead: Lead,
    subject: str | None = None,
    touch_number: int = 1,
    sequence_id: str | None = None,
    channel: str = "email",
    template_id: str | None = None,
) -> dict[str, Any]:
    """
    Build a complete content snapshot for activity recording.

    This is the standard format stored in activity.content_snapshot,
    used by WHAT/WHEN Detectors for pattern learning.

    Args:
        body: Message body content
        lead: Target lead (for personalization detection)
        subject: Email subject line (optional, for email channel)
        touch_number: Position in sequence (1-indexed)
        sequence_id: Parent sequence UUID
        channel: Channel type (email, sms, linkedin, voice)
        template_id: Optional template ID used

    Returns:
        Dict containing all content features for learning
    """
    now = datetime.utcnow()

    # Extract features
    pain_points = extract_pain_points(body)
    cta = extract_cta(body)
    personalization = detect_personalization(body, lead)

    snapshot: dict[str, Any] = {
        # Core content
        "body": body,
        "channel": channel,
        "template_id": template_id,

        # Metrics
        "word_count": len(body.split()) if body else 0,
        "char_count": len(body) if body else 0,

        # Extracted features
        "pain_points_used": pain_points,
        "cta_used": cta,

        # Personalization flags
        **personalization,

        # Sequence context
        "touch_number": touch_number,
        "sequence_id": sequence_id,

        # Timing (for WHEN Detector)
        "sent_at": now.isoformat(),
        "day_of_week": now.weekday(),  # 0=Monday, 6=Sunday
        "hour_of_day": now.hour,  # 0-23
    }

    # Add subject for email channel
    if subject is not None:
        snapshot["subject"] = subject
        snapshot["subject_word_count"] = len(subject.split())

    return snapshot


def build_sms_snapshot(
    message: str,
    lead: Lead,
    touch_number: int = 1,
    sequence_id: str | None = None,
) -> dict[str, Any]:
    """
    Build content snapshot for SMS messages.

    SMS-specific metrics include segment count (160 chars per segment).

    Args:
        message: SMS message content
        lead: Target lead
        touch_number: Position in sequence
        sequence_id: Parent sequence UUID

    Returns:
        Content snapshot dict
    """
    snapshot = build_content_snapshot(
        body=message,
        lead=lead,
        touch_number=touch_number,
        sequence_id=sequence_id,
        channel="sms",
    )

    # Add SMS-specific metrics
    snapshot["segment_count"] = (len(message) // 160) + 1 if message else 0

    return snapshot


def build_linkedin_snapshot(
    message: str,
    lead: Lead,
    message_type: str = "message",
    connection_note: str | None = None,
    touch_number: int = 1,
    sequence_id: str | None = None,
) -> dict[str, Any]:
    """
    Build content snapshot for LinkedIn messages.

    LinkedIn-specific fields include message_type (connection_request, inmail, message).

    Args:
        message: LinkedIn message content
        lead: Target lead
        message_type: Type of LinkedIn message
        connection_note: Optional connection request note
        touch_number: Position in sequence
        sequence_id: Parent sequence UUID

    Returns:
        Content snapshot dict
    """
    # For connection requests, analyze the note; otherwise the message
    content_to_analyze = connection_note if message_type == "connection_request" else message

    snapshot = build_content_snapshot(
        body=content_to_analyze or "",
        lead=lead,
        touch_number=touch_number,
        sequence_id=sequence_id,
        channel="linkedin",
    )

    # Add LinkedIn-specific fields
    snapshot["message_type"] = message_type
    snapshot["connection_note"] = connection_note
    snapshot["message_body"] = message

    return snapshot


def build_voice_snapshot(
    lead: Lead,
    script_id: str | None = None,
    script_content: str | None = None,
    outcome: str = "connected",
    duration_seconds: int = 0,
    notes: str | None = None,
    touch_number: int = 1,
    sequence_id: str | None = None,
) -> dict[str, Any]:
    """
    Build content snapshot for voice calls.

    Voice-specific fields include outcome, duration, and agent notes.

    Args:
        lead: Target lead
        script_id: ID of script used
        script_content: Script text content
        outcome: Call outcome (connected, voicemail, no_answer, etc.)
        duration_seconds: Call duration
        notes: Agent notes from call
        touch_number: Position in sequence
        sequence_id: Parent sequence UUID

    Returns:
        Content snapshot dict
    """
    snapshot = build_content_snapshot(
        body=script_content or "",
        lead=lead,
        touch_number=touch_number,
        sequence_id=sequence_id,
        channel="voice",
    )

    # Add voice-specific fields
    snapshot["script_id"] = script_id
    snapshot["script_content"] = script_content
    snapshot["outcome"] = outcome
    snapshot["duration_seconds"] = duration_seconds
    snapshot["duration_minutes"] = round(duration_seconds / 60, 1) if duration_seconds else 0
    snapshot["notes"] = notes

    return snapshot


# =============================================================================
# VERIFICATION CHECKLIST
# =============================================================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] PAIN_POINT_KEYWORDS matches WHAT Detector vocabulary
# [x] CTA_PATTERNS for common CTAs
# [x] extract_pain_points returns unique categories
# [x] extract_cta returns first match
# [x] detect_personalization checks all elements
# [x] build_content_snapshot for general use
# [x] build_sms_snapshot with segment_count
# [x] build_linkedin_snapshot with message_type
# [x] build_voice_snapshot with outcome/duration
# [x] No imports from other engines (Rule 12)
# [x] All functions have type hints
# [x] All functions have docstrings
