"""Lock test: Hunter L2 email-finder is gated on dm_verified=True (GOV-12).

Rationale: email_waterfall.py line 565 gates Hunter on dm_verified to avoid
confident email attribution on unconfirmed DMs. These tests verify the
runtime conditional is enforced — not merely documented.
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hunter_response(email: str = "john.doe@example.com", score: int = 85) -> MagicMock:
    """Return a mock httpx Response for a successful Hunter call."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": {"email": email, "score": score}}
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hunter_not_called_when_dm_not_verified():
    """When dm_verified=False, Hunter L2 must never be called."""
    os.environ["HUNTER_API_KEY"] = "test-key-123"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_hunter_response())
        mock_client_cls.return_value = mock_client

        from src.pipeline.email_waterfall import discover_email

        result = await discover_email(
            domain="example.com",
            dm_name="John Doe",
            dm_verified=False,
            skip_layers=[1, 2, 3],  # skip paid layers, force Hunter path only
        )

    # Hunter GET must never have been called
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_hunter_called_when_dm_verified_and_name_present():
    """When dm_verified=True and first/last/domain are present, Hunter L2 IS called."""
    os.environ["HUNTER_API_KEY"] = "test-key-123"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_hunter_response())
        mock_client_cls.return_value = mock_client

        from src.pipeline.email_waterfall import discover_email

        result = await discover_email(
            domain="example.com",
            dm_name="John Doe",
            dm_verified=True,
            # skip L0 contact_data, L1 contactout, L3 leadmagic so only Hunter runs
            skip_layers=[2, 3],
            contactout_result=None,
            contact_data=None,
        )

    # Hunter GET must have been called exactly once
    mock_client.get.assert_called_once()
    call_kwargs = mock_client.get.call_args
    assert "hunter.io" in call_kwargs[0][0]


@pytest.mark.asyncio
async def test_hunter_skipped_when_no_api_key():
    """When HUNTER_API_KEY is absent, Hunter is skipped even with dm_verified=True."""
    os.environ.pop("HUNTER_API_KEY", None)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_make_hunter_response())
        mock_client_cls.return_value = mock_client

        from src.pipeline.email_waterfall import discover_email

        result = await discover_email(
            domain="example.com",
            dm_name="John Doe",
            dm_verified=True,
            skip_layers=[2, 3],
            contactout_result=None,
            contact_data=None,
        )

    mock_client.get.assert_not_called()
