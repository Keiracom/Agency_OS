"""
Unit tests for Query Translator + Expanders

Tests keyword expansion, location expansion, ABN query construction,
Maps query construction, dedup logic, and filter logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))


class TestDiscoveryMode:
    """Test discovery mode selection"""

    def test_mode_enum_values(self):
        from src.pipeline.query_translator import DiscoveryMode

        # ABN_FIRST deprecated per Waterfall v3 Decision #1 (2026-03-01)
        assert DiscoveryMode.MAPS_FIRST.value == "maps"
        assert DiscoveryMode.PARALLEL.value == "parallel"


class TestQueryEstimation:
    """Test query count estimation"""

    def test_maps_query_estimation_basic(self):
        from src.pipeline.query_translator import QueryTranslator, CampaignConfig, DiscoveryMode

        # Create minimal translator
        translator = QueryTranslator(
            abn_client=Mock(),
            bright_data_client=Mock(),
            keyword_expander=Mock(),
            location_expander=Mock(),
            filters=Mock(),
        )

        config = CampaignConfig(
            campaign_id="test-123",
            industry_slug="marketing_agency",
            location="Melbourne",
            state="VIC",
            lead_volume=500,
        )

        # Use MAPS_FIRST as ABN_FIRST was deprecated
        estimate = translator.estimate_queries_needed(config, DiscoveryMode.MAPS_FIRST)
        assert estimate >= 1  # At least one query needed

    def test_maps_query_estimation(self):
        from src.pipeline.query_translator import QueryTranslator, CampaignConfig, DiscoveryMode

        translator = QueryTranslator(
            abn_client=Mock(),
            bright_data_client=Mock(),
            keyword_expander=Mock(),
            location_expander=Mock(),
            filters=Mock(),
        )

        config = CampaignConfig(
            campaign_id="test-123",
            industry_slug="plumber",
            location="Sydney",
            state="NSW",
            lead_volume=100,
        )

        # 100 leads / 20 per SERP = 5 queries
        estimate = translator.estimate_queries_needed(config, DiscoveryMode.MAPS_FIRST)
        assert estimate >= 5
        assert estimate <= 7


class TestDedupHash:
    """Test deduplication hash computation"""

    def test_abn_dedup_uses_abn(self):
        from src.pipeline.query_translator import QueryTranslator

        translator = QueryTranslator(
            abn_client=Mock(),
            bright_data_client=Mock(),
            keyword_expander=Mock(),
            location_expander=Mock(),
            filters=Mock(),
        )

        record = {"abn": "12345678901", "name": "Test Company"}
        hash_result = translator._compute_dedup_hash(record, "abn_api")

        assert hash_result == "abn:12345678901"

    def test_maps_dedup_uses_name_address(self):
        from src.pipeline.query_translator import QueryTranslator

        translator = QueryTranslator(
            abn_client=Mock(),
            bright_data_client=Mock(),
            keyword_expander=Mock(),
            location_expander=Mock(),
            filters=Mock(),
        )

        record = {"business_name": "Test Business", "address": "123 Main St"}
        hash_result = translator._compute_dedup_hash(record, "maps_serp")

        assert hash_result.startswith("maps:")
        assert len(hash_result) > 10  # Has hash component


class TestKeywordExpander:
    """Test keyword expansion"""

    @pytest.mark.asyncio
    async def test_lookup_known_vertical(self):
        from src.pipeline.keyword_expander import KeywordExpander

        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=Mock(data={"keywords": ["marketing", "advertising", "SEO"]})
        )

        expander = KeywordExpander(supabase_client=mock_supabase)

        # This would call the async method
        # keywords = await expander.expand("marketing_agency")
        # assert "marketing" in keywords

    @pytest.mark.asyncio
    async def test_fallback_to_claude(self):
        from src.pipeline.keyword_expander import KeywordExpander

        # When DB lookup returns None, should call Claude
        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute = AsyncMock(
            return_value=Mock(data=None)
        )

        expander = KeywordExpander(supabase_client=mock_supabase)

        # Would verify Claude API is called for unknown vertical

    def test_caching(self):
        from src.pipeline.keyword_expander import KeywordExpander

        expander = KeywordExpander()
        expander._cache["test_vertical"] = ["test", "keywords"]

        # Second access should use cache (sync)
        # In async, this would skip DB lookup


class TestLocationExpander:
    """Test location expansion"""

    @pytest.mark.asyncio
    async def test_lookup_known_city(self):
        from src.pipeline.location_expander import LocationExpander

        mock_supabase = Mock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = AsyncMock(
            return_value=Mock(
                data=[{"suburb": "CBD"}, {"suburb": "Richmond"}, {"suburb": "South Yarra"}]
            )
        )

        expander = LocationExpander(supabase_client=mock_supabase)

        # suburbs = await expander.expand("Melbourne", "VIC")
        # assert "CBD" in suburbs

    def test_state_inference(self):
        from src.pipeline.location_expander import LocationExpander

        expander = LocationExpander()

        assert expander.get_state_from_city("Sydney") == "NSW"
        assert expander.get_state_from_city("Melbourne") == "VIC"
        assert expander.get_state_from_city("Brisbane") == "QLD"
        assert expander.get_state_from_city("Perth") == "WA"
        assert expander.get_state_from_city("Adelaide") == "SA"


class TestDiscoveryFilters:
    """Test filter logic"""

    def test_hard_discard_cancelled_abn(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {"abn": "12345678901", "status": "Cancelled", "name": "Test"}
        passed, reason = filters.apply(record, "abn_api")

        assert passed is False
        assert reason == "cancelled_abn"

    def test_hard_discard_trust(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {"abn": "12345678901", "entity_type": "Trust", "status": "Active"}
        passed, reason = filters.apply(record, "abn_api")

        assert passed is False
        assert "trust" in reason

    def test_hard_discard_super_fund(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {"abn": "12345678901", "entity_type": "Super Fund", "status": "Active"}
        passed, reason = filters.apply(record, "abn_api")

        assert passed is False
        assert "super fund" in reason

    def test_hard_discard_government(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {"abn": "12345678901", "name": "Department of Health", "status": "Active"}
        passed, reason = filters.apply(record, "abn_api")

        assert passed is False
        assert "department of" in reason

    def test_soft_flag_holding_no_business_name(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {
            "abn": "12345678901",
            "entity_name": "KJR Holdings Pty Ltd",
            "status": "Active",
            "entity_type": "Private Company",
            "asic_names": [],
            "trading_name": "",
        }
        passed, reason = filters.apply(record, "abn_api")

        # Should pass but be soft flagged
        assert passed is True
        assert reason is not None
        assert "soft_flag" in reason

    def test_holding_with_business_name_passes(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {
            "abn": "12345678901",
            "entity_name": "KJR Holdings Pty Ltd",
            "status": "Active",
            "entity_type": "Private Company",
            "asic_names": ["Bloom Marketing"],
            "trading_name": "",
        }

        # Check the special case
        assert filters.is_holding_with_business_name(record) is True

    def test_active_company_passes(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        record = {
            "abn": "12345678901",
            "entity_name": "Mustard Creative Pty Ltd",
            "status": "Active",
            "entity_type": "Private Company",
            "gst_from": "2002-01-01",
        }
        passed, reason = filters.apply(record, "abn_api")

        assert passed is True
        assert reason is None

    def test_maps_results_pass_through(self):
        from src.pipeline.discovery_filters import DiscoveryFilters

        filters = DiscoveryFilters()

        # Maps results are filtered later with ABN verification
        record = {"name": "Any Business", "rating": 4.5}
        passed, reason = filters.apply(record, "maps_serp")

        assert passed is True
        assert reason is None


class TestCampaignConfig:
    """Test campaign configuration"""

    def test_config_fields(self):
        from src.pipeline.query_translator import CampaignConfig, DiscoveryMode

        config = CampaignConfig(
            campaign_id="camp-123",
            industry_slug="marketing_agency",
            location="Melbourne",
            state="VIC",
            lead_volume=200,
            filters={"min_employees": 5},
            discovery_mode=DiscoveryMode.PARALLEL,
        )

        assert config.campaign_id == "camp-123"
        assert config.lead_volume == 200
        assert config.discovery_mode == DiscoveryMode.PARALLEL
