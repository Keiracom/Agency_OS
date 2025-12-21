"""
FILE: tests/test_engines/test_reporter.py
PURPOSE: Unit tests for Reporter engine (metrics aggregation)
PHASE: 4 (Engines)
TASK: ENG-012
"""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.reporter import ReporterEngine, get_reporter_engine
from src.models.base import ChannelType, LeadStatus


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_campaign():
    """Create mock campaign object."""
    campaign = MagicMock()
    campaign.id = uuid4()
    campaign.name = "Q1 Outreach"
    campaign.client_id = uuid4()
    campaign.deleted_at = None
    return campaign


@pytest.fixture
def mock_client():
    """Create mock client object."""
    client = MagicMock()
    client.id = uuid4()
    client.name = "Acme Corp"
    client.subscription_status = "active"
    client.deleted_at = None
    return client


@pytest.fixture
def mock_lead():
    """Create mock lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = "john@acme.com"
    lead.first_name = "John"
    lead.last_name = "Doe"
    lead.full_name = "John Doe"
    lead.als_score = 85
    lead.als_tier = "hot"
    lead.status = LeadStatus.IN_SEQUENCE
    lead.deleted_at = None
    return lead


@pytest.fixture
def reporter_engine():
    """Create Reporter engine instance."""
    return ReporterEngine()


def create_mock_activity(
    campaign_id,
    lead_id,
    client_id,
    channel="email",
    action="sent",
    created_at=None,
):
    """Helper to create mock activity."""
    activity = MagicMock()
    activity.id = uuid4()
    activity.campaign_id = campaign_id
    activity.lead_id = lead_id
    activity.client_id = client_id
    activity.channel = MagicMock()
    activity.channel.value = channel
    activity.action = action
    activity.created_at = created_at or datetime.utcnow()
    activity.sequence_step = 1
    return activity


# ============================================
# Engine Properties Tests
# ============================================


class TestReporterEngineProperties:
    """Test Reporter engine properties."""

    def test_engine_name(self, reporter_engine):
        """Test engine name property."""
        assert reporter_engine.name == "reporter"

    def test_singleton_instance(self):
        """Test singleton pattern."""
        engine1 = get_reporter_engine()
        engine2 = get_reporter_engine()
        assert engine1 is engine2


# ============================================
# Campaign Metrics Tests
# ============================================


class TestCampaignMetrics:
    """Test campaign metrics aggregation."""

    @pytest.mark.asyncio
    async def test_get_campaign_metrics_success(
        self, reporter_engine, mock_db_session, mock_campaign
    ):
        """Test successful campaign metrics retrieval."""
        with patch.object(reporter_engine, "get_campaign_by_id", return_value=mock_campaign):
            # Mock activities
            activities = [
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "delivered"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "opened"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "clicked"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "replied"),
            ]

            # Mock database query
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_campaign_metrics(
                db=mock_db_session,
                campaign_id=mock_campaign.id,
            )

            assert result.success is True
            assert result.data["campaign_id"] == str(mock_campaign.id)
            assert result.data["campaign_name"] == mock_campaign.name
            assert "email" in result.data["channels"]
            assert result.data["channels"]["email"]["sent"] == 1
            assert result.data["channels"]["email"]["delivered"] == 1
            assert result.data["channels"]["email"]["opened"] == 1
            assert result.data["channels"]["email"]["clicked"] == 1
            assert result.data["channels"]["email"]["replied"] == 1

    @pytest.mark.asyncio
    async def test_get_campaign_metrics_rate_calculations(
        self, reporter_engine, mock_db_session, mock_campaign
    ):
        """Test campaign metrics rate calculations."""
        with patch.object(reporter_engine, "get_campaign_by_id", return_value=mock_campaign):
            # Create 10 sent, 9 delivered, 5 opened, 2 clicked
            activities = []
            for _ in range(10):
                activities.append(create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "sent"))
            for _ in range(9):
                activities.append(create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "delivered"))
            for _ in range(5):
                activities.append(create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "opened"))
            for _ in range(2):
                activities.append(create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "clicked"))

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_campaign_metrics(
                db=mock_db_session,
                campaign_id=mock_campaign.id,
            )

            assert result.success is True
            email_stats = result.data["channels"]["email"]

            # Delivery rate: 9/10 = 90%
            assert email_stats["delivery_rate"] == 90.0

            # Open rate: 5/9 = 55.56%
            assert abs(email_stats["open_rate"] - 55.56) < 0.1

            # Click rate: 2/5 = 40%
            assert email_stats["click_rate"] == 40.0

    @pytest.mark.asyncio
    async def test_get_campaign_metrics_multiple_channels(
        self, reporter_engine, mock_db_session, mock_campaign
    ):
        """Test campaign metrics with multiple channels."""
        with patch.object(reporter_engine, "get_campaign_by_id", return_value=mock_campaign):
            activities = [
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "sms", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "linkedin", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "email", "replied"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_campaign.client_id, "sms", "replied"),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_campaign_metrics(
                db=mock_db_session,
                campaign_id=mock_campaign.id,
            )

            assert result.success is True
            assert "email" in result.data["channels"]
            assert "sms" in result.data["channels"]
            assert "linkedin" in result.data["channels"]
            assert result.data["overall"]["total_sent"] == 3
            assert result.data["overall"]["total_replied"] == 2

    @pytest.mark.asyncio
    async def test_get_campaign_metrics_date_range(
        self, reporter_engine, mock_db_session, mock_campaign
    ):
        """Test campaign metrics with date range."""
        with patch.object(reporter_engine, "get_campaign_by_id", return_value=mock_campaign):
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db_session.execute.return_value = mock_result

            start = date(2025, 1, 1)
            end = date(2025, 1, 31)

            result = await reporter_engine.get_campaign_metrics(
                db=mock_db_session,
                campaign_id=mock_campaign.id,
                start_date=start,
                end_date=end,
            )

            assert result.success is True
            assert result.data["date_range"]["start"] == "2025-01-01"
            assert result.data["date_range"]["end"] == "2025-01-31"


# ============================================
# Client Metrics Tests
# ============================================


class TestClientMetrics:
    """Test client metrics aggregation."""

    @pytest.mark.asyncio
    async def test_get_client_metrics_success(
        self, reporter_engine, mock_db_session, mock_client, mock_campaign
    ):
        """Test successful client metrics retrieval."""
        with patch.object(reporter_engine, "get_client_by_id", return_value=mock_client):
            # Mock campaigns query
            campaigns_result = MagicMock()
            campaigns_result.scalars.return_value.all.return_value = [mock_campaign]

            # Mock activities query
            activities = [
                create_mock_activity(mock_campaign.id, uuid4(), mock_client.id, "email", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_client.id, "email", "delivered"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_client.id, "email", "replied"),
            ]
            activities_result = MagicMock()
            activities_result.scalars.return_value.all.return_value = activities

            # Mock execute to return different results based on query
            mock_db_session.execute.side_effect = [campaigns_result, activities_result]

            result = await reporter_engine.get_client_metrics(
                db=mock_db_session,
                client_id=mock_client.id,
            )

            assert result.success is True
            assert result.data["client_id"] == str(mock_client.id)
            assert result.data["client_name"] == mock_client.name
            assert result.data["campaigns_count"] == 1
            assert result.data["overall"]["total_sent"] == 1
            assert result.data["overall"]["total_replied"] == 1

    @pytest.mark.asyncio
    async def test_get_client_metrics_per_campaign_summary(
        self, reporter_engine, mock_db_session, mock_client, mock_campaign
    ):
        """Test client metrics includes per-campaign summary."""
        with patch.object(reporter_engine, "get_client_by_id", return_value=mock_client):
            campaigns_result = MagicMock()
            campaigns_result.scalars.return_value.all.return_value = [mock_campaign]

            activities = [
                create_mock_activity(mock_campaign.id, uuid4(), mock_client.id, "email", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_client.id, "email", "sent"),
                create_mock_activity(mock_campaign.id, uuid4(), mock_client.id, "email", "replied"),
            ]
            activities_result = MagicMock()
            activities_result.scalars.return_value.all.return_value = activities

            mock_db_session.execute.side_effect = [campaigns_result, activities_result]

            result = await reporter_engine.get_client_metrics(
                db=mock_db_session,
                client_id=mock_client.id,
            )

            assert result.success is True
            assert len(result.data["campaigns"]) == 1
            campaign_summary = result.data["campaigns"][0]
            assert campaign_summary["id"] == str(mock_campaign.id)
            assert campaign_summary["name"] == mock_campaign.name
            assert campaign_summary["sent"] == 2
            assert campaign_summary["replied"] == 1
            assert campaign_summary["reply_rate"] == 50.0


# ============================================
# ALS Distribution Tests
# ============================================


class TestALSDistribution:
    """Test ALS tier distribution."""

    @pytest.mark.asyncio
    async def test_get_als_distribution_campaign(
        self, reporter_engine, mock_db_session
    ):
        """Test ALS distribution for a campaign."""
        campaign_id = uuid4()

        # Mock query result
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("hot", 5),
            ("warm", 10),
            ("cool", 15),
            ("cold", 8),
            ("dead", 2),
        ]
        mock_db_session.execute.return_value = mock_result

        result = await reporter_engine.get_als_distribution(
            db=mock_db_session,
            campaign_id=campaign_id,
        )

        assert result.success is True
        assert result.data["distribution"]["hot"] == 5
        assert result.data["distribution"]["warm"] == 10
        assert result.data["distribution"]["cool"] == 15
        assert result.data["total_leads"] == 40
        assert result.data["percentages"]["hot"] == 12.5  # 5/40 = 12.5%

    @pytest.mark.asyncio
    async def test_get_als_distribution_client(
        self, reporter_engine, mock_db_session
    ):
        """Test ALS distribution for a client."""
        client_id = uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("hot", 10),
            ("warm", 20),
        ]
        mock_db_session.execute.return_value = mock_result

        result = await reporter_engine.get_als_distribution(
            db=mock_db_session,
            client_id=client_id,
        )

        assert result.success is True
        assert result.data["total_leads"] == 30
        assert result.data["distribution"]["hot"] == 10
        assert result.data["distribution"]["warm"] == 20

    @pytest.mark.asyncio
    async def test_get_als_distribution_requires_filter(
        self, reporter_engine, mock_db_session
    ):
        """Test ALS distribution requires campaign_id or client_id."""
        result = await reporter_engine.get_als_distribution(
            db=mock_db_session,
        )

        assert result.success is False
        assert "campaign_id" in result.error or "client_id" in result.error


# ============================================
# Lead Engagement Tests
# ============================================


class TestLeadEngagement:
    """Test lead engagement metrics."""

    @pytest.mark.asyncio
    async def test_get_lead_engagement_success(
        self, reporter_engine, mock_db_session, mock_lead
    ):
        """Test successful lead engagement retrieval."""
        with patch.object(reporter_engine, "get_lead_by_id", return_value=mock_lead):
            activities = [
                create_mock_activity(uuid4(), mock_lead.id, uuid4(), "email", "sent", datetime.utcnow() - timedelta(days=2)),
                create_mock_activity(uuid4(), mock_lead.id, uuid4(), "email", "opened", datetime.utcnow() - timedelta(days=1)),
                create_mock_activity(uuid4(), mock_lead.id, uuid4(), "email", "clicked", datetime.utcnow() - timedelta(hours=12)),
                create_mock_activity(uuid4(), mock_lead.id, uuid4(), "email", "replied", datetime.utcnow()),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_lead_engagement(
                db=mock_db_session,
                lead_id=mock_lead.id,
            )

            assert result.success is True
            assert result.data["lead_id"] == str(mock_lead.id)
            assert result.data["als_score"] == 85
            assert result.data["als_tier"] == "hot"
            assert result.data["engagement_summary"]["total_touches"] == 4
            assert result.data["engagement_summary"]["reply_count"] == 1
            assert result.data["engagement_summary"]["open_count"] == 1
            assert result.data["engagement_summary"]["click_count"] == 1
            assert result.data["engagement_summary"]["is_engaged"] is True

    @pytest.mark.asyncio
    async def test_get_lead_engagement_timeline(
        self, reporter_engine, mock_db_session, mock_lead
    ):
        """Test lead engagement includes timeline."""
        with patch.object(reporter_engine, "get_lead_by_id", return_value=mock_lead):
            activities = [
                create_mock_activity(uuid4(), mock_lead.id, uuid4(), "email", "sent"),
                create_mock_activity(uuid4(), mock_lead.id, uuid4(), "sms", "sent"),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_lead_engagement(
                db=mock_db_session,
                lead_id=mock_lead.id,
            )

            assert result.success is True
            assert len(result.data["timeline"]) == 2
            assert "email" in result.data["engagement_summary"]["channels_used"]
            assert "sms" in result.data["engagement_summary"]["channels_used"]


# ============================================
# Daily Activity Tests
# ============================================


class TestDailyActivity:
    """Test daily activity metrics."""

    @pytest.mark.asyncio
    async def test_get_daily_activity_success(
        self, reporter_engine, mock_db_session, mock_client
    ):
        """Test successful daily activity retrieval."""
        with patch.object(reporter_engine, "validate_client_active", return_value=True):
            # Create activities at different hours
            now = datetime.utcnow()
            activities = [
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "email", "sent", now.replace(hour=9)),
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "email", "sent", now.replace(hour=9)),
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "sms", "sent", now.replace(hour=14)),
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "email", "opened", now.replace(hour=15)),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_daily_activity(
                db=mock_db_session,
                client_id=mock_client.id,
            )

            assert result.success is True
            assert result.data["summary"]["total_activities"] == 4
            assert result.data["summary"]["sent"] == 3
            assert result.data["summary"]["opened"] == 1
            assert 9 in result.data["hourly_breakdown"]
            assert result.data["hourly_breakdown"][9] == 2
            assert result.metadata["peak_hour"] == 9

    @pytest.mark.asyncio
    async def test_get_daily_activity_by_channel(
        self, reporter_engine, mock_db_session, mock_client
    ):
        """Test daily activity breakdown by channel."""
        with patch.object(reporter_engine, "validate_client_active", return_value=True):
            activities = [
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "email", "sent"),
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "email", "sent"),
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "sms", "sent"),
                create_mock_activity(uuid4(), uuid4(), mock_client.id, "linkedin", "sent"),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = activities
            mock_db_session.execute.return_value = mock_result

            result = await reporter_engine.get_daily_activity(
                db=mock_db_session,
                client_id=mock_client.id,
            )

            assert result.success is True
            assert result.data["by_channel"]["email"] == 2
            assert result.data["by_channel"]["sms"] == 1
            assert result.data["by_channel"]["linkedin"] == 1


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties
# [x] Test singleton pattern
# [x] Test campaign metrics success
# [x] Test campaign metrics rate calculations
# [x] Test campaign metrics multiple channels
# [x] Test campaign metrics date range
# [x] Test client metrics success
# [x] Test client metrics per-campaign summary
# [x] Test ALS distribution for campaign
# [x] Test ALS distribution for client
# [x] Test ALS distribution requires filter
# [x] Test lead engagement success
# [x] Test lead engagement timeline
# [x] Test daily activity success
# [x] Test daily activity by channel
