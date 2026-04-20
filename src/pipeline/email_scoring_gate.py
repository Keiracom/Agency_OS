"""
Stage 8 Email Scoring Gate — CB Insights Anti-Pattern Detection
Directive #339

Pre-send scoring gate that evaluates outbound emails against the top failure
patterns identified in CB Insights analysis of 147 cold emails (93.9% failure rate).

GOV-12 compliant: runtime enforcement, not documentation-only.
Callers receive a numeric score and flag list; blocking decision stays with the caller.

Pass threshold: score >= 70
"""

from __future__ import annotations

import re
from typing import Any

PASS_THRESHOLD = 70

# Generic subject line phrases that signal low effort
_GENERIC_SUBJECTS = frozenset([
    "quick question",
    "following up",
    "touching base",
    "just checking in",
    "circling back",
    "checking in",
    "a quick note",
])

# Unmerged template token patterns — catches {name}, {{company}}, <FIRST_NAME>, [NAME], etc.
_TEMPLATE_TOKEN_RE = re.compile(
    r"(\{+\s*\w[\w\s]*\s*\}+)"           # {name} or {{company}}
    r"|(<\s*[A-Z][A-Z_\s]{2,}\s*>)"      # <FIRST_NAME>
    r"|(\[\s*[A-Z][A-Z_\s]{2,}\s*\])",   # [COMPANY_NAME]
)

# First-person pronouns
_FIRST_PERSON_RE = re.compile(r"\b(I|we|our|my)\b", re.IGNORECASE)
# Second-person pronouns
_SECOND_PERSON_RE = re.compile(r"\b(you|your|you're|you've)\b", re.IGNORECASE)

