"""Tests for HttpxScraper — Directive #295 Task B."""
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

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await scraper.scrape("example.com")

    assert result is not None
    assert result["status_code"] == 200
    assert HTML_WITH_TITLE in result["html"]
    assert result["content_length"] == len(HTML_WITH_TITLE)


@pytest.mark.asyncio
async def test_scrape_returns_none_on_timeout():
    scraper = HttpxScraper()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_client_cls.return_value = mock_client

        result = await scraper.scrape("example.com")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_returns_none_on_non_200():
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await scraper.scrape("example.com")

    assert result is None


@pytest.mark.asyncio
async def test_scrape_extracts_title():
    scraper = HttpxScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head><title>  My Dental Clinic  </title></head><body>hello</body></html>"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await scraper.scrape("example.com")

    assert result is not None
    assert result["title"] == "My Dental Clinic"
