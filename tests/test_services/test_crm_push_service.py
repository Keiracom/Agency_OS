"""
FILE: tests/test_services/test_crm_push_service.py
PURPOSE: Unit tests for CRM Push Service
PHASE: 24E - CRM Push
TASK: CRM-010
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.crm_push_service import (
    CRMConfig,
    CRMPipeline,
    CRMPushResult,
    CRMPushService,
    CRMStage,
    CRMUser,
    LeadData,
    MeetingData,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_session():
    """Mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def crm_service(db_session):
    """Create CRM push service with mocked session."""
    return CRMPushService(db_session)


@pytest.fixture
def mock_lead():
    """Create mock lead data."""
    return LeadData(
        id=uuid4(),
        email="sarah@buildright.com.au",
        first_name="Sarah",
        last_name="Chen",
        full_name="Sarah Chen",
        phone="+61412345678",
        title="Managing Director",
        organization_name="BuildRight Construction",
        organization_website="https://buildright.com.au",
        organization_industry="Construction",
        linkedin_url="https://linkedin.com/in/sarahchen",
    )


@pytest.fixture
def mock_meeting():
    """Create mock meeting data."""
    return MeetingData(
        id=uuid4(),
        scheduled_at=datetime.utcnow() + timedelta(days=3),
        duration_minutes=30,
        meeting_link="https://meet.google.com/abc-def-ghi",
        notes="Discovery call to discuss their marketing needs",
    )


@pytest.fixture
def hubspot_config():
    """Create HubSpot CRM config."""
    return CRMConfig(
        id=uuid4(),
        client_id=uuid4(),
        crm_type="hubspot",
        oauth_access_token="test-access-token",
        oauth_refresh_token="test-refresh-token",
        oauth_expires_at=datetime.utcnow() + timedelta(hours=1),
        hubspot_portal_id="12345678",
        pipeline_id="default",
        stage_id="appointmentscheduled",
        owner_id="123456",
        is_active=True,
    )


@pytest.fixture
def pipedrive_config():
    """Create Pipedrive CRM config."""
    return CRMConfig(
        id=uuid4(),
        client_id=uuid4(),
        crm_type="pipedrive",
        api_key="test-pipedrive-api-key",
        pipeline_id="1",
        stage_id="1",
        owner_id="12345",
        is_active=True,
    )


@pytest.fixture
def close_config():
    """Create Close CRM config."""
    return CRMConfig(
        id=uuid4(),
        client_id=uuid4(),
        crm_type="close",
        api_key="test-close-api-key",
        stage_id="stat_123",
        owner_id="user_123",
        is_active=True,
    )


# ============================================================================
# Test: No CRM Configured
# ============================================================================


@pytest.mark.asyncio
async def test_push_meeting_no_config(crm_service, mock_lead, mock_meeting):
    """Test push when no CRM is configured returns skipped."""
    # Mock get_config to return None
    crm_service.get_config = AsyncMock(return_value=None)

    result = await crm_service.push_meeting_booked(
        client_id=uuid4(),
        lead=mock_lead,
        meeting=mock_meeting,
    )

    assert result.skipped is True
    assert result.success is False
    assert result.reason == "No CRM configured"


@pytest.mark.asyncio
async def test_push_meeting_inactive_config(crm_service, hubspot_config, mock_lead, mock_meeting):
    """Test push when CRM config is inactive returns skipped."""
    hubspot_config.is_active = False
    crm_service.get_config = AsyncMock(return_value=hubspot_config)

    result = await crm_service.push_meeting_booked(
        client_id=hubspot_config.client_id,
        lead=mock_lead,
        meeting=mock_meeting,
    )

    assert result.skipped is True
    assert result.success is False


# ============================================================================
# Test: HubSpot Integration
# ============================================================================


