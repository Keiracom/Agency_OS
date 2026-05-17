"""src/api/webhooks/paddle.py — Paddle MoR inbound webhook handler.

KEI-150: Paddle Merchant of Record webhook scaffold.

Receives Paddle webhook POSTs at /api/webhooks/paddle, verifies the
Paddle-Signature HMAC using the ts;h1 scheme documented at:
  https://developer.paddle.com/webhooks/signature-verification

Fail-open: malformed payload / unmatched event type returns 200 OK so
Paddle doesn't retry-storm. Missing / invalid signature → 401.

Event handling (stub — extend per KEI-150 follow-ons):
  - All event types logged at INFO with event_type + event_id.
  - Returns 200 OK with {"status": "ok", "event_type": "<type>"}.

NOTE: Paddle MoR account registration is a Dave/human action and is
out of scope for this scaffold. Register at https://paddle.com and
set PADDLE_WEBHOOK_SECRET from the Paddle dashboard → Notifications.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/paddle", tags=["webhooks", "paddle"])

# Clock-skew tolerance for the Paddle ts field (seconds).
# Paddle recommends rejecting events older than 5 seconds in production;
# we use 300 s as a conservative default to survive slow relays in dev.
_TS_TOLERANCE_SECONDS = int(os.environ.get("PADDLE_TS_TOLERANCE", "300"))


def verify_paddle_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """Verify a Paddle webhook signature using the ts;h1 scheme.

    Paddle-Signature header format:
        ts=<unix-timestamp>;h1=<hex-hmac-sha256>

    Algorithm (per Paddle docs):
        signed_payload = f"{ts}:{raw_body}"
        expected_h1   = HMAC-SHA256(key=secret, msg=signed_payload).hexdigest()

    Returns True iff the h1 value matches and the timestamp is within
    _TS_TOLERANCE_SECONDS of now. Returns False (not raises) on any
    format error so callers can return 401 cleanly.
    """
    if not secret or not signature_header:
        return False
    try:
        parts = dict(item.split("=", 1) for item in signature_header.split(";"))
        ts_str = parts.get("ts", "")
        h1 = parts.get("h1", "")
    except (ValueError, AttributeError):
        return False
    if not ts_str or not h1:
        return False
    # Optional clock-skew guard (skip in tests by setting tolerance to a large value).
    try:
        ts_int = int(ts_str)
        if abs(time.time() - ts_int) > _TS_TOLERANCE_SECONDS:
            logger.warning("paddle webhook ts %s outside tolerance window", ts_str)
            return False
    except ValueError:
        return False
    signed_payload = f"{ts_str}:{body.decode('utf-8', errors='replace')}"
    expected = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, h1)


_RECEIVE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Paddle-Signature HMAC verification failed."},
}


@router.post("", responses=_RECEIVE_RESPONSES)
@router.post("/", responses=_RECEIVE_RESPONSES)
async def receive_paddle_webhook(request: Request) -> dict[str, str]:
    """Receive a Paddle webhook event, verify HMAC, log event type, return 200.

    Fail-open: malformed payload or unknown event type still returns 200 so
    Paddle does not retry-storm the endpoint. Only missing/invalid signature
    returns 401.
    """
    body = await request.body()
    secret = os.environ.get("PADDLE_WEBHOOK_SECRET", "")
    sig_header = request.headers.get("paddle-signature", "")

    if not verify_paddle_signature(secret, body, sig_header):
        logger.warning("paddle webhook signature verify failed")
        raise HTTPException(status_code=401, detail="signature verification failed")

    try:
        payload: dict[str, Any] = json.loads(body or b"{}")
    except json.JSONDecodeError:
        logger.warning("paddle webhook malformed json payload")
        return {"status": "malformed"}

    event_type: str = payload.get("event_type") or payload.get("event_id") or "unknown"
    event_id: str = payload.get("notification_id") or payload.get("event_id") or "unknown"
    logger.info("paddle webhook received event_type=%s event_id=%s", event_type, event_id)

    return {"status": "ok", "event_type": event_type}
