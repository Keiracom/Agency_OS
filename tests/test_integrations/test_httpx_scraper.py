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


# ── _extract_contact_data ─────────────────────────────────────────────────────

def test_extract_contact_data_mobile():
    scraper = HttpxScraper()
    html = "<p>Call Jane on 0412 345 678 today</p>"
    cd = scraper._extract_contact_data(html)
    assert cd["mobile"] == "0412345678"


def test_extract_contact_data_intl_mobile():
    scraper = HttpxScraper()
    html = "<p>+61412345678</p>"
    cd = scraper._extract_contact_data(html)
    assert cd["mobile"] == "0412345678"


def test_extract_contact_data_landline():
    scraper = HttpxScraper()
    html = "<p>02 9876 5432</p>"
    cd = scraper._extract_contact_data(html)
    assert cd["landline"] == "0298765432"


def test_extract_contact_data_email_skips_generic():
    scraper = HttpxScraper()
    html = '<a href="mailto:info@example.com">info</a> or <a href="mailto:dr.smith@example.com">email</a>'
    cd = scraper._extract_contact_data(html)
    assert cd["email"] == "dr.smith@example.com"


def test_extract_contact_data_linkedin():
    scraper = HttpxScraper()
    html = '<a href="https://www.linkedin.com/in/jane-smith">LinkedIn</a>'
    cd = scraper._extract_contact_data(html)
    assert "linkedin.com/in/jane-smith" in cd["linkedin"]


def test_extract_contact_data_empty_html():
    scraper = HttpxScraper()
    cd = scraper._extract_contact_data("")
    assert cd == {"mobile": None, "landline": None, "email": None, "linkedin": None}