@pytest.mark.asyncio
async def test_hubspot_find_or_create_contact_existing(crm_service, hubspot_config, mock_lead):
    """Test finding existing HubSpot contact."""
    # Mock HTTP response for search returning existing contact
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"id": "contact_123", "properties": {"email": mock_lead.email}}]
    }
    mock_response.raise_for_status = MagicMock()
    crm_service.http.post = AsyncMock(return_value=mock_response)

    contact_id = await crm_service._hubspot_find_or_create_contact(hubspot_config, mock_lead)

    assert contact_id == "contact_123"


@pytest.mark.asyncio
async def test_hubspot_find_or_create_contact_new(crm_service, hubspot_config, mock_lead, db_session):
    """Test creating new HubSpot contact when not found."""
    # First call (search) returns empty
    mock_search_response = MagicMock()
    mock_search_response.json.return_value = {"results": []}
    mock_search_response.raise_for_status = MagicMock()

    # Second call (create) returns new contact
    mock_create_response = MagicMock()
    mock_create_response.json.return_value = {"id": "new_contact_456"}
    mock_create_response.raise_for_status = MagicMock()

    crm_service.http.post = AsyncMock(side_effect=[mock_search_response, mock_create_response])

    contact_id = await crm_service._hubspot_find_or_create_contact(hubspot_config, mock_lead)

    assert contact_id == "new_contact_456"
    assert crm_service.http.post.call_count == 2


@pytest.mark.asyncio
async def test_hubspot_create_deal(crm_service, hubspot_config, mock_lead, mock_meeting):
    """Test creating HubSpot deal."""
    contact_id = "contact_123"

    # Mock deal creation response
    mock_deal_response = MagicMock()
    mock_deal_response.json.return_value = {"id": "deal_789"}
    mock_deal_response.raise_for_status = MagicMock()

    # Mock association response
    mock_assoc_response = MagicMock()

    crm_service.http.post = AsyncMock(return_value=mock_deal_response)
    crm_service.http.put = AsyncMock(return_value=mock_assoc_response)

    deal_id = await crm_service._hubspot_create_deal(
        hubspot_config, mock_lead, mock_meeting, contact_id, "BuildRight Construction - Agency OS"
    )

    assert deal_id == "deal_789"
    crm_service.http.put.assert_called_once()  # Association call


@pytest.mark.asyncio
async def test_hubspot_token_refresh(crm_service, hubspot_config, db_session):
    """Test HubSpot OAuth token refresh when expired."""
    # Set token to expire soon
    hubspot_config.oauth_expires_at = datetime.utcnow() + timedelta(minutes=2)

    # Mock token refresh response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
        "expires_in": 1800,
    }
    mock_response.raise_for_status = MagicMock()

    crm_service.http.post = AsyncMock(return_value=mock_response)
    crm_service.save_config = AsyncMock(return_value=hubspot_config)
    crm_service.log_push = AsyncMock()

    with patch("src.services.crm_push_service.settings") as mock_settings:
        mock_settings.hubspot_client_id = "test_client_id"
        mock_settings.hubspot_client_secret = "test_client_secret"

        refreshed_config = await crm_service._refresh_hubspot_token_if_needed(hubspot_config)

    assert refreshed_config.oauth_access_token == "new_access_token"
    crm_service.save_config.assert_called_once()


# ============================================================================
# Test: Pipedrive Integration
# ============================================================================


