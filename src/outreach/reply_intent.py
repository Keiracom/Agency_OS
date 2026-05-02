"""
reply_intent.py — classify inbound email/SMS/LinkedIn replies via GPT-4o-mini.

Takes the reply body + optional context (original-outreach subject, prospect name),
returns a structured intent JSON that downstream cadence orchestration can route on.

Intent taxonomy (closed set — strict enum):
  - positive_interested      prospect wants to continue the conversation
  - booking_request          asked to schedule a meeting / sent a link
  - question                 asked a clarifying question; needs human answer
  - not_interested           explicit pass / "not now" / "no thanks"
  - unsubscribe              asked to be removed / "stop" / opt-out
  - out_of_office            OOO auto-response; re-try after return_date
  - referral                 redirected to a colleague with name + email
  - unclear                  LLM low-confidence — needs human triage

Returns:
  {
    "intent": <enum above>,
    "confidence": float 0-1,
    "evidence_phrase": str,         # short quote from reply that supports intent
    "extracted": {...}              # intent-specific extras (see per-intent keys)
  }

Failure modes:
  - OpenAI error / timeout -> {"intent": "unclear", "confidence": 0.0, ...}
  - Invalid JSON from model -> same
  Never raises; cadence orchestrator always gets a valid envelope.

Cost: ~$0.0001 USD per reply (GPT-4o-mini). Off the Anthropic credit pool.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"
TIMEOUT_S = 8

VALID_INTENTS = frozenset(
    {
        "positive_interested",
        "booking_request",
        "question",
        "not_interested",
        "unsubscribe",
        "out_of_office",
        "referral",
        "unclear",
    }
)


SYSTEM_PROMPT = """You are a reply-intent classifier for a B2B cold outreach system in Australia.

Classify the inbound reply into exactly one intent from this closed set:
  positive_interested | booking_request | question | not_interested |
  unsubscribe | out_of_office | referral | unclear

Rules:
- Use `unclear` with confidence <0.5 when you genuinely can't tell. Do not guess.
- `booking_request` = they explicitly propose a time OR send a scheduling link.
- `positive_interested` = receptive but no concrete next step yet.
- `unsubscribe` = any explicit opt-out language ("remove me", "stop", "unsubscribe", "do not contact").
- `out_of_office` = auto-response pattern (return_date if detectable).
- `referral` = "contact my colleague X at x@company.com" pattern.
- `not_interested` = explicit decline even if polite.

`evidence_phrase`: a verbatim ≤80-char quote from the reply that supports your classification.

`extracted`:
  booking_request: {"proposed_time": str|null, "booking_link": str|null}
  out_of_office:   {"return_date": str|null}
  referral:        {"referred_name": str|null, "referred_email": str|null}
  unsubscribe:     {"sms_opt_out": bool}   # true if mentions "STOP" / SMS-specific
  others:          {}

Return STRICT JSON only:
{"intent": <str>, "confidence": <float 0-1>, "evidence_phrase": <str>, "extracted": <obj>}
"""


async def classify_reply(
    body: str,
    original_subject: str | None = None,
    prospect_name: str | None = None,
) -> dict[str, Any]:
    """Classify a single reply body. Always returns a valid envelope."""
    if not OPENAI_API_KEY:
        return _unclear_envelope("no_openai_key")
    if not body or not body.strip():
        return _unclear_envelope("empty_body")

    context_lines = []
    if original_subject:
        context_lines.append(f"Original subject: {original_subject}")
    if prospect_name:
        context_lines.append(f"Prospect name: {prospect_name}")
    context_block = ("\n".join(context_lines) + "\n\n") if context_lines else ""

    user_message = f"{context_block}Reply body:\n---\n{body[:4000]}\n---"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
            )
            if resp.status_code != 200:
                logger.warning(f"[reply_intent] OpenAI {resp.status_code}: {resp.text[:200]}")
                return _unclear_envelope(f"openai_http_{resp.status_code}")
            raw = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning(f"[reply_intent] call failed: {exc}")
        return _unclear_envelope(f"call_exception: {type(exc).__name__}")

    return _parse_and_validate(raw)


def _parse_and_validate(raw: str) -> dict[str, Any]:
    """Parse JSON + enforce enum + clamp confidence + ensure extracted dict."""
    try:
        data = json.loads(raw)
    except Exception as exc:
        logger.warning(f"[reply_intent] json parse failed: {exc}")
        return _unclear_envelope("json_parse_error")

    intent = data.get("intent", "unclear")
    if intent not in VALID_INTENTS:
        intent = "unclear"

    confidence = data.get("confidence", 0.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except Exception:
        confidence = 0.0

    evidence = (data.get("evidence_phrase") or "")[:80]
    extracted = data.get("extracted") or {}
    if not isinstance(extracted, dict):
        extracted = {}

    return {
        "intent": intent,
        "confidence": confidence,
        "evidence_phrase": evidence,
        "extracted": extracted,
    }


def _unclear_envelope(reason: str) -> dict[str, Any]:
    return {
        "intent": "unclear",
        "confidence": 0.0,
        "evidence_phrase": "",
        "extracted": {},
        "_reason": reason,  # underscore-prefixed = not part of public contract
    }
