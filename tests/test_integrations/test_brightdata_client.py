"""Tests for src/integrations/bright_data_linkedin_client.py — Directive #286"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.bright_data_linkedin_client import BrightDataLinkedInClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(status_code: int, json_data):
    """Create a mock httpx response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.text = str(json_data)
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx

        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock
        )
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_returns_people_list():
    """Mock trigger→progress→download; assert 2 employees returned."""
    client = BrightDataLinkedInClient(api_key="test-key")

    trigger_resp = _make_mock_response(200, {"snapshot_id": "snap123"})
    progress_resp = _make_mock_response(200, {"status": "ready", "records": 2})
    download_resp = _make_mock_response(
        200,
        [
            {
                "company": "Acme",
                "employees": [
                    {"name": "Alice Smith", "title": "Owner"},
                    {"name": "Bob Jones", "title": "Marketing Manager"},
                ],
            }
        ],
    )

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=trigger_resp)
    mock_http.get = AsyncMock(side_effect=[progress_resp, download_resp])
    mock_http.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_http):
        people = await client.lookup_company_people(
            "Acme Inc", domain="acme.com", linkedin_url="https://linkedin.com/company/acme"
        )

    assert len(people) == 2
    assert people[0]["name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_pick_dm_selects_owner_over_manager():
    """Owner should beat Marketing Manager."""
    client = BrightDataLinkedInClient(api_key="test-key")
    people = [
        {"name": "Bob", "title": "Marketing Manager"},
        {"name": "Alice", "title": "Owner"},
    ]
    result = client.pick_decision_maker(people)
    assert result is not None
    assert result["name"] == "Alice"
    assert result["confidence"] == "HIGH"


@pytest.mark.asyncio
async def test_pick_dm_priority_order():
    """owner > founder > director > ceo."""
    client = BrightDataLinkedInClient(api_key="test-key")
    people = [
        {"name": "Dave", "title": "CEO"},
        {"name": "Carol", "title": "Director of Sales"},
        {"name": "Bob", "title": "Founder"},
        {"name": "Alice", "title": "Owner"},
    ]
    result = client.pick_decision_maker(people)
    assert result is not None
    assert result["name"] == "Alice"
    assert result["confidence"] == "HIGH"

    # Remove owner — founder should win (people[:3] = Dave/Carol/Bob, no Alice)
    result2 = client.pick_decision_maker(people[:3])
    assert result2["name"] == "Bob"

    # Remove founder too — director should win (people[:2] = Dave/Carol)
    result3 = client.pick_decision_maker(people[:2])
    assert result3["name"] == "Carol"


def test_pick_dm_empty_returns_none():
    """Empty list returns None."""
    client = BrightDataLinkedInClient(api_key="test-key")
    assert client.pick_decision_maker([]) is None


@pytest.mark.asyncio
async def test_4xx_raises_valueerror():
    """HTTP 401 from trigger should raise ValueError."""
    client = BrightDataLinkedInClient(api_key="bad-key")

    trigger_resp = _make_mock_response(401, {"error": "Unauthorized"})

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=trigger_resp)
    mock_http.is_closed = False

    with patch.object(client, "_get_client", return_value=mock_http):
        with pytest.raises(ValueError, match="Bright Data API error: 401"):
            await client._scraper_request("some_dataset", [{"url": "https://example.com"}])


# ── Live smoke (Phase 1a pre-cohort sweep) ────────────────────────────────────
# Closes audit checklist item #7 (template § C) for bright_data_linkedin_client.py.
# Real BD Scrapers API call — caps at 20 records × $0.00075 = ~$0.015 USD max.

import os as _os


@pytest.mark.live
@pytest.mark.asyncio
async def test_bd_linkedin_live_smoke():
    """Real BD LinkedIn lookup of a known-stable AU company.

    Asserts the call completes and at least one structured employee/staff
    record comes back. Failure indicates BD URL/auth/dataset drift — mocks
    would not catch this (the lesson from PR #587/#588).

    Cost: ≤ 20 records × $0.00075 = ~$0.015 USD per run. Budget-safe.
    """
    if not _os.environ.get("BRIGHTDATA_API_KEY"):
        pytest.skip("BRIGHTDATA_API_KEY env var unset; live smoke skipped")

    company = _os.environ.get(
        "BD_LINKEDIN_LIVE_SMOKE_COMPANY",
        # Stable AU company — large permanent LinkedIn presence.
        "Atlassian",
    )
    # Use the direct-URL input path — that's the 1-row pattern the dispatch
    # asked for. The keyword-discover path on this dataset currently 400s
    # with "Incorrect discovery collector id" (real BD contract drift the
    # smoke surfaced on first run; tracked separately for connector fix).
    linkedin_url = _os.environ.get(
        "BD_LINKEDIN_LIVE_SMOKE_URL",
        "https://www.linkedin.com/company/atlassian/",
    )

    client = BrightDataLinkedInClient()
    people = await client.lookup_company_people(
        company_name=company,
        linkedin_url=linkedin_url,
    )

    # `lookup_company_people` swallows exceptions and returns []. Empty list
    # for a known-stable target = contract regression, fail loudly.
    assert isinstance(people, list), (
        f"BD LinkedIn returned non-list ({type(people).__name__}) for "
        f"{company!r} — schema drift?"
    )
    assert len(people) > 0, (
        f"BD LinkedIn returned 0 records for {company!r} — likely URL/auth/"
        "dataset-contract drift (mocks would not catch this)"
    )
    # Spot-check that records carry at least one of the keys downstream
    # picks decision-makers from. The dataset returns various shapes; we
    # just need ONE of these populated on the first record.
    first = people[0]
    assert isinstance(first, dict), f"first record is not a dict: {first!r}"
    has_signal = any(
        first.get(k) for k in ("name", "title", "linkedin_url", "url")
    )
    assert has_signal, (
        f"first record has no name/title/linkedin_url — schema drift?: "
        f"{first!r}"
    )
