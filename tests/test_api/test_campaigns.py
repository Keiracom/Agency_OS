"""
FILE: tests/test_api/test_campaigns.py
PURPOSE: Test campaign CRUD and status management endpoints
PHASE: 7 (API Routes)
TASK: API-004
DEPENDENCIES:
  - src/api/routes/campaigns.py
  - pytest
  - pytest-asyncio
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Test all CRUD endpoints
  - Test status transitions
  - Test sequence and resource management
  - Mock database for unit tests

NOTE: Tests fixed in Directive #158 with proper FastAPI dependency_overrides.
"""

from datetime import date, datetime, time
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.api.dependencies import (
    ClientContext,
    CurrentUser,
    get_current_client,
    get_current_user_from_token,
    get_db_session,
    require_admin,
    require_member,
)
from src.models.base import CampaignStatus, ChannelType, MembershipRole, PermissionMode

# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return MagicMock(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
    )


@pytest.fixture
def mock_client():
    """Create a mock client."""
    return MagicMock(
        id=uuid4(),
        name="Test Client",
        deleted_at=None,
    )


@pytest.fixture
def mock_membership(mock_user, mock_client):
    """Create a mock membership."""
    membership = MagicMock(
        id=uuid4(),
        user_id=mock_user.id,
        client_id=mock_client.id,
        role=MembershipRole.MEMBER,
        is_accepted=True,
        deleted_at=None,
    )
    membership.has_role = lambda *roles: membership.role in roles
    return membership


@pytest.fixture
def mock_campaign(mock_client):
    """Create a mock campaign."""
    campaign = MagicMock(
        id=uuid4(),
        client_id=mock_client.id,
        created_by=uuid4(),
        name="Test Campaign",
        description="Test Description",
        status=CampaignStatus.DRAFT,
        permission_mode=PermissionMode.CO_PILOT,
        target_industries=["Technology"],
        target_titles=["CEO", "CTO"],
        target_company_sizes=["10-50"],
        target_locations=["Australia"],
        allocation_email=70,
        allocation_sms=10,
        allocation_linkedin=20,
        allocation_voice=0,
        allocation_mail=0,
        start_date=date.today(),
        end_date=None,
        daily_limit=50,
        timezone="Australia/Sydney",
        work_hours_start=time(9, 0),
        work_hours_end=time(17, 0),
        work_days=[1, 2, 3, 4, 5],
        sequence_steps=5,
        sequence_delay_days=3,
        total_leads=100,
        leads_contacted=50,
        leads_replied=10,
        leads_converted=5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deleted_at=None,
    )
    campaign.reply_rate = 20.0
    campaign.conversion_rate = 10.0
    campaign.is_ai_suggested = False
    campaign.lead_allocation_pct = 50
    return campaign


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_current_user(mock_user):
    """Create a mock CurrentUser Pydantic model."""
    return CurrentUser(
        id=mock_user.id,
        email=mock_user.email,
        full_name=mock_user.full_name,
    )


@pytest.fixture
def mock_client_context(mock_current_user, mock_client, mock_membership):
    """Create a mock client context using model_construct to bypass validation."""
    return ClientContext.model_construct(
        client=mock_client,
        membership=mock_membership,
        user=mock_current_user,
    )


@pytest.fixture
def setup_dependency_overrides(mock_client_context, mock_db_session, mock_current_user):
    """Set up FastAPI dependency overrides for testing."""
    # Override all auth-related dependencies
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[get_current_user_from_token] = lambda: mock_current_user
    app.dependency_overrides[get_current_client] = lambda: mock_client_context
    app.dependency_overrides[require_member] = lambda: mock_client_context
    app.dependency_overrides[require_admin] = lambda: mock_client_context
    
    yield
    
    # Clear overrides after test
    app.dependency_overrides.clear()


# ============================================
# Test List Campaigns
# ============================================


