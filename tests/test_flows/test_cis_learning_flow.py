"""
Tests for CIS Learning Flow - Directive #157

Tests the configurable MIN_OUTCOMES_THRESHOLD via environment variable.
"""

import os
import pytest
from unittest.mock import patch
import importlib


class TestCISThresholdConfig:
    """Test MIN_OUTCOMES_THRESHOLD configuration via environment variable."""

    def test_default_threshold_is_20(self):
        """When env var not set, threshold defaults to 20."""
        # Ensure env var is not set
        env_copy = os.environ.copy()
        env_copy.pop("CIS_MIN_OUTCOMES_THRESHOLD", None)
        
        with patch.dict(os.environ, env_copy, clear=True):
            # Re-import to pick up new env
            import src.orchestration.flows.cis_learning_flow as cis_flow
            importlib.reload(cis_flow)
            
            assert cis_flow.MIN_OUTCOMES_THRESHOLD == 20

    def test_threshold_reads_from_env_var(self):
        """When CIS_MIN_OUTCOMES_THRESHOLD is set, it overrides the default."""
        with patch.dict(os.environ, {"CIS_MIN_OUTCOMES_THRESHOLD": "50"}):
            # Re-import to pick up new env
            import src.orchestration.flows.cis_learning_flow as cis_flow
            importlib.reload(cis_flow)
            
            assert cis_flow.MIN_OUTCOMES_THRESHOLD == 50

    def test_threshold_accepts_different_values(self):
        """Threshold can be set to various integer values."""
        test_values = [5, 10, 100, 1000]
        
        for value in test_values:
            with patch.dict(os.environ, {"CIS_MIN_OUTCOMES_THRESHOLD": str(value)}):
                import src.orchestration.flows.cis_learning_flow as cis_flow
                importlib.reload(cis_flow)
                
                assert cis_flow.MIN_OUTCOMES_THRESHOLD == value, \
                    f"Expected {value}, got {cis_flow.MIN_OUTCOMES_THRESHOLD}"
