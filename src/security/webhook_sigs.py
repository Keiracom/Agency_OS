"""
Contract: src/security/webhook_sigs.py
Purpose: Per-provider HMAC-SHA256 signature verification for inbound webhook
         and operator-action requests. Canonical entrypoint: verify_signature.
Layer:   1 - security (pure Python; no framework dependency beyond hmac/hashlib)
Imports: stdlib (hmac, hashlib, os)
Consumers: src/api/routes/outreach_webhooks.py (Salesforge / Unipile /
           ElevenAgents), src/api/routes/approvals.py, src/api/routes/campaigns.py

Env var -> HTTP header mapping:
  Salesforge      SALESFORGE_WEBHOOK_SECRET     X-Salesforge-Signature
  Unipile         UNIPILE_WEBHOOK_SECRET        X-Unipile-Signature
  ElevenAgents    ELEVENAGENTS_WEBHOOK_SECRET   X-ElevenAgents-Signature
  Operator        OPERATOR_WEBHOOK_SECRET       X-Signature

Design:
  - verify_signature(secret_env, payload, signature) -> bool: pure fn, no raise.
  - require_signature(request, provider) -> bytes: FastAPI-bound helper that
    reads the raw body + header, calls verify_signature, raises 401 on fail.
  - Missing secret in env -> rejection (fail loud in prod). Dev callers can
    set the secret to an empty string to opt out (explicit).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    secret_env: str
    header: str


PROVIDERS: dict[str, ProviderSpec] = {
    "salesforge": ProviderSpec(
        name="salesforge",
        secret_env="SALESFORGE_WEBHOOK_SECRET",
        header="X-Salesforge-Signature",
    ),
    "unipile": ProviderSpec(
        name="unipile",
        secret_env="UNIPILE_WEBHOOK_SECRET",
        header="X-Unipile-Signature",
    ),
    "elevenagents": ProviderSpec(
        name="elevenagents",
        secret_env="ELEVENAGENTS_WEBHOOK_SECRET",
        header="X-ElevenAgents-Signature",
    ),
    "operator": ProviderSpec(
        name="operator",
        secret_env="OPERATOR_WEBHOOK_SECRET",
        header="X-Signature",
    ),
}


class SignatureError(Exception):
    """Raised when callers want an exception path rather than a bool."""


def compute_signature(secret: str, payload: bytes) -> str:
    """Compute the canonical hex HMAC-SHA256 of payload."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(
    secret_env: str,
    payload: bytes,
    signature: str | None,
) -> bool:
    """Pure verify. Returns True iff signature matches HMAC(secret_env, payload).

    Returns False on:
      - missing env var (secret unset or empty)
      - missing or empty signature header
      - mismatch (constant-time compared)
    """
    secret = os.environ.get(secret_env) or ""
    if not secret:
        logger.warning("webhook signature rejected — %s not set", secret_env)
        return False
    if not signature:
        return False
    expected = compute_signature(secret, payload)
    return hmac.compare_digest(expected, signature)


def verify_provider(
    provider: str,
    payload: bytes,
    signature: str | None,
) -> bool:
    spec = PROVIDERS.get(provider.lower())
    if spec is None:
        raise SignatureError(f"unknown provider: {provider!r}")
    return verify_signature(spec.secret_env, payload, signature)


async def require_signature(request, provider: str) -> bytes:
    """FastAPI-bound helper. Reads raw body + provider header, verifies HMAC,
    raises fastapi.HTTPException(401) on failure. Returns the raw body so the
    caller does not need to await request.body() a second time."""
    from fastapi import HTTPException, status  # local import: keeps module framework-agnostic

    spec = PROVIDERS.get(provider.lower())
    if spec is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            f"unknown provider: {provider!r}",
        )
    raw = await request.body()
    sig = request.headers.get(spec.header)
    if not verify_signature(spec.secret_env, raw, sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")
    return raw


def require_header_signature(
    raw_body: bytes,
    signature: str | None,
    provider: str,
) -> None:
    """Sync variant for callers that already have the body (e.g. FastAPI
    dependency that captured body upstream). Raises HTTPException(401) on
    failure."""
    from fastapi import HTTPException, status

    if not verify_provider(provider, raw_body, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature")
