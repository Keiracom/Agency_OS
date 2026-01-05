"""
FILE: tests/test_engines/test_scout.py
PURPOSE: Unit tests for Scout engine (enrichment waterfall)
PHASE: 4 (Engines)
TASK: ENG-002
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.engines.scout import (
    CONFIDENCE_THRESHOLD,
    REQUIRED_FIELDS,
    ScoutEngine,
    get_scout_engine,
)
from src.engines.base import EngineResult
from src.models.base import LeadStatus


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def mock_apollo_client():
    """Create mock Apollo client."""
    client = AsyncMock()
    client.enrich_person = AsyncMock()
    client.enrich_company = AsyncMock()
    return client


@pytest.fixture
def mock_apify_client():
    """Create mock Apify client."""
    client = AsyncMock()
    client.scrape_linkedin_profiles = AsyncMock()
    return client


@pytest.fixture
def mock_clay_client():
    """Create mock Clay client."""
    client = AsyncMock()
    client.enrich_person = AsyncMock()
    return client


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_lead():
    """Create mock lead object."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.email = "john.doe@acme.com"
    lead.first_name = "John"
    lead.last_name = "Doe"
    lead.title = None
    lead.company = "Acme Inc"
    lead.phone = None
    lead.linkedin_url = "https://linkedin.com/in/johndoe"
    lead.domain = "acme.com"
    lead.personal_email = None
    lead.seniority_level = None
    lead.status = LeadStatus.NEW
    return lead


@pytest.fixture
def valid_enrichment_data():
    """Create valid enrichment data that passes validation."""
    return {
        "found": True,
        "confidence": 0.85,
        "source": "apollo",
        "email": "john.doe@acme.com",
        "first_name": "John",
        "last_name": "Doe",
        "title": "CEO",
        "company": "Acme Inc",
        "phone": "+61400123456",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "domain": "acme.com",
        "organization_industry": "Technology",
        "organization_employee_count": 50,
        "organization_country": "Australia",
    }


@pytest.fixture
def scout_engine(mock_apollo_client, mock_apify_client, mock_clay_client):
    """Create Scout engine with mock clients."""
    return ScoutEngine(
        apollo_client=mock_apollo_client,
        apify_client=mock_apify_client,
        clay_client=mock_clay_client,
    )


# ============================================
# Engine Properties Tests
# ============================================


class TestScoutEngineProperties:
    """Test Scout engine properties."""

    def test_engine_name(self, scout_engine):
        """Test engine name property."""
        assert scout_engine.name == "scout"

    def test_singleton_instance(self):
        """Test singleton pattern."""
        engine1 = get_scout_engine()
        engine2 = get_scout_engine()
        assert engine1 is engine2


# ============================================
# Validation Tests
# ============================================


class TestEnrichmentValidation:
    """Test enrichment data validation."""

    def test_validate_enrichment_valid(self, scout_engine, valid_enrichment_data):
        """Test validation passes for valid data."""
        assert scout_engine._validate_enrichment(valid_enrichment_data) is True

    def test_validate_enrichment_not_found(self, scout_engine):
        """Test validation fails when not found."""
        data = {"found": False, "confidence": 0.9}
        assert scout_engine._validate_enrichment(data) is False

    def test_validate_enrichment_low_confidence(self, scout_engine, valid_enrichment_data):
        """Test validation fails when confidence is below threshold."""
        valid_enrichment_data["confidence"] = 0.50  # Below 0.70
        assert scout_engine._validate_enrichment(valid_enrichment_data) is False

    def test_validate_enrichment_threshold_boundary(self, scout_engine, valid_enrichment_data):
        """Test validation at confidence threshold boundary."""
        # At threshold - should pass
        valid_enrichment_data["confidence"] = CONFIDENCE_THRESHOLD
        assert scout_engine._validate_enrichment(valid_enrichment_data) is True

        # Just below threshold - should fail
        valid_enrichment_data["confidence"] = CONFIDENCE_THRESHOLD - 0.01
        assert scout_engine._validate_enrichment(valid_enrichment_data) is False

    def test_validate_enrichment_missing_required_fields(self, scout_engine):
        """Test validation fails when required fields are missing."""
        for field in REQUIRED_FIELDS:
            data = {
                "found": True,
                "confidence": 0.85,
                "email": "test@test.com",
                "first_name": "John",
                "last_name": "Doe",
                "company": "Acme",
            }
            data[field] = None  # Remove required field
            assert scout_engine._validate_enrichment(data) is False, f"Should fail for missing {field}"


