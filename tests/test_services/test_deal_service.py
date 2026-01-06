"""
FILE: tests/test_services/test_deal_service.py
PURPOSE: Unit tests for Deal Service
PHASE: 24E (Downstream Outcomes)
TASK: OUTCOME-002
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.services.deal_service import DealService, DEAL_STAGES, LOST_REASONS


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    return session


@pytest.fixture
def deal_service(mock_session):
    """Create DealService with mock session."""
    return DealService(mock_session)


@pytest.fixture
def sample_deal():
    """Sample deal data."""
    return {
        "id": uuid4(),
        "client_id": uuid4(),
        "lead_id": uuid4(),
        "name": "Enterprise Deal - Acme Inc",
        "value": Decimal("50000.00"),
        "currency": "AUD",
        "stage": "qualification",
        "probability": 20,
        "created_at": datetime.utcnow(),
    }


class TestDealServiceCreate:
    """Tests for create operations."""

    @pytest.mark.asyncio
    async def test_create_deal(self, deal_service, mock_session):
        """Test creating a new deal."""
        client_id = uuid4()
        lead_id = uuid4()

        # Mock touches query
        touches_result = MagicMock()
        touches_row = MagicMock()
        touches_row.count = 5
        touches_row.first_channel = "email"
        touches_result.fetchone.return_value = touches_row

        # Mock insert result
        insert_result = MagicMock()
        insert_row = MagicMock()
        insert_row.id = uuid4()
        insert_row._mapping = {
            "id": insert_row.id,
            "client_id": client_id,
            "lead_id": lead_id,
            "name": "Test Deal",
            "value": Decimal("10000"),
            "stage": "qualification",
        }
        insert_result.fetchone.return_value = insert_row

        # Set up mock to return different results for different calls
        mock_session.execute.side_effect = [touches_result, insert_result, MagicMock()]

        result = await deal_service.create(
            client_id=client_id,
            lead_id=lead_id,
            name="Test Deal",
            value=10000,
        )

        assert result is not None
        assert result["name"] == "Test Deal"
        assert mock_session.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_create_deal_invalid_stage(self, deal_service, mock_session):
        """Test creating deal with invalid stage raises error."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await deal_service.create(
                client_id=uuid4(),
                lead_id=uuid4(),
                name="Test Deal",
                stage="invalid_stage",
            )

    @pytest.mark.asyncio
    async def test_create_deal_invalid_probability(self, deal_service, mock_session):
        """Test creating deal with invalid probability raises error."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await deal_service.create(
                client_id=uuid4(),
                lead_id=uuid4(),
                name="Test Deal",
                probability=150,  # Invalid: > 100
            )


class TestDealServiceStage:
    """Tests for stage management."""

    @pytest.mark.asyncio
    async def test_update_stage(self, deal_service, mock_session, sample_deal):
        """Test updating deal stage."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_deal
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {**sample_deal, "stage": "proposal", "probability": 40}
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await deal_service.update_stage(
            deal_id=sample_deal["id"],
            stage="proposal",
        )

        assert result["stage"] == "proposal"
        assert result["probability"] == 40

    @pytest.mark.asyncio
    async def test_update_stage_invalid(self, deal_service, mock_session, sample_deal):
        """Test updating to invalid stage raises error."""
        from src.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await deal_service.update_stage(
                deal_id=sample_deal["id"],
                stage="invalid_stage",
            )

    @pytest.mark.asyncio
    async def test_close_won(self, deal_service, mock_session, sample_deal):
        """Test closing deal as won."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_deal
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_deal,
            "stage": "closed_won",
            "won": True,
            "probability": 100,
            "closed_at": datetime.utcnow(),
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [
            get_result,  # get_by_id
            update_result,  # update
            MagicMock(),  # lead update
            MagicMock(),  # attribution
        ]

        result = await deal_service.close_won(
            deal_id=sample_deal["id"],
            value=60000,
        )

        assert result["stage"] == "closed_won"
        assert result["won"] is True
        assert result["probability"] == 100

    @pytest.mark.asyncio
    async def test_close_lost(self, deal_service, mock_session, sample_deal):
        """Test closing deal as lost."""
        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_deal
        get_result.fetchone.return_value = get_row

        # Mock update result
        update_result = MagicMock()
        update_row = MagicMock()
        update_row._mapping = {
            **sample_deal,
            "stage": "closed_lost",
            "won": False,
            "probability": 0,
            "lost_reason": "price_too_high",
            "closed_at": datetime.utcnow(),
        }
        update_result.fetchone.return_value = update_row

        mock_session.execute.side_effect = [get_result, update_result]

        result = await deal_service.close_lost(
            deal_id=sample_deal["id"],
            lost_reason="price_too_high",
            lost_notes="Customer went with cheaper option",
        )

        assert result["stage"] == "closed_lost"
        assert result["won"] is False
        assert result["lost_reason"] == "price_too_high"

    @pytest.mark.asyncio
    async def test_close_lost_invalid_reason(self, deal_service, mock_session, sample_deal):
        """Test closing with invalid lost reason raises error."""
        from src.exceptions import ValidationError

        # Mock get_by_id
        get_result = MagicMock()
        get_row = MagicMock()
        get_row._mapping = sample_deal
        get_result.fetchone.return_value = get_row
        mock_session.execute.return_value = get_result

        with pytest.raises(ValidationError):
            await deal_service.close_lost(
                deal_id=sample_deal["id"],
                lost_reason="invalid_reason",
            )


class TestDealServiceQueries:
    """Tests for query operations."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, deal_service, mock_session, sample_deal):
        """Test getting deal by ID."""
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = sample_deal
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        result = await deal_service.get_by_id(sample_deal["id"])

        assert result is not None
        assert result["id"] == sample_deal["id"]

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, deal_service, mock_session):
        """Test getting non-existent deal returns None."""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute.return_value = mock_result

        result = await deal_service.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_list_for_client(self, deal_service, mock_session, sample_deal):
        """Test listing deals for client."""
        mock_result = MagicMock()
        mock_rows = [MagicMock(_mapping=sample_deal), MagicMock(_mapping=sample_deal)]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        result = await deal_service.list_for_client(
            client_id=sample_deal["client_id"],
            limit=50,
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_pipeline(self, deal_service, mock_session):
        """Test getting pipeline summary."""
        mock_result = MagicMock()
        mock_rows = [
            MagicMock(stage="qualification", count=5, total_value=Decimal("50000"), avg_probability=20),
            MagicMock(stage="proposal", count=3, total_value=Decimal("30000"), avg_probability=40),
        ]
        mock_result.fetchall.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        result = await deal_service.get_pipeline(client_id=uuid4())

        assert "stages" in result
        assert "total_count" in result
        assert "total_value" in result
        assert "weighted_value" in result
        assert result["total_count"] == 8


class TestDealServiceSync:
    """Tests for external CRM sync."""

    @pytest.mark.asyncio
    async def test_sync_from_hubspot(self, deal_service, mock_session):
        """Test syncing deal from HubSpot."""
        client_id = uuid4()
        lead_id = uuid4()

        # Mock get_by_external_id returns None (new deal)
        get_ext_result = MagicMock()
        get_ext_result.fetchone.return_value = None

        # Mock lead lookup by email
        lead_result = MagicMock()
        lead_row = MagicMock()
        lead_row.id = lead_id
        lead_result.fetchone.return_value = lead_row

        # Mock touches query
        touches_result = MagicMock()
        touches_row = MagicMock()
        touches_row.count = 3
        touches_row.first_channel = "email"
        touches_result.fetchone.return_value = touches_row

        # Mock insert result
        insert_result = MagicMock()
        insert_row = MagicMock()
        insert_row.id = uuid4()
        insert_row._mapping = {
            "id": insert_row.id,
            "client_id": client_id,
            "lead_id": lead_id,
            "name": "HubSpot Deal",
            "stage": "qualification",
        }
        insert_result.fetchone.return_value = insert_row

        mock_session.execute.side_effect = [
            get_ext_result,  # get_by_external_id
            lead_result,  # find lead by email
            touches_result,  # count touches
            insert_result,  # insert deal
            MagicMock(),  # update lead
        ]

        result = await deal_service.sync_from_external(
            client_id=client_id,
            external_crm="hubspot",
            external_deal_id="12345",
            data={
                "name": "HubSpot Deal",
                "value": 50000,
                "stage": "qualification",
                "contact_email": "john@example.com",
            },
        )

        assert result is not None
        assert result["name"] == "HubSpot Deal"


class TestDealStages:
    """Tests for stage constants."""

    def test_valid_stages(self):
        """Test all expected stages are defined."""
        expected_stages = [
            "qualification",
            "proposal",
            "negotiation",
            "verbal_commit",
            "contract_sent",
            "closed_won",
            "closed_lost",
        ]
        assert DEAL_STAGES == expected_stages

    def test_valid_lost_reasons(self):
        """Test all expected lost reasons are defined."""
        expected_reasons = [
            "price_too_high",
            "chose_competitor",
            "no_budget",
            "timing_not_right",
            "no_decision",
            "champion_left",
            "project_cancelled",
            "went_silent",
            "bad_fit",
            "other",
        ]
        assert LOST_REASONS == expected_reasons


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test create operations
# [x] Test invalid stage/probability validation
# [x] Test stage updates
# [x] Test close_won
# [x] Test close_lost
# [x] Test invalid lost reason validation
# [x] Test get_by_id
# [x] Test list_for_client
# [x] Test get_pipeline
# [x] Test sync_from_external
# [x] Test constants
