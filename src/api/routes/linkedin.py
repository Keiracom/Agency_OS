"""
Contract: src/api/routes/linkedin.py
Purpose: API endpoints for LinkedIn connection via Unipile hosted auth
Layer: 5 - API routes
Phase: Unipile Migration - Hosted Auth (replaces HeyReach)

ENDPOINTS:
- GET /api/v1/linkedin/connect - Get hosted auth URL for LinkedIn connection
- GET /api/v1/linkedin/status - Get connection status
- POST /api/v1/linkedin/disconnect - Disconnect LinkedIn account
- POST /api/v1/linkedin/refresh - Refresh account status from Unipile

NOTE: No more email/password or 2FA endpoints! Unipile hosted auth handles all of that.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    CurrentUser,
    get_current_user_from_token,
    get_db_session,
)
from src.services.linkedin_connection_service import linkedin_connection_service

router = APIRouter(prefix="/linkedin", tags=["linkedin"])


# ============================================
# Pydantic Schemas
# ============================================


class LinkedInConnectUrlResponse(BaseModel):
    """Response with hosted auth URL for LinkedIn connection."""

    auth_url: str = Field(
        ...,
        description="Unipile hosted auth URL - redirect user to this URL",
    )
    status: str = Field(
        default="pending",
        description="Connection status",
    )
    message: str = Field(
        default="Redirect user to auth_url to connect LinkedIn",
        description="Instructions for frontend",
    )


class LinkedInStatusResponse(BaseModel):
    """LinkedIn connection status response."""

    status: str = Field(
        ...,
        description="Connection status: not_connected, pending, connected, failed, disconnected, credentials_required",
    )
    auth_method: Optional[str] = Field(
        default="hosted",
        description="Authentication method (hosted = Unipile hosted auth)",
    )
    profile_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    profile_name: Optional[str] = Field(None, description="LinkedIn display name")
    headline: Optional[str] = Field(None, description="LinkedIn headline")
    connection_count: Optional[int] = Field(None, description="Number of LinkedIn connections")
    connected_at: Optional[str] = Field(None, description="ISO timestamp when connected")
    error: Optional[str] = Field(None, description="Error message if failed")


class LinkedInDisconnectResponse(BaseModel):
    """Response from disconnect request."""

    status: str = Field(..., description="Should be 'disconnected'")


# ============================================
# Helper to get client_id
# ============================================


async def get_client_id_from_user(
    db: AsyncSession,
    user: CurrentUser,
) -> UUID:
    """
    Get the primary client_id for a user.

    For now, gets the first client the user is a member of.
    In the future, this could be based on a selected context.
    """
    from sqlalchemy import select
    from src.models.membership import Membership

    stmt = select(Membership.client_id).where(
        Membership.user_id == user.id,
        Membership.deleted_at.is_(None),
    ).limit(1)

    result = await db.execute(stmt)
    client_id = result.scalar_one_or_none()

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of any client",
        )

    return client_id


# ============================================
# Endpoints
# ============================================


@router.get(
    "/connect",
    response_model=LinkedInConnectUrlResponse,
    summary="Get LinkedIn connection URL",
    description="Generate Unipile hosted auth URL for LinkedIn connection",
)
async def get_connect_url(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInConnectUrlResponse:
    """
    Get Unipile hosted auth URL for LinkedIn connection.

    This replaces the old email/password flow:
    1. Frontend calls this endpoint
    2. Frontend redirects user to returned auth_url
    3. User logs into LinkedIn on Unipile's hosted page
    4. Unipile handles 2FA automatically
    5. Unipile sends webhook to our /webhooks/unipile/account
    6. User is redirected back to frontend success/failure page
    """
    client_id = await get_client_id_from_user(db, current_user)

    try:
        result = await linkedin_connection_service.get_connect_url(
            db=db,
            client_id=client_id,
        )
        return LinkedInConnectUrlResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate auth URL: {str(e)}",
        )


@router.get(
    "/status",
    response_model=LinkedInStatusResponse,
    summary="Get LinkedIn connection status",
    description="Get the current LinkedIn connection status for the client",
)
async def get_linkedin_status(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInStatusResponse:
    """
    Get LinkedIn connection status.

    Returns current status, profile info if connected,
    or error message if failed.

    Status values:
    - not_connected: Never connected
    - pending: Auth URL generated, waiting for user to complete
    - connected: Successfully connected via Unipile
    - failed: Connection failed
    - disconnected: User disconnected
    - credentials_required: Needs re-authentication (Unipile)
    """
    client_id = await get_client_id_from_user(db, current_user)

    result = await linkedin_connection_service.get_status(
        db=db,
        client_id=client_id,
    )
    return LinkedInStatusResponse(**result)


@router.post(
    "/disconnect",
    response_model=LinkedInDisconnectResponse,
    summary="Disconnect LinkedIn account",
    description="Remove LinkedIn connection from Unipile and local database",
)
async def disconnect_linkedin(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInDisconnectResponse:
    """
    Disconnect LinkedIn account.

    - Disconnects account from Unipile
    - Marks local record as disconnected
    - No credentials stored (Unipile hosted auth)
    """
    client_id = await get_client_id_from_user(db, current_user)

    try:
        result = await linkedin_connection_service.disconnect(
            db=db,
            client_id=client_id,
        )
        return LinkedInDisconnectResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect: {str(e)}",
        )


@router.post(
    "/refresh",
    response_model=LinkedInStatusResponse,
    summary="Refresh LinkedIn account status",
    description="Refresh account status from Unipile (check if re-auth needed)",
)
async def refresh_linkedin_status(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInStatusResponse:
    """
    Refresh LinkedIn account status from Unipile.

    Useful to check if:
    - Account needs re-authentication
    - Connection is still valid
    - Profile info has changed
    """
    client_id = await get_client_id_from_user(db, current_user)

    try:
        result = await linkedin_connection_service.refresh_account_status(
            db=db,
            client_id=client_id,
        )
        return LinkedInStatusResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh status: {str(e)}",
        )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] GET /connect endpoint (returns hosted auth URL)
# [x] GET /status endpoint
# [x] POST /disconnect endpoint
# [x] POST /refresh endpoint (new - refresh status from Unipile)
# [x] REMOVED: POST /connect with email/password (no longer needed)
# [x] REMOVED: POST /verify-2fa (Unipile handles 2FA)
# [x] Proper Pydantic schemas (updated for hosted auth)
# [x] Auth dependency
# [x] Client ID resolution
# [x] Error handling
# [x] Type hints
# [x] Docstrings
