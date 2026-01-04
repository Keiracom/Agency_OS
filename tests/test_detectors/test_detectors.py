"""
FILE: tests/test_detectors/test_detectors.py
PURPOSE: Unit tests for WHO, WHAT, WHEN, HOW detectors
PHASE: 16 (Conversion Intelligence)
TASK: 16A-007, 16B-005, 16C-004, 16D-004
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.detectors.who_detector import WhoDetector
from src.detectors.what_detector import WhatDetector
from src.detectors.when_detector import WhenDetector
from src.detectors.how_detector import HowDetector
from src.engines.content_utils import (
    extract_pain_points,
    extract_cta,
    detect_personalization,
    PAIN_POINT_KEYWORDS,
    CTA_PATTERNS,
)


# ============================================
# WHO Detector Tests
# ============================================


class TestWhoDetector:
    """Tests for WhoDetector class."""

    def test_has_correct_pattern_type(self):
        """WHO detector has pattern_type = 'who'."""
        detector = WhoDetector()
        assert detector.pattern_type == "who"

    def test_default_patterns_structure(self):
        """Default patterns have expected structure."""
        detector = WhoDetector()
        patterns = detector._default_patterns()

        assert patterns["type"] == "who"
        assert "version" in patterns
        assert "title_rankings" in patterns
        assert "industry_rankings" in patterns
        assert "size_analysis" in patterns
        assert "timing_signals" in patterns
        assert patterns["note"] == "Insufficient data. Using defaults."

    def test_inherits_from_base_detector(self):
        """WHO detector inherits from BaseDetector."""
        detector = WhoDetector()
        assert hasattr(detector, "calculate_confidence")
        assert hasattr(detector, "calculate_lift")
        assert hasattr(detector, "min_sample_size")


# ============================================
# WHAT Detector Tests
# ============================================


class TestWhatDetector:
    """Tests for WhatDetector class."""

    def test_has_correct_pattern_type(self):
        """WHAT detector has pattern_type = 'what'."""
        detector = WhatDetector()
        assert detector.pattern_type == "what"

    def test_default_patterns_structure(self):
        """Default patterns have expected structure."""
        detector = WhatDetector()
        patterns = detector._default_patterns()

        assert patterns["type"] == "what"
        assert "subject_patterns" in patterns
        assert "pain_points" in patterns
        assert "ctas" in patterns
        assert "angles" in patterns
        assert "optimal_length" in patterns
        assert "personalization_lift" in patterns


class TestPainPointExtraction:
    """Tests for pain point extraction utility."""

    def test_extracts_roi_pain_point(self):
        """Extracts ROI-related pain points."""
        text = "Are you struggling with poor ROI on your marketing spend?"
        result = extract_pain_points(text)
        assert "roi" in result

    def test_extracts_growth_pain_point(self):
        """Extracts growth-related pain points."""
        text = "Companies looking to scale their growth often face challenges."
        result = extract_pain_points(text)
        assert "growth" in result

    def test_handles_empty_text(self):
        """Returns empty list for empty text."""
        result = extract_pain_points("")
        assert result == []

    def test_case_insensitive(self):
        """Extraction is case insensitive."""
        text = "SCALING your business requires EFFICIENCY improvements."
        result = extract_pain_points(text)
        assert len(result) >= 2


class TestCTAExtraction:
    """Tests for CTA extraction utility."""

    def test_extracts_schedule_cta(self):
        """Extracts 'schedule a call' CTA."""
        text = "Let's schedule a call to discuss your needs."
        result = extract_cta(text)
        assert result == "schedule"

    def test_extracts_book_cta(self):
        """Extracts 'book a demo' CTA."""
        text = "Would you like to book a demo next week?"
        result = extract_cta(text)
        assert result == "book"

    def test_extracts_learn_more_cta(self):
        """Extracts 'learn more' CTA."""
        text = "Click here to learn more about our services."
        result = extract_cta(text)
        assert result == "learn_more"

    def test_returns_none_for_no_cta(self):
        """Returns None when no CTA found."""
        text = "This is just an informational message."
        result = extract_cta(text)
        assert result is None


class TestPersonalizationDetection:
    """Tests for personalization detection utility."""

    def test_detects_name_personalization(self):
        """Detects when first name is used."""
        class MockLead:
            first_name = "John"
            company = "Acme Corp"
            title = "CEO"

        text = "Hi John, I wanted to reach out about..."
        result = detect_personalization(text, MockLead())
        assert result["uses_name"] is True

    def test_detects_company_personalization(self):
        """Detects when company name is used."""
        class MockLead:
            first_name = "John"
            company = "Acme Corp"
            title = "CEO"

        text = "I noticed Acme Corp recently..."
        result = detect_personalization(text, MockLead())
        assert result["uses_company"] is True

    def test_detects_no_personalization(self):
        """Detects when no personalization is used."""
        class MockLead:
            first_name = "John"
            company = "Acme Corp"
            title = "CEO"

        text = "Dear Sir or Madam, we offer great services."
        result = detect_personalization(text, MockLead())
        assert result["uses_name"] is False
        assert result["uses_company"] is False


# ============================================
# WHEN Detector Tests
# ============================================


class TestWhenDetector:
    """Tests for WhenDetector class."""

    def test_has_correct_pattern_type(self):
        """WHEN detector has pattern_type = 'when'."""
        detector = WhenDetector()
        assert detector.pattern_type == "when"

    def test_default_patterns_structure(self):
        """Default patterns have expected structure."""
        detector = WhenDetector()
        patterns = detector._default_patterns()

        assert patterns["type"] == "when"
        assert "best_days" in patterns
        assert "best_hours" in patterns
        assert "converting_touch_distribution" in patterns
        assert "optimal_sequence_gaps" in patterns

    def test_default_gaps_provided(self):
        """Default sequence gaps are provided."""
        detector = WhenDetector()
        patterns = detector._default_patterns()
        gaps = patterns["optimal_sequence_gaps"]

        assert "touch_1_to_2" in gaps
        assert "touch_2_to_3" in gaps
        assert "touch_3_to_4" in gaps
        assert gaps["touch_1_to_2"] == 2
        assert gaps["touch_2_to_3"] == 3
        assert gaps["touch_3_to_4"] == 4


# ============================================
# HOW Detector Tests
# ============================================


class TestHowDetector:
    """Tests for HowDetector class."""

    def test_has_correct_pattern_type(self):
        """HOW detector has pattern_type = 'how'."""
        detector = HowDetector()
        assert detector.pattern_type == "how"

    def test_default_patterns_structure(self):
        """Default patterns have expected structure."""
        detector = HowDetector()
        patterns = detector._default_patterns()

        assert patterns["type"] == "how"
        assert "channel_effectiveness" in patterns
        assert "sequence_patterns" in patterns
        assert "tier_channel_effectiveness" in patterns
        assert "multi_channel_lift" in patterns

    def test_default_multi_channel_recommendation(self):
        """Default recommends multi-channel strategy."""
        detector = HowDetector()
        patterns = detector._default_patterns()
        multi = patterns["multi_channel_lift"]

        assert multi["recommendation"] == "multi"
        assert multi["multi_channel_lift"] == 1.0


# ============================================
# Detector Consistency Tests
# ============================================


class TestDetectorConsistency:
    """Tests for consistency across all detectors."""

    def test_all_detectors_have_pattern_type(self):
        """All detectors have a pattern_type attribute."""
        detectors = [WhoDetector(), WhatDetector(), WhenDetector(), HowDetector()]
        for detector in detectors:
            assert hasattr(detector, "pattern_type")
            assert detector.pattern_type in ["who", "what", "when", "how"]

    def test_all_detectors_have_detect_method(self):
        """All detectors have an async detect method."""
        detectors = [WhoDetector(), WhatDetector(), WhenDetector(), HowDetector()]
        for detector in detectors:
            assert hasattr(detector, "detect")
            assert callable(detector.detect)

    def test_all_detectors_have_default_patterns(self):
        """All detectors have _default_patterns method."""
        detectors = [WhoDetector(), WhatDetector(), WhenDetector(), HowDetector()]
        for detector in detectors:
            assert hasattr(detector, "_default_patterns")
            patterns = detector._default_patterns()
            assert isinstance(patterns, dict)
            assert "type" in patterns
            assert "version" in patterns

    def test_all_defaults_include_version(self):
        """All default patterns include version string."""
        detectors = [WhoDetector(), WhatDetector(), WhenDetector(), HowDetector()]
        for detector in detectors:
            patterns = detector._default_patterns()
            assert patterns["version"] == "1.0"

    def test_all_detectors_share_base_config(self):
        """All detectors inherit min_sample_size from base."""
        detectors = [WhoDetector(), WhatDetector(), WhenDetector(), HowDetector()]
        for detector in detectors:
            assert detector.min_sample_size == 30
            assert detector.validity_days == 14


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] WHO detector tests
# [x] WHAT detector tests
# [x] WHEN detector tests
# [x] HOW detector tests
# [x] Content utils tests (pain points, CTA, personalization)
# [x] Detector consistency tests
# [x] Default patterns structure tests
# [x] Edge case coverage
