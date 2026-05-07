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


def test_explicit_dev_env_overrides_path_heuristic():
    """FASTAPI_ENV=dev MUST short-circuit before worktree-path heuristic.

    This is the bug Elliot caught in PR #610 review: original logic returned
    True if path matched main worktree EVEN WHEN FASTAPI_ENV=dev was explicit.
    Means a developer on main worktree setting FASTAPI_ENV=dev still got
    RuntimeError at module load.

    Fix: explicit dev/test/staging env values short-circuit to False before
    path check fires.
    """
    from src.integrations.leadmagic import _is_production_environment

    for dev_value in ("dev", "development", "test", "staging", "DEV", "Test"):
        with patch.dict(os.environ, {"FASTAPI_ENV": dev_value}, clear=False):
            assert _is_production_environment() is False, (
                f"FASTAPI_ENV={dev_value} must override worktree-path heuristic"
            )


def test_explicit_production_env_returns_true_independent_of_path():
    """FASTAPI_ENV=production returns True regardless of worktree path."""
    from src.integrations.leadmagic import _is_production_environment

    with patch.dict(os.environ, {"FASTAPI_ENV": "production"}, clear=False):
        assert _is_production_environment() is True


def test_unset_env_falls_back_to_path_heuristic():
    """FASTAPI_ENV unset/empty falls back to worktree-path detection.

    Aiden worktree path (/home/elliotbot/clawd/Agency_OS-aiden/) → not main
    → returns False. Asserted directly without trying to fake __file__.
    """
    from src.integrations.leadmagic import _is_production_environment

    # Clear FASTAPI_ENV to force fallback to path heuristic
    env_without_fastapi = {k: v for k, v in os.environ.items() if k != "FASTAPI_ENV"}
    with patch.dict(os.environ, env_without_fastapi, clear=True):
        result = _is_production_environment()
        # In Aiden worktree the test file path doesn't start with main worktree
        # path → result must be False. In Elliot main worktree result would be True.
        # Test asserts function correctly reflects the path it's loaded from.
        import src.integrations.leadmagic as lm_mod

        expected = os.path.abspath(lm_mod.__file__).startswith("/home/elliotbot/clawd/Agency_OS/")
        assert result is expected


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
