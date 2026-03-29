# FILE: tests/test_clients/test_dfs_serp_linkedin.py
# PURPOSE: Unit tests for DFSLabsClient.search_linkedin_people — Directive #287

"""
Tests for search_linkedin_people SERP method.
All tests use mocks — NO live API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.dfs_labs_client import DFSLabsClient


# ============================================
# Fixtures + helpers
# ============================================


@pytest.fixture
def client():
    return DFSLabsClient(login="test@example.com", password="test_password")


def make_dfs_response(result_data, status_code: int = 20000, status_message: str = "Ok.") -> dict:
    return {
        "tasks": [
            {
                "status_code": status_code,
                "status_message": status_message,
                "result": [result_data] if result_data is not None else [],
            }
        ]
    }


def make_mock_response(json_data: dict, http_status: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = http_status
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def make_serp_items(profiles: list[dict]) -> dict:
    """Build a DFS organic SERP result payload with profile items."""
    return {
        "items": [
            {
                "url": p["url"],
                "title": p["title"],
                "description": p.get("description", ""),
            }
            for p in profiles
        ]
    }


# ============================================
# Tests
# ============================================


@pytest.mark.asyncio
async def test_search_linkedin_people_parses_name_and_title(client):
    """Standard LinkedIn title 'Name - Job Title | LinkedIn' is parsed correctly."""
    serp_data = make_serp_items([
        {
            "url": "https://www.linkedin.com/in/john-smith-12345",
            "title": "John Smith - CEO at Acme Corp | LinkedIn",
            "description": "John Smith, CEO at Acme Corp, Sydney Australia.",
        }
    ])
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        results = await client.search_linkedin_people("Acme Corp")

    assert len(results) == 1
    assert results[0]["name"] == "John Smith"
    assert results[0]["title"] == "CEO at Acme Corp"
    assert results[0]["linkedin_url"] == "https://www.linkedin.com/in/john-smith-12345"
    assert "John Smith" in results[0]["snippet"]


@pytest.mark.asyncio
async def test_search_linkedin_people_filters_non_profile_urls(client):
    """Items without linkedin.com/in/ in URL are excluded."""
    serp_data = make_serp_items([
        {
            "url": "https://www.linkedin.com/company/acme-corp",
            "title": "Acme Corp | LinkedIn",
            "description": "Company page.",
        },
        {
            "url": "https://www.linkedin.com/in/jane-doe",
            "title": "Jane Doe - Owner | LinkedIn",
            "description": "",
        },
    ])
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        results = await client.search_linkedin_people("Acme Corp")

    assert len(results) == 1
    assert results[0]["name"] == "Jane Doe"
    assert results[0]["title"] == "Owner"


@pytest.mark.asyncio
async def test_search_linkedin_people_empty_serp(client):
    """Empty SERP result → empty list returned."""
    serp_data = {"items": []}
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        results = await client.search_linkedin_people("Unknown Corp")

    assert results == []


@pytest.mark.asyncio
async def test_search_linkedin_people_accumulates_cost(client):
    """Cost counter increments by $0.01 per call."""
    serp_data = {"items": []}
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        await client.search_linkedin_people("Corp A")
        await client.search_linkedin_people("Corp B")

    from decimal import Decimal
    assert client._cost_search_linkedin_people == Decimal("0.02")


@pytest.mark.asyncio
async def test_search_linkedin_people_cost_included_in_total(client):
    """search_linkedin_people cost is included in total_cost_usd."""
    serp_data = {"items": []}
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        await client.search_linkedin_people("Corp A")

    assert client.total_cost_usd == pytest.approx(0.01)


@pytest.mark.asyncio
async def test_search_linkedin_people_uses_australia_location_by_default(client):
    """Default location_name='Australia' is sent in the API payload."""
    serp_data = {"items": []}
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        await client.search_linkedin_people("Acme Corp")

    call_kwargs = mock_http.post.call_args
    payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
    assert payload[0]["location_name"] == "Australia"


@pytest.mark.asyncio
async def test_search_linkedin_people_query_contains_site_filter(client):
    """Keyword payload contains site:linkedin.com/in filter with company name."""
    serp_data = {"items": []}
    mock_resp = make_mock_response(make_dfs_response(serp_data))

    with patch.object(client, "_get_client") as mock_get_client:
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_http

        await client.search_linkedin_people("Acme Corp")

    call_kwargs = mock_http.post.call_args
    payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
    keyword = payload[0]["keyword"]
    assert "site:linkedin.com/in" in keyword
    assert "Acme Corp" in keyword