# ============================================
# Cache Tests
# ============================================


class TestCacheBehavior:
    """Test cache behavior in enrichment waterfall."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(
        self, scout_engine, mock_db_session, mock_lead, valid_enrichment_data
    ):
        """Test that cache hit returns cached data without calling APIs."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead):
            with patch("src.engines.scout.enrichment_cache") as mock_cache:
                mock_cache.get = AsyncMock(return_value=valid_enrichment_data)

                result = await scout_engine.enrich_lead(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    force_refresh=False,
                )

                assert result.success is True
                assert result.metadata["tier"] == 0
                assert result.metadata["source"] == "cache"
                # Apollo should not be called
                scout_engine.apollo.enrich_person.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_refresh_skips_cache(
        self, scout_engine, mock_db_session, mock_lead, valid_enrichment_data
    ):
        """Test that force_refresh=True skips cache."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead):
            with patch("src.engines.scout.enrichment_cache") as mock_cache:
                mock_cache.get = AsyncMock(return_value=valid_enrichment_data)
                mock_cache.set = AsyncMock()
                scout_engine.apollo.enrich_person.return_value = valid_enrichment_data

                result = await scout_engine.enrich_lead(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                    force_refresh=True,
                )

                # Cache get should not be called
                mock_cache.get.assert_not_called()
                # Apollo should be called
                scout_engine.apollo.enrich_person.assert_called_once()


# ============================================
# Waterfall Tier Tests
# ============================================


class TestWaterfallTiers:
    """Test waterfall tier progression."""

    @pytest.mark.asyncio
    async def test_tier1_apollo_success(
        self, scout_engine, mock_db_session, mock_lead, valid_enrichment_data
    ):
        """Test Tier 1 Apollo enrichment success."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead):
            with patch("src.engines.scout.enrichment_cache") as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)  # Cache miss
                mock_cache.set = AsyncMock()
                scout_engine.apollo.enrich_person.return_value = valid_enrichment_data

                result = await scout_engine.enrich_lead(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                )

                assert result.success is True
                assert result.metadata["tier"] == 1
                assert "apollo" in result.metadata["source"]

    @pytest.mark.asyncio
    async def test_tier2_clay_fallback(
        self, scout_engine, mock_db_session, mock_lead, valid_enrichment_data
    ):
        """Test Tier 2 Clay fallback when Tier 1 fails."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead):
            with patch("src.engines.scout.enrichment_cache") as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                mock_cache.set = AsyncMock()
                # Apollo fails
                scout_engine.apollo.enrich_person.return_value = {"found": False}
                scout_engine.apify.scrape_linkedin_profiles.return_value = []
                # Clay succeeds
                clay_data = valid_enrichment_data.copy()
                clay_data["source"] = "clay"
                scout_engine.clay.enrich_person.return_value = clay_data

                result = await scout_engine.enrich_lead(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                )

                assert result.success is True
                assert result.metadata["tier"] == 2
                assert result.metadata["source"] == "clay"

    @pytest.mark.asyncio
    async def test_all_tiers_fail(
        self, scout_engine, mock_db_session, mock_lead
    ):
        """Test failure when all tiers fail."""
        with patch.object(scout_engine, "get_lead_by_id", return_value=mock_lead):
            with patch("src.engines.scout.enrichment_cache") as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                # All APIs fail
                scout_engine.apollo.enrich_person.return_value = {"found": False}
                scout_engine.apify.scrape_linkedin_profiles.return_value = []
                scout_engine.clay.enrich_person.return_value = {"found": False}

                result = await scout_engine.enrich_lead(
                    db=mock_db_session,
                    lead_id=mock_lead.id,
                )

                assert result.success is False
                assert "failed" in result.error.lower()


# ============================================
# Batch Enrichment Tests
# ============================================


class TestBatchEnrichment:
    """Test batch enrichment functionality."""

    @pytest.mark.asyncio
    async def test_batch_enrichment_clay_limit(
        self, scout_engine, mock_db_session, mock_lead, valid_enrichment_data
    ):
        """Test Clay usage is limited to 15% of batch."""
        lead_ids = [uuid4() for _ in range(10)]  # 10 leads

        with patch.object(scout_engine, "_enrich_single") as mock_enrich:
            # Simulate all needing Clay (tier 2)
            async def enrich_result(db, lead_id, force_refresh, use_clay):
                if use_clay:
                    return EngineResult.ok(data={}, metadata={"tier": 2, "source": "clay"})
                else:
                    return EngineResult.fail(error="Clay not allowed")

            mock_enrich.side_effect = enrich_result

            result = await scout_engine.enrich_batch(
                db=mock_db_session,
                lead_ids=lead_ids,
            )

            assert result.success is True
            # 15% of 10 = 1 Clay call allowed
            assert result.data["clay_budget_used"] <= 1

    @pytest.mark.asyncio
    async def test_batch_enrichment_summary(
        self, scout_engine, mock_db_session, valid_enrichment_data
    ):
        """Test batch enrichment returns correct summary."""
        lead_ids = [uuid4() for _ in range(5)]

        with patch.object(scout_engine, "_enrich_single") as mock_enrich:
            # Simulate mixed results
            results_cycle = [
                EngineResult.ok(data={}, metadata={"tier": 0, "source": "cache"}),
                EngineResult.ok(data={}, metadata={"tier": 1, "source": "apollo"}),
                EngineResult.ok(data={}, metadata={"tier": 1, "source": "apollo"}),
                EngineResult.ok(data={}, metadata={"tier": 2, "source": "clay"}),
                EngineResult.fail(error="Failed"),
            ]
            mock_enrich.side_effect = results_cycle

            result = await scout_engine.enrich_batch(
                db=mock_db_session,
                lead_ids=lead_ids,
            )

            assert result.success is True
            assert result.data["total"] == 5
            assert result.data["cache_hits"] == 1
            assert result.data["tier1_success"] == 2
            assert result.data["tier2_success"] == 1
            assert result.data["failures"] == 1


# ============================================
# Merge Tests
# ============================================


class TestEnrichmentMerge:
    """Test enrichment data merging."""

    def test_merge_fills_missing_fields(self, scout_engine):
        """Test merge fills in missing fields from secondary."""
        primary = {
            "source": "apollo",
            "email": "test@test.com",
            "first_name": "John",
            "confidence": 0.8,
        }
        secondary = {
            "source": "apify",
            "last_name": "Doe",
            "company": "Acme",
            "confidence": 0.7,
        }

        merged = scout_engine._merge_enrichment(primary, secondary)

        assert merged["email"] == "test@test.com"
        assert merged["first_name"] == "John"
        assert merged["last_name"] == "Doe"
        assert merged["company"] == "Acme"
        assert "apollo" in merged["source"]
        assert "apify" in merged["source"]

    def test_merge_prefers_primary(self, scout_engine):
        """Test merge prefers primary data over secondary."""
        primary = {
            "source": "apollo",
            "first_name": "John",
            "confidence": 0.9,
        }
        secondary = {
            "source": "apify",
            "first_name": "Jonathan",  # Different
            "confidence": 0.7,
        }

        merged = scout_engine._merge_enrichment(primary, secondary)

        assert merged["first_name"] == "John"  # Primary wins


# ============================================
# Helper Function Tests
# ============================================


class TestHelperFunctions:
    """Test helper functions."""

    def test_extract_domain_valid_email(self, scout_engine):
        """Test domain extraction from valid email."""
        assert scout_engine._extract_domain("john@acme.com") == "acme.com"
        assert scout_engine._extract_domain("user@sub.domain.co.uk") == "sub.domain.co.uk"

    def test_extract_domain_invalid_email(self, scout_engine):
        """Test domain extraction from invalid email."""
        assert scout_engine._extract_domain("not-an-email") is None
        assert scout_engine._extract_domain(None) is None
        assert scout_engine._extract_domain("") is None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test engine properties
# [x] Test singleton pattern
# [x] Test validation with confidence threshold
# [x] Test required fields validation
# [x] Test cache hit behavior
# [x] Test force refresh skips cache
# [x] Test Tier 1 (Apollo) success
# [x] Test Tier 2 (Clay) fallback
# [x] Test all tiers fail scenario
# [x] Test batch enrichment Clay limit (15%)
# [x] Test batch enrichment summary
# [x] Test enrichment merge
# [x] Test helper functions
