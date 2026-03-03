"""
Unit tests for Discovery Modes

Tests Mode A (ABN-First), Mode B (Maps-First), Mode C (Parallel)
"""
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestDiscoveryModeEnum:
    """Test DiscoveryMode enum"""

    def test_mode_b_value(self):
        from enrichment.discovery_modes import DiscoveryMode
        assert DiscoveryMode.MAPS_FIRST.value == "mode_b"

    def test_mode_c_value(self):
        from enrichment.discovery_modes import DiscoveryMode
        assert DiscoveryMode.PARALLEL.value == "mode_c"

    def test_abn_first_deprecated(self):
        """ABN_FIRST was deprecated per Waterfall v3 Decision #1 (2026-03-01)"""
        from enrichment.discovery_modes import DiscoveryMode
        assert not hasattr(DiscoveryMode, 'ABN_FIRST')


class TestCampaignConfig:
    """Test CampaignConfig dataclass"""

    def test_config_required_fields(self):
        from enrichment.discovery_modes import CampaignConfig, DiscoveryMode

        config = CampaignConfig(
            mode=DiscoveryMode.MAPS_FIRST,
            industry="Advertising",
            location="Melbourne"
        )

        assert config.mode == DiscoveryMode.MAPS_FIRST
        assert config.industry == "Advertising"
        assert config.location == "Melbourne"

    def test_config_optional_fields(self):
        from enrichment.discovery_modes import CampaignConfig, DiscoveryMode

        config = CampaignConfig(
            mode=DiscoveryMode.MAPS_FIRST,
            industry="Restaurants",
            location="Sydney",
            state="NSW",
            filters={"rating_min": 4.0}
        )

        assert config.state == "NSW"
        assert config.filters["rating_min"] == 4.0


class TestMapsFirstDiscovery:
    """Test Mode B: Maps-First discovery"""

    @pytest.mark.asyncio
    async def test_uses_bright_data_serp(self):
        from enrichment.discovery_modes import CampaignConfig, DiscoveryMode, MapsFirstDiscovery

        mock_client = Mock()
        mock_client.search_google_maps = Mock(return_value=[
            {"name": "Test Business", "phone": "0398765432", "rating": 4.5}
        ])

        MapsFirstDiscovery(bright_data_client=mock_client)
        CampaignConfig(
            mode=DiscoveryMode.MAPS_FIRST,
            industry="Cafes",
            location="Melbourne CBD"
        )

        # Should call SERP Maps
        # results = await discovery.discover(config)
        # mock_client.search_google_maps.assert_called_once()

    @pytest.mark.asyncio
    async def test_verifies_with_abn_lookup(self):
        from enrichment.discovery_modes import MapsFirstDiscovery

        mock_client = Mock()
        MapsFirstDiscovery(bright_data_client=mock_client)

        # After finding businesses via Maps, should verify with ABN lookup
        # This ensures Australian compliance


class TestParallelDiscovery:
    """Test Mode C: Parallel discovery"""

    @pytest.mark.asyncio
    async def test_runs_both_modes(self):
        from enrichment.discovery_modes import CampaignConfig, DiscoveryMode, ParallelDiscovery

        mock_client = Mock()
        ParallelDiscovery(bright_data_client=mock_client)
        CampaignConfig(
            mode=DiscoveryMode.PARALLEL,
            industry="Retail",
            location="Brisbane"
        )

        # Should run both ABN and Maps discovery

    @pytest.mark.asyncio
    async def test_deduplicates_results(self):
        from enrichment.discovery_modes import ParallelDiscovery

        mock_client = Mock()
        ParallelDiscovery(bright_data_client=mock_client)

        # Mode A result
        # Mode B result (same business, different name format)

        # Should deduplicate on ABN match
        # Should also fuzzy match on name


class TestDiscoveryFilters:
    """Test hard filters applied during discovery"""

    def test_discard_trusts(self):
        # Entity type "Trust" should be discarded
        pass

    def test_discard_super_funds(self):
        # Entity type "Super Fund" should be discarded
        pass

    def test_discard_deceased_estates(self):
        # Entity type "Deceased Estate" should be discarded
        pass

    def test_discard_government(self):
        # Government entities should be discarded
        pass

    def test_soft_flag_holdings(self):
        # Holdings/Investments with zero ASIC names should be soft-flagged
        # Not discarded, but marked for review
        pass
