"""
FILE: tests/test_engines/test_scorer.py
PURPOSE: Unit tests for Scorer engine (ALS calculation)
PHASE: 4 (Engines)
TASK: ENG-003
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.scorer import (
    DEDUCTION_BAD_TITLE,
    DEDUCTION_BOUNCED,
    SCORE_EMAIL_VERIFIED,
    SCORE_EMPLOYEE_COUNT_IDEAL,
    SCORE_HIRING,
    SCORE_INDUSTRY_MATCH,
    SCORE_LINKEDIN,
    SCORE_NEW_ROLE,
    SCORE_PHONE,
    SCORE_COUNTRY_AUSTRALIA,
    ScorerEngine,
    get_scorer_engine,
    TIER_HOT,
    TIER_WARM,
    TIER_COOL,
    TIER_COLD,
)
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
def mock_lead():
    """Create mock lead with basic data."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = "john.doe@acme.com"
    lead.email_verified = True
    lead.phone = "+61400123456"
    lead.phone_verified = True
    lead.first_name = "John"
    lead.last_name = "Doe"
    lead.title = "CEO"
    lead.company = "Acme Inc"
    lead.linkedin_url = "https://linkedin.com/in/johndoe"
    lead.personal_email = "john@personal.com"
    lead.domain = "acme.com"
    lead.organization_industry = "Technology"
    lead.organization_employee_count = 25
    lead.organization_country = "Australia"
    lead.organization_is_hiring = True
    lead.organization_latest_funding_date = date.today() - timedelta(days=90)
    lead.employment_start_date = date.today() - timedelta(days=60)
    lead.bounce_count = 0
    lead.status = LeadStatus.ENRICHED
    return lead


@pytest.fixture
def scorer_engine():
    """Create Scorer engine instance."""
    return ScorerEngine()


# ============================================
# Engine Properties Tests
# ============================================


class TestScorerEngineProperties:
    """Test Scorer engine properties."""

    def test_engine_name(self, scorer_engine):
        """Test engine name property."""
        assert scorer_engine.name == "scorer"

    def test_singleton_instance(self):
        """Test singleton pattern."""
        engine1 = get_scorer_engine()
        engine2 = get_scorer_engine()
        assert engine1 is engine2


# ============================================
# Data Quality Scoring Tests
# ============================================


class TestDataQualityScoring:
    """Test Data Quality component (max 20 points)."""

    def test_full_data_quality_score(self, scorer_engine, mock_lead):
        """Test maximum data quality score."""
        score = scorer_engine._score_data_quality(mock_lead)
        assert score == 20  # Max score

    def test_email_verified_points(self, scorer_engine, mock_lead):
        """Test email verified gives full points."""
        mock_lead.phone = None
        mock_lead.phone_verified = False
        mock_lead.linkedin_url = None
        mock_lead.personal_email = None

        score = scorer_engine._score_data_quality(mock_lead)
        assert score == SCORE_EMAIL_VERIFIED

    def test_unverified_email_partial_points(self, scorer_engine, mock_lead):
        """Test unverified email gives partial points."""
        mock_lead.email_verified = False
        mock_lead.phone = None
        mock_lead.linkedin_url = None
        mock_lead.personal_email = None

        score = scorer_engine._score_data_quality(mock_lead)
        assert score == 4  # Partial credit

    def test_phone_points(self, scorer_engine, mock_lead):
        """Test phone number adds points."""
        mock_lead.email_verified = False
        mock_lead.email = None
        mock_lead.linkedin_url = None
        mock_lead.personal_email = None
        mock_lead.phone_verified = True

        score = scorer_engine._score_data_quality(mock_lead)
        assert score == SCORE_PHONE

    def test_linkedin_points(self, scorer_engine, mock_lead):
        """Test LinkedIn URL adds points."""
        mock_lead.email = None
        mock_lead.email_verified = False
        mock_lead.phone = None
        mock_lead.personal_email = None

        score = scorer_engine._score_data_quality(mock_lead)
        assert score == SCORE_LINKEDIN


# ============================================
# Authority Scoring Tests
# ============================================


