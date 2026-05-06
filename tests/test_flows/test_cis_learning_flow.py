"""
Tests for CIS Learning Flow - Directive #157

Tests the configurable MIN_OUTCOMES_THRESHOLD via environment variable.
"""

import os
import sys
import pytest
from unittest.mock import patch


class TestCISThresholdConfig:
    """Test MIN_OUTCOMES_THRESHOLD configuration via environment variable."""

    def _reload_cis_module(self):
        """Helper to force re-import of cis_learning_flow module."""
        module_name = "src.orchestration.flows.cis_learning_flow"
        if module_name in sys.modules:
            del sys.modules[module_name]
        import src.orchestration.flows.cis_learning_flow as cis_flow

        return cis_flow

    def test_default_threshold_is_20(self):
        """When env var not set, threshold defaults to 20."""
        # Remove env var if set
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CIS_MIN_OUTCOMES_THRESHOLD", None)
            cis_flow = self._reload_cis_module()
            assert cis_flow.MIN_OUTCOMES_THRESHOLD == 20

    def test_threshold_reads_from_env_var(self):
        """When CIS_MIN_OUTCOMES_THRESHOLD is set, it overrides the default."""
        with patch.dict(os.environ, {"CIS_MIN_OUTCOMES_THRESHOLD": "50"}):
            cis_flow = self._reload_cis_module()
            assert cis_flow.MIN_OUTCOMES_THRESHOLD == 50

    def test_threshold_accepts_different_values(self):
        """Threshold can be set to various integer values."""
        test_values = [5, 10, 100, 1000]

        for value in test_values:
            with patch.dict(os.environ, {"CIS_MIN_OUTCOMES_THRESHOLD": str(value)}):
                cis_flow = self._reload_cis_module()
                assert cis_flow.MIN_OUTCOMES_THRESHOLD == value, (
                    f"Expected {value}, got {cis_flow.MIN_OUTCOMES_THRESHOLD}"
                )
