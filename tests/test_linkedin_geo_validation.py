"""
FILE: tests/test_linkedin_geo_validation.py
PURPOSE: Test LinkedIn company geo-validation for AU/NZ headquarters
DIRECTIVE: CEO Directive #168 - Prevent non-AU/NZ companies polluting leads
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.enrichment.waterfall_v2 import WaterfallV2, LeadRecord


class TestValidateAuNzHeadquarters:
    """Unit tests for _validate_au_nz_headquarters helper method."""

    @pytest.fixture
    def enricher(self):
        """Create a WaterfallV2 instance for testing."""
        return WaterfallV2(bright_data_client=None)

    # Australian company tests
    def test_australian_city_passes(self, enricher):
        """Sydney, NSW, Australia should pass."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Sydney, NSW, Australia")
        assert is_valid is True
        assert "sydney" in reason or "nsw" in reason or "australia" in reason

    def test_melbourne_passes(self, enricher):
        """Melbourne, Victoria passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Melbourne, Victoria, Australia")
        assert is_valid is True

    def test_brisbane_passes(self, enricher):
        """Brisbane, QLD passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Brisbane, QLD")
        assert is_valid is True

    def test_perth_wa_passes(self, enricher):
        """Perth, WA passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Perth, WA, Australia")
        assert is_valid is True

    def test_adelaide_passes(self, enricher):
        """Adelaide, SA passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Adelaide, SA")
        assert is_valid is True

    def test_canberra_passes(self, enricher):
        """Canberra, ACT passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Canberra, ACT, Australia")
        assert is_valid is True

    # Indian company tests (should fail)
    def test_indian_company_rejected(self, enricher):
        """Bengaluru, India should be rejected."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Bengaluru, India")
        assert is_valid is False
        assert "no_au_nz_match" in reason

    def test_mumbai_rejected(self, enricher):
        """Mumbai, Maharashtra, India should be rejected."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Mumbai, Maharashtra, India")
        assert is_valid is False

    # UK company tests (should fail)
    def test_uk_company_rejected(self, enricher):
        """London, UK should be rejected."""
        is_valid, reason = enricher._validate_au_nz_headquarters("London, UK")
        assert is_valid is False
        assert "no_au_nz_match" in reason

    def test_manchester_rejected(self, enricher):
        """Manchester, England should be rejected."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Manchester, England")
        assert is_valid is False

    # US company tests (should fail)
    def test_us_company_rejected(self, enricher):
        """San Francisco, CA, USA should be rejected."""
        is_valid, reason = enricher._validate_au_nz_headquarters("San Francisco, CA, USA")
        assert is_valid is False

    def test_new_york_rejected(self, enricher):
        """New York, NY should be rejected."""
        is_valid, reason = enricher._validate_au_nz_headquarters("New York, NY, United States")
        assert is_valid is False

    # Empty headquarters tests
    def test_empty_headquarters_passes(self, enricher):
        """Empty headquarters should pass with warning."""
        is_valid, reason = enricher._validate_au_nz_headquarters(None)
        assert is_valid is True
        assert "empty_headquarters" in reason

    def test_empty_string_passes(self, enricher):
        """Empty string headquarters should pass with warning."""
        is_valid, reason = enricher._validate_au_nz_headquarters("")
        assert is_valid is True
        assert "empty_headquarters" in reason

    # New Zealand company tests
    def test_nz_company_passes(self, enricher):
        """Auckland, New Zealand should pass."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Auckland, New Zealand")
        assert is_valid is True
        assert "nz_match" in reason or "auckland" in reason

    def test_wellington_passes(self, enricher):
        """Wellington, New Zealand passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Wellington, New Zealand")
        assert is_valid is True

    def test_christchurch_passes(self, enricher):
        """Christchurch, NZ passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Christchurch, NZ")
        assert is_valid is True

    # Edge cases
    def test_au_abbreviation_passes(self, enricher):
        """Location with 'AU' abbreviation should pass."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Sydney, AU")
        assert is_valid is True

    def test_case_insensitive(self, enricher):
        """Validation should be case-insensitive."""
        is_valid, reason = enricher._validate_au_nz_headquarters("SYDNEY, AUSTRALIA")
        assert is_valid is True

    def test_gold_coast_passes(self, enricher):
        """Gold Coast, QLD passes."""
        is_valid, reason = enricher._validate_au_nz_headquarters("Gold Coast, Queensland")
        assert is_valid is True


