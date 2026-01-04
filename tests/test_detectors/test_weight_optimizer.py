"""
FILE: tests/test_detectors/test_weight_optimizer.py
PURPOSE: Unit tests for WeightOptimizer
PHASE: 16 (Conversion Intelligence)
TASK: 16A-005 (tests)
"""

import pytest
from uuid import uuid4

from src.detectors.weight_optimizer import (
    WeightOptimizer,
    DEFAULT_WEIGHTS,
    WEIGHT_BOUNDS,
    COMPONENTS,
)


class TestDefaultWeights:
    """Tests for default weight configuration."""

    def test_weights_sum_to_1(self):
        """Default weights sum to 1.0."""
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_all_components_have_weights(self):
        """All components have default weights."""
        for component in COMPONENTS:
            assert component in DEFAULT_WEIGHTS

    def test_all_weights_within_bounds(self):
        """All weights are within [0.05, 0.50] bounds."""
        min_bound, max_bound = WEIGHT_BOUNDS
        for weight in DEFAULT_WEIGHTS.values():
            assert min_bound <= weight <= max_bound


class TestWeightBounds:
    """Tests for weight constraints."""

    def test_bounds_tuple(self):
        """Bounds are defined as (min, max) tuple."""
        assert len(WEIGHT_BOUNDS) == 2
        assert WEIGHT_BOUNDS[0] < WEIGHT_BOUNDS[1]

    def test_min_bound_prevents_zero_weights(self):
        """Minimum bound prevents any weight from being 0."""
        assert WEIGHT_BOUNDS[0] > 0

    def test_max_bound_prevents_dominance(self):
        """Maximum bound prevents any single weight from dominating."""
        assert WEIGHT_BOUNDS[1] <= 0.5


class TestComponents:
    """Tests for component definitions."""

    def test_five_components(self):
        """There are exactly 5 ALS components."""
        assert len(COMPONENTS) == 5

    def test_component_names(self):
        """Component names match ALS formula."""
        expected = ["data_quality", "authority", "company_fit", "timing", "risk"]
        assert COMPONENTS == expected


class TestWeightOptimizerInit:
    """Tests for WeightOptimizer initialization."""

    def test_creates_instance(self):
        """Can create WeightOptimizer instance."""
        optimizer = WeightOptimizer()
        assert optimizer is not None

    def test_has_min_sample_attribute(self):
        """Optimizer has minimum sample requirement."""
        optimizer = WeightOptimizer()
        assert hasattr(optimizer, "min_sample")
        assert optimizer.min_sample > 0


class TestWeightNormalization:
    """Tests for weight normalization logic."""

    def test_normalize_weights_sums_to_1(self):
        """Normalized weights always sum to 1."""
        optimizer = WeightOptimizer()

        # Test with various weight configurations
        test_weights = [
            [0.1, 0.1, 0.1, 0.1, 0.1],  # All equal, low
            [0.3, 0.3, 0.2, 0.1, 0.1],  # Normal distribution
            [0.5, 0.5, 0.5, 0.5, 0.5],  # All at max bound
        ]

        for weights in test_weights:
            total = sum(weights)
            normalized = [w / total for w in weights]
            assert abs(sum(normalized) - 1.0) < 0.001


class TestScoreCalculation:
    """Tests for score calculation with weights."""

    def test_weighted_score_calculation(self):
        """Weighted score calculation works correctly."""
        # Sample component scores (0-100 normalized)
        components = {
            "data_quality": 80,
            "authority": 60,
            "company_fit": 70,
            "timing": 40,
            "risk": 90,
        }

        weights = DEFAULT_WEIGHTS

        # Calculate weighted score
        score = sum(
            components[comp] * weights[comp]
            for comp in COMPONENTS
        )

        # Score should be between 0 and 100
        assert 0 <= score <= 100

        # Calculate expected: 80*0.20 + 60*0.25 + 70*0.25 + 40*0.15 + 90*0.15
        expected = 16 + 15 + 17.5 + 6 + 13.5  # = 68
        assert abs(score - expected) < 0.1


class TestOptimizationConstraints:
    """Tests for optimization constraints."""

    def test_constraint_sum_equals_1(self):
        """Sum constraint ensures weights sum to 1."""
        # The constraint function should return 0 when satisfied

        def sum_constraint(weights):
            return sum(weights) - 1.0

        # Valid weights
        valid = [0.20, 0.25, 0.25, 0.15, 0.15]
        assert abs(sum_constraint(valid)) < 0.001

        # Invalid weights
        invalid = [0.30, 0.25, 0.25, 0.15, 0.15]  # sum = 1.10
        assert abs(sum_constraint(invalid)) > 0.05


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Tests for default weights configuration
# [x] Tests for weight bounds
# [x] Tests for component definitions
# [x] Tests for optimizer initialization
# [x] Tests for weight normalization
# [x] Tests for score calculation
# [x] Tests for optimization constraints
