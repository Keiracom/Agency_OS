"""Tests for src/utils/gmb_reviews.py — Directive #300-FIX."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_fetch_gmb_reviews_empty_place_id():
    from src.utils.gmb_reviews import fetch_gmb_reviews
    result = await fetch_gmb_reviews("")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_gmb_reviews_http_error():
    from src.utils.gmb_reviews import fetch_gmb_reviews
    import httpx
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        mock_client_cls.return_value = mock_client
        result = await fetch_gmb_reviews("ChIJabc123")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_gmb_reviews_non_200():
    from src.utils.gmb_reviews import fetch_gmb_reviews
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        result = await fetch_gmb_reviews("ChIJabc123")
    assert result == []


@pytest.mark.asyncio
async def test_fetch_gmb_reviews_extracts_wiI7pd():
    from src.utils.gmb_reviews import fetch_gmb_reviews
    fake_html = (
        '<span class="wiI7pd">Great service, would recommend to anyone!</span>'
        '<span class="wiI7pd">Fast response and professional team.</span>'
    )
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_html
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client
        result = await fetch_gmb_reviews("ChIJabc123")
    assert len(result) == 2
    assert "Great service" in result[0]
