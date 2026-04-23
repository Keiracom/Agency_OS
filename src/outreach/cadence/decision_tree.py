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

import json
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
    "create_prospect",
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
    # Always log the referral against the original prospect's history.
    muts: list[TouchMutation] = [TouchMutation(
        action="noop",
        reason="referral logged — sequence unchanged",
        extra={
            "referral_name": extracted.get("referral_name"),
            "referral_email": extracted.get("referral_email"),
            "lead_id": state.get("lead_id"),
        },
    )]
    # When a referral email is present, emit a create_prospect mutation so the
    # webhook executor can call cadence_orchestrator.create_prospect_from_referral.
    # The mutation carries the minimum payload the orchestrator needs.
    referral_email = extracted.get("referral_email")
    if referral_email:
        muts.append(TouchMutation(
            action="create_prospect",
            reason="referral contains new prospect email — spawn cadence",
            extra={
                "source": "referral",
                "referral_email": referral_email,
                "referral_name": extracted.get("referral_name"),
                "referred_by_lead_id": state.get("lead_id"),
                "client_id": state.get("client_id"),
            },
        ))
    return muts


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


# ---------------------------------------------------------------------------
# TouchStore — canonical DB-facing executor for TouchMutation lists.
# Lives here (not in the webhook route) so Prefect flows + API handlers share
# one implementation. Injectable db_conn so tests can mock the DB entirely.
# ---------------------------------------------------------------------------

class TouchStore:
    """
    Contract: src/outreach/cadence/decision_tree.py — TouchStore
    Purpose:  Apply a list of TouchMutation to scheduled_touches + side-effects.
    Layer:    services

    Mutation → DB action map:
        cancel     → UPDATE status='cancelled'
        pause      → UPDATE status='paused'
        reschedule → UPDATE scheduled_at=new_scheduled_at
        insert     → INSERT status='pending'
        suppress   → SuppressionManager.add_to_suppression + cancel all pending for lead
        escalate   → log only (no DB write; queue TBD)
        noop       → skipped

    Backward compat: TouchStore() with no db_conn returns 0 applied (legacy stub).
    """

    def __init__(self, db_conn: Any | None = None) -> None:
        self.db = db_conn

    async def load_pending(self, lead_id: str) -> list[dict]:
        if self.db is None:
            return []
        rows = await self.db.fetch(
            """
            SELECT id, channel, sequence_step, scheduled_at, status
            FROM scheduled_touches
            WHERE lead_id = $1 AND status IN ('pending', 'paused')
            ORDER BY scheduled_at
            """,
            lead_id,
        )
        return [dict(r) for r in rows]

    async def apply(self, mutations: list[TouchMutation]) -> int:
        """Apply every mutation. Returns number of successfully-applied rows."""
        if self.db is None:
            return 0

        applied = 0
        for m in mutations:
            try:
                if await self._apply_one(m):
                    applied += 1
            except Exception as exc:
                logger.exception("TouchStore.apply failed for %s: %s", m.action, exc)
        return applied

    async def _apply_one(self, m: TouchMutation) -> bool:
        action = m.action
        if action == "cancel":
            return await self._status_update(m, "cancelled")
        if action == "pause":
            return await self._status_update(m, "paused")
        if action == "reschedule":
            return await self._reschedule(m)
        if action == "insert":
            return await self._insert(m)
        if action == "suppress":
            return await self._suppress(m)
        if action == "escalate":
            logger.info(
                "TouchStore: escalate mutation — reason=%s extra=%s",
                m.reason, m.extra,
            )
            return True
        return False

    # -- per-action helpers --------------------------------------------------

    async def _status_update(self, m: TouchMutation, status: str) -> bool:
        if not m.touch_id:
            return False
        await self.db.execute(
            """
            UPDATE scheduled_touches
            SET status = $2,
                skipped_reason = CASE WHEN $2 = 'paused' THEN $3 ELSE skipped_reason END,
                failure_reason = CASE WHEN $2 = 'cancelled' THEN $3 ELSE failure_reason END,
                updated_at = NOW()
            WHERE id = $1
            """,
            m.touch_id, status, m.reason,
        )
        return True

    async def _reschedule(self, m: TouchMutation) -> bool:
        if not m.touch_id or not m.new_scheduled_at:
            return False
        await self.db.execute(
            """
            UPDATE scheduled_touches
            SET scheduled_at = $2, updated_at = NOW()
            WHERE id = $1
            """,
            m.touch_id, m.new_scheduled_at,
        )
        return True

    async def _insert(self, m: TouchMutation) -> bool:
        client_id = m.extra.get("client_id")
        lead_id = m.extra.get("lead_id")
        if not client_id or not lead_id or not m.channel:
            logger.warning(
                "TouchStore: insert missing client_id/lead_id/channel — extra=%s",
                m.extra,
            )
            return False
        scheduled_at = m.new_scheduled_at or datetime.now(UTC)
        content = json.dumps(m.content or {})
        prospect = json.dumps(m.extra.get("prospect") or {})
        await self.db.execute(
            """
            INSERT INTO scheduled_touches (
                client_id, lead_id, channel, sequence_step,
                scheduled_at, status, content, prospect,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, 'pending', $6::jsonb, $7::jsonb, NOW(), NOW()
            )
            """,
            client_id, lead_id, m.channel,
            m.sequence_step or 0, scheduled_at, content, prospect,
        )
        return True

    async def _suppress(self, m: TouchMutation) -> bool:
        # 1. Write-through to suppression list (best-effort, non-fatal).
        result = apply_suppression(m)
        # 2. Cascade: cancel every pending/paused touch for this lead.
        lead_id = m.extra.get("lead_id")
        if lead_id:
            await self.db.execute(
                """
                UPDATE scheduled_touches
                SET status = 'cancelled',
                    failure_reason = 'suppressed',
                    updated_at = NOW()
                WHERE lead_id = $1 AND status IN ('pending', 'paused')
                """,
                lead_id,
            )
        return bool(result.get("success", True))
