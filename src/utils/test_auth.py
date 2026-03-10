"""
Contract: src/utils/test_auth.py
Purpose: Generate test authentication tokens for E2E testing
Layer: utils
Phase: Test Infrastructure

SECURITY: Only active when MOCK_CRM=true (test mode)
These tokens bypass normal authentication for E2E test flows.
"""

import logging
import time
from uuid import UUID

import jwt
from sqlalchemy import text

from src.config.settings import settings
from src.integrations.supabase import get_db_session

logger = logging.getLogger(__name__)


class TestAuthError(Exception):
    """Raised when test auth is not available."""

    pass


async def _ensure_test_user_exists(client_id: UUID) -> UUID:
    """
    Ensure test user and membership exist in database.

    Creates auth.users and memberships records if they don't exist.
    Uses client_id as user_id for simplicity.

    Args:
        client_id: Client UUID to create test user for

    Returns:
        user_id (UUID) for the test user
    """
    user_id = client_id  # Reuse client_id as user_id for test users

    try:
        async with get_db_session() as db:
            # Create test user in auth.users (ON CONFLICT DO NOTHING if exists)
            try:
                await db.execute(
                    text("""
                        INSERT INTO auth.users (id, email, role, aud, created_at, updated_at)
                        VALUES (:id, :email, 'authenticated', 'authenticated', NOW(), NOW())
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": str(user_id),
                        "email": f"test@client-{client_id}.example",
                    },
                )
            except Exception as e:
                # Silently skip if user already exists
                logger.debug(f"Test user insert skipped (may already exist): {e}")

            # Create membership (with accepted_at so it's immediately usable)
            try:
                await db.execute(
                    text("""
                        INSERT INTO memberships (user_id, client_id, role, accepted_at, created_at, updated_at)
                        VALUES (:user_id, :client_id, 'admin', NOW(), NOW(), NOW())
                        ON CONFLICT (user_id, client_id) DO UPDATE SET accepted_at = NOW(), updated_at = NOW()
                    """),
                    {
                        "user_id": str(user_id),
                        "client_id": str(client_id),
                    },
                )
            except Exception as e:
                # Silently skip if membership already exists
                logger.debug(f"Membership insert skipped (may already exist): {e}")

            await db.commit()
            logger.info(f"Created test user and membership for client {client_id}")

    except Exception as e:
        # Log but don't fail - token generation can proceed
        logger.warning(f"Could not ensure test user exists: {e}")

    return user_id


async def generate_test_token(
    client_id: UUID,
    user_id: UUID | None = None,
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

    # Ensure test user exists in database (only when MOCK_CRM=true)
    if user_id is None:
        user_id = await _ensure_test_user_exists(client_id)

    now = int(time.time())
    expires_at = now + expires_in

    # Create Supabase-compatible JWT payload
    payload = {
        "aud": "authenticated",
        "exp": expires_at,
        "iat": now,
        "iss": settings.supabase_url or "http://localhost:54321",
        "sub": str(user_id),
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