@pytest.mark.asyncio
async def test_pipedrive_find_or_create_person_existing(crm_service, pipedrive_config, mock_lead):
    """Test finding existing Pipedrive person."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {"items": [{"item": {"id": 12345}}]}
    }
    mock_response.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_response)

    person_id = await crm_service._pipedrive_find_or_create_person(pipedrive_config, mock_lead)

    assert person_id == "12345"


@pytest.mark.asyncio
async def test_pipedrive_find_or_create_person_new(crm_service, pipedrive_config, mock_lead, db_session):
    """Test creating new Pipedrive person."""
    # Search returns empty
    mock_search_response = MagicMock()
    mock_search_response.json.return_value = {"data": None}
    mock_search_response.raise_for_status = MagicMock()

    # Create returns new person
    mock_create_response = MagicMock()
    mock_create_response.json.return_value = {"data": {"id": 67890}}
    mock_create_response.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_search_response)
    crm_service.http.post = AsyncMock(return_value=mock_create_response)

    person_id = await crm_service._pipedrive_find_or_create_person(pipedrive_config, mock_lead)

    assert person_id == "67890"


@pytest.mark.asyncio
async def test_pipedrive_create_deal(crm_service, pipedrive_config, mock_lead, mock_meeting, db_session):
    """Test creating Pipedrive deal."""
    person_id = "12345"

    # Mock org search (empty)
    mock_org_search = MagicMock()
    mock_org_search.json.return_value = {"data": None}
    mock_org_search.raise_for_status = MagicMock()

    # Mock org create
    mock_org_create = MagicMock()
    mock_org_create.json.return_value = {"data": {"id": 111}}
    mock_org_create.raise_for_status = MagicMock()

    # Mock deal create
    mock_deal_create = MagicMock()
    mock_deal_create.json.return_value = {"data": {"id": 222}}
    mock_deal_create.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_org_search)
    crm_service.http.post = AsyncMock(side_effect=[mock_org_create, mock_deal_create])

    deal_id, org_id = await crm_service._pipedrive_create_deal(
        pipedrive_config, mock_lead, mock_meeting, person_id, "BuildRight Construction - Agency OS"
    )

    assert deal_id == "222"
    assert org_id == "111"


# ============================================================================
# Test: Close Integration
# ============================================================================


@pytest.mark.asyncio
async def test_close_find_or_create_lead_existing(crm_service, close_config, mock_lead):
    """Test finding existing Close lead."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"id": "lead_abc123"}]
    }
    mock_response.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_response)

    lead_id = await crm_service._close_find_or_create_lead(close_config, mock_lead)

    assert lead_id == "lead_abc123"


@pytest.mark.asyncio
async def test_close_find_or_create_lead_new(crm_service, close_config, mock_lead, db_session):
    """Test creating new Close lead."""
    # Search returns empty
    mock_search_response = MagicMock()
    mock_search_response.json.return_value = {"data": []}
    mock_search_response.raise_for_status = MagicMock()

    # Create returns new lead
    mock_create_response = MagicMock()
    mock_create_response.json.return_value = {"id": "lead_xyz789"}
    mock_create_response.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_search_response)
    crm_service.http.post = AsyncMock(return_value=mock_create_response)

    lead_id = await crm_service._close_find_or_create_lead(close_config, mock_lead)

    assert lead_id == "lead_xyz789"


@pytest.mark.asyncio
async def test_close_create_opportunity(crm_service, close_config, mock_lead, mock_meeting):
    """Test creating Close opportunity."""
    close_lead_id = "lead_abc123"

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "oppo_def456"}
    mock_response.raise_for_status = MagicMock()

    crm_service.http.post = AsyncMock(return_value=mock_response)

    opp_id = await crm_service._close_create_opportunity(
        close_config, mock_lead, mock_meeting, close_lead_id, "BuildRight Construction - Agency OS"
    )

    assert opp_id == "oppo_def456"


# ============================================================================
# Test: Full Push Flow
# ============================================================================


@pytest.mark.asyncio
async def test_push_meeting_success_hubspot(crm_service, hubspot_config, mock_lead, mock_meeting, db_session):
    """Test full meeting push flow for HubSpot."""
    crm_service.get_config = AsyncMock(return_value=hubspot_config)
    crm_service._refresh_hubspot_token_if_needed = AsyncMock(return_value=hubspot_config)
    crm_service.find_or_create_contact = AsyncMock(return_value="contact_123")
    crm_service.create_deal = AsyncMock(return_value=("deal_456", None))
    crm_service.log_push = AsyncMock()

    result = await crm_service.push_meeting_booked(
        client_id=hubspot_config.client_id,
        lead=mock_lead,
        meeting=mock_meeting,
    )

    assert result.success is True
    assert result.crm_contact_id == "contact_123"
    assert result.crm_deal_id == "deal_456"


