"""src/integrations/resend_client.py — thin Resend SDK wrapper.

Task #20 — Email Integration Backend (aiden/email-backend).

Single send entrypoint + HMAC verification helper for inbound webhooks.
The Resend Python SDK (`pip install resend`) is the canonical client.
We keep the wrapper minimal so route handlers don't need to know about
SDK shape.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResendError(RuntimeError):
    """Raised when Resend send fails for any reason."""


def _build_client():
    """Configure and return the resend module. Raises ResendError if env or
    package missing — surfaced as 503 by the route handler."""
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise ResendError("RESEND_API_KEY env var is not set")
    try:
        import resend  # type: ignore
    except ImportError as exc:
        raise ResendError(
            "resend package not installed. Run: pip install 'resend>=0.8.0'"
        ) from exc
    resend.api_key = api_key
    return resend


def send_email(
    *,
    to: str | list[str],
    subject: str,
    body_html: str | None = None,
    body_text: str | None = None,
    from_address: str | None = None,
) -> dict[str, Any]:
    """Send one email via Resend. Returns the SDK response dict (contains
    `id` = message_id). Raises ResendError on any failure."""
    if not body_html and not body_text:
        raise ResendError("either body_html or body_text is required")
    sender = from_address or os.environ.get(
        "RESEND_DEFAULT_FROM", "noreply@keiracom.com",
    )
    resend = _build_client()
    payload: dict[str, Any] = {
        "from": sender,
        "to": [to] if isinstance(to, str) else list(to),
        "subject": subject,
    }
    if body_html:
        payload["html"] = body_html
    if body_text:
        payload["text"] = body_text
    try:
        result = resend.Emails.send(payload)
    except Exception as exc:
        logger.error("[resend_client] send failed to=%s: %s", to, exc)
        raise ResendError(str(exc)) from exc
    if not isinstance(result, dict) or "id" not in result:
        raise ResendError(f"unexpected Resend response shape: {result!r}")
    return result


WEBHOOK_TOLERANCE_SECONDS = 300  # 5 minutes — Svix/Resend default


def verify_webhook_signature(
    raw_body: bytes,
    signature_header: str | None,
    msg_id: str | None = None,
    timestamp: str | None = None,
) -> bool:
    """Verify Resend webhook HMAC-SHA256 with replay protection — Svix spec.

    Svix signs ``{msg_id}.{timestamp}.{body}`` (not raw body alone).
    Timestamps outside a 5-minute tolerance window are rejected to prevent
    replay attacks. All three Svix headers (svix-id, svix-timestamp,
    svix-signature) are required — missing any header fails closed.

    The signing secret comes from ``RESEND_WEBHOOK_SECRET``. Svix secrets
    are prefixed ``whsec_``; the base64 payload after the prefix is the
    actual HMAC key.
    """
    if not signature_header or not msg_id or not timestamp:
        return False
    secret = os.environ.get("RESEND_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning(
            "[resend_client] RESEND_WEBHOOK_SECRET unset — rejecting webhook"
        )
        return False

    # Timestamp replay check
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        logger.warning("[resend_client] invalid svix-timestamp: %s", timestamp)
        return False
    now = int(time.time())
    if abs(now - ts) > WEBHOOK_TOLERANCE_SECONDS:
        logger.warning(
            "[resend_client] webhook timestamp outside tolerance: ts=%s now=%s",
            ts, now,
        )
        return False

    # Svix signing payload: "{msg_id}.{timestamp}.{body}"
    sign_payload = f"{msg_id}.{timestamp}.".encode() + raw_body

    # Svix secrets are prefixed "whsec_" — decode the base64 key after prefix
    key_material = secret.removeprefix("whsec_")
    try:
        key_bytes = base64.b64decode(key_material)
    except Exception:
        key_bytes = key_material.encode("utf-8")

    try:
        digest = hmac.new(key_bytes, sign_payload, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(digest).decode("ascii")
    except Exception as exc:
        logger.warning("[resend_client] HMAC compute failed: %s", exc)
        return False

    # Svix delivers multiple signatures separated by spaces, each shaped
    # ``v1,<base64>``. Strip the prefix and constant-time-compare each.
    candidates: list[str] = []
    for token in signature_header.replace("\t", " ").split():
        token = token.strip().rstrip(",")
        if not token:
            continue
        if token.startswith("v1,"):
            candidates.append(token[len("v1,"):])
        else:
            candidates.append(token)
    return any(
        hmac.compare_digest(expected_b64, c) for c in candidates
    )
