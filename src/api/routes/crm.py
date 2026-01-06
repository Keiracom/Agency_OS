"""
FILE: src/api/routes/crm.py
TASK: CRM-009
PHASE: 24E - CRM Push
PURPOSE: API endpoints for CRM integration (HubSpot, Pipedrive, Close)

DEPENDENCIES:
- src/api/dependencies.py
- src/services/crm_push_service.py

ENDPOINTS:
- GET /api/v1/crm/config - Get current CRM configuration
- PUT /api/v1/crm/config - Update CRM configuration (pipeline, stage, owner)
- POST /api/v1/crm/connect/hubspot - Start HubSpot OAuth flow
- GET /api/v1/crm/callback/hubspot - HubSpot OAuth callback
- POST /api/v1/crm/connect/pipedrive - Connect Pipedrive with API key
- POST /api/v1/crm/connect/close - Connect Close with API key
- DELETE /api/v1/crm/disconnect - Disconnect CRM
- POST /api/v1/crm/test - Test CRM connection
- GET /api/v1/crm/pipelines - List available pipelines
- GET /api/v1/crm/stages/{pipeline_id} - List stages for a pipeline
- GET /api/v1/crm/users - List CRM users for owner dropdown
- GET /api/v1/crm/logs - Get CRM push logs
"""

import secrets
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    CurrentUser,
    get_current_user_from_token,
    get_db_session,
)
from src.config.settings import settings
from src.services.crm_push_service import (
    CRMConfig,
    CRMPipeline,
    CRMPushService,
    CRMStage,
    CRMUser,
)

router = APIRouter(prefix="/crm", tags=["crm"])


# ============================================
# Pydantic Schemas
# ============================================


class CRMConfigResponse(BaseModel):
    """CRM configuration response."""

    id: Optional[UUID] = None
    client_id: UUID
    crm_type: Optional[str] = None
    is_active: bool = False
    connection_status: str = "disconnected"
    connected_at: Optional[datetime] = None
    pipeline_id: Optional[str] = None
    pipeline_name: Optional[str] = None
    stage_id: Optional[str] = None
    stage_name: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    last_successful_push_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None


class CRMConfigUpdateRequest(BaseModel):
    """Request to update CRM configuration."""

    pipeline_id: Optional[str] = Field(None, description="Pipeline ID")
    pipeline_name: Optional[str] = Field(None, description="Pipeline display name")
    stage_id: Optional[str] = Field(None, description="Stage ID for new deals")
    stage_name: Optional[str] = Field(None, description="Stage display name")
    owner_id: Optional[str] = Field(None, description="Owner user ID")
    owner_name: Optional[str] = Field(None, description="Owner display name")
    owner_email: Optional[str] = Field(None, description="Owner email")


class HubSpotOAuthResponse(BaseModel):
    """Response with HubSpot OAuth URL."""

    oauth_url: str = Field(description="URL to redirect user for OAuth")
    state: str = Field(description="State parameter for CSRF protection")


class APIKeyConnectRequest(BaseModel):
    """Request to connect CRM with API key."""

    api_key: str = Field(min_length=10, description="CRM API key")


class TestConnectionResponse(BaseModel):
    """Response from test connection."""

    success: bool
    message: str
    error: Optional[str] = None


class PipelineResponse(BaseModel):
    """Pipeline with stages."""

    id: str
    name: str
    stages: list["StageResponse"]


class StageResponse(BaseModel):
    """Stage within a pipeline."""

    id: str
    name: str
    probability: Optional[float] = None


class UserResponse(BaseModel):
    """CRM user for owner dropdown."""

    id: str
    name: str
    email: Optional[str] = None


class CRMPushLogResponse(BaseModel):
    """CRM push log entry."""

    id: UUID
    operation: str
    status: str
    lead_id: Optional[UUID] = None
    meeting_id: Optional[UUID] = None
    crm_contact_id: Optional[str] = None
    crm_deal_id: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime


