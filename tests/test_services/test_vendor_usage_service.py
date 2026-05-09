"""Tests for vendor_usage_service (E1 R3)."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from src.services.vendor_usage_service import log_vendor_usage

SENTINEL = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_log_vendor_usage_writes_required_fields(mock_session):
    """Happy path: writes a row with all required fields and commits."""
    log_id = await log_vendor_usage(
        db=mock_session,
        client_id=SENTINEL,
        vendor="dataforseo",
        endpoint="domain_rank_overview",
        cost_aud=0.0155,
        units=1,
        duration_ms=850,
        success=True,
    )

    assert isinstance(log_id, UUID)
    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_awaited_once()

    bind_params = mock_session.execute.await_args.args[1]
    assert bind_params["client_id"] == str(SENTINEL)
    assert bind_params["vendor"] == "dataforseo"
    assert bind_params["endpoint"] == "domain_rank_overview"
    assert bind_params["cost_aud"] == 0.0155
    assert bind_params["units"] == 1
    assert bind_params["units_unit"] == "api_calls"  # default
    assert bind_params["duration_ms"] == 850
    assert bind_params["success"] is True
    assert bind_params["lead_id"] is None
    assert bind_params["error_message"] is None


@pytest.mark.asyncio
async def test_log_vendor_usage_success_false_with_error_message(mock_session):
    """Failure path: success=False + error_message persisted verbatim."""
    await log_vendor_usage(
        db=mock_session,
        client_id=SENTINEL,
        vendor="leadmagic",
        endpoint="find_email",
        cost_aud=0.0,
        success=False,
        error_message="HTTP 402 Payment Required",
    )

    bind_params = mock_session.execute.await_args.args[1]
    assert bind_params["success"] is False
    assert bind_params["error_message"] == "HTTP 402 Payment Required"
    assert bind_params["cost_aud"] == 0.0


@pytest.mark.asyncio
async def test_log_vendor_usage_lead_id_serialised(mock_session):
    """When lead_id provided, it's stringified for the bind."""
    lead_id = uuid4()
    await log_vendor_usage(
        db=mock_session,
        client_id=SENTINEL,
        vendor="contactout",
        endpoint="phone_lookup",
        lead_id=lead_id,
        units=1,
        units_unit="credits",
    )

    bind_params = mock_session.execute.await_args.args[1]
    assert bind_params["lead_id"] == str(lead_id)
    assert bind_params["units_unit"] == "credits"


@pytest.mark.asyncio
async def test_log_vendor_usage_returns_unique_ids(mock_session):
    """Each invocation returns a fresh UUID."""
    id1 = await log_vendor_usage(
        db=mock_session, client_id=SENTINEL, vendor="brightdata", endpoint="gmb_lookup"
    )
    id2 = await log_vendor_usage(
        db=mock_session, client_id=SENTINEL, vendor="brightdata", endpoint="gmb_lookup"
    )
    assert id1 != id2
