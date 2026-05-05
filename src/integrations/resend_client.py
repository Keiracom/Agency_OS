"""src/integrations/resend_client.py — thin Resend SDK wrapper.

Task #20 — Email Integration Backend (aiden/email-backend).

Single send entrypoint + HMAC verification helper for inbound webhooks.
The Resend Python SDK (`pip install resend`) is the canonical client.
We keep the wrapper minimal so route handlers don't need to know about
SDK shape.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
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


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify Resend webhook HMAC-SHA256.

    Resend sends `svix-signature` (the underlying provider). We accept any
    header value of shape `v1,<base64>` or `<hex>` for forward-compat with
    plain HMAC senders. Returns False on any error.

    The signing secret comes from `RESEND_WEBHOOK_SECRET`. If unset, this
    function returns False — the route handler converts that to 401.
    """
    if not signature_header:
        return False
    secret = os.environ.get("RESEND_WEBHOOK_SECRET", "")
    if not secret:
        logger.warning(
            "[resend_client] RESEND_WEBHOOK_SECRET unset — rejecting webhook"
        )
        return False
    try:
        expected = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256,
        ).hexdigest()
    except Exception as exc:
        logger.warning("[resend_client] HMAC compute failed: %s", exc)
        return False
    # Accept either `v1,<sig>` (svix-style, sig portion) or the plain hex
    # digest. Constant-time compare to defeat timing attacks.
    candidates: list[str] = []
    for token in signature_header.split(","):
        token = token.strip()
        if "=" in token:
            token = token.split("=", 1)[1]
        candidates.append(token)
    candidates.append(signature_header.strip())
    return any(hmac.compare_digest(expected, c) for c in candidates)
