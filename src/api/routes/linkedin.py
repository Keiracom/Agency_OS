"""
Contract: src/api/routes/linkedin.py
Purpose: API endpoints for LinkedIn credential connection
Layer: 5 - API routes
Phase: 24H - LinkedIn Credential Connection

ENDPOINTS:
- POST /api/v1/linkedin/connect - Start LinkedIn connection
- POST /api/v1/linkedin/verify-2fa - Submit 2FA verification code
- GET /api/v1/linkedin/status - Get connection status
- POST /api/v1/linkedin/disconnect - Disconnect LinkedIn account
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


class LinkedInConnectRequest(BaseModel):
    """Request to start LinkedIn connection."""

    linkedin_email: str = Field(
        ...,
        description="LinkedIn account email",
        min_length=5,
        max_length=255,
    )
    linkedin_password: str = Field(
        ...,
        description="LinkedIn account password",
        min_length=6,
        max_length=255,
    )


class TwoFactorRequest(BaseModel):
    """Request to submit 2FA verification code."""

    code: str = Field(
        ...,
        description="2FA verification code",
        min_length=4,
        max_length=10,
    )


class LinkedInStatusResponse(BaseModel):
    """LinkedIn connection status response."""

    status: str = Field(
        ...,
        description="Connection status: not_connected, pending, connecting, awaiting_2fa, connected, failed, disconnected",
    )
    profile_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    profile_name: Optional[str] = Field(None, description="LinkedIn display name")
    headline: Optional[str] = Field(None, description="LinkedIn headline")
    connection_count: Optional[int] = Field(None, description="Number of LinkedIn connections")
    connected_at: Optional[str] = Field(None, description="ISO timestamp when connected")
    error: Optional[str] = Field(None, description="Error message if failed")
    two_fa_method: Optional[str] = Field(None, description="2FA method if awaiting verification")


class LinkedInConnectResponse(BaseModel):
    """Response from LinkedIn connection attempt."""

    status: str = Field(
        ...,
        description="Result: connected, awaiting_2fa, or failed",
    )
    profile_url: Optional[str] = Field(None, description="LinkedIn profile URL if connected")
    profile_name: Optional[str] = Field(None, description="LinkedIn name if connected")
    method: Optional[str] = Field(None, description="2FA method if awaiting verification")
    message: Optional[str] = Field(None, description="Message for user")
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


@router.post(
    "/connect",
    response_model=LinkedInConnectResponse,
    summary="Start LinkedIn connection",
    description="Encrypt and store LinkedIn credentials, initiate HeyReach connection",
)
async def connect_linkedin(
    request: LinkedInConnectRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInConnectResponse:
    """
    Start LinkedIn connection process.

    - Encrypts credentials with AES-256
    - Stores in database
    - Initiates HeyReach account connection
    - Returns status (may require 2FA)
    """
    client_id = await get_client_id_from_user(db, current_user)

    try:
        result = await linkedin_connection_service.start_connection(
            db=db,
            client_id=client_id,
            linkedin_email=request.linkedin_email,
            linkedin_password=request.linkedin_password,
        )
        return LinkedInConnectResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect LinkedIn: {str(e)}",
        )


@router.post(
    "/verify-2fa",
    response_model=LinkedInConnectResponse,
    summary="Submit 2FA verification code",
    description="Complete LinkedIn connection by submitting the 2FA code",
)
async def verify_2fa(
    request: TwoFactorRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInConnectResponse:
    """
    Submit 2FA verification code.

    - Retrieves stored credentials
    - Submits code to HeyReach
    - Marks connection as complete if successful
    """
    client_id = await get_client_id_from_user(db, current_user)

    try:
        result = await linkedin_connection_service.submit_2fa_code(
            db=db,
            client_id=client_id,
            code=request.code,
        )
        return LinkedInConnectResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify 2FA: {str(e)}",
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
    description="Remove LinkedIn connection from HeyReach and local database",
)
async def disconnect_linkedin(
    db: AsyncSession = Depends(get_db_session),
    current_user: CurrentUser = Depends(get_current_user_from_token),
) -> LinkedInDisconnectResponse:
    """
    Disconnect LinkedIn account.

    - Removes sender from HeyReach
    - Marks local record as disconnected
    - Credentials remain encrypted but connection is inactive
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


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] POST /connect endpoint
# [x] POST /verify-2fa endpoint
# [x] GET /status endpoint
# [x] POST /disconnect endpoint
# [x] Proper Pydantic schemas
# [x] Auth dependency
# [x] Client ID resolution
# [x] Error handling
# [x] Type hints
# [x] Docstrings
