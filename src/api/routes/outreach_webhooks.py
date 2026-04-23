"""
Contract: src/api/routes/outreach_webhooks.py
Purpose: Inbound webhook endpoints for Salesforge / Unipile / ElevenAgents reply events.
Layer:   api
Imports: fastapi, stdlib (hmac/hashlib), reply_router, reply_intent, decision_tree
Consumers: provider webhook deliveries

Per-provider flow (shared):
    1. HMAC-SHA256 verify request signature vs <PROVIDER>_WEBHOOK_SECRET env
    2. Extract reply body + metadata
    3. Fast-path classify via src/pipeline/reply_router.classify_reply
    4. If confidence < FAST_PATH_FLOOR or intent == 'unclear':
         LLM-escalate via src/outreach/reply_intent.classify_reply
    5. Load prospect_state (pending touches for this lead)
    6. CadenceDecisionTree.decide() -> list[TouchMutation]
    7. Execute mutations on scheduled_touches (+ SuppressionManager for suppress)

Signature pattern follows src/integrations/calendar_booking.py:verify_cal_signature —
hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest(), compared via
hmac.compare_digest.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.outreach.cadence.decision_tree import (
    CadenceDecisionTree,
    TouchMutation,
    apply_suppression,
)
from src.outreach.reply_intent import classify_reply as llm_classify
from src.pipeline.reply_router import classify_reply as keyword_classify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["outreach-webhooks"])

FAST_PATH_FLOOR = 0.7

# Map fast-path (reply_router) intents to the reply_intent taxonomy the
# decision_tree uses.
_FAST_TO_CANONICAL = {
    "positive":       "positive_interested",
    "booking":        "booking_request",
    "not_interested": "not_interested",
    "unsubscribe":    "unsubscribe",
    "ooo":            "out_of_office",
    "bounce":         "unsubscribe",  # bounce is a hard suppression
    "unclear":        "unclear",
}


# ---------------------------------------------------------------------------
# Signature verification — delegated to src/security/webhook_sigs.py (slice 8)
# ---------------------------------------------------------------------------

from src.security.webhook_sigs import verify_signature as _webhook_verify


def _verify(secret_env: str, payload: bytes, signature: str | None) -> bool:
    """Thin wrapper preserved for test-layer compatibility — delegates to
    src.security.webhook_sigs.verify_signature which is the canonical
    per-provider HMAC entrypoint from slice 8 onward."""
    return _webhook_verify(secret_env, payload, signature)


# ---------------------------------------------------------------------------
# DB-facing shim — injectable for tests
# ---------------------------------------------------------------------------

class TouchStore:
    """Interface the webhooks use to talk to scheduled_touches. Override in tests."""

    async def load_pending(self, lead_id: str) -> list[dict]:
        return []

    async def apply(self, mutations: list[TouchMutation]) -> int:
        return 0


_default_store = TouchStore()


def get_touch_store() -> TouchStore:
    return _default_store


# ---------------------------------------------------------------------------
# Shared pipeline
# ---------------------------------------------------------------------------

async def _process_reply(
    *,
    body_text: str,
    subject: str,
    sender: str,
    lead_id: str,
    client_id: str,
    store: TouchStore,
) -> dict[str, Any]:
    fast = keyword_classify(subject=subject, body=body_text, sender_email=sender)
    intent = _FAST_TO_CANONICAL.get(fast["intent"], "unclear")
    confidence = float(fast.get("confidence", 0.0))
    extracted = dict(fast.get("extracted_data") or {})

    escalated = False
    if confidence < FAST_PATH_FLOOR or intent == "unclear":
        llm = await llm_classify(body=body_text, original_subject=subject)
        if llm.get("intent") in _ALL_CANONICAL:
            intent = llm["intent"]
            confidence = float(llm.get("confidence", 0.0))
            extracted = dict(llm.get("extracted") or extracted)
            escalated = True

    pending = await store.load_pending(lead_id)
    prospect_state = {
        "lead_id":    lead_id,
        "client_id":  client_id,
        "prospect":   {"email": sender},
        "pending_touches": pending,
    }
    mutations = CadenceDecisionTree().decide(intent, confidence, prospect_state, extracted)

    # Execute suppression synchronously; other mutations go to the store.
    for m in mutations:
        if m.action == "suppress":
            apply_suppression(m)
    applied = await store.apply(mutations)

    return {
        "status": "ok",
        "intent": intent,
        "confidence": confidence,
        "escalated_to_llm": escalated,
        "mutations": len(mutations),
        "applied": applied,
    }


_ALL_CANONICAL = frozenset({
    "positive_interested", "booking_request", "not_interested",
    "unsubscribe", "out_of_office", "question", "referral", "unclear",
})


async def _read_and_verify(request: Request, secret_env: str, header: str) -> dict:
    raw = await request.body()
    sig = request.headers.get(header, "")
    if not _verify(secret_env, raw, sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")
    try:
        return await request.json()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid json: {exc}") from exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/salesforge")
async def salesforge_webhook(
    request: Request,
    store: TouchStore = Depends(get_touch_store),
):
    payload = await _read_and_verify(request, "SALESFORGE_WEBHOOK_SECRET", "X-Salesforge-Signature")
    return await _process_reply(
        body_text=payload.get("body", ""),
        subject=payload.get("subject", ""),
        sender=payload.get("from_email", ""),
        lead_id=str(payload.get("lead_id", "")),
        client_id=str(payload.get("client_id", "")),
        store=store,
    )


@router.post("/unipile")
async def unipile_webhook(
    request: Request,
    store: TouchStore = Depends(get_touch_store),
):
    payload = await _read_and_verify(request, "UNIPILE_WEBHOOK_SECRET", "X-Unipile-Signature")
    return await _process_reply(
        body_text=payload.get("message", ""),
        subject=payload.get("thread_subject", ""),
        sender=payload.get("from_profile_url", ""),
        lead_id=str(payload.get("lead_id", "")),
        client_id=str(payload.get("client_id", "")),
        store=store,
    )


@router.post("/elevenagents")
async def elevenagents_webhook(
    request: Request,
    store: TouchStore = Depends(get_touch_store),
):
    payload = await _read_and_verify(request, "ELEVENAGENTS_WEBHOOK_SECRET", "X-ElevenAgents-Signature")
    transcript = payload.get("transcript") or payload.get("summary") or ""
    return await _process_reply(
        body_text=transcript,
        subject=f"voice_call_{payload.get('call_id', '')}",
        sender=payload.get("phone_number", ""),
        lead_id=str(payload.get("lead_id", "")),
        client_id=str(payload.get("client_id", "")),
        store=store,
    )
