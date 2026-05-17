"""KEI-164 — JWT minting for container spawn.

Issues per-container JWT with tenant_id + scope claims; verified via shared
HS256 secret. Default scopes: task:read, task:write. Sits in the dispatcher
product layer (KEI-110); used by KEI-115 container lifecycle when a customer
spawns a managed Claude container, so the container can authenticate against
the dispatcher API without holding a tenant-wide credential.

Acceptance (Linear KEI-164): JWT issued per container spawn; includes
tenant_id + scope=['task:read', 'task:write']; signature verifies.
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
_DEV_FALLBACK_SECRET = "dev-container-jwt-secret-not-for-production"


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
) -> str:
    """Mint a JWT for a container spawn.

    Raises ValueError when tenant_id is blank — prevents anonymous container
    tokens that would later confuse the dispatcher tenant-isolation layer.
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required and must be non-blank")
    now = datetime.now(UTC)
    payload: dict = {
        "tenant_id": tenant_id,
        "scope": list(scopes) if scopes is not None else list(DEFAULT_SCOPES),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in_seconds),
    }
    return jwt.encode(payload, _signing_secret(), algorithm=JWT_ALGORITHM)


def verify_container_jwt(token: str) -> dict:
    """Verify + decode a container JWT.

    Raises jwt.InvalidTokenError (or one of its subclasses — ExpiredSignatureError,
    InvalidSignatureError, etc.) on any verification failure.
    """
    return jwt.decode(token, _signing_secret(), algorithms=[JWT_ALGORITHM])
