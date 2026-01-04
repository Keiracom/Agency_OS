"""
FILE: tests/test_detectors/test_base_detector.py
PURPOSE: Unit tests for BaseDetector class
PHASE: 16 (Conversion Intelligence)
TASK: 16A-004 (tests)
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.detectors.base import BaseDetector
from src.models.conversion_patterns import ConversionPattern


class TestConversionRateBy:
    """Tests for the conversion_rate_by helper method."""

    def test_empty_items_returns_empty_list(self):
        """Empty input returns empty list."""
        result = BaseDetector.conversion_rate_by(
            items=[],
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
        )
        assert result == []

    def test_groups_by_key_correctly(self):
        """Items are grouped by key function."""
        items = [
            {"key": "A", "converted": True},
            {"key": "A", "converted": False},
            {"key": "B", "converted": True},
            {"key": "B", "converted": True},
        ]

        result = BaseDetector.conversion_rate_by(
            items=items,
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
            min_sample=1,
        )

        assert len(result) == 2

        # Find results by key
        result_map = {r["key"]: r for r in result}

        assert result_map["A"]["total"] == 2
        assert result_map["A"]["converted"] == 1
        assert result_map["A"]["rate"] == 0.5

        assert result_map["B"]["total"] == 2
        assert result_map["B"]["converted"] == 2
        assert result_map["B"]["rate"] == 1.0

    def test_min_sample_filters_small_groups(self):
        """Groups below min_sample are excluded."""
        items = [
            {"key": "A", "converted": True},
            {"key": "B", "converted": True},
            {"key": "B", "converted": True},
            {"key": "B", "converted": False},
        ]

        result = BaseDetector.conversion_rate_by(
            items=items,
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
            min_sample=2,  # Only groups with 2+ items
        )

        # Only B has 3 items, A has 1
        assert len(result) == 1
        assert result[0]["key"] == "B"

    def test_results_sorted_by_rate_descending(self):
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

        result = BaseDetector.conversion_rate_by(
            items=items,
            key_fn=lambda x: x["key"],
            is_converted_fn=lambda x: x["converted"],
            min_sample=2,
        )

        assert len(result) == 3
        assert result[0]["key"] == "High"  # 100%
        assert result[1]["key"] == "Med"   # 50%
        assert result[2]["key"] == "Low"   # 33%


class TestCalculateConfidence:
    """Tests for confidence score calculation."""

    def test_zero_samples_returns_zero(self):
        """Zero sample size returns 0 confidence."""
        result = BaseDetector.calculate_confidence(0)
        assert result == 0.0

    def test_min_sample_returns_low_confidence(self):
        """30 samples (minimum) returns low confidence."""
        result = BaseDetector.calculate_confidence(30)
        # Log(30) / Log(1000) = ~0.49
        assert 0.4 < result < 0.6

    def test_1000_samples_returns_full_confidence(self):
        """1000+ samples returns 1.0 confidence."""
        result = BaseDetector.calculate_confidence(1000)
        assert result == 1.0

    def test_100_samples_returns_medium_confidence(self):
        """100 samples returns medium confidence."""
        result = BaseDetector.calculate_confidence(100)
        # Log(100) / Log(1000) = ~0.67
        assert 0.6 < result < 0.8

    def test_confidence_capped_at_1(self):
        """Confidence never exceeds 1.0."""
        result = BaseDetector.calculate_confidence(10000)
        assert result == 1.0


class TestCalculateLift:
    """Tests for lift calculation."""

    def test_baseline_zero_returns_1(self):
        """Zero baseline returns 1.0 lift."""
        result = BaseDetector.calculate_lift(
            segment_rate=0.5,
            baseline_rate=0.0,
        )
        assert result == 1.0

    def test_equal_rates_returns_1(self):
        """Equal segment and baseline returns 1.0 lift."""
        result = BaseDetector.calculate_lift(
            segment_rate=0.3,
            baseline_rate=0.3,
        )
        assert result == 1.0

    def test_higher_segment_returns_positive_lift(self):
        """Segment rate higher than baseline returns lift > 1."""
        result = BaseDetector.calculate_lift(
            segment_rate=0.6,
            baseline_rate=0.3,
        )
        assert result == 2.0

    def test_lower_segment_returns_negative_lift(self):
        """Segment rate lower than baseline returns lift < 1."""
        result = BaseDetector.calculate_lift(
            segment_rate=0.15,
            baseline_rate=0.3,
        )
        assert result == 0.5


class TestPatternValidity:
    """Tests for pattern validity period."""

    def test_default_validity_is_14_days(self):
        """Default validity period is 14 days."""
        detector = BaseDetector.__new__(BaseDetector)
        assert detector.validity_days == 14

    def test_min_sample_size_is_30(self):
        """Minimum sample size is 30."""
        detector = BaseDetector.__new__(BaseDetector)
        assert detector.min_sample_size == 30


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for conversion_rate_by
# [x] Tests for calculate_confidence
# [x] Tests for calculate_lift
# [x] Tests for validity constants
# [x] Edge cases covered (empty, zero, boundary)