class TestAuthorityScoring:
    """Test Authority component (max 25 points)."""

    def test_ceo_gets_max_points(self, scorer_engine, mock_lead):
        """Test CEO title gets maximum points."""
        mock_lead.title = "CEO"
        score = scorer_engine._score_authority(mock_lead)
        assert score == 25

    def test_founder_gets_max_points(self, scorer_engine, mock_lead):
        """Test Founder title gets maximum points."""
        mock_lead.title = "Founder & CEO"
        score = scorer_engine._score_authority(mock_lead)
        assert score == 25

    def test_vp_gets_18_points(self, scorer_engine, mock_lead):
        """Test VP title gets 18 points."""
        mock_lead.title = "Vice President of Sales"
        score = scorer_engine._score_authority(mock_lead)
        assert score == 18

    def test_director_gets_15_points(self, scorer_engine, mock_lead):
        """Test Director title gets 15 points."""
        mock_lead.title = "Director of Marketing"
        score = scorer_engine._score_authority(mock_lead)
        assert score == 15

    def test_manager_gets_7_points(self, scorer_engine, mock_lead):
        """Test Manager title gets 7 points."""
        mock_lead.title = "Marketing Manager"
        score = scorer_engine._score_authority(mock_lead)
        assert score == 7

    def test_no_title_gets_zero(self, scorer_engine, mock_lead):
        """Test no title gets zero points."""
        mock_lead.title = None
        score = scorer_engine._score_authority(mock_lead)
        assert score == 0


# ============================================
# Company Fit Scoring Tests
# ============================================


class TestCompanyFitScoring:
    """Test Company Fit component (max 25 points)."""

    def test_full_company_fit_score(self, scorer_engine, mock_lead):
        """Test maximum company fit score."""
        mock_lead.organization_industry = "Technology"
        mock_lead.organization_employee_count = 25
        mock_lead.organization_country = "Australia"

        score = scorer_engine._score_company_fit(mock_lead)
        assert score == 25  # Max score

    def test_target_industry_points(self, scorer_engine, mock_lead):
        """Test target industry gives points."""
        mock_lead.organization_employee_count = None
        mock_lead.organization_country = None

        score = scorer_engine._score_company_fit(mock_lead)
        assert score == SCORE_INDUSTRY_MATCH

    def test_ideal_employee_count_points(self, scorer_engine, mock_lead):
        """Test ideal employee count (5-50) gives full points."""
        mock_lead.organization_industry = None
        mock_lead.organization_country = None
        mock_lead.organization_employee_count = 30

        score = scorer_engine._score_company_fit(mock_lead)
        assert score == SCORE_EMPLOYEE_COUNT_IDEAL

    def test_medium_company_partial_points(self, scorer_engine, mock_lead):
        """Test medium company (51-200) gives partial points."""
        mock_lead.organization_industry = None
        mock_lead.organization_country = None
        mock_lead.organization_employee_count = 100

        score = scorer_engine._score_company_fit(mock_lead)
        assert score == 5  # Partial credit

    def test_australia_gives_points(self, scorer_engine, mock_lead):
        """Test Australia location gives points."""
        mock_lead.organization_industry = None
        mock_lead.organization_employee_count = None

        score = scorer_engine._score_company_fit(mock_lead)
        assert score == SCORE_COUNTRY_AUSTRALIA


# ============================================
# Timing Scoring Tests
# ============================================


class TestTimingScoring:
    """Test Timing component (max 15 points)."""

    def test_full_timing_score(self, scorer_engine, mock_lead):
        """Test maximum timing score."""
        mock_lead.employment_start_date = date.today() - timedelta(days=60)
        mock_lead.organization_is_hiring = True
        mock_lead.organization_latest_funding_date = date.today() - timedelta(days=90)

        score = scorer_engine._score_timing(mock_lead)
        assert score == 15  # Max score

    def test_new_role_points(self, scorer_engine, mock_lead):
        """Test new role (< 6 months) gives points."""
        mock_lead.employment_start_date = date.today() - timedelta(days=90)
        mock_lead.organization_is_hiring = False
        mock_lead.organization_latest_funding_date = None

        score = scorer_engine._score_timing(mock_lead)
        assert score == SCORE_NEW_ROLE

    def test_hiring_points(self, scorer_engine, mock_lead):
        """Test company hiring gives points."""
        mock_lead.employment_start_date = None
        mock_lead.organization_is_hiring = True
        mock_lead.organization_latest_funding_date = None

        score = scorer_engine._score_timing(mock_lead)
        assert score == SCORE_HIRING


