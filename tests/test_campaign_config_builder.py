"""
Tests for CampaignConfigBuilder.

CEO Directive #163: Verify Campaign → CampaignConfig translation.
"""

import pytest
from uuid import uuid4

from src.enrichment.query_translator import CampaignConfig
from src.services.campaign_config_builder import CampaignConfigBuilder


class MockCampaign:
    """Mock Campaign ORM for testing."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.industry_slug = kwargs.get("industry_slug")
        self.state = kwargs.get("state")
        self.lead_volume = kwargs.get("lead_volume", 1250)
        self.target_industries = kwargs.get("target_industries")
        self.target_locations = kwargs.get("target_locations")
        self.target_titles = kwargs.get("target_titles")
        self.target_company_sizes = kwargs.get("target_company_sizes")


class TestCampaignConfigBuilder:
    """Tests for CampaignConfigBuilder.build()."""

    def test_all_fields_provided(self):
        """Test: all fields provided → CampaignConfig matches exactly."""
        campaign = MockCampaign(
            industry_slug="marketing-agency",
            state="NSW",
            lead_volume=2000,
            target_industries=["marketing", "advertising"],
            target_locations=["Sydney", "Melbourne"],
            target_titles=["CEO", "Founder"],
            target_company_sizes=["11-50", "51-200"],
        )

        config = CampaignConfigBuilder.build(campaign)

        assert config.industry_slug == "marketing-agency"
        assert config.state == "NSW"
        assert config.lead_volume == 2000
        assert config.location == "Sydney"
        assert config.filters["titles"] == ["CEO", "Founder"]
        assert config.filters["sizes"] == ["11-50", "51-200"]
        assert config.filters["industries"] == ["marketing", "advertising"]
        assert config.discovery_mode is None

    def test_industry_slug_fallback_to_target_industries(self):
        """Test: industry_slug missing, target_industries present → falls back."""
        campaign = MockCampaign(
            industry_slug=None,
            target_industries=["digital-agency", "seo"],
        )

        config = CampaignConfigBuilder.build(campaign)

        assert config.industry_slug == "digital-agency"

    def test_all_optional_fields_missing_defaults_apply(self):
        """Test: all optional fields missing → defaults apply."""
        campaign = MockCampaign(
            industry_slug=None,
            state=None,
            lead_volume=1250,
            target_industries=None,
            target_locations=None,
            target_titles=None,
            target_company_sizes=None,
        )

        config = CampaignConfigBuilder.build(campaign)

        assert config.industry_slug == "general"
        assert config.location == "Melbourne"
        assert config.state == "VIC"
        assert config.lead_volume == 1250
        assert config.filters["titles"] == []
        assert config.filters["sizes"] == []
        assert config.filters["industries"] == []

    def test_returns_valid_campaign_config_type(self):
        """Test: CampaignConfigBuilder.build() returns valid CampaignConfig."""
        campaign = MockCampaign()

        config = CampaignConfigBuilder.build(campaign)

        assert isinstance(config, CampaignConfig)
        assert config.campaign_id == str(campaign.id)

    def test_empty_lists_not_none(self):
        """Test: empty lists used for filters, not None."""
        campaign = MockCampaign(
            target_industries=[],
            target_locations=[],
            target_titles=[],
            target_company_sizes=[],
        )

        config = CampaignConfigBuilder.build(campaign)

        assert config.filters["titles"] == []
        assert config.filters["sizes"] == []
        assert config.filters["industries"] == []
        # Empty target_industries means industry_slug falls back to "general"
        assert config.industry_slug == "general"
        # Empty target_locations means location falls back to "Melbourne"
        assert config.location == "Melbourne"
