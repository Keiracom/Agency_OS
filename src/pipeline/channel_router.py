"""channel_router.py — Voice-first outreach channel routing.

Key insight: 58% of AU SMB leads have no email. Instead of abandoning them,
route to voice (tradies answer phones) + LinkedIn as primary channels.
"""

from __future__ import annotations


def route_prospect(
    has_email: bool,
    has_phone: bool,
    has_linkedin: bool,
    cis_score: int | None = None,
    propensity_score: int = 0,
) -> dict:
    """Determine primary and fallback outreach channels for a prospect.

    Returns:
        {
            "primary_channel": str,         # email | voice | linkedin | none
            "fallback_channels": list[str],
            "channels_available": list[str],
            "routing_reason": str,
            "recommended_sequence": list[dict],  # ordered touch sequence
        }
    """
    channels_available = _available(has_email, has_phone, has_linkedin)

    # ------------------------------------------------------------------ #
    # No reachability
    # ------------------------------------------------------------------ #
    if not channels_available:
        return {
            "primary_channel": "none",
            "fallback_channels": [],
            "channels_available": [],
            "routing_reason": "no_reachability",
            "recommended_sequence": [],
        }

    # ------------------------------------------------------------------ #
    # Determine base routing by channel combination
    # ------------------------------------------------------------------ #
    combo = (has_email, has_phone, has_linkedin)

    if combo == (True, True, True):
        primary, fallbacks, reason = "email", ["voice", "linkedin"], "full_coverage"
        base_sequence = _seq_email_phone_linkedin()

    elif combo == (True, False, True):
        primary, fallbacks, reason = "email", ["linkedin"], "email_linkedin"
        base_sequence = _seq_email_linkedin()

    elif combo == (False, True, True):
        primary, fallbacks, reason = "voice", ["linkedin"], "voice_linkedin_no_email"
        base_sequence = _seq_voice_linkedin()

    elif combo == (True, False, False):
        primary, fallbacks, reason = "email", [], "email_only"
        base_sequence = _seq_email_only()

    elif combo == (False, True, False):
        primary, fallbacks, reason = "voice", [], "phone_only"
        base_sequence = _seq_voice_only()

    elif combo == (False, False, True):
        primary, fallbacks, reason = "linkedin", [], "linkedin_only"
        base_sequence = _seq_linkedin_only()

    elif combo == (True, True, False):
        primary, fallbacks, reason = "email", ["voice"], "email_phone_no_linkedin"
        base_sequence = _seq_email_phone()

    else:
        # Unreachable given guard above, but be defensive
        return {
            "primary_channel": "none",
            "fallback_channels": [],
            "channels_available": channels_available,
            "routing_reason": "no_reachability",
            "recommended_sequence": [],
        }

    # ------------------------------------------------------------------ #
    # CIS-based adjustments (only when cis_score is explicitly provided)
    # ------------------------------------------------------------------ #
    score = cis_score if cis_score is not None else 0
    cis_supplied = cis_score is not None

    sequence = (
        _apply_cis_adjustments(base_sequence, score, has_email, has_phone, has_linkedin)
        if cis_supplied
        else base_sequence
    )

    # High CIS: voice > linkedin > email for personal touch
    if cis_supplied and score >= 85 and has_phone and primary == "email":
        primary = "voice"
        fallbacks = _reorder_fallbacks(["email", "linkedin"], has_linkedin)
        reason += "+high_cis_voice_priority"

    # Low CIS: reduce to email-only if available, otherwise keep as-is
    if cis_supplied and score < 40 and has_email:
        primary = "email"
        fallbacks = []
        reason += "+low_cis_email_only"
        email_touches = [t for t in sequence if t["channel"] == "email"]
        # Re-number touch indices to stay sequential
        sequence = [{**t, "touch": i + 1} for i, t in enumerate(email_touches)]

    return {
        "primary_channel": primary,
        "fallback_channels": fallbacks,
        "channels_available": channels_available,
        "routing_reason": reason,
        "recommended_sequence": sequence,
    }


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _available(has_email: bool, has_phone: bool, has_linkedin: bool) -> list[str]:
    ch = []
    if has_email:
        ch.append("email")
    if has_phone:
        ch.append("voice")
    if has_linkedin:
        ch.append("linkedin")
    return ch


