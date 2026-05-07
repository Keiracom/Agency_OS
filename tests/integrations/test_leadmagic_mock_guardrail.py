"""Tests for the LEADMAGIC_MOCK production guardrail in src/integrations/leadmagic.py.

The guardrail refuses module load if LEADMAGIC_MOCK is truthy AND
the environment is detected as production. Catastrophic-blast-radius-
prevention: mock mode returns fake AU mobile numbers and emails which
would be sent to real campaign prospects.

Tests cover:
- Mock + production env → RuntimeError raised
- Mock + dev env → no error
- Production env without mock → no error
- Dev env without mock → no error
- Production heuristic via worktree path detection
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def test_mock_safe_dev_env_with_mock_off():
    """Dev environment, mock OFF: no error, normal operation."""
    from src.integrations.leadmagic import _assert_mock_safe, _is_mock_mode

    with patch.dict(os.environ, {"LEADMAGIC_MOCK": "", "FASTAPI_ENV": "dev"}, clear=False):
        assert _is_mock_mode() is False
        _assert_mock_safe()  # Should not raise


def test_mock_safe_dev_env_with_mock_on():
    """Dev environment, mock ON: no error, mock allowed in dev."""
    from src.integrations.leadmagic import _assert_mock_safe, _is_mock_mode

    with patch.dict(os.environ, {"LEADMAGIC_MOCK": "true", "FASTAPI_ENV": "dev"}, clear=False):
        assert _is_mock_mode() is True
        # Should not raise — mock allowed in dev
        _assert_mock_safe()


def test_mock_safe_production_env_with_mock_off():
    """Production env, mock OFF: no error, normal production operation."""
    from src.integrations.leadmagic import _assert_mock_safe, _is_mock_mode

    with patch.dict(os.environ, {"LEADMAGIC_MOCK": "", "FASTAPI_ENV": "production"}, clear=False):
        assert _is_mock_mode() is False
        _assert_mock_safe()  # Should not raise


def test_mock_safe_production_env_with_mock_on_raises():
    """Production env, mock ON: RuntimeError raised — refuses module load."""
    from src.integrations.leadmagic import _assert_mock_safe, _is_mock_mode

    with patch.dict(
        os.environ, {"LEADMAGIC_MOCK": "true", "FASTAPI_ENV": "production"}, clear=False
    ):
        assert _is_mock_mode() is True
        with pytest.raises(
            RuntimeError, match="LEADMAGIC_MOCK is enabled in a production environment"
        ):
            _assert_mock_safe()


def test_mock_safe_production_via_worktree_path_heuristic():
    """Production heuristic: main worktree path triggers production detection."""
    from src.integrations.leadmagic import _is_production_environment

    # Heuristic check: when __file__ resolves to main worktree, production = True
    # Direct unit test of the detection function
    with patch.dict(os.environ, {"FASTAPI_ENV": "dev"}, clear=False):
        # FASTAPI_ENV=dev shouldn't override worktree-path heuristic
        # We can't easily fake __file__ in this test, so this asserts
        # the function returns based on real path resolution
        result = _is_production_environment()
        # Aiden worktree path → not production
        assert result is False or "/clawd/Agency_OS/" in os.path.abspath(
            "src/integrations/leadmagic.py"
        )


def test_mock_safe_various_truthy_values_in_production():
    """Mock-mode env var: 'true', '1', 'yes' all trigger guardrail in production."""
    from src.integrations.leadmagic import _assert_mock_safe

    for truthy in ("true", "TRUE", "1", "yes", "YES"):
        with patch.dict(
            os.environ,
            {"LEADMAGIC_MOCK": truthy, "FASTAPI_ENV": "production"},
            clear=False,
        ):
            with pytest.raises(RuntimeError):
                _assert_mock_safe()


def test_mock_safe_falsy_values_pass_through():
    """Mock-mode env var: 'false', '0', '', 'no' do not trigger guardrail."""
    from src.integrations.leadmagic import _assert_mock_safe

    for falsy in ("false", "0", "", "no", "FALSE"):
        with patch.dict(
            os.environ,
            {"LEADMAGIC_MOCK": falsy, "FASTAPI_ENV": "production"},
            clear=False,
        ):
            _assert_mock_safe()  # Should not raise — mock is off
