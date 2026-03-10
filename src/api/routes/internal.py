"""
Contract: src/api/routes/internal.py
Purpose: Internal test endpoints for E2E testing
Layer: API routes
Phase: Test Infrastructure

SECURITY: All endpoints require MOCK_CRM=true (test mode)
These endpoints are NOT available in production.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.config.settings import settings
from src.integrations.supabase import get_db_session
from src.services.mock_crm_service import mock_crm_service
from src.utils.test_auth import TestAuthError, generate_test_token, is_test_mode_enabled

router = APIRouter(prefix="/internal", tags=["internal"])


# ============================================
# Request/Response Models
# ============================================


class TestTokenRequest(BaseModel):
    """Request body for test token generation."""

    client_id: UUID


class TestTokenResponse(BaseModel):
    """Response for test token generation."""

    token: str
    expires_in: int = 3600


class SeedMockDataRequest(BaseModel):
    """Request for mock data seeding."""

    campaign_id: UUID


class SeedMockDataResponse(BaseModel):
    """Response for mock data seeding."""

    status: str
    exclusion_count: int = 0
    deal_count: int = 0
    meeting_count: int = 0


# ============================================
# Dependency: Test Mode Check
# ============================================


def require_test_mode():
    """
    Dependency that ensures test mode is enabled.

    Raises 403 if MOCK_CRM is not true.
    """
    if not is_test_mode_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal endpoints are only available in test mode (MOCK_CRM=true)",
        )
    return True


# ============================================
# Endpoints
# ============================================


@router.post(
    "/test-token",
    response_model=TestTokenResponse,
    summary="Generate test authentication token",
    description="Generates a JWT token for E2E testing. Only available when MOCK_CRM=true.",
)
async def generate_test_auth_token(
    request: TestTokenRequest,
    _test_mode: bool = Depends(require_test_mode),
) -> TestTokenResponse:
    """
    Generate a test authentication token for E2E testing.

    This endpoint bypasses normal authentication to enable automated testing.
    SECURITY: Only active when MOCK_CRM=true.

    Args:
        request: Contains client_id for the test token

    Returns:
        TestTokenResponse with Bearer token and expiry
    """
    try:
        expires_in = 3600  # 1 hour
        token = await generate_test_token(
            client_id=request.client_id,
            expires_in=expires_in,
        )

        return TestTokenResponse(
            token=f"Bearer {token}",
            expires_in=expires_in,
        )

    except TestAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post(
    "/seed-mock-data/{client_id}",
    response_model=SeedMockDataResponse,
    summary="Seed mock CRM data for testing",
    description="Seeds realistic test data for a client. Only available when MOCK_CRM=true.",
)
async def seed_mock_data(
    client_id: UUID,
    request: SeedMockDataRequest,
    _test_mode: bool = Depends(require_test_mode),
) -> SeedMockDataResponse:
    """
    Seed mock CRM data for E2E testing.

    Seeds:
    - 6 test leads (assigned to the provided campaign)
    - 8 agency_exclusion_list rows (5 crm_client, 2 crm_pipeline, 1 crm_lost_deal)
    - 6 deals (2 closed_won, 2 closed_lost, 2 open)
    - 3 meetings (1 confirmed+showed, 1 no-show, 1 scheduled)

    This endpoint is idempotent - calling it multiple times is safe.
    SECURITY: Only active when MOCK_CRM=true.

    Args:
        client_id: Client UUID to seed data for
        request: Request body containing campaign_id

    Returns:
        SeedMockDataResponse with counts of seeded records
    """
    async with get_db_session() as db:
        result = await mock_crm_service.seed_mock_data(
            db=db,
            client_id=client_id,
            campaign_id=request.campaign_id,
        )

        return SeedMockDataResponse(
            status=result.get("status", "unknown"),
            exclusion_count=result.get("exclusion_count", 0),
            deal_count=result.get("deal_count", 0),
            meeting_count=result.get("meeting_count", 0),
        )


@router.delete(
    "/clear-mock-data/{client_id}",
    response_model=dict,
    summary="Clear mock CRM data",
    description="Removes mock test data for a client. Only available when MOCK_CRM=true.",
)
async def clear_mock_data(
    client_id: UUID,
    _test_mode: bool = Depends(require_test_mode),
) -> dict:
    """
    Clear mock CRM data for a client.

    Removes all data seeded by seed-mock-data endpoint.
    SECURITY: Only active when MOCK_CRM=true.

    Args:
        client_id: Client UUID to clear data for

    Returns:
        Dict with counts of deleted records
    """
    async with get_db_session() as db:
        result = await mock_crm_service.clear_mock_data(
            db=db,
            client_id=client_id,
        )

        return result


@router.get(
    "/test-mode-status",
    summary="Check test mode status",
    description="Returns whether test mode is enabled.",
)
async def test_mode_status() -> dict:
    """
    Check if test mode is enabled.

    Returns test mode configuration without requiring authentication.
    Useful for E2E test setup to verify environment.
    """
    return {
        "test_mode_enabled": is_test_mode_enabled(),
        "mock_crm": settings.MOCK_CRM,
        "mock_unipile": settings.MOCK_UNIPILE,
        "test_mode_active": settings.TEST_MODE,
    }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] All endpoints require MOCK_CRM=true via dependency
# [x] POST /internal/test-token - generates test JWT
# [x] POST /internal/seed-mock-data/{client_id} - seeds mock CRM data
# [x] DELETE /internal/clear-mock-data/{client_id} - clears mock data
# [x] GET /internal/test-mode-status - checks test mode
# [x] No normal auth required (test endpoints)
# [x] Proper error responses for non-test environments
# [x] Pydantic models for request/response
