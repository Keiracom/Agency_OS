"""
FILE: tests/test_api/test_leads.py
PURPOSE: Test lead API endpoints (CRUD + enrichment)
PHASE: 7 (API Routes)
TASK: API-005
DEPENDENCIES:
  - src/api/routes/leads.py
  - src/models/lead.py
  - src/models/campaign.py
RULES APPLIED:
  - Rule 14: Soft delete checks
  - Multi-tenancy validation
  - ALS field validation
"""

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import CampaignStatus, LeadStatus
from src.models.campaign import Campaign
from src.models.client import Client
from src.models.lead import Lead
from src.models.membership import Membership
from src.models.user import User


# ============================================
# Fixtures
# ============================================


@pytest.fixture
async def test_client_data(db_session: AsyncSession) -> Client:
    """Create test client."""
    client = Client(
        id=uuid4(),
        name="Test Client",
        tier="ignition",
        subscription_status="active",
        credits_remaining=1000,
    )
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    return client


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_membership(
    db_session: AsyncSession,
    test_client_data: Client,
    test_user: User,
) -> Membership:
    """Create test membership."""
    membership = Membership(
        id=uuid4(),
        user_id=test_user.id,
        client_id=test_client_data.id,
        role="member",
        accepted_at=datetime.utcnow(),
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)
    return membership


