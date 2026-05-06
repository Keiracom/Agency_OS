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

from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.full_name = "Test User"
    return user


@pytest.fixture
def mock_client():
    """Create a mock client."""
    client = MagicMock()
    client.id = uuid4()
    client.configure_mock(name="Test Client")
    client.deleted_at = None
    return client


@pytest.fixture
def mock_membership(mock_user, mock_client):
    """Create a mock membership."""
    membership = MagicMock()
    membership.id = uuid4()
    membership.user_id = mock_user.id
    membership.client_id = mock_client.id
    membership.role = MembershipRole.MEMBER
    membership.is_accepted = True
    membership.deleted_at = None
    membership.has_role = lambda *roles: membership.role in roles
    return membership


@pytest.fixture
def mock_campaign(mock_client):
    """Create a mock campaign."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.client_id = mock_client.id
    campaign.created_by = uuid4()
    campaign.configure_mock(name="Test Campaign")
    campaign.description = "Test Description"
    campaign.status = CampaignStatus.DRAFT
    campaign.permission_mode = PermissionMode.CO_PILOT
    campaign.target_industries = ["Technology"]
    campaign.target_titles = ["CEO", "CTO"]
    campaign.target_company_sizes = ["10-50"]
    campaign.target_locations = ["Australia"]
    campaign.allocation_email = 70
    campaign.allocation_sms = 10
    campaign.allocation_linkedin = 20
    campaign.allocation_voice = 0
    campaign.allocation_mail = 0
    campaign.start_date = date.today()
    campaign.end_date = None
    campaign.daily_limit = 50
    campaign.timezone = "Australia/Sydney"
    campaign.work_hours_start = time(9, 0)
    campaign.work_hours_end = time(17, 0)
    campaign.work_days = [1, 2, 3, 4, 5]
    campaign.sequence_steps = 5
    campaign.sequence_delay_days = 3
    campaign.uses_default_sequence = True
    campaign.total_leads = 100
    campaign.leads_contacted = 50
    campaign.leads_replied = 10
    campaign.leads_converted = 5
    campaign.created_at = datetime.now(timezone.utc)
    campaign.updated_at = datetime.now(timezone.utc)
    campaign.deleted_at = None
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
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[get_current_user_from_token] = lambda: mock_current_user
    app.dependency_overrides[get_current_client] = lambda: mock_client_context
    app.dependency_overrides[require_member] = lambda: mock_client_context
    app.dependency_overrides[require_admin] = lambda: mock_client_context

    yield

    app.dependency_overrides.clear()


# ============================================
# Helper Functions
# ============================================


def create_campaign_result(campaign):
    """Create mock result for campaign fetch (scalar_one_or_none pattern)."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = campaign
    return result


def create_metrics_result(total_meetings=0, showed_count=0, active_count=0):
    """Create mock result for metrics queries (fetchone pattern)."""
    result = MagicMock()
    row = MagicMock()
    row.total_meetings = total_meetings
    row.showed_count = showed_count
    row.active_count = active_count
    result.fetchone.return_value = row
    return result


def create_count_result(count=0):
    """Create mock result for count queries (scalar_one pattern)."""
    result = MagicMock()
    result.scalar_one.return_value = count
    return result