# Fake-threading prefixes
_FAKE_THREAD_RE = re.compile(r"^\s*(re|fw|fwd)\s*:", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Subject-line checks
# ---------------------------------------------------------------------------

def _check_subject(subject: str, flags: list[dict], score: int) -> int:
    stripped = subject.strip()

    if len(stripped) < 5:
        flags.append({
            "pattern": "weak_subject",
            "severity": "high",
            "detail": "Subject line is empty or too short (< 5 chars).",
        })
        score -= 30
        return score

    if stripped.isupper() or len(re.findall(r"[!?]", stripped)) > 2:
        flags.append({
            "pattern": "spammy_subject",
            "severity": "medium",
            "detail": "Subject is all-caps or contains excessive punctuation (> 2 ! or ?).",
        })
        score -= 15

    if _FAKE_THREAD_RE.match(stripped):
        flags.append({
            "pattern": "fake_threading",
            "severity": "high",
            "detail": "Subject starts with RE: or FW: suggesting a false thread.",
        })
        score -= 20

    if stripped.lower() in _GENERIC_SUBJECTS:
        flags.append({
            "pattern": "generic_subject",
            "severity": "low",
            "detail": f"Subject '{stripped}' is a known low-effort phrase.",
        })
        score -= 10

    return score


# ---------------------------------------------------------------------------
# Body checks
# ---------------------------------------------------------------------------

def _check_body(
    body: str,
    recipient_company: str | None,
    flags: list[dict],
    score: int,
) -> int:
    if _TEMPLATE_TOKEN_RE.search(body):
        flags.append({
            "pattern": "mail_merge_failure",
            "severity": "critical",
            "detail": "Body contains unmerged template tokens (e.g. {name}, <FIRST_NAME>).",
        })
        score -= 25

    body_lower = body.lower()
    company_mentioned = (
        recipient_company and recipient_company.lower() in body_lower
    )
    if not company_mentioned:
        flags.append({
            "pattern": "zero_buyer_knowledge",
            "severity": "medium",
            "detail": "Recipient company not mentioned — shows no buyer research.",
        })
        score -= 15

    word_count = len(body.split())
    if word_count > 300:
        flags.append({
            "pattern": "too_long",
            "severity": "low",
            "detail": f"Body is {word_count} words — cold emails should be under 300.",
        })
        score -= 10

    score = _check_pronoun_balance(body, flags, score)
    score = _check_cta(body, flags, score)

    if "unsubscribe" in body_lower and "http" not in body_lower:
        flags.append({
            "pattern": "missing_unsubscribe_link",
            "severity": "low",
            "detail": "Mentions 'unsubscribe' but no URL present.",
        })
        score -= 5

    return score


def _check_pronoun_balance(body: str, flags: list[dict], score: int) -> int:
    """Deduct if first-person pronouns dominate before any second-person usage."""
    # Find position of first second-person pronoun
    second_match = _SECOND_PERSON_RE.search(body)
    if second_match:
        prefix = body[: second_match.start()]
    else:
        prefix = body

    first_count_before = len(_FIRST_PERSON_RE.findall(prefix))
    if first_count_before > 3:
        flags.append({
            "pattern": "self_focused",
            "severity": "medium",
            "detail": (
                f"First-person pronouns appear {first_count_before}x before any "
                "second-person reference — email is seller-centric, not buyer-centric."
            ),
        })
        score -= 15
    return score


def _check_cta(body: str, flags: list[dict], score: int) -> int:
    """Deduct if the last two sentences contain no question mark."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body.strip()) if s.strip()]
    last_two = sentences[-2:] if len(sentences) >= 2 else sentences
    if not any("?" in s for s in last_two):
        flags.append({
            "pattern": "no_call_to_action",
            "severity": "medium",
            "detail": "Last two sentences contain no question — no clear CTA.",
        })
        score -= 10
    return score


# ---------------------------------------------------------------------------
# Sequence checks
# ---------------------------------------------------------------------------

def _check_sequence(
    sequence_position: int,
    total_sequence_length: int,
    flags: list[dict],
    score: int,
) -> int:
    if total_sequence_length == 1:
        flags.append({
            "pattern": "insufficient_follow_up",
            "severity": "medium",
            "detail": "Sequence has only one touch — 80% of sales need 5+ follow-ups.",
        })
        score -= 10

    if sequence_position > 5:
        flags.append({
            "pattern": "spam_fatigue_risk",
            "severity": "low",
            "detail": f"Touch #{sequence_position} — beyond touch 5 risks fatigue/spam reports.",
        })
        score -= 5

    return score


# ---------------------------------------------------------------------------
# Personalisation checks
# ---------------------------------------------------------------------------

def _check_personalisation(
    body: str,
    recipient_name: str | None,
    recipient_company: str | None,
    flags: list[dict],
    score: int,
) -> int:
    body_lower = body.lower()

    if recipient_name and recipient_name.lower() not in body_lower:
        flags.append({
            "pattern": "name_unused",
            "severity": "low",
            "detail": f"Recipient name '{recipient_name}' was available but not used in body.",
        })
        score -= 10

    # Company already deducted in _check_body; skip double-penalising.
    # This check only runs if company was NOT already flagged.
    already_flagged = any(f["pattern"] == "zero_buyer_knowledge" for f in flags)
    if recipient_company and not already_flagged:
        if recipient_company.lower() not in body_lower:
            flags.append({
                "pattern": "company_unused",
                "severity": "low",
                "detail": f"Company '{recipient_company}' was available but not used in body.",
            })
            score -= 10

    return score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_email(
    subject: str,
    body: str,
    recipient_name: str | None = None,
    recipient_company: str | None = None,
    sequence_position: int = 1,
    total_sequence_length: int = 1,
) -> dict[str, Any]:
    """Score an outbound email against CB Insights anti-patterns.

    Args:
        subject: Email subject line.
        body: Plain-text email body.
        recipient_name: Known first name of recipient (optional).
        recipient_company: Known company name of recipient (optional).
        sequence_position: Which touch in the outreach sequence (1-indexed).
        total_sequence_length: Total planned touches in the sequence.

    Returns:
        {
            "score": 0-100,
            "pass": bool,        # True if score >= PASS_THRESHOLD (70)
            "flags": [{"pattern": str, "severity": str, "detail": str}],
            "recommendations": [str],
        }
    """
    flags: list[dict] = []
    score = 100

    score = _check_subject(subject, flags, score)
    score = _check_body(body, recipient_company, flags, score)
    score = _check_sequence(sequence_position, total_sequence_length, flags, score)
    score = _check_personalisation(body, recipient_name, recipient_company, flags, score)

    score = max(0, score)

    recommendations = _build_recommendations(flags)

    return {
        "score": score,
        "pass": score >= PASS_THRESHOLD,
        "flags": flags,
        "recommendations": recommendations,
    }


def score_and_suggest(
    subject: str,
    body: str,
    recipient_name: str | None = None,
    recipient_company: str | None = None,
    sequence_position: int = 1,
    total_sequence_length: int = 1,
) -> dict[str, Any]:
    """Single-pass evaluator: score the email and generate actionable suggestions.

    Wraps score_email() and maps each flag to a concrete revision suggestion.
    The caller decides whether to revise and re-call.

    Returns:
        {
            "score": int,
            "passed": bool,
            "flags": [...],          # same as score_email()
            "suggestions": [str],    # one suggestion per failing flag
            "recommendations": [...] # existing general recs (unchanged)
        }
    """
    result = score_email(
        subject=subject,
        body=body,
        recipient_name=recipient_name,
        recipient_company=recipient_company,
        sequence_position=sequence_position,
        total_sequence_length=total_sequence_length,
    )

    suggestions = _build_suggestions(result["flags"], body, recipient_company)

    return {
        "score": result["score"],
        "passed": result["pass"],
        "flags": result["flags"],
        "suggestions": suggestions,
        "recommendations": result["recommendations"],
    }


_SUGGESTION_MAP: dict[str, str] = {
    "weak_subject": "Make subject specific to recipient's industry or pain point",
    "spammy_subject": "Remove all-caps and reduce punctuation to 1 ! or ? maximum",
    "fake_threading": "Remove RE:/FW: prefix unless this is a genuine reply",
    "generic_subject": "Replace the generic phrase with something specific to this prospect",
    "zero_buyer_knowledge": "Add reference to the recipient's company industry or recent activity",
    "self_focused": "Rewrite opening to lead with recipient's challenge, not your offering",
    "no_call_to_action": "End with a specific question (e.g., 'Would a 15-min call this week work?')",
    "too_long": "Cut to under 300 words — remove the least buyer-relevant paragraph",
    "missing_unsubscribe_link": "Add a real unsubscribe URL if referencing opt-out",
    "insufficient_follow_up": "Plan at least 5 touches — 80% of deals close after follow-up #5",
    "spam_fatigue_risk": "Consider retiring this contact or changing the channel after 5 touches",
    "name_unused": "Use the recipient's first name at least once to increase open-to-reply conversion",
    "company_unused": "Reference the recipient's company name to show you know who you're writing to",
}


def _build_suggestions(
    flags: list[dict],
    body: str,
    recipient_company: str | None,
) -> list[str]:
    """Map flags to actionable suggestions. mail_merge_failure lists the tokens found."""
    suggestions: list[str] = []
    for flag in flags:
        pattern = flag["pattern"]
        if pattern == "mail_merge_failure":
            tokens = _TEMPLATE_TOKEN_RE.findall(body)
            flat_tokens = [t for group in tokens for t in group if t]
            token_str = ", ".join(flat_tokens) if flat_tokens else "see body"
            suggestions.append(f"Fix unmerged template tokens: {token_str}")
        elif pattern == "zero_buyer_knowledge":
            company_hint = recipient_company or "the recipient's company"
            suggestions.append(
                f"Add reference to {company_hint}'s industry or recent activity"
            )
        elif pattern in _SUGGESTION_MAP:
            suggestions.append(_SUGGESTION_MAP[pattern])
    return suggestions


def _build_recommendations(flags: list[dict]) -> list[str]:
    _MAP = {
        "weak_subject": "Write a specific subject line referencing the prospect's business or pain point.",
        "spammy_subject": "Remove all-caps and reduce punctuation to 1 ! or ? maximum.",
        "fake_threading": "Remove RE:/FW: prefix unless this is a genuine reply.",
        "generic_subject": "Replace the generic phrase with something specific to this prospect.",
        "mail_merge_failure": "All template tokens ({name}, <FIRST_NAME>, etc.) must be replaced before sending.",
        "zero_buyer_knowledge": "Mention the recipient's company or industry by name to demonstrate research.",
        "too_long": "Cut the email to under 300 words — shorter emails get higher reply rates.",
        "self_focused": "Lead with a buyer-centric observation before introducing yourself.",
        "no_call_to_action": "End with a clear question that asks for a specific next step.",
        "missing_unsubscribe_link": "Add a real unsubscribe URL if referencing opt-out.",
        "insufficient_follow_up": "Plan at least 5 touches — 80% of deals close after follow-up #5.",
        "spam_fatigue_risk": "Consider retiring this contact or changing the channel after 5 touches.",
        "name_unused": "Use the recipient's first name at least once to increase open-to-reply conversion.",
        "company_unused": "Reference the recipient's company name to show you know who you're writing to.",
    }
    return [_MAP[f["pattern"]] for f in flags if f["pattern"] in _MAP]
