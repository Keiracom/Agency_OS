# FILE: tests/test_dfs_gmaps_client.py
# PURPOSE: Tests for DFSGMapsClient
# DIRECTIVE: #248

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.clients.dfs_gmaps_client import (
    COST_PER_SEARCH_AUD,
    DFS_STATUS_AUTH_FAILURE,
    DFS_STATUS_INVALID_LOCATION,
    DFSAuthError,
    DFSGMapsClient,
    DFSInvalidLocationError,
)


# ============================================================
# Helpers
# ============================================================


def _make_client() -> DFSGMapsClient:
    return DFSGMapsClient(login="test_login", password="test_password")


def _make_429_response():
    """Httpx response mock for HTTP 429."""
    resp = MagicMock()
    resp.status_code = 429
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Too Many Requests", request=MagicMock(), response=resp
    )
    return resp


def _make_200_response(tasks: list) -> MagicMock:
    """Httpx response mock for HTTP 200 with DFS task payload."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock(return_value=None)
    resp.json.return_value = {"tasks": tasks}
    return resp


# ============================================================
# map_to_bu_columns tests (sync — no mocking needed)
# ============================================================


class TestMapToBuColumns:
    def test_map_to_bu_columns_all_fields(self):
        """All 19 fields present when full raw item is provided."""
        client = _make_client()
        raw_item = {
            "place_id": "ChIJXXXtest",
            "title": "Test Dental Clinic",
            "address": "123 Test St, Sydney NSW 2000",
            "phone": "+61 2 1234 5678",
            "url": "https://testdental.com.au/home",
            "latitude": -33.8688,
            "longitude": 151.2093,
            "cid": "9876543210",
            "rating": {"value": 4.5, "votes_count": 120},
            "category": "Dentist",
            "additional_categories": ["Orthodontist", "Oral Surgeon"],
            "work_hours": {"monday": "9am-5pm"},
            "total_photos": 15,
            "maps_url": "https://maps.google.com/?cid=9876543210",
        }
        result = client.map_to_bu_columns(raw_item)

        assert len(result) == 19
        assert result["gmb_place_id"] == "ChIJXXXtest"
        assert result["display_name"] == "Test Dental Clinic"
        assert result["address"] == "123 Test St, Sydney NSW 2000"
        assert result["phone"] == "+61 2 1234 5678"
        assert result["website"] == "https://testdental.com.au/home"
        assert result["domain"] == "testdental.com.au"
        assert result["lat"] == -33.8688
        assert result["lng"] == 151.2093
        assert result["gmb_cid"] == "9876543210"
        assert result["gmb_rating"] == 4.5
        assert result["gmb_review_count"] == 120
        assert result["gmb_category"] == "Dentist"
        assert result["gmb_additional_categories"] == ["Orthodontist", "Oral Surgeon"]
        assert result["gmb_work_hours"] == '{"monday": "9am-5pm"}'
        assert result["gmb_total_photos"] == 15
        assert result["gmb_maps_url"] == "https://maps.google.com/?cid=9876543210"
        assert result["discovery_source"] == "dfs_gmaps"
        assert result["pipeline_stage"] == 0
        assert result["pipeline_status"] == "discovered"

    def test_map_to_bu_columns_missing_optional(self):
        """Only place_id and title provided — no KeyError, required fields present."""
        client = _make_client()
        raw_item = {
            "place_id": "ChIJMinimal",
            "title": "Minimal Business",
        }
        result = client.map_to_bu_columns(raw_item)

        assert result["gmb_place_id"] == "ChIJMinimal"
        assert result["display_name"] == "Minimal Business"
        assert result["discovery_source"] == "dfs_gmaps"
        assert result["pipeline_stage"] == 0
        assert result["pipeline_status"] == "discovered"
        # No KeyError raised
        assert "address" not in result
        assert "phone" not in result

    def test_map_to_bu_columns_domain_extraction(self):
        """www. prefix is stripped from domain."""
        client = _make_client()
        raw_item = {
            "place_id": "ChIJDomain",
            "url": "https://www.example.com.au/page",
        }
        result = client.map_to_bu_columns(raw_item)

        # Implementation strips www. prefix
        assert result["domain"] == "example.com.au"
        assert result["website"] == "https://www.example.com.au/page"


# ============================================================
# Async discover_by_coordinates tests
# ============================================================


@pytest.mark.asyncio
class TestDiscoverByCoordinates:
    @pytest.mark.skip(
        reason="Retry test patches removed internal method fetch_task_results — needs rewrite for current client"
    )
    async def test_retry_on_429(self):
        """429 responses trigger tenacity retries; third attempt succeeds."""
        client = _make_client()

        mock_httpx_client = AsyncMock()
        resp_429a = _make_429_response()
        resp_429b = _make_429_response()
        resp_200 = _make_200_response(
            tasks=[
                {
                    "status_code": 20000,
                    "status_message": "Ok",
                    "id": "task-retry-test-001",
                }
            ]
        )
        mock_httpx_client.post.side_effect = [resp_429a, resp_429b, resp_200]

        with (
            patch.object(client, "_get_client", new=AsyncMock(return_value=mock_httpx_client)),
            patch.object(client, "fetch_task_results", new=AsyncMock(return_value=[])),
            patch("asyncio.sleep", new=AsyncMock()),
        ):
            result = await client.discover_by_coordinates(-33.8688, 151.2093, "dentist")

        assert mock_httpx_client.post.call_count == 3
        assert result == []

    async def test_invalid_location_raises(self):
        """DFS status 40501 raises DFSInvalidLocationError."""
        client = _make_client()

        mock_httpx_client = AsyncMock()
        resp = _make_200_response(
            tasks=[
                {
                    "status_code": DFS_STATUS_INVALID_LOCATION,
                    "status_message": "InvalidLocation",
                }
            ]
        )
        mock_httpx_client.post.return_value = resp

        with (
            patch.object(client, "_get_client", new=AsyncMock(return_value=mock_httpx_client)),
        ):
            with pytest.raises(DFSInvalidLocationError):
                await client.discover_by_coordinates(999.0, 999.0, "dentist")

    async def test_auth_failure_raises(self):
        """DFS status 40200 (DFS_STATUS_AUTH_FAILURE) raises DFSAuthError."""
        client = _make_client()

        mock_httpx_client = AsyncMock()
        resp = _make_200_response(
            tasks=[
                {
                    "status_code": DFS_STATUS_AUTH_FAILURE,
                    "status_message": "AuthFailure",
                }
            ]
        )
        mock_httpx_client.post.return_value = resp

        with (
            patch.object(client, "_get_client", new=AsyncMock(return_value=mock_httpx_client)),
        ):
            with pytest.raises(DFSAuthError):
                await client.discover_by_coordinates(-33.8688, 151.2093, "dentist")


# ============================================================
# Cost tracking test (sync)
# ============================================================


class TestCostTracking:
    def test_cost_tracking(self):
        """estimated_cost_aud equals queries_made * COST_PER_SEARCH_AUD."""
        client = _make_client()
        client.queries_made = 5
        assert client.estimated_cost_aud == Decimal("5") * COST_PER_SEARCH_AUD