# ============================================
# Risk Scoring Tests
# ============================================


class TestRiskScoring:
    """Test Risk component (15 base with deductions)."""

    def test_no_risk_full_points(self, scorer_engine, mock_lead):
        """Test no risk factors gives full 15 points."""
        mock_lead.bounce_count = 0
        mock_lead.status = LeadStatus.ENRICHED
        mock_lead.domain = "safe.com"
        mock_lead.title = "CEO"

        score = scorer_engine._score_risk(mock_lead)
        assert score == 15

    def test_bounced_deduction(self, scorer_engine, mock_lead):
        """Test bounced email causes deduction."""
        mock_lead.bounce_count = 1

        score = scorer_engine._score_risk(mock_lead)
        assert score == 15 + DEDUCTION_BOUNCED  # 15 - 10 = 5

    def test_bad_title_deduction(self, scorer_engine, mock_lead):
        """Test bad title causes deduction."""
        mock_lead.title = "Marketing Intern"

        score = scorer_engine._score_risk(mock_lead)
        assert score == 15 + DEDUCTION_BAD_TITLE  # 15 - 5 = 10

    def test_competitor_domain_deduction(self, scorer_engine, mock_lead):
        """Test competitor domain causes deduction."""
        mock_lead.domain = "competitor.com"

        score = scorer_engine._score_risk(
            mock_lead,
            competitor_domains=["competitor.com"],
        )
        assert score == 0  # 15 - 15 = 0


# ============================================
# Tier Assignment Tests
# ============================================


class TestTierAssignment:
    """Test tier assignment logic."""

    def test_hot_tier(self, scorer_engine):
        """Test hot tier assignment (85-100)."""
        assert scorer_engine._get_tier(100) == "hot"
        assert scorer_engine._get_tier(85) == "hot"
        assert scorer_engine._get_tier(90) == "hot"

    def test_warm_tier(self, scorer_engine):
        """Test warm tier assignment (60-84)."""
        assert scorer_engine._get_tier(84) == "warm"
        assert scorer_engine._get_tier(60) == "warm"
        assert scorer_engine._get_tier(72) == "warm"

    def test_cool_tier(self, scorer_engine):
        """Test cool tier assignment (35-59)."""
        assert scorer_engine._get_tier(59) == "cool"
        assert scorer_engine._get_tier(35) == "cool"
        assert scorer_engine._get_tier(45) == "cool"

    def test_cold_tier(self, scorer_engine):
        """Test cold tier assignment (20-34)."""
        assert scorer_engine._get_tier(34) == "cold"
        assert scorer_engine._get_tier(20) == "cold"
        assert scorer_engine._get_tier(25) == "cold"

    def test_dead_tier(self, scorer_engine):
        """Test dead tier assignment (0-19)."""
        assert scorer_engine._get_tier(19) == "dead"
        assert scorer_engine._get_tier(0) == "dead"
        assert scorer_engine._get_tier(10) == "dead"


# ============================================
# Channel Assignment Tests
# ============================================