class TestEnrichTier2GeoValidation:
    """Integration tests for geo-validation in enrich_tier_2()."""

    @pytest.fixture
    def mock_bd_client(self):
        """Create a mock Bright Data client."""
        return MagicMock()

    @pytest.fixture
    def enricher(self, mock_bd_client):
        """Create a WaterfallV2 with mock BD client."""
        return WaterfallV2(bright_data_client=mock_bd_client)

    @pytest.fixture
    def base_lead(self):
        """Create a base lead record for testing."""
        return LeadRecord(
            id="test-lead-001",
            business_name="Test Company",
            linkedin_company_url="https://linkedin.com/company/test-company",
            enrichment_tiers_completed=[],
            enrichment_errors=[],
            cost_aud=0.0,
        )

    @pytest.mark.asyncio
    async def test_australian_company_data_written(self, enricher, base_lead):
        """Australian company data should be written to lead record."""
        linkedin_data = {
            "name": "AdVisible Australia",
            "headquarters": "Sydney, NSW, Australia",
            "company_size": "11-50",
            "industries": "Marketing",
            "employees": [],
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        result = await enricher.enrich_tier_2(base_lead)

        assert result.linkedin_data == linkedin_data
        assert result.headquarters == "Sydney, NSW, Australia"
        assert result.company_size == "11-50"
        assert "tier_2" in result.enrichment_tiers_completed
        assert result.cost_aud > 0

    @pytest.mark.asyncio
    async def test_indian_company_data_not_written(self, enricher, base_lead):
        """Indian company data should NOT be written to lead record."""
        linkedin_data = {
            "name": "ADVISIBLE India",
            "headquarters": "Bengaluru, India",
            "company_size": "201-500",
            "industries": "IT Services",
            "employees": [],
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        result = await enricher.enrich_tier_2(base_lead)

        # Data should NOT be written
        assert result.linkedin_data is None or result.linkedin_data == {}
        assert result.headquarters is None
        assert result.company_size is None
        # But tier should still be marked complete and cost added
        assert "tier_2" in result.enrichment_tiers_completed
        assert result.cost_aud > 0

    @pytest.mark.asyncio
    async def test_uk_company_data_not_written(self, enricher, base_lead):
        """UK company data should NOT be written to lead record."""
        linkedin_data = {
            "name": "UK Company Ltd",
            "headquarters": "London, UK",
            "company_size": "51-200",
            "industries": "Finance",
            "employees": [],
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        result = await enricher.enrich_tier_2(base_lead)

        assert result.linkedin_data is None or result.linkedin_data == {}
        assert result.headquarters is None
        assert "tier_2" in result.enrichment_tiers_completed
        assert result.cost_aud > 0

    @pytest.mark.asyncio
    async def test_empty_headquarters_data_written(self, enricher, base_lead):
        """Empty headquarters should allow data through with warning."""
        linkedin_data = {
            "name": "Mystery Company",
            "headquarters": None,
            "company_size": "11-50",
            "industries": "Consulting",
            "employees": [],
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        result = await enricher.enrich_tier_2(base_lead)

        # Data SHOULD be written (empty headquarters allowed)
        assert result.linkedin_data == linkedin_data
        assert result.company_size == "11-50"
        assert "tier_2" in result.enrichment_tiers_completed

    @pytest.mark.asyncio
    async def test_nz_company_data_written(self, enricher, base_lead):
        """New Zealand company data should be written to lead record."""
        linkedin_data = {
            "name": "Kiwi Agency",
            "headquarters": "Auckland, New Zealand",
            "company_size": "11-50",
            "industries": "Marketing",
            "employees": [],
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        result = await enricher.enrich_tier_2(base_lead)

        assert result.linkedin_data == linkedin_data
        assert result.headquarters == "Auckland, New Zealand"
        assert "tier_2" in result.enrichment_tiers_completed

    @pytest.mark.asyncio
    async def test_no_exception_on_geo_validation_fail(self, enricher, base_lead):
        """Geo-validation failure should NOT raise exception."""
        linkedin_data = {
            "name": "Foreign Company",
            "headquarters": "Tokyo, Japan",
            "company_size": "1001-5000",
            "industries": "Technology",
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        # Should NOT raise
        result = await enricher.enrich_tier_2(base_lead)

        assert "tier_2" in result.enrichment_tiers_completed
        # No enrichment error added for geo-validation fail
        assert len([e for e in result.enrichment_errors if e.get("tier") == "tier_2"]) == 0

    @pytest.mark.asyncio
    async def test_cost_added_even_on_rejection(self, enricher, base_lead):
        """Cost should be added even when geo-validation fails."""
        linkedin_data = {
            "name": "Singapore Corp",
            "headquarters": "Singapore",
            "company_size": "51-200",
        }
        enricher.bd.scrape_linkedin_company = AsyncMock(return_value=linkedin_data)

        initial_cost = base_lead.cost_aud
        result = await enricher.enrich_tier_2(base_lead)

        # Cost should be added (we paid for the API call)
        assert result.cost_aud > initial_cost
