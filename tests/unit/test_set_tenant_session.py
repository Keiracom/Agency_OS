"""
KEI-181 — Unit tests for set_tenant_session() helper.

No database required — uses MagicMock to intercept execute calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.supabase import set_tenant_session

# ---------------------------------------------------------------------------
# Happy-path: explicit connection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_tenant_session_calls_set_local_with_connection() -> None:
    """set_tenant_session(2, connection=...) must issue SET LOCAL with tenant_id=2."""
    mock_conn = AsyncMock()

    await set_tenant_session(2, connection=mock_conn)

    mock_conn.execute.assert_called_once()
    executed_sql = str(mock_conn.execute.call_args[0][0])
    assert "SET LOCAL agency_os.tenant_id = '2'" in executed_sql


@pytest.mark.asyncio
async def test_set_tenant_session_calls_set_local_tenant_1() -> None:
    """set_tenant_session(1, connection=...) sets tenant_id=1 (Dave)."""
    mock_conn = AsyncMock()

    await set_tenant_session(1, connection=mock_conn)

    executed_sql = str(mock_conn.execute.call_args[0][0])
    assert "SET LOCAL agency_os.tenant_id = '1'" in executed_sql


# ---------------------------------------------------------------------------
# Happy-path: connection=None (opens own session)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_tenant_session_no_connection_uses_get_db_session() -> None:
    """connection=None path must open a session via get_db_session()."""
    mock_session = AsyncMock()

    # get_db_session is an asynccontextmanager — patch it to yield mock_session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def fake_db_session():
        yield mock_session

    with patch("src.integrations.supabase.get_db_session", fake_db_session):
        await set_tenant_session(3)

    mock_session.execute.assert_called_once()
    executed_sql = str(mock_session.execute.call_args[0][0])
    assert "SET LOCAL agency_os.tenant_id = '3'" in executed_sql


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_tenant_session_rejects_zero() -> None:
    """tenant_id=0 must raise ValueError."""
    with pytest.raises(ValueError, match="tenant_id must be a positive integer"):
        await set_tenant_session(0)


@pytest.mark.asyncio
async def test_set_tenant_session_rejects_negative() -> None:
    """Negative tenant_id must raise ValueError."""
    with pytest.raises(ValueError, match="tenant_id must be a positive integer"):
        await set_tenant_session(-5)


@pytest.mark.asyncio
async def test_set_tenant_session_rejects_string() -> None:
    """String tenant_id must raise ValueError."""
    with pytest.raises(ValueError, match="tenant_id must be a positive integer"):
        await set_tenant_session("1")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_set_tenant_session_rejects_none() -> None:
    """None tenant_id must raise ValueError."""
    with pytest.raises(ValueError, match="tenant_id must be a positive integer"):
        await set_tenant_session(None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_set_tenant_session_rejects_float() -> None:
    """Float tenant_id must raise ValueError (not a plain int)."""
    with pytest.raises(ValueError, match="tenant_id must be a positive integer"):
        await set_tenant_session(1.5)  # type: ignore[arg-type]
