"""Tests for ads_transparency stub — Directive #290."""
import pytest
from src.integrations.ads_transparency import check_google_ads


@pytest.mark.asyncio
async def test_stub_returns_none():
    assert await check_google_ads("testdental.com.au") is None


@pytest.mark.asyncio
async def test_accepts_any_domain():
    for d in ["dental.com.au", "plumber.com", "lawyer.net.au"]:
        assert await check_google_ads(d) is None
