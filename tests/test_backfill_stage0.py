"""Tests for the stage-0 backfill script."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_fetch_stage0_domains_returns_list():
    """fetch_stage0_domains returns a list of domain strings."""
    from scripts.backfill_stage0 import fetch_stage0_domains

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(
        return_value=[
            {"domain": "dental1.com.au"},
            {"domain": "dental2.com.au"},
        ]
    )
    mock_conn.close = AsyncMock()

    with patch("asyncpg.connect", return_value=mock_conn):
        domains = await fetch_stage0_domains(batch_size=50, offset=0)

    assert domains == ["dental1.com.au", "dental2.com.au"]
    mock_conn.fetch.assert_called_once()
    sql = mock_conn.fetch.call_args[0][0]
    assert "pipeline_stage = 0" in sql
    assert "LIMIT" in sql


@pytest.mark.asyncio
async def test_count_stage0_returns_int():
    """count_stage0 returns the count of stage-0 rows."""
    from scripts.backfill_stage0 import count_stage0

    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"cnt": 5022})
    mock_conn.close = AsyncMock()

    with patch("asyncpg.connect", return_value=mock_conn):
        count = await count_stage0()

    assert count == 5022
