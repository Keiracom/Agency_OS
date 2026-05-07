# FILE: tests/test_clients/test_dfs_labs_client.py
# PURPOSE: Unit tests for DFSLabsClient date params + 40501 error handling — Directive #284

"""
Tests for domain_metrics_by_categories date parameters and error handling.
All tests use mocks — NO live API calls.
"""

import re
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations.dfs_labs_client import DFSLabsClient

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


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ============================================
# Test 1: payload includes first_date and second_date
# ============================================


@pytest.mark.asyncio
async def test_domain_metrics_by_categories_includes_dates(client):
    """domain_metrics_by_categories must include first_date and second_date in the API payload."""
    result_data = {"items": [], "total_count": 0}
    mock_resp = make_mock_response(make_dfs_response(result_data))

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_resp)

    with patch.object(client, "_get_client", return_value=mock_http_client):
        await client.domain_metrics_by_categories(category_codes=[10233])

    call_args = mock_http_client.post.call_args
    payload_sent = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
    item = payload_sent[0]

    assert "first_date" in item, "first_date must be in the payload"
    assert "second_date" in item, "second_date must be in the payload"

    # Both must be YYYY-MM-DD format
    assert _DATE_RE.match(item["first_date"]), f"first_date not YYYY-MM-DD: {item['first_date']}"
    assert _DATE_RE.match(item["second_date"]), f"second_date not YYYY-MM-DD: {item['second_date']}"

    # first_date must be ~180 days before second_date
    d1 = date.fromisoformat(item["first_date"])
    d2 = date.fromisoformat(item["second_date"])
    delta = (d2 - d1).days
    assert 170 <= delta <= 190, f"Expected ~180 day gap, got {delta}"


# ============================================
# Test 2: 40501 raises ValueError (not silent empty)
# ============================================


@pytest.mark.asyncio
async def test_domain_metrics_by_categories_raises_on_40501(client):
    """When DFS returns 40501, domain_metrics_by_categories must raise, not return empty list."""
    invalid_field_response = make_dfs_response(
        None,
        status_code=40501,
        status_message="Invalid Field: 'first_date' is required",
    )
    # result list is empty so make_dfs_response with None gives []
    invalid_field_response["tasks"][0]["result"] = []

    mock_resp = make_mock_response(invalid_field_response)
    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_resp)

    with patch.object(client, "_get_client", return_value=mock_http_client):
        with pytest.raises(ValueError, match="40501"):
            await client.domain_metrics_by_categories(category_codes=[10233])


# ============================================
# Test 3: caller can override first_date and second_date
# ============================================


@pytest.mark.asyncio
async def test_domain_metrics_by_categories_custom_dates(client):
    """Caller-supplied first_date and second_date override the auto-computed defaults."""
    result_data = {"items": [], "total_count": 0}
    mock_resp = make_mock_response(make_dfs_response(result_data))

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_resp)

    custom_first = "2024-01-01"
    custom_second = "2024-06-30"

    with patch.object(client, "_get_client", return_value=mock_http_client):
        await client.domain_metrics_by_categories(
            category_codes=[10233],
            first_date=custom_first,
            second_date=custom_second,
        )

    call_args = mock_http_client.post.call_args
    payload_sent = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
    item = payload_sent[0]

    assert item["first_date"] == custom_first
    assert item["second_date"] == custom_second


# ============================================
# Test 4: _get_latest_available_date — success
# Directive #304-FIX
# ============================================


@pytest.mark.asyncio
async def test_get_latest_available_date_uses_api(client):
    """
    When domain_metrics_by_categories is called with no explicit dates,
    it calls _get_latest_available_date() and uses the returned date
    as second_date (NOT today's date, which exceeds the DFS history window).
    The result is cached so available_history is only called once per session.
    """
    available_date = "2026-03-01"

    # Stub _get_latest_available_date so no real HTTP call is needed
    with patch.object(
        client,
        "_get_latest_available_date",
        new=AsyncMock(return_value=available_date),
    ):
        result_data = {"items": [], "total_count": 0}
        mock_resp = make_mock_response(make_dfs_response(result_data))
        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_resp)

        with patch.object(client, "_get_client", return_value=mock_http_client):
            await client.domain_metrics_by_categories(category_codes=[10514])

    call_args = mock_http_client.post.call_args
    payload_sent = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
    item = payload_sent[0]

    # second_date must come from available_history, not today
    assert item["second_date"] == available_date, (
        f"second_date should be {available_date} from available_history, got {item['second_date']}"
    )
    # first_date must be ~180 days before the available_history date
    d1 = date.fromisoformat(item["first_date"])
    d2 = date.fromisoformat(available_date)
    delta = (d2 - d1).days
    assert 170 <= delta <= 190, (
        f"first_date should be ~180 days before {available_date}, gap was {delta} days"
    )


# ============================================
# Test 5: _get_latest_available_date — fallback on empty response
# Directive #304-FIX
# ============================================


@pytest.mark.asyncio
async def test_get_latest_available_date_fallback_on_empty(client):
    """
    If available_history returns an empty result list,
    _get_latest_available_date() falls back to today minus 35 days.
    No exception is raised; the fallback date is used for the API call.
    """
    from datetime import date

    # Mock GET available_history returning empty result
    empty_hist_resp = make_mock_response(
        {"tasks": [{"status_code": 20000, "status_message": "Ok.", "result": []}]}
    )
    metrics_resp = make_mock_response(make_dfs_response({"items": [], "total_count": 0}))

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=empty_hist_resp)
    mock_http_client.post = AsyncMock(return_value=metrics_resp)

    with patch.object(client, "_get_client", return_value=mock_http_client):
        # Clear any cached value
        client._available_history_date = None
        result = await client._get_latest_available_date()

    expected_fallback = (date.today() - timedelta(days=35)).strftime("%Y-%m-%d")
    assert result == expected_fallback, (
        f"Fallback should be today-35d ({expected_fallback}), got {result}"
    )
    assert client._available_history_date == expected_fallback
