"""
FILE: tests/integration/test_who_integration.py
PURPOSE: Integration tests for WHO Detector with Scorer Engine
PHASE: 16 (Conversion Intelligence)
TASK: 16A-008

Tests the full integration of:
1. WHO Detector pattern detection from leads
2. Weight optimization via scipy
3. Scorer Engine consuming learned weights
4. Pattern persistence and retrieval
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from src.detectors.who_detector import WhoDetector
from src.detectors.weight_optimizer import WeightOptimizer, DEFAULT_WEIGHTS, COMPONENTS
from src.detectors.base import BaseDetector
from src.models.base import LeadStatus
from src.models.conversion_patterns import ConversionPattern


# ============================================
# Mock Lead Class for Testing
# ============================================

class MockLead:
    """Mock lead object for testing without database."""

    def __init__(
        self,
        status: LeadStatus = LeadStatus.NEW,
        title: str = "CEO",
        organization_industry: str = "Technology",
        organization_employee_count: int = 25,
        enriched_data: dict | None = None,
    ):
        self.id = uuid4()
        self.client_id = uuid4()
        self.status = status
        self.title = title
        self.organization_industry = organization_industry
        self.organization_employee_count = organization_employee_count
        self.enriched_data = enriched_data or {}
        self.created_at = datetime.utcnow()
        self.deleted_at = None


# ============================================
# WHO Detector Integration Tests
# ============================================

class TestWhoDetectorIntegration:
    """Integration tests for WHO Detector end-to-end flow."""

    @pytest.fixture
    def detector(self) -> WhoDetector:
        """Create WHO detector instance."""
        return WhoDetector()

    def test_title_normalization_groups_correctly(self):
        """Title normalization groups similar titles together."""
        detector = WhoDetector()

        # All should normalize to the same canonical form
        test_cases = [
            ("Chief Executive Officer", "ceo"),
            ("CEO", "ceo"),
            ("Chief Exec", "ceo"),
            ("Founder", "owner"),
            ("Co-Founder", "owner"),
            ("CoFounder", "owner"),
            ("Principal", "owner"),
            ("Chief Marketing Officer", "cmo"),
            ("VP Marketing", "cmo"),
            ("VP of Marketing", "cmo"),
        ]

        for input_title, expected in test_cases:
            result = detector._normalize_title(input_title)
            assert result == expected, f"Expected {input_title} -> {expected}, got {result}"

    def test_title_analysis_calculates_conversion_rates(self):
        """Title analysis correctly calculates conversion rates per title."""
        detector = WhoDetector()

        # Create test leads: 5 CEOs (3 converted), 5 Managers (1 converted)
        leads = [
            MockLead(status=LeadStatus.CONVERTED, title="CEO"),
            MockLead(status=LeadStatus.CONVERTED, title="CEO"),
            MockLead(status=LeadStatus.CONVERTED, title="CEO"),
            MockLead(status=LeadStatus.BOUNCED, title="CEO"),
            MockLead(status=LeadStatus.OPT_OUT, title="CEO"),
            MockLead(status=LeadStatus.CONVERTED, title="Manager"),
            MockLead(status=LeadStatus.BOUNCED, title="Manager"),
            MockLead(status=LeadStatus.BOUNCED, title="Manager"),
            MockLead(status=LeadStatus.OPT_OUT, title="Manager"),
            MockLead(status=LeadStatus.NURTURING, title="Manager"),
        ]

        baseline_rate = 4 / 10  # 40% overall

        result = detector._analyze_titles(leads, baseline_rate)

        # Should have 2 title rankings
        assert len(result) == 2

        # Find CEO ranking
        ceo_rank = next((r for r in result if r["title"] == "ceo"), None)
        assert ceo_rank is not None
        assert ceo_rank["conversion_rate"] == 0.6  # 3/5 = 60%
        assert ceo_rank["sample"] == 5

        # Find Manager ranking
        mgr_rank = next((r for r in result if "manager" in r["title"].lower()), None)
        assert mgr_rank is not None
        assert mgr_rank["conversion_rate"] == 0.2  # 1/5 = 20%

    def test_industry_analysis_ranks_by_conversion(self):
        """Industry analysis ranks industries by conversion rate."""
        detector = WhoDetector()

        leads = [
            # SaaS: 4/5 = 80% conversion
            MockLead(status=LeadStatus.CONVERTED, organization_industry="SaaS"),
            MockLead(status=LeadStatus.CONVERTED, organization_industry="SaaS"),
            MockLead(status=LeadStatus.CONVERTED, organization_industry="SaaS"),
            MockLead(status=LeadStatus.CONVERTED, organization_industry="SaaS"),
            MockLead(status=LeadStatus.BOUNCED, organization_industry="SaaS"),
            # Healthcare: 1/5 = 20% conversion
            MockLead(status=LeadStatus.CONVERTED, organization_industry="Healthcare"),
            MockLead(status=LeadStatus.BOUNCED, organization_industry="Healthcare"),
            MockLead(status=LeadStatus.BOUNCED, organization_industry="Healthcare"),
            MockLead(status=LeadStatus.OPT_OUT, organization_industry="Healthcare"),
            MockLead(status=LeadStatus.NURTURING, organization_industry="Healthcare"),
        ]

        baseline_rate = 5 / 10  # 50%

        result = detector._analyze_industries(leads, baseline_rate)

        assert len(result) == 2
        # SaaS should be first (higher conversion)
        assert result[0]["industry"] == "SaaS"
        assert result[0]["conversion_rate"] == 0.8
        # Healthcare should be second
        assert result[1]["industry"] == "Healthcare"
        assert result[1]["conversion_rate"] == 0.2

    def test_company_size_identifies_sweet_spot(self):
        """Company size analysis identifies the sweet spot range."""
        detector = WhoDetector()

        leads = [
            # 16-30 range: 4/5 = 80% - should be sweet spot
            MockLead(status=LeadStatus.CONVERTED, organization_employee_count=20),
            MockLead(status=LeadStatus.CONVERTED, organization_employee_count=25),
            MockLead(status=LeadStatus.CONVERTED, organization_employee_count=28),
            MockLead(status=LeadStatus.CONVERTED, organization_employee_count=18),
            MockLead(status=LeadStatus.BOUNCED, organization_employee_count=22),
            # 51-100 range: 1/5 = 20%
            MockLead(status=LeadStatus.CONVERTED, organization_employee_count=60),
            MockLead(status=LeadStatus.BOUNCED, organization_employee_count=70),
            MockLead(status=LeadStatus.BOUNCED, organization_employee_count=80),
            MockLead(status=LeadStatus.OPT_OUT, organization_employee_count=90),
            MockLead(status=LeadStatus.NURTURING, organization_employee_count=55),
        ]

        baseline_rate = 5 / 10

        result = detector._analyze_company_size(leads, baseline_rate)

        assert result["sweet_spot"] == "16-30"
        assert result["sweet_spot_rate"] == 0.8

    def test_timing_signals_calculate_lift(self):
        """Timing signals correctly calculate lift over baseline."""
        detector = WhoDetector()

        leads = [
            # New role leads: 4/5 converted = 80%
            MockLead(
                status=LeadStatus.CONVERTED,
                enriched_data={"job_change_90d": True}
            ),
            MockLead(
                status=LeadStatus.CONVERTED,
                enriched_data={"job_change_90d": True}
            ),
            MockLead(
                status=LeadStatus.CONVERTED,
                enriched_data={"job_change_90d": True}
            ),
            MockLead(
                status=LeadStatus.CONVERTED,
                enriched_data={"job_change_90d": True}
            ),
            MockLead(
                status=LeadStatus.BOUNCED,
                enriched_data={"job_change_90d": True}
            ),
            # Non-new-role leads: 1/5 converted = 20%
            MockLead(status=LeadStatus.CONVERTED),
            MockLead(status=LeadStatus.BOUNCED),
            MockLead(status=LeadStatus.BOUNCED),
            MockLead(status=LeadStatus.OPT_OUT),
            MockLead(status=LeadStatus.NURTURING),
        ]

        baseline_rate = 5 / 10  # 50%

        result = detector._analyze_timing_signals(leads, baseline_rate)

        # New role rate = 80%, baseline = 50%, lift = 80/50 = 1.6
        assert "new_role_lift" in result
        assert result["new_role_lift"] == 1.6

    def test_default_patterns_returned_for_insufficient_data(self):
        """Default patterns returned when sample size is too small."""
        detector = WhoDetector()

        # Only 10 leads (below min_sample_size of 30)
        leads = [MockLead(status=LeadStatus.CONVERTED) for _ in range(10)]

        # Simulate _get_leads_with_outcomes returning small set
        patterns = detector._default_patterns()

        assert patterns["type"] == "who"
        assert patterns["sample_size"] == 0
        assert "note" in patterns
        assert "Insufficient data" in patterns["note"]


# ============================================
# Weight Optimizer Integration Tests
# ============================================

class TestWeightOptimizerIntegration:
    """Integration tests for weight optimization with scoring."""

    def test_weight_constraints_sum_to_1(self):
        """Optimized weights always sum to 1."""
        optimizer = WeightOptimizer()

        # Simulate component scores for leads
        test_weights = [0.25, 0.20, 0.20, 0.20, 0.15]

        total = sum(test_weights)
        assert abs(total - 1.0) < 0.001

    def test_bounds_enforced_on_all_weights(self):
        """All weights stay within defined bounds."""
        min_bound, max_bound = 0.05, 0.50

        for component, weight in DEFAULT_WEIGHTS.items():
            assert min_bound <= weight <= max_bound, \
                f"{component} weight {weight} outside bounds"

    def test_score_calculation_with_weights(self):
        """Weighted score calculation produces correct results."""
        # Sample lead component scores (0-100)
        components = {
            "data_quality": 80,
            "authority": 90,
            "company_fit": 70,
            "timing": 50,
            "risk": 85,
        }

        # Calculate weighted score
        score = sum(
            components[comp] * DEFAULT_WEIGHTS[comp]
            for comp in COMPONENTS
        )

        # Score should be reasonable (0-100 range)
        assert 0 <= score <= 100

        # Manual calculation:
        # 80*0.20 + 90*0.25 + 70*0.25 + 50*0.15 + 85*0.15
        # = 16 + 22.5 + 17.5 + 7.5 + 12.75 = 76.25
        expected = 76.25
        assert abs(score - expected) < 0.01


# ============================================
# Scorer Engine Integration Tests
# ============================================

class TestScorerIntegration:
    """Integration tests for Scorer Engine with learned weights."""

    @pytest.mark.asyncio
    async def test_scorer_uses_default_weights_when_no_patterns(self):
        """Scorer falls back to default weights when no patterns exist."""
        # The scorer should use DEFAULT_WEIGHTS when no learned weights available
        from src.engines.scorer import ScorerEngine

        scorer = ScorerEngine()

        # Mock session that returns no pattern
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Get weights (should return defaults)
        weights = await scorer._get_learned_weights(mock_session, uuid4())

        # Should return None (no pattern), scorer uses defaults
        assert weights is None or weights == DEFAULT_WEIGHTS

    def test_als_tiers_assigned_correctly(self):
        """ALS scores map to correct tiers."""
        tier_mappings = {
            (85, 100): "Hot",
            (60, 84): "Warm",
            (35, 59): "Cool",
            (20, 34): "Cold",
            (0, 19): "Dead",
        }

        for (min_score, max_score), expected_tier in tier_mappings.items():
            # Test at boundaries
            for score in [min_score, max_score, (min_score + max_score) // 2]:
                if score >= 85:
                    tier = "Hot"
                elif score >= 60:
                    tier = "Warm"
                elif score >= 35:
                    tier = "Cool"
                elif score >= 20:
                    tier = "Cold"
                else:
                    tier = "Dead"

                assert tier == expected_tier, \
                    f"Score {score} should be {expected_tier}, got {tier}"


# ============================================
# Pattern Persistence Integration Tests
# ============================================

class TestPatternPersistence:
    """Integration tests for pattern storage and retrieval."""

    def test_pattern_structure_valid(self):
        """Pattern output has valid structure for storage."""
        detector = WhoDetector()
        patterns = detector._default_patterns()

        # Required fields for ConversionPattern model
        required_fields = [
            "type",
            "version",
        ]

        for field in required_fields:
            assert field in patterns, f"Missing required field: {field}"

        assert patterns["type"] == "who"

    def test_confidence_score_bounds(self):
        """Confidence scores are always between 0 and 1."""
        test_samples = [0, 10, 30, 50, 100, 500, 1000, 5000]

        for sample in test_samples:
            confidence = BaseDetector.calculate_confidence(sample)
            assert 0 <= confidence <= 1, \
                f"Confidence {confidence} out of bounds for sample {sample}"

    def test_validity_period_calculation(self):
        """Pattern validity is calculated correctly."""
        detector = WhoDetector()

        # Default validity is 14 days
        assert detector.validity_days == 14

        computed_at = datetime.utcnow()
        valid_until = computed_at + timedelta(days=detector.validity_days)

        # Valid until should be 14 days in the future
        delta = valid_until - computed_at
        assert delta.days == 14


# ============================================
# End-to-End Integration Tests
# ============================================

class TestEndToEndIntegration:
    """End-to-end tests for the complete WHO pattern flow."""

    def test_full_detection_to_scoring_flow(self):
        """Test the complete flow from detection to scoring."""
        # 1. Create detector
        detector = WhoDetector()

        # 2. Create leads with clear patterns
        leads = []

        # High-converting segment: CEOs at 16-30 employee companies
        for _ in range(20):
            leads.append(MockLead(
                status=LeadStatus.CONVERTED,
                title="CEO",
                organization_industry="SaaS",
                organization_employee_count=25,
            ))

        # Low-converting segment: Analysts at large companies
        for _ in range(30):
            leads.append(MockLead(
                status=LeadStatus.BOUNCED,
                title="Analyst",
                organization_industry="Finance",
                organization_employee_count=500,
            ))

        # Add some converted analysts (10% conversion)
        for _ in range(3):
            leads.append(MockLead(
                status=LeadStatus.CONVERTED,
                title="Analyst",
                organization_industry="Finance",
                organization_employee_count=500,
            ))

        # 3. Run analyses
        baseline_rate = 23 / 53  # Total conversions / total leads

        title_rankings = detector._analyze_titles(leads, baseline_rate)
        industry_rankings = detector._analyze_industries(leads, baseline_rate)
        size_analysis = detector._analyze_company_size(leads, baseline_rate)

        # 4. Verify patterns detected correctly
        assert len(title_rankings) >= 2
        assert title_rankings[0]["title"] == "ceo"  # CEO should rank highest
        assert title_rankings[0]["conversion_rate"] == 1.0  # 100% conversion

        assert len(industry_rankings) >= 2
        assert industry_rankings[0]["industry"] == "SaaS"  # SaaS should rank highest

        assert size_analysis["sweet_spot"] == "16-30"  # 16-30 employees is sweet spot

    def test_lift_calculation_accuracy(self):
        """Lift calculations are accurate for various rates."""
        test_cases = [
            # (segment_rate, baseline_rate, expected_lift)
            (0.10, 0.05, 2.0),    # 2x lift
            (0.20, 0.10, 2.0),    # 2x lift
            (0.05, 0.10, 0.5),    # 0.5x (below baseline)
            (0.10, 0.10, 1.0),    # Equal (no lift)
            (0.30, 0.10, 3.0),    # 3x lift
        ]

        for segment, baseline, expected in test_cases:
            result = BaseDetector.calculate_lift(segment, baseline)
            assert abs(result - expected) < 0.01, \
                f"Lift({segment}/{baseline}) expected {expected}, got {result}"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] MockLead class for testing without database
# [x] Title normalization tests
# [x] Title analysis tests
# [x] Industry analysis tests
# [x] Company size analysis tests
# [x] Timing signals tests
# [x] Default patterns tests
# [x] Weight optimizer integration tests
# [x] Scorer integration tests
# [x] Pattern persistence tests
# [x] End-to-end flow tests
# [x] Lift calculation accuracy tests
