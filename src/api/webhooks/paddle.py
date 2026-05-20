"""src/api/webhooks/paddle.py — Paddle MoR inbound webhook handler.

KEI-150: Paddle Merchant of Record webhook scaffold.
KEI-152: invoice.paid + subscription.updated event handlers.

Receives Paddle webhook POSTs at /api/webhooks/paddle, verifies the
Paddle-Signature HMAC using the ts;h1 scheme documented at:
  https://developer.paddle.com/webhooks/signature-verification

Fail-open: malformed payload / unmatched event type returns 200 OK so
Paddle doesn't retry-storm. Missing / invalid signature → 401.

Event handling (KEI-152):
  - transaction.completed / invoice.paid → _handle_invoice_paid (UPDATE customers.last_paid_at)
  - subscription.updated → _handle_subscription_updated (UPDATE customers.tier via PADDLE_PRICE_TO_TIER map)
  - All other event types logged at INFO with event_type + event_id.
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
        pairs = (item.split("=", 1) for item in signature_header.split(";"))
        parts = {kv[0]: kv[1] for kv in pairs if len(kv) == 2}
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


def _dsn_from_env() -> str:
    """Resolve DSN with +asyncpg strip — same pattern as src/api/webhooks/linear.py."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1) if dsn else ""


def _handle_invoice_paid(payload: dict) -> None:
    """KEI-152: invoice.paid event → UPDATE customers SET last_paid_at = NOW().

    Locates customer via payload['data']['subscription_id'] (Paddle MoR ships
    the subscription id on the transaction event). If subscription_id is missing
    or no matching customer row exists (table may not exist yet — foundation
    pending), logs warning and returns (fail-open — Paddle doesn't retry-storm).
    """
    sub_id = (payload.get("data") or {}).get("subscription_id") or ""
    if not sub_id:
        logger.warning("paddle invoice.paid missing subscription_id — no customer update")
        return
    dsn = _dsn_from_env()
    if not dsn:
        logger.warning("paddle handler: DATABASE_URL unset, skipping last_paid_at update")
        return
    try:
        import psycopg  # noqa: PLC0415

        with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.customers
                   SET last_paid_at = NOW(), updated_at = NOW()
                 WHERE paddle_subscription_id = %s
                """,
                (sub_id,),
            )
            conn.commit()
            logger.info(
                "paddle invoice.paid: marked customer paid for sub=%s rowcount=%d",
                sub_id,
                cur.rowcount,
            )
    except Exception as exc:  # noqa: BLE001 — webhook fail-open
        logger.warning("paddle invoice.paid handler failed for sub=%s: %s", sub_id, exc)


def _handle_subscription_updated(payload: dict) -> None:
    """KEI-152: subscription.updated event → UPDATE customers SET tier = <new_tier>.

    Paddle ships price/product id on the event; we map price id → tier name
    via PADDLE_PRICE_TO_TIER env (JSON dict). If unset OR price unmapped,
    logs warning + returns (fail-open).
    """
    data = payload.get("data") or {}
    sub_id = data.get("id") or data.get("subscription_id") or ""
    items = data.get("items") or []
    price_id = ""
    if items and isinstance(items[0], dict):
        price_id = (items[0].get("price") or {}).get("id") or items[0].get("price_id") or ""
    if not (sub_id and price_id):
        logger.warning("paddle subscription.updated missing sub_id or price_id — no tier update")
        return
    import json as _json  # noqa: PLC0415

    tier_map_raw = os.environ.get("PADDLE_PRICE_TO_TIER", "{}")
    try:
        tier_map: dict[str, str] = _json.loads(tier_map_raw)
    except (ValueError, TypeError):
        tier_map = {}
    new_tier = tier_map.get(price_id, "")
    if not new_tier:
        logger.warning(
            "paddle subscription.updated: price_id %s not in PADDLE_PRICE_TO_TIER map",
            price_id,
        )
        return
    dsn = _dsn_from_env()
    if not dsn:
        logger.warning("paddle handler: DATABASE_URL unset, skipping tier update")
        return
    try:
        import psycopg  # noqa: PLC0415

        with psycopg.connect(dsn, prepare_threshold=None) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.customers
                   SET tier = %s, updated_at = NOW()
                 WHERE paddle_subscription_id = %s
                """,
                (new_tier, sub_id),
            )
            conn.commit()
            logger.info(
                "paddle subscription.updated: set tier=%s for sub=%s rowcount=%d",
                new_tier,
                sub_id,
                cur.rowcount,
            )
    except Exception as exc:  # noqa: BLE001 — webhook fail-open
        logger.warning("paddle subscription.updated handler failed for sub=%s: %s", sub_id, exc)


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

    if event_type in ("invoice.paid", "transaction.completed"):
        _handle_invoice_paid(payload)
    elif event_type == "subscription.updated":
        _handle_subscription_updated(payload)

    return {"status": "ok", "event_type": event_type}
