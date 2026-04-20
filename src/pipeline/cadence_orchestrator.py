"""cadence_orchestrator.py — Multi-touch outreach sequencing with response-triggered pauses.

Stateless: makes decisions from inputs, does not track state internally.
Pure Python, no external dependencies.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Intents that halt the cadence — prospect has engaged positively or opted out
_PAUSE_INTENTS: frozenset[str] = frozenset({"positive", "booked", "meeting_request"})
_SUPPRESS_INTENTS: frozenset[str] = frozenset({"unsubscribe", "opt_out"})
_CONVERTED_INTENTS: frozenset[str] = frozenset({"booked"})

# Channel preference order when a prospect's preferred channel is unavailable
_FALLBACK_ORDER: list[str] = ["email", "linkedin", "voice"]

# ---------------------------------------------------------------------------
# Default sequence
# ---------------------------------------------------------------------------

_DEFAULT_SEQUENCE: list[dict] = [
    {"step": 1, "channel": "email",    "delay_after_previous": 0},
    {"step": 2, "channel": "email",    "delay_after_previous": 3},
    {"step": 3, "channel": "linkedin", "delay_after_previous": 4},
    {"step": 4, "channel": "email",    "delay_after_previous": 7},
    {"step": 5, "channel": "voice",    "delay_after_previous": 3},
]


def get_default_sequence() -> list[dict]:
    """Return the canonical 5-touch outreach sequence.

    Each item contains:
      step                  — 1-based position in the sequence
      channel               — preferred channel: "email" | "linkedin" | "voice"
      delay_after_previous  — calendar days to wait after the prior step fires
    """
    return [dict(step) for step in _DEFAULT_SEQUENCE]


# ---------------------------------------------------------------------------
# Core decision functions
# ---------------------------------------------------------------------------

def should_pause(prospect_id: str, response_intent: str) -> bool:  # noqa: ARG001
    """Return True if the cadence must pause due to the prospect's reply intent.

    Pauses on: positive reply, meeting booked, meeting request, unsubscribe.
    The caller is responsible for acting on a pause (e.g. suppressing future steps).

    Args:
        prospect_id:      Identifier of the prospect (unused — stateless; included for
                          future caller-side logging without breaking the signature).
        response_intent:  Intent label from the reply classifier, e.g. "positive",
                          "booked", "unsubscribe", "not_interested".
    """
    return response_intent in _PAUSE_INTENTS | _SUPPRESS_INTENTS


def is_converted(response_intent: str) -> bool:
    """Return True if the prospect should be marked as converted (e.g. booked)."""
    return response_intent in _CONVERTED_INTENTS


def is_suppressed(response_intent: str) -> bool:
    """Return True if the prospect must be permanently suppressed."""
    return response_intent in _SUPPRESS_INTENTS


def get_channel_for_step(
    step: int,
    has_email: bool,
    has_phone: bool,
    has_linkedin: bool,
) -> str | None:
    """Return the channel to use for a given sequence step.

    Looks up the preferred channel in the default sequence, then falls back
    through _FALLBACK_ORDER if the preferred channel's data is unavailable.
    Returns None if no channel has the required contact data.

    Args:
        step:         1-based step number from the sequence.
        has_email:    Prospect has a verified email address.
        has_phone:    Prospect has a verified phone number.
        has_linkedin: Prospect has a LinkedIn profile URL.
    """
    availability: dict[str, bool] = {
        "email": has_email,
        "voice": has_phone,
        "linkedin": has_linkedin,
    }

    # Determine preferred channel for this step
    seq = {s["step"]: s["channel"] for s in _DEFAULT_SEQUENCE}
    preferred = seq.get(step)

    # Build ordered candidate list: preferred first, then fallbacks
    candidates: list[str] = []
    if preferred:
        candidates.append(preferred)
    for ch in _FALLBACK_ORDER:
        if ch not in candidates:
            candidates.append(ch)

    for channel in candidates:
        if availability.get(channel, False):
            return channel

    return None


def get_next_step(
    prospect_id: str,  # noqa: ARG001
    current_step: int,
    last_response: str | None,
) -> dict:
    """Determine the next action for a prospect.

    Returns a result dict:
      action        — "send" | "pause" | "suppress" | "complete"
      next_step     — step number to execute (only present when action == "send")
      reason        — human-readable explanation
      converted     — True when prospect should be marked as converted

    Args:
        prospect_id:   Identifier of the prospect (stateless; for caller logging).
        current_step:  The step that just fired (0 = no step fired yet).
        last_response: Intent string from the reply classifier, or None if no reply.
    """
    # --- Response-driven branches ---
    if last_response is not None:
        if is_suppressed(last_response):
            return {
                "action": "suppress",
                "reason": f"Prospect opted out (intent={last_response})",
                "converted": False,
            }

        if should_pause(prospect_id, last_response):
            return {
                "action": "pause",
                "reason": f"Positive engagement detected (intent={last_response})",
                "converted": is_converted(last_response),
            }

    # --- Sequence progression ---
    next_step = current_step + 1
    max_step = max(s["step"] for s in _DEFAULT_SEQUENCE)

    if next_step > max_step:
        return {
            "action": "complete",
            "reason": "All sequence steps exhausted without response",
            "converted": False,
        }

    step_def = next(s for s in _DEFAULT_SEQUENCE if s["step"] == next_step)
    return {
        "action": "send",
        "next_step": next_step,
        "channel": step_def["channel"],
        "delay_days": step_def["delay_after_previous"],
        "reason": f"No reply — advancing to step {next_step}",
        "converted": False,
    }
