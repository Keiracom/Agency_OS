# FILE: tests/test_dfs_serp_client.py
# PURPOSE: Tests for DFSSerpClient — DM extraction, cost tracking, POST structure
# DIRECTIVE: #250

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.dfs_serp_client import (
    COST_PER_SERP_AUD,
    DFS_STATUS_IN_QUEUE,
    DFS_STATUS_SUCCESS,
    DFSSerpClient,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> DFSSerpClient:
    return DFSSerpClient(login="test_user", password="test_pass")


def _task_post_response(task_id: str = "task-001") -> dict:
    return {
        "tasks": [{
            "id": task_id,
            "status_code": DFS_STATUS_SUCCESS,
            "status_message": "Ok.",
        }]
    }


def _task_get_response(task_id: str, items: list[dict]) -> dict:
    return {
        "tasks": [{
            "id": task_id,
            "status_code": DFS_STATUS_SUCCESS,
            "result": [{"items": items}],
        }]
    }


def _linkedin_item(url: str, title: str, rank_group: int = 1) -> dict:
    return {
        "url": url,
        "title": title,
        "rank_group": rank_group,
    }


def _mock_http_client(post_response: dict, get_response: dict):
    """Returns an AsyncMock httpx client with preset responses."""
    mock_client = AsyncMock()

    post_resp = MagicMock()
    post_resp.json.return_value = post_response
    post_resp.raise_for_status = MagicMock()
    mock_client.post.return_value = post_resp

    get_resp = MagicMock()
    get_resp.json.return_value = get_response
    get_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = get_resp

    mock_client.is_closed = False
    return mock_client


# ---------------------------------------------------------------------------
# Test 1: find_dm returns correctly mapped fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_dm_returns_mapped_fields():
    client = _make_client()
    task_id = "task-001"
    items = [
        _linkedin_item(
            url="https://www.linkedin.com/in/john-doe",
            title="John Doe - CEO - Acme Corp | LinkedIn",
            rank_group=1,
        )
    ]
    mock_http = _mock_http_client(
        _task_post_response(task_id),
        _task_get_response(task_id, items),
    )
    client._client = mock_http

    result = await client.find_decision_maker("Acme Corp", "Sydney", "NSW")

    assert result is not None
    assert "linkedin.com/in/john-doe" in result["dm_linkedin_url"]
    assert result["dm_name"] == "John Doe"
    assert result["dm_title"] == "CEO"
    assert result["dm_source"] == "dfs_serp"


# ---------------------------------------------------------------------------
# Test 2: find_dm returns None when no LinkedIn results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_dm_returns_none_no_linkedin():
    client = _make_client()
    task_id = "task-002"
    items = [
        {"url": "https://www.someotherdomain.com/profile/john", "title": "John - CEO", "rank_group": 1},
        {"url": "https://facebook.com/john.doe", "title": "John Doe", "rank_group": 2},
    ]
    mock_http = _mock_http_client(
        _task_post_response(task_id),
        _task_get_response(task_id, items),
    )
    client._client = mock_http

    result = await client.find_decision_maker("Some Corp", "Melbourne", "VIC")

    assert result is None


# ---------------------------------------------------------------------------
# Test 3: dm_confidence is lower at position 5
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dm_confidence_lower_at_position_5():
    client = _make_client()
    task_id = "task-003"
    items = [
        _linkedin_item(
            url="https://www.linkedin.com/in/jane-smith",
            title="Jane Smith - CFO - Beta Ltd | LinkedIn",
            rank_group=5,
        )
    ]
    mock_http = _mock_http_client(
        _task_post_response(task_id),
        _task_get_response(task_id, items),
    )
    client._client = mock_http

    result = await client.find_decision_maker("Beta Ltd", "Brisbane", "QLD")

    assert result is not None
    assert result["dm_confidence"] < Decimal("0.70"), (
        f"Expected confidence < 0.70 at position 5, got {result['dm_confidence']}"
    )


# ---------------------------------------------------------------------------
# Test 4: cost tracking increments correctly across multiple calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cost_tracking_increments():
    client = _make_client()
    task_id = "task-004"
    items = [
        _linkedin_item(
            url="https://www.linkedin.com/in/person",
            title="Person Name - Role - Corp | LinkedIn",
            rank_group=1,
        )
    ]
    mock_http = _mock_http_client(
        _task_post_response(task_id),
        _task_get_response(task_id, items),
    )
    client._client = mock_http

    # Reset mock for multiple calls
    post_resp = MagicMock()
    post_resp.json.return_value = _task_post_response(task_id)
    post_resp.raise_for_status = MagicMock()
    mock_http.post.return_value = post_resp

    get_resp = MagicMock()
    get_resp.json.return_value = _task_get_response(task_id, items)
    get_resp.raise_for_status = MagicMock()
    mock_http.get.return_value = get_resp

    for _ in range(3):
        await client.find_decision_maker("Corp", "Sydney", "NSW")

    assert client.queries_made == 3, f"Expected 3 queries, got {client.queries_made}"
    expected_cost = Decimal("3") * COST_PER_SERP_AUD
    assert client.estimated_cost_aud == expected_cost, (
        f"Expected cost {expected_cost}, got {client.estimated_cost_aud}"
    )


# ---------------------------------------------------------------------------
# Test 5: POST body contains exactly 1 task
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_one_task_per_post_body():
    client = _make_client()
    task_id = "task-005"
    items = []
    mock_http = _mock_http_client(
        _task_post_response(task_id),
        _task_get_response(task_id, items),
    )
    client._client = mock_http

    await client.find_decision_maker("Some Biz", "Perth", "WA")

    # Capture what was passed to POST
    call_args = mock_http.post.call_args
    # The second positional arg (or json= kwarg) is the payload
    post_payload = call_args.kwargs.get("json") or call_args.args[1]

    assert isinstance(post_payload, list), "POST payload should be a list"
    assert len(post_payload) == 1, (
        f"Expected exactly 1 task in POST body, got {len(post_payload)}"
    )
