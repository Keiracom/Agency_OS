"""tests/config/test_email_costs.py — unit tests for per-channel email cost config.

Pure-function tests; no DB, no network.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.config.email_costs import (
    RESEND_COST_AUD_PER_EMAIL,
    SMARTLEAD_COST_AUD_PER_EMAIL,
    cost_for_channel,
)


def test_resend_cost_is_decimal():
    """Resend cost is a Decimal with cent precision (DB column is DECIMAL(8,4))."""
    assert isinstance(RESEND_COST_AUD_PER_EMAIL, Decimal)
    assert Decimal("0") < RESEND_COST_AUD_PER_EMAIL
    # Sanity: should be sub-cent, well under $0.01 per send
    assert Decimal("0.01") > RESEND_COST_AUD_PER_EMAIL


def test_smartlead_cost_is_zero():
    """SmartLead is flat-rate subscription — per-send variable cost is 0."""
    assert Decimal("0") == SMARTLEAD_COST_AUD_PER_EMAIL


def test_cost_for_channel_resend():
    assert cost_for_channel("resend") == RESEND_COST_AUD_PER_EMAIL
    assert cost_for_channel("Resend") == RESEND_COST_AUD_PER_EMAIL  # case-insensitive
    assert cost_for_channel("  RESEND  ") == RESEND_COST_AUD_PER_EMAIL  # strip


def test_cost_for_channel_smartlead():
    assert cost_for_channel("smartlead") == SMARTLEAD_COST_AUD_PER_EMAIL
    assert cost_for_channel("SmartLead") == SMARTLEAD_COST_AUD_PER_EMAIL


def test_cost_for_channel_unknown_raises():
    """Unknown channel raises ValueError — fail loud, don't silently zero."""
    with pytest.raises(ValueError, match="Unknown email channel"):
        cost_for_channel("salesforge")
    with pytest.raises(ValueError, match="Unknown email channel"):
        cost_for_channel("")
    with pytest.raises(ValueError, match="Unknown email channel"):
        cost_for_channel(None)  # type: ignore[arg-type]


def test_cost_decimal_arithmetic_safe():
    """Decimal preserves precision through arithmetic — no float drift."""
    total = sum((RESEND_COST_AUD_PER_EMAIL for _ in range(1000)), Decimal("0"))
    # 1000 × 0.0010 = 1.0000
    assert total == Decimal("1.0000")
