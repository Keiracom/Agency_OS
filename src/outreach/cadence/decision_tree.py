"""
Contract: src/outreach/cadence/decision_tree.py
Purpose: Map a classified reply intent to concrete scheduled_touches mutations.
Layer:   services (pure Python — no framework deps)
Imports: stdlib + cadence_orchestrator + suppression_manager
Consumers: src/api/routes/outreach_webhooks.py, Prefect flows

Intent taxonomy (closed set — aligned with src/outreach/reply_intent.py):
  - positive_interested  -> cancel remaining touches, insert booking outreach
  - booking_request      -> cancel remaining, insert meeting confirmation
  - not_interested       -> cancel remaining, suppress
  - unsubscribe          -> cancel remaining, suppress permanently
  - out_of_office        -> reschedule all pending to return_date + 2 days
  - question             -> pause 48h, escalate to human review
  - referral             -> log referral, continue existing sequence
  - unclear              -> noop (human triage)

A low confidence (< CONFIDENCE_FLOOR) always downgrades to 'unclear' so
the webhook layer can trigger LLM escalation or human review. The tree
itself never calls the LLM — that's the webhook's job.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.pipeline.cadence_orchestrator import should_pause
from src.pipeline.suppression_manager import SuppressionManager

logger = logging.getLogger(__name__)

CONFIDENCE_FLOOR = 0.7
QUESTION_PAUSE_HOURS = 48
OOO_RESUME_OFFSET_DAYS = 2

VALID_ACTIONS = frozenset({
    "cancel", "pause", "reschedule", "insert", "suppress", "escalate", "noop",
})


@dataclass
class TouchMutation:
    """One mutation to apply to scheduled_touches. Executor is the webhook layer."""

    action: str  # cancel | pause | reschedule | insert | suppress | escalate | noop
    touch_id: str | None = None
    new_scheduled_at: datetime | None = None
    reason: str = ""
    channel: str | None = None            # for 'insert' mutations
    sequence_step: int | None = None      # for 'insert' mutations
    content: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


class CadenceDecisionTree:
    """
    Contract: src/outreach/cadence/decision_tree.py — CadenceDecisionTree
    Purpose:  Translate (intent, confidence, prospect_state, extracted) into mutations.
    Layer:    services (pure)

    prospect_state is the snapshot the caller has already loaded from
    scheduled_touches + leads:
        {
            "lead_id": uuid,
            "client_id": uuid,
            "prospect": {"email": ..., "phone": ...},
            "pending_touches": [{"id": uuid, "channel": ..., "sequence_step": ..., "scheduled_at": datetime}, ...],
        }
    """

    def decide(
        self,
        intent: str,
        confidence: float,
        prospect_state: dict,
        extracted_data: dict | None = None,
    ) -> list[TouchMutation]:
        """Return the ordered list of mutations for this intent."""
        extracted_data = extracted_data or {}

        # Low-confidence replies always route to 'unclear' — webhook will
        # have already tried LLM escalation before we get here.
        if confidence < CONFIDENCE_FLOOR and intent != "unclear":
            logger.info(
                "decision_tree: intent=%s confidence=%.2f below floor — forcing unclear",
                intent, confidence,
            )
            intent = "unclear"

        handler = _INTENT_HANDLERS.get(intent, _handle_unclear)
        return handler(prospect_state, extracted_data)


# ---------------------------------------------------------------------------
# Per-intent handlers — each returns list[TouchMutation]
# ---------------------------------------------------------------------------

def _cancel_all_pending(state: dict, reason: str) -> list[TouchMutation]:
    return [
        TouchMutation(action="cancel", touch_id=str(t["id"]), reason=reason)
        for t in state.get("pending_touches", [])
    ]


def _handle_positive(state: dict, extracted: dict) -> list[TouchMutation]:
    muts = _cancel_all_pending(state, "positive_reply — booking outreach next")
    muts.append(TouchMutation(
        action="insert",
        channel="email",
        sequence_step=0,
        reason="send booking link in response to positive reply",
        content={"template": "booking_offer", "extracted": extracted},
    ))
    # cadence_orchestrator agrees we should pause cycle here
    assert should_pause(str(state.get("lead_id", "")), "positive")
    return muts


def _handle_booking(state: dict, extracted: dict) -> list[TouchMutation]:
    muts = _cancel_all_pending(state, "booking_request — confirmation outreach next")
    muts.append(TouchMutation(
        action="insert",
        channel="email",
        sequence_step=0,
        reason="send meeting confirmation in response to booking request",
        content={"template": "meeting_confirmation", "extracted": extracted},
    ))
    return muts


def _handle_not_interested(state: dict, _: dict) -> list[TouchMutation]:
    muts = _cancel_all_pending(state, "not_interested — cadence terminated")
    muts.append(_suppress_mutation(state, reason="not_interested"))
    return muts


def _handle_unsubscribe(state: dict, _: dict) -> list[TouchMutation]:
    muts = _cancel_all_pending(state, "unsubscribe — SPAM Act compliance")
    muts.append(_suppress_mutation(state, reason="unsubscribe"))
    return muts


def _handle_ooo(state: dict, extracted: dict) -> list[TouchMutation]:
    # extracted may carry ooo_return (from keyword router) or return_date (from LLM)
    raw = extracted.get("return_date") or extracted.get("ooo_return")
    resume = _parse_resume_date(raw) + timedelta(days=OOO_RESUME_OFFSET_DAYS)
    return [
        TouchMutation(
            action="reschedule",
            touch_id=str(t["id"]),
            new_scheduled_at=_shift_to_resume(t.get("scheduled_at"), resume),
            reason=f"ooo — resume after {resume.date().isoformat()}",
        )
        for t in state.get("pending_touches", [])
    ]


def _handle_question(state: dict, _: dict) -> list[TouchMutation]:
    resume = datetime.now(UTC) + timedelta(hours=QUESTION_PAUSE_HOURS)
    muts: list[TouchMutation] = [
        TouchMutation(
            action="pause", touch_id=str(t["id"]),
            new_scheduled_at=resume,
            reason=f"question — paused {QUESTION_PAUSE_HOURS}h for human answer",
        )
        for t in state.get("pending_touches", [])
    ]
    muts.append(TouchMutation(
        action="escalate", reason="question — human review required",
        extra={"lead_id": state.get("lead_id")},
    ))
    return muts


def _handle_referral(state: dict, extracted: dict) -> list[TouchMutation]:
    # Log the referral + continue the existing sequence untouched.
    return [TouchMutation(
        action="noop",
        reason="referral logged — sequence unchanged",
        extra={
            "referral_name": extracted.get("referral_name"),
            "referral_email": extracted.get("referral_email"),
            "lead_id": state.get("lead_id"),
        },
    )]


def _handle_unclear(state: dict, _: dict) -> list[TouchMutation]:
    return [TouchMutation(
        action="noop", reason="unclear intent — deferring to human review",
        extra={"lead_id": state.get("lead_id")},
    )]


_INTENT_HANDLERS = {
    "positive_interested": _handle_positive,
    "booking_request":     _handle_booking,
    "not_interested":      _handle_not_interested,
    "unsubscribe":         _handle_unsubscribe,
    "out_of_office":       _handle_ooo,
    "question":            _handle_question,
    "referral":            _handle_referral,
    "unclear":             _handle_unclear,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _suppress_mutation(state: dict, *, reason: str) -> TouchMutation:
    """Build a suppress mutation; actual SuppressionManager call is deferred to executor."""
    email = (state.get("prospect") or {}).get("email") or ""
    return TouchMutation(
        action="suppress", reason=reason,
        extra={
            "email": email,
            "suppression_reason": reason,
            "channel": "all",
            "source": "decision_tree",
        },
    )


def _parse_resume_date(raw: Any) -> datetime:
    """Parse ooo return_date string to timezone-aware datetime; fallback +7d."""
    fallback = datetime.now(UTC) + timedelta(days=7)
    if not raw:
        return fallback
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        logger.warning("decision_tree: unparseable return_date %r — falling back to +7d", raw)
        return fallback


def _shift_to_resume(original: Any, resume: datetime) -> datetime:
    """Push an original scheduled_at forward to resume if it's earlier; else keep it."""
    if not isinstance(original, datetime):
        return resume
    orig = original if original.tzinfo else original.replace(tzinfo=UTC)
    return resume if orig < resume else orig


def apply_suppression(mutation: TouchMutation) -> dict:
    """Helper for executors — call SuppressionManager per suppress mutation."""
    if mutation.action != "suppress":
        return {"success": False, "error": "not a suppress mutation"}
    return SuppressionManager.add_to_suppression(
        email=mutation.extra.get("email", ""),
        reason=mutation.extra.get("suppression_reason", "unsubscribe"),
        channel=mutation.extra.get("channel", "all"),
        source=mutation.extra.get("source", "decision_tree"),
    )
