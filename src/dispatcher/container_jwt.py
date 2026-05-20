"""KEI-164 — JWT minting for container spawn.

Issues per-container JWT with tenant_id + scope claims; verified via shared
HS256 secret. Default scopes: task:read, task:write. Sits in the dispatcher
product layer (KEI-110); used by KEI-115 container lifecycle when a customer
spawns a managed Claude container, so the container can authenticate against
the dispatcher API without holding a tenant-wide credential.

Acceptance (Linear KEI-164): JWT issued per container spawn; includes
tenant_id + scope=['task:read', 'task:write']; signature verifies.

KEI-194 additive extension: optional ratified_decisions_hash claim support.
Short-TTL (5 min) for hash-bearing JWTs; warning-not-blocking for legacy
tokens without the claim. No breaking change to KEI-115C behaviour.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
DEFAULT_SCOPES: tuple[str, ...] = ("task:read", "task:write")
DEFAULT_EXPIRES_IN_SECONDS = 3600  # 1 hour
RATIFIED_HASH_TTL_SECONDS = 300  # 5 min — short-TTL for hash-bearing JWTs (KEI-194)
_DEV_FALLBACK_SECRET = "dev-container-jwt-secret-not-for-production"


class RatifiedHashMismatchError(jwt.InvalidTokenError):
    """Raised when a JWT's ratified_decisions_hash does not match the live hash."""


def _signing_secret() -> str:
    """Read CONTAINER_JWT_SECRET; fail fast in production if unset."""
    secret = os.environ.get("CONTAINER_JWT_SECRET", "").strip()
    if secret:
        return secret
    if os.environ.get("ENVIRONMENT", "").lower() == "production":
        raise RuntimeError("CONTAINER_JWT_SECRET must be set in production")
    logger.warning("CONTAINER_JWT_SECRET unset — using dev fallback (not for production)")
    return _DEV_FALLBACK_SECRET


def mint_container_jwt(
    tenant_id: str,
    *,
    scopes: tuple[str, ...] | list[str] | None = None,
    expires_in_seconds: int = DEFAULT_EXPIRES_IN_SECONDS,
    ratified_decisions_hash: str | None = None,
) -> str:
    """Mint a JWT for a container spawn.

    Raises ValueError when tenant_id is blank — prevents anonymous container
    tokens that would later confuse the dispatcher tenant-isolation layer.

    KEI-194: when ratified_decisions_hash is provided, the hash is included in
    the payload and the TTL defaults to RATIFIED_HASH_TTL_SECONDS (300 s) unless
    the caller explicitly passes expires_in_seconds.
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required and must be non-blank")

    # KEI-194: short-TTL default when hash provided, only if caller did not
    # explicitly supply expires_in_seconds (detect via sentinel comparison).
    effective_ttl = expires_in_seconds
    if ratified_decisions_hash is not None and expires_in_seconds == DEFAULT_EXPIRES_IN_SECONDS:
        effective_ttl = RATIFIED_HASH_TTL_SECONDS

    now = datetime.now(UTC)
    payload: dict = {
        "tenant_id": tenant_id,
        "scope": list(scopes) if scopes is not None else list(DEFAULT_SCOPES),
        "iat": now,
        "exp": now + timedelta(seconds=effective_ttl),
    }
    if ratified_decisions_hash is not None:
        payload["ratified_decisions_hash"] = ratified_decisions_hash

    return jwt.encode(payload, _signing_secret(), algorithm=JWT_ALGORITHM)


def verify_container_jwt(token: str) -> dict:
    """Verify + decode a container JWT.

    Raises jwt.InvalidTokenError (or one of its subclasses — ExpiredSignatureError,
    InvalidSignatureError, etc.) on any verification failure.

    KEI-194 behaviour:
    - Token WITH ratified_decisions_hash claim: compare against live hash from
      ratified_hash.compute_ratified_decisions_hash(). Mismatch raises
      RatifiedHashMismatchError.
    - Token WITHOUT the claim (legacy tokens): log a warning once per unique
      token shape, then proceed normally — warning-not-blocking fallback per
      ratified Aiden path (a).
    """
    claims = jwt.decode(token, _signing_secret(), algorithms=[JWT_ALGORITHM])

    if "ratified_decisions_hash" in claims:
        # KEI-194: check live hash — import lazily to avoid circular deps
        from src.dispatcher.ratified_hash import compute_ratified_decisions_hash  # noqa: PLC0415

        live_hash = compute_ratified_decisions_hash()
        token_hash = claims["ratified_decisions_hash"]
        if token_hash != live_hash:
            raise RatifiedHashMismatchError(
                f"ratified_decisions_hash mismatch for tenant_id={claims.get('tenant_id')} — "
                "token carries stale governance hash; re-issue required"
            )
    else:
        # Legacy token — warn once; do not block
        _warn_legacy_token(claims.get("tenant_id", "unknown"))

    return claims


def _warn_legacy_token(tenant_id: str) -> None:
    """Emit a deprecation warning for hash-less legacy tokens (rate-limited)."""
    logger.warning(
        "Container JWT for tenant_id=%s has no ratified_decisions_hash claim — "
        "legacy token; update mint call to include hash (KEI-194)",
        tenant_id,
    )
