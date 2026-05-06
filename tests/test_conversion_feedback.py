"""Tests for BU audit gap #7 — conversion feedback loop."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.pipeline.conversion_feedback import (
    CONVERSION_BOOST,
    get_category_conversion_boost,
    get_category_conversion_boosts,
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
# get_category_conversion_boosts batch function tests (Fix #1 — N+1 elimination)
# ---------------------------------------------------------------------------


def _make_conn_batch(rows: list[dict]) -> MagicMock:
    """Return a mock asyncpg connection whose fetch() returns a list of row-like dicts."""
    conn = MagicMock()
    # asyncpg rows support dict-style access; use MagicMock with __getitem__
    mock_rows = []
    for r in rows:
        row = MagicMock()
        row.__getitem__ = lambda self, k, _r=r: _r[k]
        mock_rows.append(row)
    conn.fetch = AsyncMock(return_value=mock_rows)
    return conn


@pytest.mark.asyncio
async def test_batch_empty_categories_returns_empty_dict_no_db_call():
    """Empty categories list must return {} and make no DB call."""
    conn = MagicMock()
    conn.fetch = AsyncMock()
    result = await get_category_conversion_boosts(conn, [])
    assert result == {}
    conn.fetch.assert_not_called()


@pytest.mark.asyncio
async def test_batch_returns_correct_boosts_for_tiers():
    """Batch function maps counts to correct tier boosts."""
    conn = _make_conn_batch(
        [
            {"gmb_category": "Plumber", "conversions": 6},  # high → 15
            {"gmb_category": "Electrician", "conversions": 3},  # moderate → 10
            {"gmb_category": "Dentist", "conversions": 1},  # low → 5
        ]
    )
    result = await get_category_conversion_boosts(conn, ["Plumber", "Electrician", "Dentist"])
    assert result["Plumber"] == 15
    assert result["Electrician"] == 10
    assert result["Dentist"] == 5


@pytest.mark.asyncio
async def test_batch_missing_category_not_in_result():
    """Categories with zero conversions are absent from the result dict (default 0)."""
    conn = _make_conn_batch(
        [
            {"gmb_category": "Plumber", "conversions": 2},
        ]
    )
    result = await get_category_conversion_boosts(conn, ["Plumber", "NoHits"])
    assert result.get("Plumber") == 5
    assert "NoHits" not in result  # caller defaults to 0 via .get()


@pytest.mark.asyncio
async def test_batch_db_error_returns_empty_dict_fail_open():
    """DB error must return empty dict (fail-open), not raise."""
    conn = MagicMock()
    conn.fetch = AsyncMock(side_effect=Exception("connection lost"))
    result = await get_category_conversion_boosts(conn, ["Plumber"])
    assert result == {}


@pytest.mark.asyncio
async def test_batch_single_query_regardless_of_category_count():
    """Regardless of list length, exactly ONE fetch() call is made."""
    conn = _make_conn_batch([])
    categories = ["Plumber", "Electrician", "Dentist", "Accountant", "Builder"]
    await get_category_conversion_boosts(conn, categories)
    conn.fetch.assert_called_once()


# ---------------------------------------------------------------------------
# Rescore wiring verification (structural tests — batch pattern)
# ---------------------------------------------------------------------------


def test_rescore_engine_uses_batch_boost_cache():
    """_rescore_row must use the conversion_boost_cache dict, not a per-row DB call."""
    from src.pipeline.rescore_engine import RescoreEngine

    source = inspect.getsource(RescoreEngine._rescore_row)
    assert "conversion_boost_cache" in source, (
        "_rescore_row must accept and use conversion_boost_cache (N+1 batch fix missing)"
    )


def test_rescore_engine_run_calls_batch_fetch():
    """run() must call get_category_conversion_boosts once before the row loop."""
    from src.pipeline.rescore_engine import RescoreEngine

    source = inspect.getsource(RescoreEngine.run)
    assert "get_category_conversion_boosts" in source, (
        "run() must call get_category_conversion_boosts for batch pre-fetch"
    )