# ============================================
# Helper Functions
# ============================================


async def get_user_client_id(
    user: CurrentUser,
    db: AsyncSession,
) -> UUID:
    """Get the client ID for the current user."""
    # Get user's primary client from membership
    result = await db.execute(
        text("""
            SELECT client_id FROM memberships
            WHERE user_id = :user_id
            AND deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT 1
        """),
        {"user_id": str(user.id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client found for user",
        )

    return row.client_id


# ============================================
# CRM Configuration Endpoints
# ============================================


@router.get("/config", response_model=CRMConfigResponse)
async def get_crm_config(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Get current CRM configuration for the user's client."""
    client_id = await get_user_client_id(user, db)

    result = await db.execute(
        text("""
            SELECT * FROM client_crm_configs
            WHERE client_id = :client_id
        """),
        {"client_id": str(client_id)},
    )
    row = result.fetchone()

    if not row:
        return CRMConfigResponse(
            client_id=client_id,
            is_active=False,
            connection_status="disconnected",
        )

    return CRMConfigResponse(
        id=row.id,
        client_id=row.client_id,
        crm_type=row.crm_type,
        is_active=row.is_active,
        connection_status=row.connection_status,
        connected_at=row.connected_at,
        pipeline_id=row.pipeline_id,
        pipeline_name=row.pipeline_name,
        stage_id=row.stage_id,
        stage_name=row.stage_name,
        owner_id=row.owner_id,
        owner_name=row.owner_name,
        owner_email=row.owner_email,
        last_successful_push_at=row.last_successful_push_at,
        last_error=row.last_error,
        last_error_at=row.last_error_at,
    )


@router.put("/config", response_model=CRMConfigResponse)
async def update_crm_config(
    request: CRMConfigUpdateRequest,
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Update CRM configuration (pipeline, stage, owner)."""
    client_id = await get_user_client_id(user, db)

    # Check if config exists
    result = await db.execute(
        text("""
            SELECT id FROM client_crm_configs
            WHERE client_id = :client_id AND is_active = true
        """),
        {"client_id": str(client_id)},
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active CRM connection. Connect a CRM first.",
        )

    # Update config
    await db.execute(
        text("""
            UPDATE client_crm_configs
            SET pipeline_id = COALESCE(:pipeline_id, pipeline_id),
                pipeline_name = COALESCE(:pipeline_name, pipeline_name),
                stage_id = COALESCE(:stage_id, stage_id),
                stage_name = COALESCE(:stage_name, stage_name),
                owner_id = COALESCE(:owner_id, owner_id),
                owner_name = COALESCE(:owner_name, owner_name),
                owner_email = COALESCE(:owner_email, owner_email),
                updated_at = NOW()
            WHERE client_id = :client_id
        """),
        {
            "client_id": str(client_id),
            "pipeline_id": request.pipeline_id,
            "pipeline_name": request.pipeline_name,
            "stage_id": request.stage_id,
            "stage_name": request.stage_name,
            "owner_id": request.owner_id,
            "owner_name": request.owner_name,
            "owner_email": request.owner_email,
        },
    )
    await db.commit()

    # Return updated config
    return await get_crm_config(user, db)


# ============================================
# HubSpot OAuth Flow
# ============================================


# Store OAuth states temporarily (in production, use Redis)
_oauth_states: dict[str, dict] = {}


@router.post("/connect/hubspot", response_model=HubSpotOAuthResponse)
async def start_hubspot_oauth(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Start HubSpot OAuth flow. Returns URL to redirect user."""
    client_id = await get_user_client_id(user, db)

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "client_id": str(client_id),
        "user_id": str(user.id),
        "created_at": datetime.utcnow().isoformat(),
    }

    # Build OAuth URL
    crm_service = CRMPushService(db)
    oauth_url = crm_service.get_hubspot_oauth_url(state)
    await crm_service.close()

    return HubSpotOAuthResponse(oauth_url=oauth_url, state=state)


@router.get("/callback/hubspot")
async def hubspot_oauth_callback(
    code: str = Query(..., description="Authorization code from HubSpot"),
    state: str = Query(..., description="State parameter for CSRF"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    HubSpot OAuth callback. Exchanges code for tokens and saves config.
    Redirects to frontend settings page.
    """
    # Verify state
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    client_id = UUID(state_data["client_id"])
    user_id = UUID(state_data["user_id"])

    # Exchange code for tokens
    crm_service = CRMPushService(db)
    try:
        tokens = await crm_service.exchange_hubspot_code(code)

        # Get account info from tokens
        portal_id = tokens.get("hub_id") or tokens.get("portal_id")

        # Calculate token expiration
        expires_in = tokens.get("expires_in", 1800)  # Default 30 min
        expires_at = datetime.utcnow()
        from datetime import timedelta
        expires_at = expires_at + timedelta(seconds=expires_in)

        # Save config
        config = CRMConfig(
            id=uuid4(),
            client_id=client_id,
            crm_type="hubspot",
            oauth_access_token=tokens["access_token"],
            oauth_refresh_token=tokens.get("refresh_token"),
            oauth_expires_at=expires_at,
            hubspot_portal_id=str(portal_id) if portal_id else None,
            is_active=True,
        )

        await crm_service.save_config(config)

    finally:
        await crm_service.close()

    # Redirect to frontend settings page
    frontend_url = "https://agency-os-liart.vercel.app"  # TODO: Make configurable
    return RedirectResponse(
        url=f"{frontend_url}/settings/integrations?crm=hubspot&status=connected",
        status_code=status.HTTP_302_FOUND,
    )


# ============================================
# API Key CRM Connections (Pipedrive, Close)
# ============================================


@router.post("/connect/pipedrive", response_model=CRMConfigResponse)
async def connect_pipedrive(
    request: APIKeyConnectRequest,
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Connect Pipedrive with API key."""
    client_id = await get_user_client_id(user, db)

    # Create config
    config = CRMConfig(
        id=uuid4(),
        client_id=client_id,
        crm_type="pipedrive",
        api_key=request.api_key,
        is_active=True,
    )

    crm_service = CRMPushService(db)
    try:
        # Test connection first
        success, error = await crm_service.test_connection(config)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to Pipedrive: {error}",
            )

        # Save config
        await crm_service.save_config(config)
    finally:
        await crm_service.close()

    return await get_crm_config(user, db)


@router.post("/connect/close", response_model=CRMConfigResponse)
async def connect_close(
    request: APIKeyConnectRequest,
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Connect Close CRM with API key."""
    client_id = await get_user_client_id(user, db)

    # Create config
    config = CRMConfig(
        id=uuid4(),
        client_id=client_id,
        crm_type="close",
        api_key=request.api_key,
        is_active=True,
    )

    crm_service = CRMPushService(db)
    try:
        # Test connection first
        success, error = await crm_service.test_connection(config)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to Close: {error}",
            )

        # Save config
        await crm_service.save_config(config)
    finally:
        await crm_service.close()

    return await get_crm_config(user, db)


# ============================================
# Disconnect & Test
# ============================================


@router.delete("/disconnect")
async def disconnect_crm(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Disconnect CRM integration."""
    client_id = await get_user_client_id(user, db)

    crm_service = CRMPushService(db)
    try:
        await crm_service.disconnect(client_id)
    finally:
        await crm_service.close()

    return {"success": True, "message": "CRM disconnected"}


@router.post("/test", response_model=TestConnectionResponse)
async def test_crm_connection(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Test CRM connection."""
    client_id = await get_user_client_id(user, db)

    crm_service = CRMPushService(db)
    try:
        config = await crm_service.get_config(client_id)
        if not config:
            return TestConnectionResponse(
                success=False,
                message="No CRM configured",
                error="Connect a CRM first",
            )

        success, error = await crm_service.test_connection(config)

        if success:
            return TestConnectionResponse(
                success=True,
                message=f"Successfully connected to {config.crm_type.capitalize()}",
            )
        else:
            return TestConnectionResponse(
                success=False,
                message="Connection test failed",
                error=error,
            )
    finally:
        await crm_service.close()


# ============================================
# CRM Data Endpoints (Pipelines, Stages, Users)
# ============================================


@router.get("/pipelines", response_model=list[PipelineResponse])
async def get_crm_pipelines(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Get available pipelines from connected CRM."""
    client_id = await get_user_client_id(user, db)

    crm_service = CRMPushService(db)
    try:
        config = await crm_service.get_config(client_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CRM configured",
            )

        pipelines = await crm_service.get_pipelines(config)

        return [
            PipelineResponse(
                id=p.id,
                name=p.name,
                stages=[
                    StageResponse(id=s.id, name=s.name, probability=s.probability)
                    for s in p.stages
                ],
            )
            for p in pipelines
        ]
    finally:
        await crm_service.close()


@router.get("/stages/{pipeline_id}", response_model=list[StageResponse])
async def get_pipeline_stages(
    pipeline_id: str,
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Get stages for a specific pipeline."""
    client_id = await get_user_client_id(user, db)

    crm_service = CRMPushService(db)
    try:
        config = await crm_service.get_config(client_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CRM configured",
            )

        pipelines = await crm_service.get_pipelines(config)

        # Find the requested pipeline
        for pipeline in pipelines:
            if pipeline.id == pipeline_id:
                return [
                    StageResponse(id=s.id, name=s.name, probability=s.probability)
                    for s in pipeline.stages
                ]

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found",
        )
    finally:
        await crm_service.close()


@router.get("/users", response_model=list[UserResponse])
async def get_crm_users(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
):
    """Get available users from connected CRM (for owner dropdown)."""
    client_id = await get_user_client_id(user, db)

    crm_service = CRMPushService(db)
    try:
        config = await crm_service.get_config(client_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CRM configured",
            )

        users = await crm_service.get_users(config)

        return [UserResponse(id=u.id, name=u.name, email=u.email) for u in users]
    finally:
        await crm_service.close()


# ============================================
# CRM Push Logs
# ============================================


@router.get("/logs", response_model=list[CRMPushLogResponse])
async def get_crm_push_logs(
    user: CurrentUser = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get CRM push logs for the user's client."""
    client_id = await get_user_client_id(user, db)

    result = await db.execute(
        text("""
            SELECT id, operation, status, lead_id, meeting_id,
                   crm_contact_id, crm_deal_id, error_message,
                   duration_ms, created_at
            FROM crm_push_log
            WHERE client_id = :client_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"client_id": str(client_id), "limit": limit, "offset": offset},
    )
    rows = result.fetchall()

    return [
        CRMPushLogResponse(
            id=row.id,
            operation=row.operation,
            status=row.status,
            lead_id=row.lead_id,
            meeting_id=row.meeting_id,
            crm_contact_id=row.crm_contact_id,
            crm_deal_id=row.crm_deal_id,
            error_message=row.error_message,
            duration_ms=row.duration_ms,
            created_at=row.created_at,
        )
        for row in rows
    ]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] GET /crm/config - Get current config
# [x] PUT /crm/config - Update config
# [x] POST /crm/connect/hubspot - Start OAuth
# [x] GET /crm/callback/hubspot - OAuth callback
# [x] POST /crm/connect/pipedrive - Connect with API key
# [x] POST /crm/connect/close - Connect with API key
# [x] DELETE /crm/disconnect - Disconnect
# [x] POST /crm/test - Test connection
# [x] GET /crm/pipelines - List pipelines
# [x] GET /crm/stages/{pipeline_id} - List stages
# [x] GET /crm/users - List users
# [x] GET /crm/logs - Push audit logs
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Pydantic response models
# [x] OAuth state management
# [x] Error handling
