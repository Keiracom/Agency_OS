"""Tests for GMB rating parsing in DFSLabsClient.maps_search_gmb — Directive #295 Task C."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal


def _make_dfs_result(item: dict) -> dict:
    """Wrap an item in the DFS tasks/result envelope."""
    return {
        "tasks": [{
            "status_code": 20000,
            "result": [{"items": [item]}],
        }]
    }


def _make_dfs_empty() -> dict:
    return {"tasks": [{"status_code": 20000, "result": [{"items": []}]}]}


async def _call_gmb(item_or_none):
    """Helper: call maps_search_gmb with a mocked HTTP client."""
    from src.clients.dfs_labs_client import DFSLabsClient

    mock_response = MagicMock()
    mock_response.status_code = 200
    if item_or_none is None:
        mock_response.json.return_value = _make_dfs_empty()
    else:
        mock_response.json.return_value = _make_dfs_result(item_or_none)
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=mock_response)

    with patch.object(DFSLabsClient, "_get_client", return_value=mock_http):
        client = DFSLabsClient(login="test", password="test")
        return await client.maps_search_gmb("Dentist Sydney", location_name="Sydney")


@pytest.mark.asyncio
async def test_gmb_rating_scalar():
    """Rating is already a float scalar — should pass through."""
    result = await _call_gmb({"place_id": "abc", "rating": 4.5, "rating_count": 42})
    assert result["gmb_rating"] == 4.5
    assert result["gmb_review_count"] == 42


@pytest.mark.asyncio
async def test_gmb_rating_dict_with_value():
    """Rating is a dict {"value": 4.2, "votes_count": 87} — extract scalar."""
    result = await _call_gmb({"place_id": "abc", "rating": {"value": 4.2, "votes_count": 87}})
    assert result["gmb_rating"] == 4.2
    assert result["gmb_review_count"] == 87


@pytest.mark.asyncio
async def test_gmb_rating_dict_with_rating_type():
    """Rating dict has rating_type key — still extract value."""
    result = await _call_gmb({
        "place_id": "abc",
        "rating": {"rating_type": "Max5", "value": 3.8, "votes_count": 15}
    })
    assert result["gmb_rating"] == 3.8
    assert result["gmb_review_count"] == 15


@pytest.mark.asyncio
async def test_gmb_review_count_prefers_rating_count_over_votes():
    """rating_count field takes priority over votes_count in rating dict."""
    result = await _call_gmb({
        "place_id": "abc",
        "rating": {"value": 4.0, "votes_count": 10},
        "rating_count": 55,
    })
    assert result["gmb_review_count"] == 55


@pytest.mark.asyncio
async def test_gmb_rating_none():
    """No rating field — should return None rating, 0 count."""
    result = await _call_gmb({"place_id": "abc"})
    assert result["gmb_rating"] is None
    assert result["gmb_review_count"] == 0


@pytest.mark.asyncio
async def test_gmb_empty_items():
    """Empty items list — returns None."""
    result = await _call_gmb(None)
    assert result is None


def test_prospect_scorer_gmb_review_count_int_cast():
    """ProspectScorer.score_intent_full: review_count as string doesn't crash."""
    from src.pipeline.prospect_scorer import ProspectScorer
    scorer = ProspectScorer()
    enrichment = {
        "has_google_ads_tag": False,
        "has_meta_pixel": False,
        "website_cms": None,
        "is_running_ads": False,
        "ads_count": 0,
        "website_tracking_codes": [],
        "website_booking_system": False,
        "website_team_names": [],
        "website_social_links": [],
    }
    gmb_data = {"gmb_review_count": "25", "gmb_rating": "4.5"}
    result = scorer.score_intent_full(enrichment, ads_data=None, gmb_data=gmb_data)
    assert result.band in ("NOT_TRYING", "DABBLING", "TRYING", "STRUGGLING")


def test_prospect_scorer_gmb_review_count_dict_doesnt_crash():
    """ProspectScorer.score_intent_full: review_count as raw dict doesn't crash."""
    from src.pipeline.prospect_scorer import ProspectScorer
    scorer = ProspectScorer()
    enrichment = {
        "has_google_ads_tag": False, "has_meta_pixel": False,
        "website_cms": None, "is_running_ads": False, "ads_count": 0,
        "website_tracking_codes": [], "website_booking_system": False,
        "website_team_names": [], "website_social_links": [],
    }
    # Simulates bug: raw dict passed through accidentally
    gmb_data = {"gmb_review_count": {"value": 25}, "gmb_rating": 4.2}
    result = scorer.score_intent_full(enrichment, ads_data=None, gmb_data=gmb_data)
    assert result.band in ("NOT_TRYING", "DABBLING", "TRYING", "STRUGGLING")
