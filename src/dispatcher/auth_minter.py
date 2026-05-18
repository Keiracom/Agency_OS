"""KEI-209 — Auth minter for Dispatcher agent sessions.

Mints short-lived (15-minute TTL) HS256 JWTs identifying an agent session to
the Dispatcher API. Distinct from `container_jwt.py` (KEI-164) which issues
longer-lived tokens for managed-container spawns: this component identifies
an *agent session* (tenant_id + callsign + session_id) and is auto-reissued
by the Dispatcher before expiry.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 15 * 60


def _signing_secret() -> str:
    """Read DISPATCHER_JWT_SECRET; fail fast if unset.

    No dev fallback — every environment must provide an explicit secret per
    KEI-209 acceptance criterion "No hardcoded secrets".
    """
    secret = os.environ.get("DISPATCHER_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("DISPATCHER_JWT_SECRET must be set")
    return secret


def mint_token(tenant_id: str, callsign: str, session_id: str) -> str:
    """Mint a short-lived agent-session JWT.

    Payload claims: tenant_id, callsign, session_id, iat, exp.
    Raises ValueError on any blank required field — prevents anonymous tokens.
    """
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id is required and must be non-blank")
    if not callsign or not callsign.strip():
        raise ValueError("callsign is required and must be non-blank")
    if not session_id or not session_id.strip():
        raise ValueError("session_id is required and must be non-blank")
    now = datetime.now(UTC)
    payload: dict = {
        "tenant_id": tenant_id,
        "callsign": callsign,
        "session_id": session_id,
        "iat": now,
        "exp": now + timedelta(seconds=TOKEN_TTL_SECONDS),
    }
    return jwt.encode(payload, _signing_secret(), algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verify + decode an agent-session JWT.

    Returns the decoded claims dict on success, or None on any verification
    failure (expired, tampered, wrong secret, malformed). Callers must check
    for None before trusting the result.
    """
    try:
        return jwt.decode(token, _signing_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.InvalidTokenError as exc:
        logger.debug("auth_minter verify_token rejected: %s", exc)
        return None