def _reorder_fallbacks(candidates: list[str], has_linkedin: bool) -> list[str]:
    order = ["voice", "linkedin", "email"]
    return [c for c in order if c in candidates and (c != "linkedin" or has_linkedin)]


# ------------------------------------------------------------------ #
# Base sequences (pre-CIS adjustment)
# ------------------------------------------------------------------ #


def _seq_email_phone_linkedin() -> list[dict]:
    """5-touch: email + voice + linkedin."""
    return [
        {"day": 0, "channel": "email", "touch": 1, "note": "intro email"},
        {"day": 2, "channel": "voice", "touch": 2, "note": "intro call"},
        {"day": 4, "channel": "linkedin", "touch": 3, "note": "linkedin connect"},
        {"day": 7, "channel": "email", "touch": 4, "note": "follow-up email"},
        {"day": 10, "channel": "voice", "touch": 5, "note": "final call"},
    ]


def _seq_email_linkedin() -> list[dict]:
    """4-touch: email + linkedin."""
    return [
        {"day": 0, "channel": "email", "touch": 1, "note": "intro email"},
        {"day": 3, "channel": "linkedin", "touch": 2, "note": "linkedin connect"},
        {"day": 6, "channel": "email", "touch": 3, "note": "follow-up email"},
        {"day": 10, "channel": "linkedin", "touch": 4, "note": "linkedin message"},
    ]


def _seq_voice_linkedin() -> list[dict]:
    """3-touch: voice + linkedin."""
    return [
        {"day": 0, "channel": "voice", "touch": 1, "note": "intro call"},
        {"day": 2, "channel": "linkedin", "touch": 2, "note": "linkedin connect"},
        {"day": 5, "channel": "voice", "touch": 3, "note": "follow-up call"},
    ]


def _seq_voice_only() -> list[dict]:
    """2-touch: voice only."""
    return [
        {"day": 0, "channel": "voice", "touch": 1, "note": "intro call"},
        {"day": 5, "channel": "voice", "touch": 2, "note": "follow-up call"},
    ]


def _seq_linkedin_only() -> list[dict]:
    """3-touch: linkedin only."""
    return [
        {"day": 0, "channel": "linkedin", "touch": 1, "note": "linkedin connect"},
        {"day": 4, "channel": "linkedin", "touch": 2, "note": "linkedin message"},
        {"day": 9, "channel": "linkedin", "touch": 3, "note": "linkedin follow-up"},
    ]


def _seq_email_only() -> list[dict]:
    """3-touch: email only."""
    return [
        {"day": 0, "channel": "email", "touch": 1, "note": "intro email"},
        {"day": 4, "channel": "email", "touch": 2, "note": "follow-up email"},
        {"day": 9, "channel": "email", "touch": 3, "note": "final email"},
    ]


def _seq_email_phone() -> list[dict]:
    """4-touch: email + phone, no linkedin."""
    return [
        {"day": 0, "channel": "email", "touch": 1, "note": "intro email"},
        {"day": 2, "channel": "voice", "touch": 2, "note": "intro call"},
        {"day": 5, "channel": "email", "touch": 3, "note": "follow-up email"},
        {"day": 8, "channel": "voice", "touch": 4, "note": "follow-up call"},
    ]


# ------------------------------------------------------------------ #
# CIS adjustments
# ------------------------------------------------------------------ #


def _apply_cis_adjustments(
    sequence: list[dict],
    cis_score: int,
    has_email: bool,
    has_phone: bool,
    has_linkedin: bool,
) -> list[dict]:
    """Add extra touches for high CIS; trim for low CIS."""
    if cis_score >= 85:
        # Add an extra personal touch at the end if phone or linkedin available
        extra_channel = "voice" if has_phone else ("linkedin" if has_linkedin else None)
        if extra_channel:
            next_touch = len(sequence) + 1
            last_day = sequence[-1]["day"] if sequence else 0
            sequence = sequence + [
                {
                    "day": last_day + 4,
                    "channel": extra_channel,
                    "touch": next_touch,
                    "note": "high-value extra touch",
                }
            ]
    return sequence
