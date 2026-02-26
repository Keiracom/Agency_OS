"""
Contract: src/utils/test_auth.py
Purpose: Generate test authentication tokens for E2E testing
Layer: utils
Phase: Test Infrastructure

SECURITY: Only active when MOCK_CRM=true (test mode)
These tokens bypass normal authentication for E2E test flows.
"""

import time
from typing import Optional
from uuid import UUID

import jwt

from src.config.settings import settings


class TestAuthError(Exception):
    """Raised when test auth is not available."""

    pass


def generate_test_token(
    client_id: UUID,
    user_id: Optional[UUID] = None,
    role: str = "admin",
    expires_in: int = 3600,
) -> str:
    """
    Generate a test JWT token for E2E testing.

    SECURITY: Only works when MOCK_CRM=true

    Args:
        client_id: Client UUID to include in token
        user_id: Optional user UUID (defaults to generated test user)
        role: Role for the token (default: admin)
        expires_in: Token expiry in seconds (default: 1 hour)

    Returns:
        JWT token string

    Raises:
        TestAuthError: If MOCK_CRM is not enabled
    """
    if not settings.MOCK_CRM:
        raise TestAuthError(
            "Test authentication is only available when MOCK_CRM=true. "
            "Set MOCK_CRM=true in your environment to enable test mode."
        )

    # Use service key as JWT secret (same as Supabase uses)
    jwt_secret = settings.supabase_jwt_secret or settings.supabase_service_key
    if not jwt_secret:
        raise TestAuthError(
            "No JWT secret available. Set SUPABASE_JWT_SECRET or SUPABASE_SERVICE_KEY."
        )

    now = int(time.time())
    expires_at = now + expires_in

    # Create Supabase-compatible JWT payload
    payload = {
        "aud": "authenticated",
        "exp": expires_at,
        "iat": now,
        "iss": settings.supabase_url or "http://localhost:54321",
        "sub": str(user_id) if user_id else str(client_id),
        "email": f"test@client-{client_id}.example",
        "role": "authenticated",
        # Custom claims for Agency OS
        "app_metadata": {
            "client_id": str(client_id),
            "role": role,
        },
        "user_metadata": {
            "test_mode": True,
        },
    }

    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    return token


def is_test_mode_enabled() -> bool:
    """Check if test mode is enabled."""
    return settings.MOCK_CRM is True


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Only works when MOCK_CRM=true
# [x] Generates Supabase-compatible JWT
# [x] Includes client_id in app_metadata
# [x] Includes test_mode flag in user_metadata
# [x] Uses configurable expiry
# [x] Proper error handling when not in test mode