def create_list_result(items):
    """Create mock result for list queries (scalars().all() pattern)."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


# ============================================
# Test List Campaigns
# ============================================


@pytest.mark.asyncio
async def test_list_campaigns_empty(setup_dependency_overrides, mock_db_session, mock_client):
    """Test listing campaigns when none exist."""
    mock_count_result = create_count_result(0)
    mock_list_result = create_list_result([])
    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

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
    mock_count_result = create_count_result(1)
    mock_list_result = create_list_result([mock_campaign])
    # enrich_campaign_response calls compute_campaign_metrics which does 2 more queries
    mock_meetings_result = create_metrics_result(total_meetings=5, showed_count=3)
    mock_sequences_result = create_metrics_result(active_count=10)
    mock_db_session.execute = AsyncMock(
        side_effect=[
            mock_count_result,
            mock_list_result,
            mock_meetings_result,
            mock_sequences_result,
        ]
    )

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
    mock_count_result = create_count_result(1)
    mock_list_result = create_list_result([mock_campaign])
    mock_meetings_result = create_metrics_result(total_meetings=5, showed_count=3)
    mock_sequences_result = create_metrics_result(active_count=10)
    mock_db_session.execute = AsyncMock(
        side_effect=[
            mock_count_result,
            mock_list_result,
            mock_meetings_result,
            mock_sequences_result,
        ]
    )

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
    mock_count_result = create_count_result(1)
    mock_list_result = create_list_result([mock_campaign])
    mock_meetings_result = create_metrics_result(total_meetings=5, showed_count=3)
    mock_sequences_result = create_metrics_result(active_count=10)
    mock_db_session.execute = AsyncMock(
        side_effect=[
            mock_count_result,
            mock_list_result,
            mock_meetings_result,
            mock_sequences_result,
        ]
    )

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
    # Set up sequential mock results for all DB queries
    mock_campaign_result = create_campaign_result(mock_campaign)
    mock_meetings_result = create_metrics_result(total_meetings=5, showed_count=3)
    mock_sequences_result = create_metrics_result(active_count=10)

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_campaign_result, mock_meetings_result, mock_sequences_result]
    )

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
    mock_result = create_campaign_result(None)
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
    created_campaign = MagicMock()
    created_campaign.id = uuid4()
    created_campaign.client_id = mock_client.id
    created_campaign.configure_mock(name="New Campaign")
    created_campaign.status = CampaignStatus.DRAFT
    created_campaign.description = None
    created_campaign.permission_mode = None
    created_campaign.created_by = None
    created_campaign.target_industries = None
    created_campaign.target_titles = None
    created_campaign.target_company_sizes = None
    created_campaign.target_locations = None
    created_campaign.allocation_email = 100
    created_campaign.allocation_sms = 0
    created_campaign.allocation_linkedin = 0
    created_campaign.allocation_voice = 0
    created_campaign.allocation_mail = 0
    created_campaign.start_date = None
    created_campaign.end_date = None
    created_campaign.daily_limit = 50
    created_campaign.timezone = "Australia/Sydney"
    created_campaign.work_hours_start = time(9, 0)
    created_campaign.work_hours_end = time(17, 0)
    created_campaign.work_days = [1, 2, 3, 4, 5]
    created_campaign.sequence_steps = 5
    created_campaign.sequence_delay_days = 3
    created_campaign.uses_default_sequence = True
    created_campaign.total_leads = 0
    created_campaign.leads_contacted = 0
    created_campaign.leads_replied = 0
    created_campaign.leads_converted = 0
    created_campaign.created_at = datetime.now(timezone.utc)
    created_campaign.updated_at = datetime.now(timezone.utc)
    created_campaign.deleted_at = None
    created_campaign.reply_rate = 0.0
    created_campaign.conversion_rate = 0.0
    created_campaign.is_ai_suggested = False
    created_campaign.lead_allocation_pct = 50

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
async def test_create_campaign_invalid_allocation(
    setup_dependency_overrides, mock_db_session, mock_client
):
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
            },
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_campaign_with_all_fields(
    setup_dependency_overrides, mock_db_session, mock_client
):
    """Test creating a campaign with all fields."""
    created_campaign = MagicMock()
    created_campaign.id = uuid4()
    created_campaign.client_id = mock_client.id
    created_campaign.configure_mock(name="Full Campaign")
    created_campaign.description = "Full Description"
    created_campaign.status = CampaignStatus.DRAFT
    created_campaign.permission_mode = PermissionMode.AUTOPILOT
    created_campaign.created_by = None
    created_campaign.target_industries = ["Tech"]
    created_campaign.target_titles = ["CEO"]
    created_campaign.target_company_sizes = ["10-50"]
    created_campaign.target_locations = ["Sydney"]
    created_campaign.allocation_email = 60
    created_campaign.allocation_sms = 20
    created_campaign.allocation_linkedin = 20
    created_campaign.allocation_voice = 0
    created_campaign.allocation_mail = 0
    created_campaign.start_date = date.today()
    created_campaign.end_date = None
    created_campaign.daily_limit = 100
    created_campaign.timezone = "Australia/Sydney"
    created_campaign.work_hours_start = time(8, 0)
    created_campaign.work_hours_end = time(18, 0)
    created_campaign.work_days = [1, 2, 3, 4, 5]
    created_campaign.sequence_steps = 10
    created_campaign.sequence_delay_days = 2
    created_campaign.uses_default_sequence = True
    created_campaign.total_leads = 0
    created_campaign.leads_contacted = 0
    created_campaign.leads_replied = 0
    created_campaign.leads_converted = 0
    created_campaign.created_at = datetime.now(timezone.utc)
    created_campaign.updated_at = datetime.now(timezone.utc)
    created_campaign.deleted_at = None
    created_campaign.reply_rate = 0.0
    created_campaign.conversion_rate = 0.0
    created_campaign.is_ai_suggested = False
    created_campaign.lead_allocation_pct = 50

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
    mock_result = create_campaign_result(mock_campaign)
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
    mock_result = create_campaign_result(mock_campaign)
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    mock_result = create_campaign_result(mock_campaign)
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
    """Test activating an approved campaign."""
    mock_campaign.status = CampaignStatus.APPROVED
    mock_result = create_campaign_result(mock_campaign)
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
    mock_result = create_campaign_result(mock_campaign)
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
    mock_result = create_campaign_result(mock_campaign)
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
    mock_result = create_campaign_result(mock_campaign)
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
    mock_result = create_campaign_result(mock_campaign)
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
    mock_result = create_campaign_result(mock_campaign)
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}/status",
            headers={"Authorization": "Bearer test-token"},
            json={"status": "active"},
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
    mock_sequence = MagicMock()
    mock_sequence.id = uuid4()
    mock_sequence.campaign_id = mock_campaign.id
    mock_sequence.step_number = 1
    mock_sequence.channel = ChannelType.EMAIL
    mock_sequence.delay_days = 0
    mock_sequence.subject_template = "Hello {{first_name}}"
    mock_sequence.body_template = "Hi there!"
    mock_sequence.skip_if_replied = True
    mock_sequence.skip_if_bounced = True
    mock_sequence.purpose = None
    mock_sequence.skip_if = None
    mock_sequence.created_at = datetime.now(timezone.utc)
    mock_sequence.updated_at = datetime.now(timezone.utc)

    mock_campaign_result = create_campaign_result(mock_campaign)
    mock_sequences_result = create_list_result([mock_sequence])

    mock_db_session.execute = AsyncMock(side_effect=[mock_campaign_result, mock_sequences_result])

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
    mock_campaign_result = create_campaign_result(mock_campaign)
    mock_existing_result = create_campaign_result(None)  # No existing step

    mock_db_session.execute = AsyncMock(side_effect=[mock_campaign_result, mock_existing_result])

    # Mock refresh to set required fields on the created sequence
    async def mock_refresh(obj):
        obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_db_session.refresh = mock_refresh

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
    mock_resource = MagicMock()
    mock_resource.id = uuid4()
    mock_resource.campaign_id = mock_campaign.id
    mock_resource.channel = ChannelType.EMAIL
    mock_resource.resource_id = "sender@example.com"
    mock_resource.resource_name = "Main Sender"
    mock_resource.daily_limit = 50
    mock_resource.daily_used = 10
    mock_resource.remaining = 40
    mock_resource.last_used_at = datetime.now(timezone.utc)
    mock_resource.last_reset_at = datetime.now(timezone.utc)
    mock_resource.is_active = True
    mock_resource.is_warmed = True
    mock_resource.is_available = True
    mock_resource.created_at = datetime.now(timezone.utc)
    mock_resource.updated_at = datetime.now(timezone.utc)

    mock_campaign_result = create_campaign_result(mock_campaign)
    mock_resources_result = create_list_result([mock_resource])

    mock_db_session.execute = AsyncMock(side_effect=[mock_campaign_result, mock_resources_result])

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
    mock_campaign_result = create_campaign_result(mock_campaign)
    mock_existing_result = create_campaign_result(None)  # No existing resource

    mock_db_session.execute = AsyncMock(side_effect=[mock_campaign_result, mock_existing_result])

    # Mock refresh to set required non-computed fields on the created resource
    # Note: 'remaining' and 'is_available' are computed properties, don't set them
    async def mock_refresh(obj):
        obj.id = uuid4()
        obj.campaign_id = mock_campaign.id
        obj.daily_used = 0
        obj.last_reset_at = datetime.now(timezone.utc)
        obj.is_active = True
        obj.is_warmed = False
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_db_session.refresh = mock_refresh

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
    mock_count_result = create_count_result(50)
    mock_list_result = create_list_result([])
    mock_db_session.execute = AsyncMock(side_effect=[mock_count_result, mock_list_result])

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
    mock_campaign_result = create_campaign_result(mock_campaign)
    mock_meetings_result = create_metrics_result(total_meetings=5, showed_count=3)
    mock_sequences_result = create_metrics_result(active_count=10)

    mock_db_session.execute = AsyncMock(
        side_effect=[mock_campaign_result, mock_meetings_result, mock_sequences_result]
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/clients/{mock_client.id}/campaigns/{mock_campaign.id}",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    required_fields = [
        "id",
        "client_id",
        "name",
        "status",
        "allocation_email",
        "allocation_sms",
        "allocation_linkedin",
        "allocation_voice",
        "allocation_mail",
        "daily_limit",
        "timezone",
        "work_hours_start",
        "work_hours_end",
        "work_days",
        "sequence_steps",
        "sequence_delay_days",
        "total_leads",
        "leads_contacted",
        "leads_replied",
        "leads_converted",
        "created_at",
        "updated_at",
    ]

    for field in required_fields:
        assert field in data, f"Missing field: {field}"
