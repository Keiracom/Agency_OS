"""
Test suite for SIEGE Discovery Enhancements.

Tests:
1. Audit logging for all enrichment operations
2. AU leads use SIEGE waterfall
3. Mock data validation

TASK: SIEGE Discovery Enhancement
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Import the modules under test
from src.engines.scout import ScoutEngine
from src.integrations.siege_waterfall import (
    EnrichmentTier,
    SiegeWaterfall,
)


class MockLead:
    """Mock Lead model for testing."""

    def __init__(
        self,
        email: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
        domain: str | None = None,
        linkedin_url: str | None = None,
        title: str | None = None,
        organization_country: str | None = None,
        abn: str | None = None,
        phone: str | None = None,
    ):
        self.id = uuid4()
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.company = company
        self.domain = domain
        self.linkedin_url = linkedin_url
        self.title = title
        self.organization_country = organization_country
        self.abn = abn
        self.phone = phone


class TestAustralianLeadNoApolloFallback:
    """Test that AU leads use SIEGE (Apollo removed - FCO-002)."""

    @pytest.fixture
    def mock_siege_waterfall(self):
        """Mock Siege Waterfall."""
        mock = AsyncMock()
        # Return a result with some sources used
        mock.enrich_lead.return_value = MagicMock(
            sources_used=2,
            enriched_data={
                "email": "found@company.com.au",
                "first_name": "Test",
                "found": True,
            },
            total_cost_aud=0.018,
            tier_results=[
                MagicMock(tier=EnrichmentTier.ABN, success=True),
                MagicMock(tier=EnrichmentTier.GMB, success=True),
            ],
        )
        return mock

    @pytest.mark.asyncio
    async def test_au_lead_uses_siege(
        self, mock_siege_waterfall
    ):
        """Test that Australian leads use SIEGE waterfall."""
        # Create AU lead
        lead = MockLead(
            email=None,  # No email, needs enrichment
            first_name="Bruce",
            last_name="Wayne",
            company="Wayne Enterprises",
            domain="wayne.com.au",  # .au domain = Australian
        )

        # Create scout engine with mocks (Apollo removed - FCO-002)
        engine = ScoutEngine(
            siege_waterfall=mock_siege_waterfall,
        )

        # Patch the audit logging to avoid DB calls
        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            result = await engine._enrich_tier1(lead, "wayne.com.au")

        # Verify SIEGE was called
        mock_siege_waterfall.enrich_lead.assert_called_once()

        # Verify we got SIEGE result
        assert result["found"] is True
        assert "siege_waterfall" in result["source"]

    @pytest.mark.asyncio
    async def test_au_lead_siege_fails_returns_none(self):
        """Test that when SIEGE fails for AU lead, result is None."""
        # Create mock siege that returns no sources
        mock_siege = AsyncMock()
        mock_siege.enrich_lead.return_value = MagicMock(
            sources_used=0,  # No sources found
            enriched_data={},
            total_cost_aud=0.0,
            tier_results=[],
        )

        lead = MockLead(
            first_name="Unknown",
            last_name="Person",
            company="Obscure Company",
            domain="obscure.com.au",  # .au domain
        )

        engine = ScoutEngine(
            siege_waterfall=mock_siege,
        )

        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            result = await engine._enrich_tier1(lead, "obscure.com.au")

        # Verify SIEGE was called
        mock_siege.enrich_lead.assert_called_once()

        # Result should be None (no data found)
        assert result is None

    @pytest.mark.asyncio
    async def test_non_au_lead_uses_siege(self):
        """Test that non-Australian leads also use SIEGE (Apollo removed FCO-002)."""
        # Mock Siege success
        mock_siege = AsyncMock()
        mock_siege.enrich_lead.return_value = MagicMock(
            sources_used=2,
            enriched_data={
                "email": "john@acme.com",
                "first_name": "John",
                "last_name": "Doe",
                "found": True,
            },
            total_cost_aud=0.018,
            tier_results=[],
        )

        # Non-AU lead
        lead = MockLead(
            email=None,
            first_name="John",
            last_name="Doe",
            company="Acme Inc",
            domain="acme.com",  # .com, not .com.au
            organization_country="United States",
        )

        engine = ScoutEngine(
            siege_waterfall=mock_siege,
        )

        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            result = await engine._enrich_tier1(lead, "acme.com")

        # Verify SIEGE was called (used for all leads now)
        mock_siege.enrich_lead.assert_called_once()

        # Verify we got result
        assert result["found"] is True


class TestAustralianLeadDetection:
    """Test detection of Australian leads."""

    def test_au_domain_detected(self):
        """Test .au domain is detected as Australian."""
        lead = MockLead(domain="company.com.au")
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com.au") is True

    def test_au_country_detected(self):
        """Test Australia country is detected."""
        lead = MockLead(
            domain="company.com",
            organization_country="Australia",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is True

    def test_abn_detected(self):
        """Test ABN presence indicates Australian."""
        lead = MockLead(
            domain="company.com",
            abn="12345678901",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is True

    def test_au_phone_detected(self):
        """Test +61 phone number indicates Australian."""
        lead = MockLead(
            domain="company.com",
            phone="+61 2 9999 1234",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is True

    def test_non_au_not_detected(self):
        """Test non-Australian leads are not flagged."""
        lead = MockLead(
            domain="company.com",
            organization_country="United States",
        )
        engine = ScoutEngine()
        assert engine._is_australian_lead(lead, "company.com") is False


class TestMockDataEnrichment:
    """Test full enrichment flow with mock data."""

    @pytest.fixture
    def mock_au_lead_data(self):
        """Sample Australian lead for testing."""
        return {
            "id": str(uuid4()),
            "company_name": "Brisbane Marketing Agency",
            "domain": "brismarketing.com.au",
            "city": "Brisbane",
            "state": "QLD",
            "country": "Australia",
        }

    @pytest.fixture
    def mock_non_au_lead_data(self):
        """Sample non-Australian lead for testing."""
        return {
            "id": str(uuid4()),
            "email": "contact@uscompany.com",
            "first_name": "Mike",
            "last_name": "Johnson",
            "company_name": "US Marketing Inc",
            "domain": "uscompany.com",
            "country": "United States",
        }

    @pytest.mark.asyncio
    async def test_au_lead_siege_enrichment(self, mock_au_lead_data):
        """Test Australian lead goes through SIEGE waterfall."""
        # Create mocked waterfall that returns enriched data
        mock_waterfall = AsyncMock()
        mock_waterfall.enrich_lead.return_value = MagicMock(
            sources_used=2,
            enriched_data={
                "email": "sarah@brismarketing.com.au",
                "first_name": "Sarah",
                "last_name": "Thompson",
                "title": "CEO",
                "found": True,
            },
            total_cost_aud=0.02,
            tier_results=[],
        )

        # Create scout engine with mock waterfall
        engine = ScoutEngine(siege_waterfall=mock_waterfall)

        # Patch audit logging
        with patch.object(engine, "_log_enrichment_audit", new_callable=AsyncMock):
            # Create mock lead
            lead = MockLead(
                company=mock_au_lead_data["company_name"],
                domain=mock_au_lead_data["domain"],
            )
            result = await engine._enrich_tier1(lead, mock_au_lead_data["domain"])

        # Verify enrichment succeeded
        assert result is not None
        assert result.get("email") == "sarah@brismarketing.com.au"
        assert result.get("first_name") == "Sarah"


# ============================================
# RUN TESTS
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
