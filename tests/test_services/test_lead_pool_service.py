"""
FILE: tests/test_services/test_lead_pool_service.py
PURPOSE: Unit tests for Lead Pool Service
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-015
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.lead_pool_service import LeadPoolService


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def pool_service(mock_session):
    """Create LeadPoolService with mock session."""
    return LeadPoolService(mock_session)


@pytest.fixture
def sample_pool_lead():
    """Sample pool lead data."""
    return {
        "email": "john@example.com",
        "email_status": "verified",
        "first_name": "John",
        "last_name": "Doe",
        "title": "CEO",
        "seniority": "c_suite",
        "company_name": "Acme Inc",
        "company_domain": "acme.com",
        "company_industry": "Technology",
        "company_employee_count": 50,
        "company_country": "Australia",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "phone": "+61400000000",
    }


class TestLeadPoolServiceCreate:
    """Tests for create operations."""

    @pytest.mark.asyncio
    async def test_create_pool_lead(self, pool_service, mock_session, sample_pool_lead):
        """Test creating a new pool lead."""
        # Mock the execute result
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = uuid4()
        mock_row.email = sample_pool_lead["email"]
        mock_row._mapping = {**sample_pool_lead, "id": mock_row.id}
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await pool_service.create(sample_pool_lead)

        assert result is not None
        assert result["email"] == sample_pool_lead["email"]
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_or_update_existing(self, pool_service, mock_session, sample_pool_lead):
        """Test create_or_update with existing lead."""
        pool_id = uuid4()

        # First call returns existing lead
        existing_result = MagicMock()
        existing_row = MagicMock()
        existing_row.id = pool_id
        existing_row._mapping = {"id": pool_id, **sample_pool_lead}
        existing_result.fetchone.return_value = existing_row

        # Update call result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {"id": pool_id, **sample_pool_lead, "title": "CTO"}
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [existing_result, update_result]

        result = await pool_service.create_or_update(
            email=sample_pool_lead["email"],
            data={**sample_pool_lead, "title": "CTO"},
        )

        assert result is not None
        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_create_validates_email(self, pool_service, mock_session):
        """Test that create validates email."""
        with pytest.raises(ValueError, match="Email is required"):
            await pool_service.create({"first_name": "John"})


class TestLeadPoolServiceRead:
    """Tests for read operations."""

    @pytest.mark.asyncio
    async def test_get_by_email(self, pool_service, mock_session, sample_pool_lead):
        """Test getting lead by email."""
        pool_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"id": pool_id, **sample_pool_lead}
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await pool_service.get_by_email("john@example.com")

        assert result is not None
        assert result["email"] == "john@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, pool_service, mock_session):
        """Test getting non-existent lead by email."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = await pool_service.get_by_email("nonexistent@example.com")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, pool_service, mock_session, sample_pool_lead):
        """Test getting lead by UUID."""
        pool_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"id": pool_id, **sample_pool_lead}
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await pool_service.get_by_id(pool_id)

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_available(self, pool_service, mock_session, sample_pool_lead):
        """Test searching for available leads."""
        pool_id = uuid4()

        mock_result = MagicMock()
        mock_rows = [
            MagicMock(_mapping={"id": pool_id, **sample_pool_lead, "pool_status": "available"}),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        results = await pool_service.search_available(
            industries=["Technology"],
            countries=["Australia"],
            limit=10,
        )

        assert len(results) == 1
        assert results[0]["pool_status"] == "available"


class TestLeadPoolServiceUpdate:
    """Tests for update operations."""

    @pytest.mark.asyncio
    async def test_update_pool_lead(self, pool_service, mock_session, sample_pool_lead):
        """Test updating a pool lead."""
        pool_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"id": pool_id, **sample_pool_lead, "title": "CTO"}
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await pool_service.update(pool_id, {"title": "CTO"})

        assert result is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_bounced(self, pool_service, mock_session):
        """Test marking lead as bounced."""
        pool_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = pool_id
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await pool_service.mark_bounced(pool_id)

        assert result is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_unsubscribed(self, pool_service, mock_session):
        """Test marking lead as unsubscribed."""
        pool_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = pool_id
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await pool_service.mark_unsubscribed(pool_id)

        assert result is True


class TestLeadPoolServiceStats:
    """Tests for stats operations."""

    @pytest.mark.asyncio
    async def test_get_pool_stats(self, pool_service, mock_session):
        """Test getting pool statistics."""
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "total_leads": 1000,
            "available": 500,
            "assigned": 400,
            "converted": 80,
            "bounced": 15,
            "unsubscribed": 5,
        }
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        stats = await pool_service.get_pool_stats()

        assert stats["total_leads"] == 1000
        assert stats["available"] == 500
        assert stats["assigned"] == 400


class TestLeadPoolServiceBulk:
    """Tests for bulk operations."""

    @pytest.mark.asyncio
    async def test_bulk_create(self, pool_service, mock_session, sample_pool_lead):
        """Test bulk creating pool leads."""
        leads = [
            {**sample_pool_lead, "email": "lead1@example.com"},
            {**sample_pool_lead, "email": "lead2@example.com"},
            {**sample_pool_lead, "email": "lead3@example.com"},
        ]

        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_session.execute.return_value = mock_result

        result = await pool_service.bulk_create(leads)

        assert result["inserted"] == 3
        mock_session.commit.assert_called()
