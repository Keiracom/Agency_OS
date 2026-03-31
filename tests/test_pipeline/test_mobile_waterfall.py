"""Tests for src/pipeline/mobile_waterfall.py — Directive #300-FIX Issue 11."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.pipeline.mobile_waterfall import (
    MobileResult,
    extract_mobile_from_html,
    run_mobile_waterfall,
)


# ── extract_mobile_from_html ──────────────────────────────────────────────────

def test_extract_mobile_standard():
    html = "<p>Call us on 0412 345 678</p>"
    assert extract_mobile_from_html(html) == "0412345678"


def test_extract_mobile_international():
    html = "<p>Phone: +61412345678</p>"
    result = extract_mobile_from_html(html)
    assert result == "0412345678"


def test_extract_mobile_dashes():
    html = "<p>0400-123-456</p>"
    assert extract_mobile_from_html(html) == "0400123456"


def test_extract_mobile_none_when_absent():
    html = "<p>Call (02) 9876 5432</p>"
    assert extract_mobile_from_html(html) is None


def test_extract_mobile_empty():
    assert extract_mobile_from_html("") is None


def test_extract_mobile_prefers_intl():
    html = "<p>+61412345678 or 0287654321</p>"
    result = extract_mobile_from_html(html)
    # Should find the international (mobile) pattern first
    assert result == "0412345678"


# ── run_mobile_waterfall ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_layer1_hit_from_contact_data():
    result = await run_mobile_waterfall(
        domain="example.com.au",
        dm_linkedin_url="https://linkedin.com/in/jane",
        contact_data={"mobile": "0412345678"},
    )
    assert result.mobile == "0412345678"
    assert result.source == "html_regex"
    assert result.tier_used == 1
    assert result.cost_usd == Decimal("0")


@pytest.mark.asyncio
async def test_layer2_leadmagic_hit():
    mock_lm = MagicMock()
    mock_lm.find_mobile = AsyncMock(return_value={"mobile": "0423456789"})
    result = await run_mobile_waterfall(
        domain="example.com.au",
        dm_linkedin_url="https://linkedin.com/in/jane",
        contact_data={},
        leadmagic_client=mock_lm,
    )
    assert result.mobile == "0423456789"
    assert result.source == "leadmagic"
    assert result.tier_used == 2
    assert result.cost_usd == Decimal("0.077")


@pytest.mark.asyncio
async def test_layer3_brightdata_fallback():
    mock_lm = MagicMock()
    mock_lm.find_mobile = AsyncMock(return_value=None)
    mock_bd = MagicMock()
    mock_bd.get_profile = AsyncMock(return_value={"mobile": "0434567890"})
    result = await run_mobile_waterfall(
        domain="example.com.au",
        dm_linkedin_url="https://linkedin.com/in/jane",
        contact_data={},
        leadmagic_client=mock_lm,
        brightdata_client=mock_bd,
    )
    assert result.mobile == "0434567890"
    assert result.source == "brightdata"
    assert result.tier_used == 3


@pytest.mark.asyncio
async def test_all_layers_fail_returns_empty():
    mock_lm = MagicMock()
    mock_lm.find_mobile = AsyncMock(return_value=None)
    mock_bd = MagicMock()
    mock_bd.get_profile = AsyncMock(return_value=None)
    result = await run_mobile_waterfall(
        domain="example.com.au",
        dm_linkedin_url="https://linkedin.com/in/jane",
        contact_data={},
        leadmagic_client=mock_lm,
        brightdata_client=mock_bd,
    )
    assert result.mobile is None
    assert result.source is None
    assert result.tier_used is None


@pytest.mark.asyncio
async def test_no_clients_returns_empty():
    result = await run_mobile_waterfall(
        domain="example.com.au",
        dm_linkedin_url=None,
        contact_data={},
    )
    assert result.mobile is None
    assert result.tier_used is None


@pytest.mark.asyncio
async def test_layer1_wins_over_paid():
    """Layer 1 should short-circuit — paid clients never called."""
    mock_lm = MagicMock()
    mock_lm.find_mobile = AsyncMock()
    result = await run_mobile_waterfall(
        domain="example.com.au",
        dm_linkedin_url="https://linkedin.com/in/jane",
        contact_data={"mobile": "0412999888"},
        leadmagic_client=mock_lm,
    )
    assert result.source == "html_regex"
    mock_lm.find_mobile.assert_not_called()
