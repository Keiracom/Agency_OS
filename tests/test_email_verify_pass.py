"""Tests for the post-discovery email verification pass."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.pipeline.email_waterfall import EmailResult, verify_discovered_email


@pytest.mark.asyncio
async def test_verify_sets_verified_true_on_deliverable():
    """Leadmagic returns deliverable → verified=True."""
    email_result = EmailResult(
        email="test@dental.com.au",
        verified=False,
        source="pattern",
        confidence="medium",
        cost_usd=0.0,
    )
    mock_client = AsyncMock()
    mock_client.verify_email = AsyncMock(
        return_value={"email": "test@dental.com.au", "status": "valid", "is_deliverable": True}
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.pipeline.email_waterfall.LeadmagicClient", return_value=mock_client):
        result = await verify_discovered_email(email_result)

    assert result.verified is True
    assert result.cost_usd == 0.00375


@pytest.mark.asyncio
async def test_verify_leaves_unverified_on_invalid():
    """Leadmagic returns invalid → verified stays False."""
    email_result = EmailResult(
        email="bad@gone.com",
        verified=False,
        source="pattern",
        confidence="medium",
        cost_usd=0.0,
    )
    mock_client = AsyncMock()
    mock_client.verify_email = AsyncMock(
        return_value={"email": "bad@gone.com", "status": "invalid", "is_deliverable": False}
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.pipeline.email_waterfall.LeadmagicClient", return_value=mock_client):
        result = await verify_discovered_email(email_result)

    assert result.verified is False
    assert result.cost_usd == 0.0


@pytest.mark.asyncio
async def test_verify_skips_already_verified():
    """Already-verified emails are not re-verified."""
    email_result = EmailResult(
        email="verified@dental.com.au",
        verified=True,
        source="leadmagic",
        confidence="high",
        cost_usd=0.015,
    )
    result = await verify_discovered_email(email_result)
    assert result.verified is True
    assert result.cost_usd == 0.015  # unchanged


@pytest.mark.asyncio
async def test_verify_skips_null_email():
    """Null emails are returned as-is."""
    email_result = EmailResult(
        email=None,
        verified=False,
        source="none",
        confidence="low",
        cost_usd=0.0,
    )
    result = await verify_discovered_email(email_result)
    assert result.verified is False


@pytest.mark.asyncio
async def test_verify_handles_api_error_gracefully():
    """API errors don't crash — email stays unverified."""
    email_result = EmailResult(
        email="test@dental.com.au",
        verified=False,
        source="pattern",
        confidence="medium",
        cost_usd=0.0,
    )
    mock_client = AsyncMock()
    mock_client.verify_email = AsyncMock(side_effect=RuntimeError("API down"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.pipeline.email_waterfall.LeadmagicClient", return_value=mock_client):
        result = await verify_discovered_email(email_result)

    assert result.verified is False
    assert result.cost_usd == 0.0
