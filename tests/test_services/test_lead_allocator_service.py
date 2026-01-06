"""
FILE: tests/test_services/test_lead_allocator_service.py
PURPOSE: Unit tests for Lead Allocator Service
PHASE: 24A (Lead Pool Architecture)
TASK: POOL-015
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.lead_allocator_service import LeadAllocatorService


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def allocator_service(mock_session):
    """Create LeadAllocatorService with mock session."""
    return LeadAllocatorService(mock_session)


@pytest.fixture
def sample_icp_criteria():
    """Sample ICP criteria for allocation."""
    return {
        "industries": ["Technology", "SaaS"],
        "countries": ["Australia"],
        "employee_min": 10,
        "employee_max": 200,
        "seniorities": ["c_suite", "vp", "director"],
        "email_status": "verified",
    }


class TestLeadAllocatorAllocate:
    """Tests for allocation operations."""

    @pytest.mark.asyncio
    async def test_allocate_leads(self, allocator_service, mock_session, sample_icp_criteria):
        """Test allocating leads from pool."""
        client_id = uuid4()
        campaign_id = uuid4()
        pool_id = uuid4()

        # Mock find query result
        find_result = MagicMock()
        find_result.fetchall.return_value = [
            MagicMock(
                id=pool_id,
                email="lead@example.com",
                first_name="John",
                last_name="Doe",
                title="CEO",
                company_name="Acme Inc",
                enrichment_confidence=0.95,
            ),
        ]

        # Mock assignment result
        assign_result = MagicMock()
        assign_row = MagicMock()
        assign_row.id = uuid4()
        assign_result.fetchone.return_value = assign_row

        # Mock update result (for pool status update)
        update_result = MagicMock()

        mock_session.execute.side_effect = [find_result, assign_result, update_result]

        result = await allocator_service.allocate_leads(
            client_id=client_id,
            icp_criteria=sample_icp_criteria,
            count=10,
            campaign_id=campaign_id,
        )

        assert len(result) == 1
        assert result[0]["email"] == "lead@example.com"
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_allocate_leads_empty_pool(self, allocator_service, mock_session, sample_icp_criteria):
        """Test allocation when no matching leads found."""
        client_id = uuid4()

        # Mock empty result
        find_result = MagicMock()
        find_result.fetchall.return_value = []
        mock_session.execute.return_value = find_result

        result = await allocator_service.allocate_leads(
            client_id=client_id,
            icp_criteria=sample_icp_criteria,
            count=10,
        )

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_allocate_validates_count(self, allocator_service, mock_session, sample_icp_criteria):
        """Test that count validation works."""
        client_id = uuid4()

        with pytest.raises(Exception):  # ValidationError
            await allocator_service.allocate_leads(
                client_id=client_id,
                icp_criteria=sample_icp_criteria,
                count=0,  # Invalid
            )

        with pytest.raises(Exception):  # ValidationError
            await allocator_service.allocate_leads(
                client_id=client_id,
                icp_criteria=sample_icp_criteria,
                count=5000,  # Too many
            )


class TestLeadAllocatorAssignment:
    """Tests for assignment operations."""

    @pytest.mark.asyncio
    async def test_get_assignment(self, allocator_service, mock_session):
        """Test getting assignment by pool ID."""
        pool_id = uuid4()
        client_id = uuid4()
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": assignment_id,
            "lead_pool_id": pool_id,
            "client_id": client_id,
            "status": "active",
            "total_touches": 3,
        }
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await allocator_service.get_assignment(pool_id, client_id)

        assert result is not None
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_client_assignments(self, allocator_service, mock_session):
        """Test getting all assignments for a client."""
        client_id = uuid4()

        mock_result = MagicMock()
        mock_rows = [
            MagicMock(_mapping={
                "id": uuid4(),
                "lead_pool_id": uuid4(),
                "client_id": client_id,
                "status": "active",
                "email": "lead1@example.com",
            }),
            MagicMock(_mapping={
                "id": uuid4(),
                "lead_pool_id": uuid4(),
                "client_id": client_id,
                "status": "active",
                "email": "lead2@example.com",
            }),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        results = await allocator_service.get_client_assignments(
            client_id=client_id,
            status="active",
            limit=100,
        )

        assert len(results) == 2


class TestLeadAllocatorRelease:
    """Tests for release operations."""

    @pytest.mark.asyncio
    async def test_release_lead(self, allocator_service, mock_session):
        """Test releasing lead back to pool."""
        assignment_id = uuid4()
        pool_id = uuid4()

        # Mock get assignment result
        get_result = MagicMock()
        get_row = MagicMock()
        get_row.lead_pool_id = pool_id
        get_result.fetchone.return_value = get_row

        # Mock update results
        update_result = MagicMock()
        pool_update_result = MagicMock()

        mock_session.execute.side_effect = [get_result, update_result, pool_update_result]

        result = await allocator_service.release_lead(assignment_id, reason="manual")

        assert result is True
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_release_lead_not_found(self, allocator_service, mock_session):
        """Test releasing non-existent assignment."""
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = await allocator_service.release_lead(assignment_id)

        assert result is False


class TestLeadAllocatorConversion:
    """Tests for conversion operations."""

    @pytest.mark.asyncio
    async def test_mark_converted(self, allocator_service, mock_session):
        """Test marking lead as converted."""
        assignment_id = uuid4()
        pool_id = uuid4()

        # Mock get assignment result
        get_result = MagicMock()
        get_row = MagicMock()
        get_row.lead_pool_id = pool_id
        get_result.fetchone.return_value = get_row

        # Mock update results
        update_result = MagicMock()
        pool_update_result = MagicMock()

        mock_session.execute.side_effect = [get_result, update_result, pool_update_result]

        result = await allocator_service.mark_converted(
            assignment_id,
            conversion_type="meeting_booked",
        )

        assert result is True
        mock_session.commit.assert_called()


class TestLeadAllocatorTracking:
    """Tests for tracking operations."""

    @pytest.mark.asyncio
    async def test_record_touch(self, allocator_service, mock_session):
        """Test recording a touch."""
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = assignment_id
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await allocator_service.record_touch(assignment_id, "email")

        assert result is True
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_record_reply(self, allocator_service, mock_session):
        """Test recording a reply."""
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = assignment_id
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await allocator_service.record_reply(assignment_id, "interested")

        assert result is True
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_set_cooling_period(self, allocator_service, mock_session):
        """Test setting cooling period."""
        assignment_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row.id = assignment_id
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await allocator_service.set_cooling_period(assignment_id, days=7)

        assert result is True
        mock_session.commit.assert_called()


class TestLeadAllocatorStats:
    """Tests for stats operations."""

    @pytest.mark.asyncio
    async def test_get_client_stats(self, allocator_service, mock_session):
        """Test getting client statistics."""
        client_id = uuid4()

        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {
            "client_id": str(client_id),
            "total_assignments": 100,
            "active_assignments": 80,
            "converted_assignments": 15,
            "released_assignments": 5,
            "replied_leads": 30,
            "total_touches": 250,
            "avg_touches_per_lead": 2.5,
        }
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        stats = await allocator_service.get_client_stats(client_id)

        assert stats["total_assignments"] == 100
        assert stats["active_assignments"] == 80

    @pytest.mark.asyncio
    async def test_release_client_leads(self, allocator_service, mock_session):
        """Test releasing all leads for a client."""
        client_id = uuid4()

        # Mock release query
        release_result = MagicMock()
        release_result.fetchall.return_value = [
            MagicMock(lead_pool_id=uuid4()),
            MagicMock(lead_pool_id=uuid4()),
        ]

        # Mock pool update
        pool_update_result = MagicMock()

        mock_session.execute.side_effect = [release_result, pool_update_result]

        result = await allocator_service.release_client_leads(
            client_id=client_id,
            reason="client_cancelled",
        )

        assert result == 2
        mock_session.commit.assert_called()
