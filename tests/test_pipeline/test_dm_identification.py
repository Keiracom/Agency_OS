"""Tests for src/pipeline/dm_identification.py — Directive #287"""

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


def _make_dfs_client(people=None):
    """Return a mock DFSLabsClient with search_linkedin_people stubbed."""
    mock = MagicMock()
    mock.search_linkedin_people = AsyncMock(return_value=people or [])
    return mock


# ---------------------------------------------------------------------------
# T-DM1: SERP LinkedIn tests (Directive #287)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_serp_t_dm1_returns_best_by_title():
    """SERP returns multiple people → highest-scoring title wins."""
    people = [
        {
            "name": "Alice Smith",
            "title": "Sales Manager",
            "linkedin_url": "https://li.com/in/alice",
            "snippet": "",
        },
        {
            "name": "Bob Jones",
            "title": "Owner",
            "linkedin_url": "https://li.com/in/bob",
            "snippet": "",
        },
    ]
    dfs = _make_dfs_client(people=people)

    identifier = DMIdentification(dfs_client=dfs)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
    )

    assert result.name == "Bob Jones"
    assert result.title == "Owner"
    assert result.source == "serp_linkedin"
    assert result.confidence == "HIGH"
    assert result.tier_used == "T-DM1"
    assert result.linkedin_url == "https://li.com/in/bob"


@pytest.mark.asyncio
async def test_serp_t_dm1_first_result_when_no_title_match():
    """SERP results with no DM-keyword title → first named result returned."""
    people = [
        {
            "name": "Charlie Brown",
            "title": "Consultant",
            "linkedin_url": "https://li.com/in/charlie",
            "snippet": "",
        },
    ]
    dfs = _make_dfs_client(people=people)

    identifier = DMIdentification(dfs_client=dfs)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
    )

    assert result.name == "Charlie Brown"
    assert result.source == "serp_linkedin"
    assert result.tier_used == "T-DM1"


@pytest.mark.asyncio
async def test_serp_t_dm1_empty_falls_through_to_bd():
    """SERP returns empty → falls through to T-DM2 Bright Data."""
    dfs = _make_dfs_client(people=[])
    dm_return = {"name": "Dave", "title": "CEO", "linkedin_url": None, "confidence": "HIGH"}
    bd = _make_bd_client(people=[{"name": "Dave"}], dm=dm_return)

    identifier = DMIdentification(bd_client=bd, dfs_client=dfs)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
    )

    assert result.name == "Dave"
    assert result.source == "brightdata_linkedin"
    assert result.tier_used == "T-DM2"


@pytest.mark.asyncio
async def test_serp_exception_falls_through_to_bd():
    """SERP raises → exception swallowed, falls through to T-DM2 Bright Data."""
    dfs = _make_dfs_client()
    dfs.search_linkedin_people = AsyncMock(side_effect=RuntimeError("timeout"))
    dm_return = {"name": "Eve", "title": "Director", "linkedin_url": None, "confidence": "HIGH"}
    bd = _make_bd_client(people=[{"name": "Eve"}], dm=dm_return)

    identifier = DMIdentification(bd_client=bd, dfs_client=dfs)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
    )

    assert result.source == "brightdata_linkedin"
    assert result.tier_used == "T-DM2"


@pytest.mark.asyncio
async def test_serp_no_named_results_falls_through():
    """SERP results all have empty name → falls through to T-DM2."""
    people = [{"name": "", "title": "Owner", "linkedin_url": "https://li.com/in/x", "snippet": ""}]
    dfs = _make_dfs_client(people=people)
    dm_return = {"name": "Frank", "title": "Owner", "linkedin_url": None, "confidence": "MEDIUM"}
    bd = _make_bd_client(people=[{"name": "Frank"}], dm=dm_return)

    identifier = DMIdentification(bd_client=bd, dfs_client=dfs)
    result = await identifier.identify(
        domain="example.com",
        company_name="Example Co",
    )

    assert result.source == "brightdata_linkedin"
    assert result.tier_used == "T-DM2"


# ---------------------------------------------------------------------------
# T-DM2: Bright Data LinkedIn tests (was T-DM1 in Directive #286)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_bd_uses_linkedin_url_from_spider_data():
    """spider_data with linkedin social → BD lookup uses reconstructed URL; returns T-DM2."""
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
    assert result.tier_used == "T-DM2"


@pytest.mark.asyncio
async def test_identify_bd_falls_back_to_company_name_search():
    """No linkedin in spider_data → BD lookup called with linkedin_url=None; returns T-DM2."""
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
    assert result.tier_used == "T-DM2"


# ---------------------------------------------------------------------------
# T-DM3: Website scrape tests (was T-DM2 in Directive #286)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_falls_back_to_spider_names():
    """BD returns empty → spider_data team_names used as T-DM3."""
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
    assert result.tier_used == "T-DM3"


# ---------------------------------------------------------------------------
# T-DM4: ABN entity tests (was T-DM3 in Directive #286)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_falls_back_to_abn():
    """BD empty, no spider names, abn entity → extract name as T-DM4."""
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
    assert result.tier_used == "T-DM4"


# ---------------------------------------------------------------------------
# No DM found
# ---------------------------------------------------------------------------


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