class TestChannelAssignment:
    """Test channel assignment per tier."""

    def test_hot_tier_all_channels(self, scorer_engine):
        """Test hot tier gets all channels."""
        channels = scorer_engine._get_channels_for_tier("hot")
        assert len(channels) == 5
        assert ChannelType.EMAIL in channels
        assert ChannelType.SMS in channels
        assert ChannelType.LINKEDIN in channels
        assert ChannelType.VOICE in channels
        assert ChannelType.MAIL in channels

    def test_warm_tier_channels(self, scorer_engine):
        """Test warm tier gets email, LinkedIn, voice."""
        channels = scorer_engine._get_channels_for_tier("warm")
        assert len(channels) == 3
        assert ChannelType.EMAIL in channels
        assert ChannelType.LINKEDIN in channels
        assert ChannelType.VOICE in channels
        assert ChannelType.SMS not in channels

    def test_cool_tier_channels(self, scorer_engine):
        """Test cool tier gets email, LinkedIn."""
        channels = scorer_engine._get_channels_for_tier("cool")
        assert len(channels) == 2
        assert ChannelType.EMAIL in channels
        assert ChannelType.LINKEDIN in channels

    def test_cold_tier_email_only(self, scorer_engine):
        """Test cold tier gets email only."""
        channels = scorer_engine._get_channels_for_tier("cold")
        assert len(channels) == 1
        assert ChannelType.EMAIL in channels

    def test_dead_tier_no_channels(self, scorer_engine):
        """Test dead tier gets no channels."""
        channels = scorer_engine._get_channels_for_tier("dead")
        assert len(channels) == 0


# ============================================
# Full Scoring Tests
# ============================================


class TestFullScoring:
    """Test complete scoring flow."""

    @pytest.mark.asyncio
    async def test_score_lead_success(self, scorer_engine, mock_db_session, mock_lead):
        """Test successful lead scoring."""
        with patch.object(scorer_engine, "get_lead_by_id", return_value=mock_lead):
            result = await scorer_engine.score_lead(
                db=mock_db_session,
                lead_id=mock_lead.id,
            )

            assert result.success is True
            assert "als_score" in result.data
            assert "als_tier" in result.data
            assert result.data["als_score"] >= 0
            assert result.data["als_score"] <= 100
            assert result.data["als_tier"] in ["hot", "warm", "cool", "cold", "dead"]

    @pytest.mark.asyncio
    async def test_score_lead_with_perfect_data(self, scorer_engine, mock_db_session, mock_lead):
        """Test lead with perfect data gets high score."""
        # Mock lead already has perfect data
        with patch.object(scorer_engine, "get_lead_by_id", return_value=mock_lead):
            result = await scorer_engine.score_lead(
                db=mock_db_session,
                lead_id=mock_lead.id,
            )

            assert result.success is True
            # Perfect lead should be hot tier
            assert result.data["als_tier"] == "hot"
            assert result.data["als_score"] >= TIER_HOT


# ============================================
# Batch Scoring Tests
# ============================================


class TestBatchScoring:
    """Test batch scoring functionality."""

    @pytest.mark.asyncio
    async def test_batch_scoring_success(self, scorer_engine, mock_db_session, mock_lead):
        """Test batch scoring returns summary."""
        lead_ids = [uuid4() for _ in range(3)]

        with patch.object(scorer_engine, "get_lead_by_id", return_value=mock_lead):
            result = await scorer_engine.score_batch(
                db=mock_db_session,
                lead_ids=lead_ids,
            )

            assert result.success is True
            assert result.data["total"] == 3
            assert result.data["scored"] == 3
            assert result.data["failures"] == 0

    @pytest.mark.asyncio
    async def test_batch_scoring_tier_distribution(self, scorer_engine, mock_db_session, mock_lead):
        """Test batch scoring calculates tier distribution."""
        lead_ids = [uuid4() for _ in range(3)]

        with patch.object(scorer_engine, "get_lead_by_id", return_value=mock_lead):
            result = await scorer_engine.score_batch(
                db=mock_db_session,
                lead_ids=lead_ids,
            )

            assert "tier_distribution" in result.data
            total_in_tiers = sum(result.data["tier_distribution"].values())
            assert total_in_tiers == result.data["scored"]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties
# [x] Test singleton pattern
# [x] Test data quality scoring (20 max)
# [x] Test authority scoring (25 max)
# [x] Test company fit scoring (25 max)
# [x] Test timing scoring (15 max)
# [x] Test risk scoring (deductions)
# [x] Test tier assignment thresholds
# [x] Test channel assignment per tier
# [x] Test full scoring flow
# [x] Test batch scoring
# [x] Test tier distribution calculation
