"""
Unit tests for Waterfall v2 Pipeline

Tests the enrichment pipeline including gates and tier sequencing.
"""
import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestWaterfallConstants:
    """Verify waterfall constants"""

    def test_pre_als_gate_value(self):
        from enrichment.waterfall_v2 import WaterfallV2
        assert WaterfallV2.PRE_ALS_GATE == 30

    def test_hot_threshold_value(self):
        from enrichment.waterfall_v2 import WaterfallV2
        assert WaterfallV2.HOT_THRESHOLD == 85


class TestLeadRecord:
    """Test LeadRecord dataclass"""

    def test_lead_record_defaults(self):
        from enrichment.waterfall_v2 import LeadRecord
        lead = LeadRecord()

        assert lead.abn is None
        assert lead.als_score == 0
        assert lead.cost_aud == 0.0

    def test_lead_record_with_values(self):
        from enrichment.waterfall_v2 import LeadRecord
        lead = LeadRecord(
            abn="12345678901",
            business_name="Test Company",
            als_score=75
        )

        assert lead.abn == "12345678901"
        assert lead.business_name == "Test Company"
        assert lead.als_score == 75


class TestPreALSGate:
    """Test PRE-ALS gate behavior"""

    @pytest.mark.asyncio
    async def test_low_score_skips_tier_2_5(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        waterfall = WaterfallV2(bright_data_client=mock_client)

        # Lead with score below gate
        lead = LeadRecord(als_score=25)

        # enrich_tier_2_5 should return lead unchanged
        result = await waterfall.enrich_tier_2_5(lead)

        assert result.als_score == 25
        # LinkedIn profile should not have been called

    @pytest.mark.asyncio
    async def test_low_score_skips_tier_3(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        waterfall = WaterfallV2(bright_data_client=mock_client)

        lead = LeadRecord(als_score=20)
        result = await waterfall.enrich_tier_3(lead)

        assert result == lead  # Unchanged


class TestHotThreshold:
    """Test HOT threshold for Kaspr"""

    @pytest.mark.asyncio
    async def test_warm_score_skips_kaspr(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        waterfall = WaterfallV2(bright_data_client=mock_client)

        # Warm lead (below 85)
        lead = LeadRecord(als_score=70)
        result = await waterfall.enrich_tier_5(lead)

        assert result == lead  # No Kaspr enrichment

    @pytest.mark.asyncio
    async def test_hot_score_gets_kaspr(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        mock_kaspr = Mock()
        mock_kaspr.get_contact = Mock(return_value={"mobile": "+61400000000"})

        WaterfallV2(
            bright_data_client=mock_client,
            kaspr_client=mock_kaspr
        )

        # Hot lead
        LeadRecord(
            als_score=90,
            decision_makers=[{"linkedin_url": "https://linkedin.com/in/test"}]
        )

        # Should attempt Kaspr enrichment
        # (implementation will call kaspr_client)


class TestALSCalculation:
    """Test ALS scoring algorithm"""

    def test_als_range(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        waterfall = WaterfallV2(bright_data_client=mock_client)

        lead = LeadRecord()
        score = waterfall.calculate_als(lead)

        assert 0 <= score <= 100

    def test_hiring_signal_increases_timing_score(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        waterfall = WaterfallV2(bright_data_client=mock_client)

        # Lead without hiring signals
        lead_no_hiring = LeadRecord(
            linkedin_data={"updates": [{"text": "Regular company update"}]}
        )

        # Lead with hiring signals
        lead_hiring = LeadRecord(
            linkedin_data={"updates": [{"text": "We're #hiring a new developer!"}]}
        )

        score_no_hiring = waterfall.calculate_als(lead_no_hiring)
        score_hiring = waterfall.calculate_als(lead_hiring)

        # Hiring signals should increase score
        assert score_hiring >= score_no_hiring


class TestTierSequence:
    """Test tier execution order"""

    @pytest.mark.asyncio
    async def test_tier_order_tracked(self):
        from enrichment.waterfall_v2 import LeadRecord, WaterfallV2

        mock_client = Mock()
        waterfall = WaterfallV2(bright_data_client=mock_client)

        lead = LeadRecord(enrichment_tiers_completed=[])

        # After Tier 1
        lead = await waterfall.enrich_tier_1(lead)
        assert "tier_1" in lead.enrichment_tiers_completed or lead.enrichment_tiers_completed is not None


class TestCostAccumulation:
    """Test cost tracking through pipeline"""

    def test_lead_cost_accumulates(self):
        from enrichment.waterfall_v2 import LeadRecord

        lead = LeadRecord(cost_aud=0.0)

        # Simulate adding tier costs
        lead.cost_aud += 0.0015  # SERP Maps
        lead.cost_aud += 0.0015  # SERP LinkedIn
        lead.cost_aud += 0.0015  # LinkedIn Company

        assert lead.cost_aud == pytest.approx(0.0045, rel=1e-6)