@pytest.mark.asyncio
async def test_push_meeting_error_handling(crm_service, hubspot_config, mock_lead, mock_meeting, db_session):
    """Test error handling during push."""
    crm_service.get_config = AsyncMock(return_value=hubspot_config)
    crm_service._refresh_hubspot_token_if_needed = AsyncMock(return_value=hubspot_config)
    crm_service.find_or_create_contact = AsyncMock(side_effect=Exception("API error"))
    crm_service.log_push = AsyncMock()

    result = await crm_service.push_meeting_booked(
        client_id=hubspot_config.client_id,
        lead=mock_lead,
        meeting=mock_meeting,
    )

    assert result.success is False
    assert "API error" in result.error


# ============================================================================
# Test: Pipeline and User Fetching
# ============================================================================


@pytest.mark.asyncio
async def test_get_hubspot_pipelines(crm_service, hubspot_config):
    """Test fetching HubSpot pipelines."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": "pipeline_1",
                "label": "Sales Pipeline",
                "stages": [
                    {"id": "stage_1", "label": "New Lead", "metadata": {"probability": 0.2}},
                    {"id": "stage_2", "label": "Meeting Booked", "metadata": {"probability": 0.5}},
                ]
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_response)

    pipelines = await crm_service.get_hubspot_pipelines(hubspot_config)

    assert len(pipelines) == 1
    assert pipelines[0].id == "pipeline_1"
    assert pipelines[0].name == "Sales Pipeline"
    assert len(pipelines[0].stages) == 2


@pytest.mark.asyncio
async def test_get_hubspot_users(crm_service, hubspot_config):
    """Test fetching HubSpot users."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"id": "user_1", "firstName": "John", "lastName": "Doe", "email": "john@example.com"},
            {"id": "user_2", "firstName": "Jane", "lastName": "Smith", "email": "jane@example.com"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    crm_service.http.get = AsyncMock(return_value=mock_response)

    users = await crm_service.get_hubspot_users(hubspot_config)

    assert len(users) == 2
    assert users[0].id == "user_1"
    assert users[0].name == "John Doe"


# ============================================================================
# Test: Connection Test
# ============================================================================


@pytest.mark.asyncio
async def test_test_connection_success(crm_service, hubspot_config, db_session):
    """Test successful connection test."""
    crm_service._refresh_hubspot_token_if_needed = AsyncMock(return_value=hubspot_config)
    crm_service.get_hubspot_pipelines = AsyncMock(return_value=[])
    crm_service.log_push = AsyncMock()

    success, error = await crm_service.test_connection(hubspot_config)

    assert success is True
    assert error is None


@pytest.mark.asyncio
async def test_test_connection_failure(crm_service, hubspot_config, db_session):
    """Test failed connection test."""
    crm_service._refresh_hubspot_token_if_needed = AsyncMock(return_value=hubspot_config)
    crm_service.get_hubspot_pipelines = AsyncMock(side_effect=Exception("Auth failed"))
    crm_service.log_push = AsyncMock()

    success, error = await crm_service.test_connection(hubspot_config)

    assert success is False
    assert "Auth failed" in error


# ============================================================================
# Test: Config Management
# ============================================================================


@pytest.mark.asyncio
async def test_disconnect_crm(crm_service, db_session):
    """Test disconnecting CRM."""
    client_id = uuid4()

    success = await crm_service.disconnect(client_id)

    assert success is True
    db_session.execute.assert_called_once()
    db_session.commit.assert_called_once()


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Test no CRM configured
# [x] Test inactive CRM config
# [x] Test HubSpot find existing contact
# [x] Test HubSpot create new contact
# [x] Test HubSpot create deal
# [x] Test HubSpot token refresh
# [x] Test Pipedrive find existing person
# [x] Test Pipedrive create new person
# [x] Test Pipedrive create deal
# [x] Test Close find existing lead
# [x] Test Close create new lead
# [x] Test Close create opportunity
# [x] Test full push flow success
# [x] Test error handling
# [x] Test pipeline fetching
# [x] Test user fetching
# [x] Test connection test success/failure
# [x] Test disconnect
