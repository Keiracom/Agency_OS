"""reply_router.py — Classify inbound email replies and determine next action.

Pure Python, no LLM calls, no external dependencies.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Keyword maps
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "unsubscribe": [
        "unsubscribe",
        "opt out",
        "opt-out",
        "remove from list",
    ],
    "bounce": [
        "delivery failed",
        "undeliverable",
        "mailbox full",
        "user unknown",
        "550",
        "553",
    ],
    "not_interested": [
        "not interested",
        "no thanks",
        "don't contact",
        "do not contact",
        "remove me",
        "stop emailing",
        "not for us",
    ],
    "ooo": [
        "out of office",
        "away from",
        "limited access",
        "return on",
        "back on",
    ],
    "booking": [
        "book",
        "schedule",
        "calendar",
        "meet",
        "call me",
        "available",
        "tuesday",
        "wednesday",
        "monday",
        "thursday",
        "friday",
    ],
    "positive": [
        "interested",
        "tell me more",
        "sounds good",
        "let's chat",
        "lets chat",
        "happy to",
        "can you send",
        "love to",
    ],
}

_INTENT_ACTIONS: dict[str, str] = {
    "positive": "pause_cadence",
    "booking": "book_meeting",
    "not_interested": "remove_from_cadence",
    "ooo": "mark_ooo",
    "unsubscribe": "suppress",
    "bounce": "suppress",
    "unclear": "escalate_human",
}

# Order matters: higher-priority intents checked first so that e.g. an
# unsubscribe in a bounce body is classified as unsubscribe (legal priority).
_PRIORITY_ORDER = [
    "unsubscribe",
    "bounce",
    "not_interested",
    "ooo",
    "booking",
    "positive",
]

# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    # "Tuesday 2pm", "Wednesday at 10am", "Monday 9:30"
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"[\s,at]*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
    # ISO / numeric date "2026-05-01", "01/05/2026", "May 1", "1 May 2026"
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
    r"\b(\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s+\d{2,4})\b",
    r"\b((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:\s*,\s*\d{4})?)\b",
]

_OOO_RETURN_PATTERNS = [
    r"(?:return(?:ing)?|back)\s+(?:on|by)?\s*(\d{4}-\d{2}-\d{2})",
    r"(?:return(?:ing)?|back)\s+(?:on|by)?\s*"
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    r"(?:return(?:ing)?|back)\s+(?:on|by)?\s*"
    r"(\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s+\d{2,4})",
    r"(?:return(?:ing)?|back)\s+(?:on|by)?\s*"
    r"((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?)",
    # "return on" with explicit "return on" phrase
    r"return\s+on\s+(\d{4}-\d{2}-\d{2})",
    r"return\s+on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
]


def _extract_dates(text: str) -> list[str]:
    """Return all date/time strings found in text (case-insensitive)."""
    found: list[str] = []
    lower = text.lower()
    for pattern in _DATE_PATTERNS:
        for m in re.finditer(pattern, lower, re.IGNORECASE):
            snippet = m.group(0).strip()
            if snippet and snippet not in found:
                found.append(snippet)
    return found


def _extract_ooo_return(text: str) -> str | None:
    """Return the first OOO return-date string found, or None."""
    for pattern in _OOO_RETURN_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------


def classify_reply(
    subject: str,
    body: str,
    sender_email: str,
    original_sequence_step: int = 1,
) -> dict[str, Any]:
    """Classify an inbound email reply and determine next action.

    Returns:
        {
            "intent": str,
            "confidence": float,
            "action": str,
            "reason": str,
            "extracted_data": dict,
        }
    """
    combined = f"{subject} {body}".lower()

    # Count keyword hits per intent
    hits: dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in combined)
        if count:
            hits[intent] = count

    # Resolve winning intent by priority order
    winner: str | None = None
    for intent in _PRIORITY_ORDER:
        if intent in hits:
            winner = intent
            break

    if winner is None:
        return {
            "intent": "unclear",
            "confidence": 0.0,
            "action": _INTENT_ACTIONS["unclear"],
            "reason": "No recognisable intent keywords found in reply.",
            "extracted_data": {},
        }

    # Confidence: proportion of matched keywords relative to max possible for
    # that intent (capped at 1.0).
    total_keywords = len(_INTENT_KEYWORDS[winner])
    raw_confidence = hits[winner] / total_keywords
    confidence = round(min(raw_confidence, 1.0), 4)

    extracted_data: dict[str, Any] = {}

    if winner == "booking":
        dates = _extract_dates(f"{subject} {body}")
        if dates:
            extracted_data["meeting_time"] = dates[0]
        if len(dates) > 1:
            extracted_data["meeting_time_alternatives"] = dates[1:]

    elif winner == "ooo":
        return_date = _extract_ooo_return(f"{subject} {body}")
        if return_date:
            extracted_data["ooo_return"] = return_date

    reason_map = {
        "positive": "Reply contains interest signals — warm lead, pause cadence.",
        "booking": "Reply indicates desire to schedule a meeting.",
        "not_interested": "Reply contains explicit rejection language.",
        "ooo": "Reply is an out-of-office auto-response.",
        "unsubscribe": "Reply contains opt-out / unsubscribe request (SPAM Act compliance).",
        "bounce": "Reply is a delivery failure notification.",
    }

    return {
        "intent": winner,
        "confidence": confidence,
        "action": _INTENT_ACTIONS[winner],
        "reason": reason_map[winner],
        "extracted_data": extracted_data,
    }
