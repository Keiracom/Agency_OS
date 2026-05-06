"""
FILE: tests/test_detectors/test_base_detector.py
PURPOSE: Unit tests for BaseDetector class
PHASE: 16 (Conversion Intelligence)
TASK: 16A-004 (tests)
"""

from typing import Any

import pytest

from src.detectors.base import BaseDetector


# Concrete test implementation of BaseDetector
class TestableDetector(BaseDetector):
    """Concrete detector for testing BaseDetector methods."""

    @property
    def pattern_type(self) -> str:
        return "test"

    async def detect(self, *args, **kwargs) -> dict[str, Any]:
        return {}

    def _default_patterns(self) -> dict[str, Any]:
        return {"type": "test", "version": "1.0"}


@pytest.fixture
def detector():
    """Create a testable detector instance."""
    return TestableDetector()


class TestConversionRateBy:
    """Tests for the conversion_rate_by helper method."""

    def test_empty_items_returns_empty_list(self, detector):
        """Empty input returns empty list."""
        result = detector.conversion_rate_by(
            items=[],
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
        )
        assert result == []

    def test_groups_by_key_correctly(self, detector):
        """Items are grouped by key function."""
        items = [
            {"key": "A", "converted": True},
            {"key": "A", "converted": False},
            {"key": "B", "converted": True},
            {"key": "B", "converted": True},
        ]

        result = detector.conversion_rate_by(
            items=items,
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
            min_sample=1,
        )

        assert len(result) == 2

        # Find results by key
        result_map = {r["key"]: r for r in result}

        assert result_map["A"]["sample"] == 2
        assert result_map["A"]["converted"] == 1
        assert result_map["A"]["conversion_rate"] == 0.5

        assert result_map["B"]["sample"] == 2
        assert result_map["B"]["converted"] == 2
        assert result_map["B"]["conversion_rate"] == 1.0

    def test_min_sample_filters_small_groups(self, detector):
        """Groups below min_sample are excluded."""
        items = [
            {"key": "A", "converted": True},
            {"key": "B", "converted": True},
            {"key": "B", "converted": True},
            {"key": "B", "converted": False},
        ]

        result = detector.conversion_rate_by(
            items=items,
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
            min_sample=2,  # Only groups with 2+ items
        )

        # Only B has 3 items, A has 1
        assert len(result) == 1
        assert result[0]["key"] == "B"

    def test_results_sorted_by_rate_descending(self, detector):
        """Results are sorted by conversion rate, highest first."""
        items = [
            {"key": "Low", "converted": False},
            {"key": "Low", "converted": False},
            {"key": "Low", "converted": True},
            {"key": "Med", "converted": True},
            {"key": "Med", "converted": False},
            {"key": "High", "converted": True},
            {"key": "High", "converted": True},
        ]

        result = detector.conversion_rate_by(
            items=items,
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
            min_sample=2,
        )

        assert len(result) == 3
        assert result[0]["key"] == "High"  # 100%
        assert result[1]["key"] == "Med"  # 50%
        assert result[2]["key"] == "Low"  # 33%


class TestCalculateConfidence:
    """Tests for confidence score calculation."""

    def test_low_samples_returns_baseline(self, detector):
        """Very low sample size (<10) returns baseline 0.2 confidence."""
        result = detector.calculate_confidence(0)
        assert result == 0.2
        result = detector.calculate_confidence(5)
        assert result == 0.2

    def test_min_sample_returns_medium_confidence(self, detector):
        """30 samples (minimum) returns ~0.5 confidence per docstring."""
        result = detector.calculate_confidence(30)
        assert 0.5 <= result <= 0.75

    def test_1000_samples_returns_high_confidence(self, detector):
        """1000+ samples returns 0.95 confidence per docstring."""
        result = detector.calculate_confidence(1000)
        assert result == 0.95

    def test_100_samples_returns_medium_confidence(self, detector):
        """100 samples returns ~0.7 confidence per docstring."""
        result = detector.calculate_confidence(100)
        assert 0.65 < result < 0.85

    def test_confidence_capped_at_95(self, detector):
        """Confidence caps at 0.95."""
        result = detector.calculate_confidence(10000)
        assert result == 0.95


class TestCalculateLift:
    """Tests for lift calculation."""

    def test_baseline_zero_returns_1(self, detector):
        """Zero baseline returns 1.0 lift."""
        result = detector.calculate_lift(
            segment_rate=0.5,
            baseline_rate=0.0,
        )
        assert result == 1.0

    def test_equal_rates_returns_1(self, detector):
        """Equal segment and baseline returns 1.0 lift."""
        result = detector.calculate_lift(
            segment_rate=0.3,
            baseline_rate=0.3,
        )
        assert result == 1.0

    def test_higher_segment_returns_positive_lift(self, detector):
        """Segment rate higher than baseline returns lift > 1."""
        result = detector.calculate_lift(
            segment_rate=0.6,
            baseline_rate=0.3,
        )
        assert result == 2.0

    def test_lower_segment_returns_negative_lift(self, detector):
        """Segment rate lower than baseline returns lift < 1."""
        result = detector.calculate_lift(
            segment_rate=0.15,
            baseline_rate=0.3,
        )
        assert result == 0.5


class TestPatternValidity:
    """Tests for pattern validity period."""

    def test_default_validity_is_14_days(self, detector):
        """Default validity period is 14 days."""
        assert detector.validity_days == 14

    def test_min_sample_size_is_30(self, detector):
        """Minimum sample size is 30."""
        assert detector.min_sample_size == 30


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for conversion_rate_by
# [x] Tests for calculate_confidence
# [x] Tests for calculate_lift
# [x] Tests for validity constants
# [x] Edge cases covered (empty, zero, boundary)
# [x] Uses concrete TestableDetector subclass
# [x] Uses pytest fixture for detector instance
