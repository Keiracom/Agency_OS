"""Tests for BU audit gap #7 — conversion feedback loop."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.pipeline.conversion_feedback import (
    CONVERSION_BOOST,
    get_category_conversion_boost,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_conn(fetchval_return):
    """Return a mock asyncpg connection whose fetchval resolves to fetchval_return."""
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value=fetchval_return)
    return conn


# ---------------------------------------------------------------------------
# get_category_conversion_boost unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_conversions_returns_zero():
    conn = _make_conn(0)
    result = await get_category_conversion_boost(conn, "Plumber")
    assert result == 0


@pytest.mark.asyncio
async def test_one_conversion_returns_low_boost():
    conn = _make_conn(1)
    result = await get_category_conversion_boost(conn, "Electrician")
    assert result == CONVERSION_BOOST["low"]
    assert result == 5


@pytest.mark.asyncio
async def test_two_conversions_returns_low_boost():
    conn = _make_conn(2)
    result = await get_category_conversion_boost(conn, "Electrician")
    assert result == CONVERSION_BOOST["low"]
    assert result == 5


@pytest.mark.asyncio
async def test_three_conversions_returns_moderate_boost():
    conn = _make_conn(3)
    result = await get_category_conversion_boost(conn, "Dentist")
    assert result == CONVERSION_BOOST["moderate"]
    assert result == 10


@pytest.mark.asyncio
async def test_four_conversions_returns_moderate_boost():
    conn = _make_conn(4)
    result = await get_category_conversion_boost(conn, "Dentist")
    assert result == CONVERSION_BOOST["moderate"]
    assert result == 10


@pytest.mark.asyncio
async def test_five_conversions_returns_high_boost():
    conn = _make_conn(5)
    result = await get_category_conversion_boost(conn, "Accountant")
    assert result == CONVERSION_BOOST["high"]
    assert result == 15


@pytest.mark.asyncio
async def test_six_conversions_returns_high_boost():
    conn = _make_conn(6)
    result = await get_category_conversion_boost(conn, "Accountant")
    assert result == CONVERSION_BOOST["high"]
    assert result == 15


@pytest.mark.asyncio
async def test_null_gmb_category_returns_zero_without_db_call():
    conn = _make_conn(None)
    result = await get_category_conversion_boost(conn, None)
    assert result == 0
    conn.fetchval.assert_not_called()


@pytest.mark.asyncio
async def test_empty_string_gmb_category_returns_zero_without_db_call():
    conn = _make_conn(None)
    result = await get_category_conversion_boost(conn, "")
    assert result == 0
    conn.fetchval.assert_not_called()


@pytest.mark.asyncio
async def test_db_error_returns_zero_fail_open():
    conn = MagicMock()
    conn.fetchval = AsyncMock(side_effect=Exception("DB connection lost"))
    result = await get_category_conversion_boost(conn, "Plumber")
    assert result == 0


@pytest.mark.asyncio
async def test_fetchval_returns_none_treated_as_zero():
    """asyncpg returns None when COUNT(*) returns no rows (edge case)."""
    conn = _make_conn(None)
    result = await get_category_conversion_boost(conn, "Builder")
    assert result == 0


# ---------------------------------------------------------------------------
# Rescore wiring verification (structural test)
# ---------------------------------------------------------------------------


def test_rescore_engine_calls_conversion_feedback():
    """Verify _rescore_row source references get_category_conversion_boost."""
    from src.pipeline.rescore_engine import RescoreEngine

    source = inspect.getsource(RescoreEngine._rescore_row)
    assert "get_category_conversion_boost" in source, (
        "_rescore_row must call get_category_conversion_boost (gap #7 wiring missing)"
    )


def test_rescore_engine_imports_conversion_feedback_module():
    """Verify _rescore_row source imports from conversion_feedback module."""
    from src.pipeline.rescore_engine import RescoreEngine

    source = inspect.getsource(RescoreEngine._rescore_row)
    assert "conversion_feedback" in source, (
        "_rescore_row must import from src.pipeline.conversion_feedback"
    )