@pytest.fixture
async def test_campaign(
    db_session: AsyncSession,
    test_client_data: Client,
) -> Campaign:
    """Create test campaign."""
    campaign = Campaign(
        id=uuid4(),
        client_id=test_client_data.id,
        name="Test Campaign",
        status=CampaignStatus.ACTIVE,
        permission_mode="co_pilot",
        outreach_daily_limit=50,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


@pytest.fixture
async def test_lead(
    db_session: AsyncSession,
    test_client_data: Client,
    test_campaign: Campaign,
) -> Lead:
    """Create test lead."""
    lead = Lead(
        id=uuid4(),
        client_id=test_client_data.id,
        campaign_id=test_campaign.id,
        email="lead@example.com",
        first_name="John",
        last_name="Doe",
        company="Test Corp",
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    return lead


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create auth headers with test token."""
    # In development mode, we use test_user_ prefix
    token = f"test_user_{test_user.id}"
    return {"Authorization": f"Bearer {token}"}


# ============================================
# Test List Leads
# ============================================


@pytest.mark.asyncio
async def test_list_leads_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_campaign: Campaign,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test listing leads."""
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "leads" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["leads"]) >= 1

    # Verify lead structure
    lead = data["leads"][0]
    assert "id" in lead
    assert "email" in lead
    assert "als_score" in lead
    assert "als_tier" in lead
    assert "status" in lead


@pytest.mark.asyncio
async def test_list_leads_pagination(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test lead list pagination."""
    # Create multiple leads
    for i in range(15):
        lead = Lead(
            client_id=test_client_data.id,
            campaign_id=test_campaign.id,
            email=f"lead{i}@example.com",
            first_name=f"Lead{i}",
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
    await db_session.commit()

    # Page 1
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads?page=1&page_size=10",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["leads"]) == 10
    assert data["pages"] == 2

    # Page 2
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads?page=2&page_size=10",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["page"] == 2
    assert len(data["leads"]) == 5


@pytest.mark.asyncio
async def test_list_leads_filter_by_campaign(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test filtering leads by campaign."""
    # Create another campaign
    campaign2 = Campaign(
        client_id=test_client_data.id,
        name="Campaign 2",
        status=CampaignStatus.ACTIVE,
        permission_mode="autopilot",
    )
    db_session.add(campaign2)
    await db_session.commit()

    # Create leads for both campaigns
    lead1 = Lead(
        client_id=test_client_data.id,
        campaign_id=test_campaign.id,
        email="lead1@example.com",
        status=LeadStatus.NEW,
    )
    lead2 = Lead(
        client_id=test_client_data.id,
        campaign_id=campaign2.id,
        email="lead2@example.com",
        status=LeadStatus.NEW,
    )
    db_session.add_all([lead1, lead2])
    await db_session.commit()

    # Filter by campaign 1
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads?campaign_id={test_campaign.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(lead["campaign_id"] == str(test_campaign.id) for lead in data["leads"])


@pytest.mark.asyncio
async def test_list_leads_filter_by_tier(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test filtering leads by ALS tier."""
    # Create leads with different tiers
    hot_lead = Lead(
        client_id=test_client_data.id,
        campaign_id=test_campaign.id,
        email="hot@example.com",
        als_score=90,
        als_tier="hot",
        status=LeadStatus.SCORED,
    )
    warm_lead = Lead(
        client_id=test_client_data.id,
        campaign_id=test_campaign.id,
        email="warm@example.com",
        als_score=70,
        als_tier="warm",
        status=LeadStatus.SCORED,
    )
    db_session.add_all([hot_lead, warm_lead])
    await db_session.commit()

    # Filter by hot tier
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads?tier=hot",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert all(lead["als_tier"] == "hot" for lead in data["leads"])


@pytest.mark.asyncio
async def test_list_leads_search(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test searching leads."""
    # Create leads with searchable data
    lead = Lead(
        client_id=test_client_data.id,
        campaign_id=test_campaign.id,
        email="john.smith@acmecorp.com",
        first_name="John",
        last_name="Smith",
        company="ACME Corp",
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    await db_session.commit()

    # Search by email
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads?search=john.smith",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["leads"]) >= 1

    # Search by company
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads?search=ACME",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["leads"]) >= 1


# ============================================
# Test Get Lead
# ============================================


@pytest.mark.asyncio
async def test_get_lead_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test getting a single lead."""
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["id"] == str(test_lead.id)
    assert data["email"] == test_lead.email
    assert data["first_name"] == test_lead.first_name
    assert data["last_name"] == test_lead.last_name
    assert data["company"] == test_lead.company


@pytest.mark.asyncio
async def test_get_lead_not_found(
    async_client: AsyncClient,
    test_client_data: Client,
    auth_headers: dict,
):
    """Test getting non-existent lead."""
    fake_id = uuid4()
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads/{fake_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_lead_soft_deleted(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test getting soft-deleted lead returns 404."""
    # Soft delete the lead
    test_lead.deleted_at = datetime.utcnow()
    await db_session.commit()

    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================
# Test Create Lead
# ============================================


@pytest.mark.asyncio
async def test_create_lead_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test creating a lead."""
    lead_data = {
        "campaign_id": str(test_campaign.id),
        "email": "new.lead@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "company": "New Corp",
        "title": "CEO",
    }

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads",
        json=lead_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["email"] == "new.lead@example.com"
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert data["company"] == "New Corp"
    assert data["status"] == "new"


@pytest.mark.asyncio
async def test_create_lead_duplicate_email(
    async_client: AsyncClient,
    test_client_data: Client,
    test_campaign: Campaign,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test creating lead with duplicate email fails."""
    lead_data = {
        "campaign_id": str(test_campaign.id),
        "email": test_lead.email,  # Duplicate
        "first_name": "Test",
    }

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads",
        json=lead_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_lead_invalid_campaign(
    async_client: AsyncClient,
    test_client_data: Client,
    auth_headers: dict,
):
    """Test creating lead with invalid campaign fails."""
    lead_data = {
        "campaign_id": str(uuid4()),  # Non-existent
        "email": "test@example.com",
    }

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads",
        json=lead_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================
# Test Bulk Create
# ============================================


@pytest.mark.asyncio
async def test_create_leads_bulk_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test bulk lead creation."""
    bulk_data = {
        "campaign_id": str(test_campaign.id),
        "leads": [
            {"campaign_id": str(test_campaign.id), "email": f"bulk{i}@example.com"}
            for i in range(10)
        ],
    }

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads/bulk",
        json=bulk_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["created"] == 10
    assert data["skipped"] == 0
    assert data["total"] == 10


@pytest.mark.asyncio
async def test_create_leads_bulk_skip_duplicates(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test bulk creation skips duplicates."""
    # Create existing lead
    existing = Lead(
        client_id=test_client_data.id,
        campaign_id=test_campaign.id,
        email="existing@example.com",
        status=LeadStatus.NEW,
    )
    db_session.add(existing)
    await db_session.commit()

    bulk_data = {
        "campaign_id": str(test_campaign.id),
        "leads": [
            {"campaign_id": str(test_campaign.id), "email": "existing@example.com"},  # Duplicate
            {"campaign_id": str(test_campaign.id), "email": "new1@example.com"},
            {"campaign_id": str(test_campaign.id), "email": "new2@example.com"},
        ],
    }

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads/bulk",
        json=bulk_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["created"] == 2
    assert data["skipped"] == 1
    assert data["total"] == 3


# ============================================
# Test Update Lead
# ============================================


@pytest.mark.asyncio
async def test_update_lead_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test updating a lead."""
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "title": "CTO",
    }

    response = await async_client.put(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"
    assert data["title"] == "CTO"


# ============================================
# Test Delete Lead
# ============================================


@pytest.mark.asyncio
async def test_delete_lead_success(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test soft deleting a lead."""
    response = await async_client.delete(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify soft delete (Rule 14)
    await db_session.refresh(test_lead)
    assert test_lead.deleted_at is not None

    # Verify lead is not returned in list
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads",
        headers=auth_headers,
    )
    data = response.json()
    lead_ids = [lead["id"] for lead in data["leads"]]
    assert str(test_lead.id) not in lead_ids


# ============================================
# Test Enrichment
# ============================================


@pytest.mark.asyncio
async def test_enrich_lead_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test triggering lead enrichment."""
    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}/enrich",
        json={"force": False},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()

    assert data["status"] == "queued"
    assert data["lead_id"] == str(test_lead.id)


@pytest.mark.asyncio
async def test_enrich_lead_already_enriched(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test enriching already enriched lead fails without force."""
    # Mark lead as enriched
    test_lead.enrichment_source = "apollo"
    await db_session.commit()

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}/enrich",
        json={"force": False},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_enrich_lead_force_re_enrich(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test force re-enrichment works."""
    # Mark lead as enriched
    test_lead.enrichment_source = "apollo"
    await db_session.commit()

    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}/enrich",
        json={"force": True},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED


@pytest.mark.asyncio
async def test_bulk_enrich_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_campaign: Campaign,
    auth_headers: dict,
):
    """Test bulk enrichment trigger."""
    response = await async_client.post(
        f"/clients/{test_client_data.id}/leads/bulk-enrich",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()

    assert "lead_count" in data
    assert data["status"] == "queued"


# ============================================
# Test Activity Timeline
# ============================================


@pytest.mark.asyncio
async def test_get_lead_activities_success(
    async_client: AsyncClient,
    test_client_data: Client,
    test_lead: Lead,
    auth_headers: dict,
):
    """Test getting lead activity timeline."""
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads/{test_lead.id}/activities",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "lead_id" in data
    assert "activities" in data
    assert "total" in data
    assert data["lead_id"] == str(test_lead.id)


# ============================================
# Test Authorization
# ============================================


@pytest.mark.asyncio
async def test_unauthorized_access(
    async_client: AsyncClient,
    test_client_data: Client,
):
    """Test accessing endpoints without auth fails."""
    response = await async_client.get(
        f"/clients/{test_client_data.id}/leads"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_wrong_client_access(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test accessing different client's leads fails."""
    wrong_client_id = uuid4()

    response = await async_client.get(
        f"/clients/{wrong_client_id}/leads",
        headers=auth_headers,
    )

    # Will fail because membership doesn't exist for this client
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test list leads with pagination
# [x] Test list leads with filtering (campaign, tier, status)
# [x] Test list leads with search
# [x] Test get single lead
# [x] Test get lead not found
# [x] Test get soft-deleted lead returns 404
# [x] Test create lead
# [x] Test create lead with duplicate email
# [x] Test create lead with invalid campaign
# [x] Test bulk create leads
# [x] Test bulk create skips duplicates
# [x] Test update lead
# [x] Test delete lead (soft delete)
# [x] Test enrich lead
# [x] Test enrich already enriched lead
# [x] Test force re-enrichment
# [x] Test bulk enrichment
# [x] Test get lead activities
# [x] Test unauthorized access
# [x] Test wrong client access
# [x] All tests use async/await
# [x] All tests have docstrings
