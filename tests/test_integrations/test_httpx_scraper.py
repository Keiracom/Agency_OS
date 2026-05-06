"""Tests for HttpxScraper — Directive #295, updated #300-FIX (Issue 9)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.integrations.httpx_scraper import HttpxScraper


HTML_WITH_TITLE = "<html><head><title>Test Page</title></head><body>content</body></html>"


@pytest.mark.asyncio
async def test_scrape_returns_dict_on_200():
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_WITH_TITLE

    mock_client = MagicMock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.integrations.httpx_scraper.httpx.AsyncClient", return_value=mock_client):
        result = await scraper.scrape("example.com")

    assert result is not None
    assert result["status_code"] == 200
    assert HTML_WITH_TITLE in result["html"]
    assert result["content_length"] == len(HTML_WITH_TITLE)


@pytest.mark.asyncio
async def test_scrape_returns_none_on_timeout():
    scraper = HttpxScraper()

    mock_client = MagicMock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    with patch("src.integrations.httpx_scraper.httpx.AsyncClient", return_value=mock_client):
        result = await scraper.scrape("example.com")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_returns_none_on_non_200():
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"

    mock_client = MagicMock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.integrations.httpx_scraper.httpx.AsyncClient", return_value=mock_client):
        result = await scraper.scrape("example.com")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_extracts_title():
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = (
        "<html><head><title>  My Dental Clinic  </title></head><body>hello</body></html>"
    )

    mock_client = MagicMock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("src.integrations.httpx_scraper.httpx.AsyncClient", return_value=mock_client):
        result = await scraper.scrape("example.com")

    assert result is not None
    assert result["title"] == "My Dental Clinic"


@pytest.mark.asyncio
async def test_scraper_reuses_persistent_client():
    """Verify the persistent client is reused across multiple scrape() calls."""
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_WITH_TITLE

    mock_client = MagicMock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch(
        "src.integrations.httpx_scraper.httpx.AsyncClient", return_value=mock_client
    ) as mock_cls:
        await scraper.scrape("example.com")
        await scraper.scrape("example2.com")
        # AsyncClient constructor called only once (persistent)
        assert mock_cls.call_count == 1


@pytest.mark.asyncio
async def test_close_resets_client():
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = HTML_WITH_TITLE

    mock_client = MagicMock()
    mock_client.is_closed = False
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.aclose = AsyncMock()

    with patch("src.integrations.httpx_scraper.httpx.AsyncClient", return_value=mock_client):
        await scraper.scrape("example.com")
        await scraper.close()

    mock_client.aclose.assert_called_once()
    assert scraper._client is None
