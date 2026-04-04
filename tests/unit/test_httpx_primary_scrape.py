"""
Tests for Task 1.3 — httpx primary scraper with Spider fallback.

Verifies:
- httpx usable content → Spider NOT called
- httpx returns Cloudflare challenge → Spider IS called
- httpx returns empty response → Spider IS called
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.pipeline.free_enrichment import FreeEnrichment


def _make_enrichment() -> FreeEnrichment:
    conn = MagicMock()
    return FreeEnrichment(conn=conn)


USABLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Acme Dental | Sydney</title></head>
<body>
<script src="/app.js"></script>
<p>Welcome to our dental practice. We offer family dentistry in Sydney.
Our team of experienced dentists provides comprehensive dental care including
general check-ups, teeth whitening, fillings, crowns, bridges, and orthodontics.
We are conveniently located in the heart of Sydney CBD and welcome patients
of all ages. Book your appointment online or call us today.
Our friendly staff are here to help you achieve and maintain excellent oral health.
We bulk-bill eligible patients and offer flexible payment plans.</p>
<a href="/about">About</a>
<a href="/services">Services</a>
<a href="mailto:info@acmedental.com.au">Email us</a>
</body>
</html>
"""

CF_CHALLENGE_HTML = """<!DOCTYPE html>
<html>
<head><title>Just a moment...</title></head>
<body>
<div class="cf-browser-verification">Checking your browser before accessing the site.</div>
<p>Cloudflare Ray ID: abc123</p>
</body>
</html>
"""

EMPTY_HTML = ""


def _mock_httpx_response(text: str, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    return resp


@pytest.mark.asyncio
async def test_usable_httpx_content_does_not_call_spider():
    """When httpx returns usable HTML, Spider should NOT be called."""
    fe = _make_enrichment()

    mock_response = _mock_httpx_response(USABLE_HTML)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient", return_value=mock_client):
        with patch.object(fe, "_spider_scrape", new_callable=AsyncMock) as mock_spider:
            result = await fe._scrape_website("acmedental.com.au")

    mock_spider.assert_not_called()
    assert result.get("title") == "Acme Dental | Sydney"
    assert fe._spider_fallback_count == 0


@pytest.mark.asyncio
async def test_cloudflare_challenge_triggers_spider_fallback():
    """When httpx returns a Cloudflare challenge page, Spider should be called."""
    fe = _make_enrichment()

    mock_response = _mock_httpx_response(CF_CHALLENGE_HTML)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    spider_result = {"title": "Acme Dental", "website_cms": None}

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient", return_value=mock_client):
        with patch.object(fe, "_spider_scrape", new_callable=AsyncMock, return_value=spider_result) as mock_spider:
            result = await fe._scrape_website("acmedental.com.au")

    mock_spider.assert_called_once_with("acmedental.com.au")
    assert result == spider_result


@pytest.mark.asyncio
async def test_empty_response_triggers_spider_fallback():
    """When httpx returns an empty response, Spider should be called."""
    fe = _make_enrichment()

    mock_response = _mock_httpx_response(EMPTY_HTML)
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    spider_result = {"title": "Acme Dental", "website_cms": "wordpress"}

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient", return_value=mock_client):
        with patch.object(fe, "_spider_scrape", new_callable=AsyncMock, return_value=spider_result) as mock_spider:
            result = await fe._scrape_website("acmedental.com.au")

    mock_spider.assert_called_once_with("acmedental.com.au")
    assert result == spider_result


@pytest.mark.asyncio
async def test_httpx_exception_triggers_spider_fallback():
    """When httpx raises an exception, Spider should be called."""
    fe = _make_enrichment()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    spider_result = {"title": "Acme Dental", "website_cms": None}

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient", return_value=mock_client):
        with patch.object(fe, "_spider_scrape", new_callable=AsyncMock, return_value=spider_result) as mock_spider:
            result = await fe._scrape_website("acmedental.com.au")

    mock_spider.assert_called_once_with("acmedental.com.au")
    assert result == spider_result


def test_is_content_usable_returns_false_for_short_content():
    fe = _make_enrichment()
    assert fe._is_content_usable("short") is False


def test_is_content_usable_returns_false_for_cf_browser_verification():
    fe = _make_enrichment()
    content = "x" * 1000 + " cf-browser-verification present"
    assert fe._is_content_usable(content) is False


def test_is_content_usable_returns_false_for_cf_waiting_room():
    fe = _make_enrichment()
    content = "just a moment... cloudflare is checking " + "x" * 1000
    assert fe._is_content_usable(content) is False


def test_is_content_usable_returns_false_no_script_under_2000():
    fe = _make_enrichment()
    content = "<html><body>" + "x" * 700 + "</body></html>"
    assert fe._is_content_usable(content) is False


def test_is_content_usable_returns_true_for_normal_page():
    fe = _make_enrichment()
    assert fe._is_content_usable(USABLE_HTML) is True