@pytest.mark.asyncio
async def test_list_campaigns_empty(setup_dependency_overrides, mock_db_session, mock_client):
    """Test listing campaigns when none exist."""
    # Mock empty result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0

    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["campaigns"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["pages"] == 0


@pytest.mark.asyncio
async def test_list_campaigns_with_results(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test listing campaigns with results."""
    # Mock result with one campaign
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_campaign]

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["campaigns"]) == 1
    assert data["total"] == 1
    assert data["campaigns"][0]["name"] == "Test Campaign"


@pytest.mark.asyncio
async def test_list_campaigns_with_status_filter(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test listing campaigns filtered by status."""
    mock_campaign.status = CampaignStatus.ACTIVE

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_campaign]

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns?status=active",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["campaigns"][0]["status"] == "active"


@pytest.mark.asyncio
async def test_list_campaigns_with_search(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test listing campaigns with search query."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_campaign]

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1

    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns?search=Test",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK


# ============================================
# Test Get Campaign
# ============================================


@pytest.mark.asyncio
async def test_get_campaign_success(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test getting a single campaign."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Test Campaign"
    assert data["allocation_email"] == 70


@pytest.mark.asyncio
async def test_get_campaign_not_found(setup_dependency_overrides, mock_db_session, mock_client):
    """Test getting a non-existent campaign."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns/{uuid4()}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================
# Test Create Campaign
# ============================================


@pytest.mark.asyncio
async def test_create_campaign_success(setup_dependency_overrides, mock_db_session, mock_client):
    """Test creating a campaign."""
    created_campaign = MagicMock(
        id=uuid4(),
        client_id=mock_client.id,
        name="New Campaign",
        status=CampaignStatus.DRAFT,
        allocation_email=100,
        allocation_sms=0,
        allocation_linkedin=0,
        allocation_voice=0,
        allocation_mail=0,
        daily_limit=50,
        timezone="Australia/Sydney",
        work_hours_start=time(9, 0),
        work_hours_end=time(17, 0),
        work_days=[1, 2, 3, 4, 5],
        sequence_steps=5,
        sequence_delay_days=3,
        total_leads=0,
        leads_contacted=0,
        leads_replied=0,
        leads_converted=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deleted_at=None,
        description=None,
        permission_mode=None,
        created_by=None,
        target_industries=None,
        target_titles=None,
        target_company_sizes=None,
        target_locations=None,
        start_date=None,
        end_date=None,
        reply_rate=0.0,
        conversion_rate=0.0,
        is_ai_suggested=False,
        lead_allocation_pct=50,
    )

    async def mock_refresh(obj):
        for attr in dir(created_campaign):
            if not attr.startswith("_"):
                try:
                    setattr(obj, attr, getattr(created_campaign, attr))
                except (AttributeError, TypeError):
                    pass

    mock_db_session.refresh = mock_refresh

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns",
            headers={"Authorization": "Bearer test-token"},
            json={
                "name": "New Campaign",
                "allocation_email": 100,
                "allocation_sms": 0,
                "allocation_linkedin": 0,
                "allocation_voice": 0,
                "allocation_mail": 0,
            },
        )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_create_campaign_invalid_allocation(setup_dependency_overrides, mock_db_session, mock_client):
    """Test creating a campaign with invalid allocation (not summing to 100)."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns",
            headers={"Authorization": "Bearer test-token"},
            json={
                "name": "Invalid Campaign",
                "allocation_email": 50,
                "allocation_sms": 10,
                "allocation_linkedin": 10,
                "allocation_voice": 0,
                "allocation_mail": 0,
                # Sum = 70, not 100
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_campaign_with_all_fields(setup_dependency_overrides, mock_db_session, mock_client):
    """Test creating a campaign with all fields."""
    created_campaign = MagicMock(
        id=uuid4(),
        client_id=mock_client.id,
        name="Full Campaign",
        description="Full Description",
        status=CampaignStatus.DRAFT,
        permission_mode=PermissionMode.AUTOPILOT,
        target_industries=["Tech"],
        target_titles=["CEO"],
        target_company_sizes=["10-50"],
        target_locations=["Sydney"],
        allocation_email=60,
        allocation_sms=20,
        allocation_linkedin=20,
        allocation_voice=0,
        allocation_mail=0,
        start_date=date.today(),
        end_date=None,
        daily_limit=100,
        timezone="Australia/Sydney",
        work_hours_start=time(8, 0),
        work_hours_end=time(18, 0),
        work_days=[1, 2, 3, 4, 5],
        sequence_steps=10,
        sequence_delay_days=2,
        total_leads=0,
        leads_contacted=0,
        leads_replied=0,
        leads_converted=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deleted_at=None,
        created_by=None,
        reply_rate=0.0,
        conversion_rate=0.0,
        is_ai_suggested=False,
        lead_allocation_pct=50,
    )

    async def mock_refresh(obj):
        for attr in dir(created_campaign):
            if not attr.startswith("_"):
                try:
                    setattr(obj, attr, getattr(created_campaign, attr))
                except (AttributeError, TypeError):
                    pass

    mock_db_session.refresh = mock_refresh

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns",
            headers={"Authorization": "Bearer test-token"},
            json={
                "name": "Full Campaign",
                "description": "Full Description",
                "permission_mode": "autopilot",
                "target_industries": ["Tech"],
                "target_titles": ["CEO"],
                "target_company_sizes": ["10-50"],
                "target_locations": ["Sydney"],
                "allocation_email": 60,
                "allocation_sms": 20,
                "allocation_linkedin": 20,
                "allocation_voice": 0,
                "allocation_mail": 0,
                "daily_limit": 100,
                "work_hours_start": "08:00:00",
                "work_hours_end": "18:00:00",
                "sequence_steps": 10,
                "sequence_delay_days": 2,
            },
        )

    assert response.status_code == status.HTTP_201_CREATED


# ============================================
# Test Update Campaign
# ============================================


@pytest.mark.asyncio
async def test_update_campaign_success(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test updating a campaign."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}",
            headers={"Authorization": "Bearer test-token"},
            json={"name": "Updated Campaign"},
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_update_campaign_allocation(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test updating campaign allocation."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Update allocation to still sum to 100
        response = await client.put(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}",
            headers={"Authorization": "Bearer test-token"},
            json={
                "allocation_email": 50,
                "allocation_sms": 20,
                "allocation_linkedin": 30,
            },
        )

    assert response.status_code == status.HTTP_200_OK


# ============================================
# Test Delete Campaign
# ============================================


@pytest.mark.asyncio
async def test_delete_campaign_success(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test soft deleting a campaign."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_204_NO_CONTENT


# ============================================
# Test Status Transitions
# ============================================


@pytest.mark.asyncio
async def test_activate_campaign_from_approved(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test activating an approved campaign (LAW: campaign_approval_flow)."""
    mock_campaign.status = CampaignStatus.APPROVED

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/activate",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_activate_campaign_from_paused(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test activating a paused campaign."""
    mock_campaign.status = CampaignStatus.PAUSED

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/activate",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_pause_campaign(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test pausing an active campaign."""
    mock_campaign.status = CampaignStatus.ACTIVE

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/pause",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_pause_non_active_campaign_fails(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test that pausing a non-active campaign fails."""
    mock_campaign.status = CampaignStatus.DRAFT

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/pause",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_status_update_valid_transition(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test valid status transition via PATCH."""
    mock_campaign.status = CampaignStatus.ACTIVE

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/status",
            headers={"Authorization": "Bearer test-token"},
            json={"status": "paused"},
        )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_status_update_invalid_transition(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test invalid status transition."""
    mock_campaign.status = CampaignStatus.COMPLETED

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/status",
            headers={"Authorization": "Bearer test-token"},
            json={"status": "active"},  # Can't go from completed to active
        )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================
# Test Sequence Routes
# ============================================


@pytest.mark.asyncio
async def test_list_sequences(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test listing campaign sequences."""
    mock_sequence = MagicMock(
        id=uuid4(),
        campaign_id=mock_campaign.id,
        step_number=1,
        channel=ChannelType.EMAIL,
        delay_days=0,
        subject_template="Hello {{first_name}}",
        body_template="Hi there!",
        skip_if_replied=True,
        skip_if_bounced=True,
        purpose=None,
        skip_if=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Mock get campaign
    mock_campaign_result = MagicMock()
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    # Mock get sequences
    mock_sequences_result = MagicMock()
    mock_sequences_result.scalars.return_value.all.return_value = [mock_sequence]

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_campaign_result, mock_sequences_result]
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/sequences",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["step_number"] == 1


@pytest.mark.asyncio
async def test_create_sequence(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test creating a sequence step."""
    # Mock get campaign
    mock_campaign_result = MagicMock()
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    # Mock check for existing step
    mock_existing_result = MagicMock()
    mock_existing_result.scalar_one_or_none.return_value = None

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_campaign_result, mock_existing_result]
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/sequences",
            headers={"Authorization": "Bearer test-token"},
            json={
                "step_number": 1,
                "channel": "email",
                "delay_days": 0,
                "body_template": "Hello!",
            },
        )

    assert response.status_code == status.HTTP_201_CREATED


# ============================================
# Test Resource Routes
# ============================================


@pytest.mark.asyncio
async def test_list_resources(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test listing campaign resources."""
    mock_resource = MagicMock(
        id=uuid4(),
        campaign_id=mock_campaign.id,
        channel=ChannelType.EMAIL,
        resource_id="sender@example.com",
        resource_name="Main Sender",
        daily_limit=50,
        daily_used=10,
        remaining=40,
        last_used_at=datetime.utcnow(),
        last_reset_at=datetime.utcnow(),
        is_active=True,
        is_warmed=True,
        is_available=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Mock get campaign
    mock_campaign_result = MagicMock()
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    # Mock get resources
    mock_resources_result = MagicMock()
    mock_resources_result.scalars.return_value.all.return_value = [mock_resource]

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_campaign_result, mock_resources_result]
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/resources",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["resource_id"] == "sender@example.com"


@pytest.mark.asyncio
async def test_create_resource(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test creating a campaign resource."""
    # Mock get campaign
    mock_campaign_result = MagicMock()
    mock_campaign_result.scalar_one_or_none.return_value = mock_campaign

    # Mock check for existing resource
    mock_existing_result = MagicMock()
    mock_existing_result.scalar_one_or_none.return_value = None

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_campaign_result, mock_existing_result]
    )

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/resources",
            headers={"Authorization": "Bearer test-token"},
            json={
                "channel": "email",
                "resource_id": "sender@example.com",
                "resource_name": "Main Sender",
                "daily_limit": 50,
            },
        )

    assert response.status_code == status.HTTP_201_CREATED


# ============================================
# Test Pagination
# ============================================


@pytest.mark.asyncio
async def test_list_campaigns_pagination(setup_dependency_overrides, mock_db_session, mock_client):
    """Test campaign list pagination parameters."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 50

    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_result])

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns?page=2&page_size=10",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert data["total"] == 50
    assert data["pages"] == 5


# ============================================
# Test Response Structure
# ============================================


@pytest.mark.asyncio
async def test_campaign_response_structure(
    setup_dependency_overrides, mock_db_session, mock_client, mock_campaign
):
    """Test that campaign response has all required fields."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign

    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Check required fields
    required_fields = [
        "id", "client_id", "name", "status",
        "allocation_email", "allocation_sms", "allocation_linkedin",
        "allocation_voice", "allocation_mail",
        "daily_limit", "timezone", "work_hours_start", "work_hours_end",
        "work_days", "sequence_steps", "sequence_delay_days",
        "total_leads", "leads_contacted", "leads_replied", "leads_converted",
        "created_at", "updated_at",
    ]

    for field in required_fields:
        assert field in data, f"Missing field: {field}"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test list campaigns (empty, with results, filtered, search)
# [x] Test get campaign (success, not found)
# [x] Test create campaign (success, invalid allocation, all fields)
# [x] Test update campaign (success, allocation update)
# [x] Test delete campaign (soft delete)
# [x] Test status transitions (activate, pause, invalid)
# [x] Test sequence routes (list, create)
# [x] Test resource routes (list, create)
# [x] Test pagination
# [x] Test response structure
# [x] Mock database for unit tests
# [x] Mock auth dependencies
# [x] All tests use pytest.mark.asyncio
# [x] All tests have descriptive docstrings
# [x] Contract comment at top
