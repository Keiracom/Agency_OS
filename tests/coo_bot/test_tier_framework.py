"""tests/coo_bot/test_tier_framework.py — unit tests for the COO tier gate.

MAX-COO-PHASE-B / Phase B File 1.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def tier_module(tmp_path, monkeypatch):
    """Re-import tier_framework with the override path pointing at tmp_path
    so tests don't touch the real /home/elliotbot/clawd/state file."""
    override = tmp_path / "coo_tier_override"
    monkeypatch.setenv("COO_TIER_OVERRIDE_PATH", str(override))
    monkeypatch.delenv("COO_APPROVAL_TIER", raising=False)
    import importlib

    import src.coo_bot.tier_framework as tf

    importlib.reload(tf)
    yield tf, override
    # Reload again post-test so the module's global path doesn't leak.
    importlib.reload(tf)


def test_tier_zero_denies_all(tier_module):
    tf, _ = tier_module
    assert tf.can_post("governance_flag", 0) is False
    assert tf.can_post("dispatch_ack", 0) is False
    assert tf.can_post("status_report", 0) is False


def test_tier_one_allows_pre_approved(tier_module):
    tf, _ = tier_module
    assert tf.can_post("governance_flag", 1) is True
    assert tf.can_post("dispatch_ack", 1) is True


def test_tier_one_denies_non_approved(tier_module):
    tf, _ = tier_module
    # routine ops are Tier 2, full proxy is Tier 3 — not allowed at Tier 1.
    assert tf.can_post("status_report", 1) is False
    assert tf.can_post("directive_issuance", 1) is False
    # Unknown action types are closed-by-default at every tier.
    assert tf.can_post("unknown_action", 3) is False


def test_stop_max_overrides_higher_tier(tier_module, monkeypatch):
    tf, override = tier_module
    monkeypatch.setenv("COO_APPROVAL_TIER", "3")
    tf.write_stop_override("test reason")
    assert override.is_file()
    assert tf.force_tier_zero() is True
    assert tf.get_current_tier() == 0
    # Even Tier 3 actions are denied while STOP MAX is active.
    assert tf.can_post("directive_issuance") is False
    assert tf.can_post("governance_flag") is False


def test_stop_max_clear_restores_tier(tier_module, monkeypatch):
    tf, override = tier_module
    monkeypatch.setenv("COO_APPROVAL_TIER", "2")
    tf.write_stop_override()
    assert tf.get_current_tier() == 0
    tf.clear_stop_override()
    assert override.is_file() is False
    assert tf.force_tier_zero() is False
    assert tf.get_current_tier() == 2
    assert tf.can_post("status_report") is True


def test_env_var_read_returns_int(tier_module, monkeypatch):
    tf, _ = tier_module
    monkeypatch.setenv("COO_APPROVAL_TIER", "1")
    assert tf.get_current_tier() == 1
    monkeypatch.setenv("COO_APPROVAL_TIER", "3")
    assert tf.get_current_tier() == 3
    # Out-of-range clamps; non-int falls to 0.
    monkeypatch.setenv("COO_APPROVAL_TIER", "9")
    assert tf.get_current_tier() == 3
    monkeypatch.setenv("COO_APPROVAL_TIER", "not-an-int")
    assert tf.get_current_tier() == 0
