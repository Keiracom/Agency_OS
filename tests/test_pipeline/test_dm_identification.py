"""Tests for src/pipeline/dm_identification.py — Directive #286"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.pipeline.dm_identification import DMIdentification, DMResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bd_client(people=None, dm=None):
    """Return a mock BrightDataLinkedInClient."""
    mock = MagicMock()
    mock.lookup_company_people = AsyncMock(return_value=people or [])
    mock.pick_decision_maker = MagicMock(return_value=dm)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_uses_linkedin_url_from_spider_data():
    """spider_data with linkedin social → lookup uses reconstructed URL."""
    dm_return = {"name": "Alice", "title": "Owner", "linkedin_url": None, "confidence": "HIGH"}
    bd = _make_bd_client(people=[{"name": "Alice", "title": "Owner"}], dm=dm_return)

    identifier = DMIdentification(bd_client=bd)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
        spider_data={"socials": {"linkedin": "example-co"}},
    )

    called_kwargs = bd.lookup_company_people.call_args
    assert "https://www.linkedin.com/company/example-co" in str(called_kwargs)
    assert result.source == "brightdata_linkedin"
    assert result.tier_used == "T-DM1"


@pytest.mark.asyncio
async def test_identify_falls_back_to_company_name_search():
    """No linkedin in spider_data → lookup called with linkedin_url=None."""
    dm_return = {"name": "Bob", "title": "CEO", "linkedin_url": None, "confidence": "MEDIUM"}
    bd = _make_bd_client(people=[{"name": "Bob", "title": "CEO"}], dm=dm_return)

    identifier = DMIdentification(bd_client=bd)
    result = await identifier.identify(
        domain="nolinkedin.com",
        company_name="No LinkedIn Co",
        spider_data={},
    )

    _, kwargs = bd.lookup_company_people.call_args
    assert kwargs.get("linkedin_url") is None
    assert result.name == "Bob"
    assert result.source == "brightdata_linkedin"


@pytest.mark.asyncio
async def test_identify_falls_back_to_spider_names():
    """bd returns empty → spider_data team_names used."""
    bd = _make_bd_client(people=[], dm=None)

    identifier = DMIdentification(bd_client=bd)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
        spider_data={"team_names": ["Dr. Sarah Jones", "Tom Smith"]},
    )

    assert result.name == "Dr. Sarah Jones"
    assert result.source == "website_scrape"
    assert result.confidence == "MEDIUM"
    assert result.tier_used == "T-DM2"


@pytest.mark.asyncio
async def test_identify_falls_back_to_abn():
    """bd empty, no spider names, abn entity → extract name."""
    bd = _make_bd_client(people=[], dm=None)

    identifier = DMIdentification(bd_client=bd)
    result = await identifier.identify(
        domain="ferraridenial.com.au",
        company_name="Ferrari Dental",
        spider_data={},
        abn_data={"entity_name": "FERRARI DENTAL PTY LTD"},
    )

    assert result.name == "Ferrari"
    assert result.source == "abn_entity"
    assert result.confidence == "LOW"
    assert result.tier_used == "T-DM3"


@pytest.mark.asyncio
async def test_identify_returns_none_result_when_all_empty():
    """All sources empty → DMResult with all defaults."""
    bd = _make_bd_client(people=[], dm=None)

    identifier = DMIdentification(bd_client=bd)
    result = await identifier.identify(
        domain="mystery.com",
        company_name="Mystery Corp",
        spider_data={},
        abn_data={},
    )

    assert result.name is None
    assert result.source == "none"
    assert result.tier_used == "none"
