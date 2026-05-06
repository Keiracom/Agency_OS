"""
Tests for Task 1.3 — httpx primary scraper with Spider fallback.

Architecture: FreeEnrichment._scrape_website() calls self._httpx.scrape() (HttpxScraper).
- If HttpxScraper returns a result with html >= 1000 chars → use it, Spider NOT called
- If HttpxScraper returns None or short html → Spider fallback (increment _spider_fallback_count)
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


@pytest.mark.asyncio
async def test_usable_httpx_content_does_not_call_spider():
    """When HttpxScraper returns usable HTML (>=1000 chars), Spider should NOT be called."""
    fe = _make_enrichment()

    # HttpxScraper returns a good result
    httpx_result = {"html": USABLE_HTML * 5, "title": "Acme Dental | Sydney", "status_code": 200}
    fe._httpx.scrape = AsyncMock(return_value=httpx_result)

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient") as mock_httpx_cls:
        result = await fe._scrape_website("acmedental.com.au")

    # Spider (httpx.AsyncClient.post) should NOT have been called
    mock_httpx_cls.assert_not_called()
    assert result.get("scraper_used") == "httpx"
    assert fe._spider_fallback_count == 0


@pytest.mark.asyncio
async def test_httpx_returns_none_triggers_spider_fallback():
    """When HttpxScraper returns None (failed/blocked), Spider should be called."""
    fe = _make_enrichment()
    fe._httpx.scrape = AsyncMock(return_value=None)

    spider_result = {
        "title": "Acme Dental",
        "website_cms": "wordpress",
        "website_tech_stack": [],
        "website_tracking_codes": [],
        "website_team_names": [],
        "website_contact_emails": [],
        "website_address": None,
        "_raw_html": "<html>real content</html>",
        "scraper_used": "spider",
        "has_google_ads_tag": False,
        "has_meta_pixel": False,
        "has_any_ad_tag": False,
    }

    async with MagicMock() as mock_client:
        mock_client.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value=[
                        {
                            "content": "<html>real content</html>",
                            "links": [],
                            "metadata": {"title": "Acme Dental"},
                        }
                    ]
                ),
            )
        )

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient") as mock_httpx_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value=[
                        {
                            "content": "real content " * 100,
                            "links": [],
                            "metadata": {"title": "Acme Dental"},
                        }
                    ]
                ),
            )
        )
        mock_httpx_cls.return_value = mock_client_instance

        result = await fe._scrape_website("acmedental.com.au")

    assert fe._spider_fallback_count == 1
    assert result.get("scraper_used") == "spider"


@pytest.mark.asyncio
async def test_httpx_returns_short_html_triggers_spider_fallback():
    """When HttpxScraper returns html < 1000 chars, Spider should be called."""
    fe = _make_enrichment()
    fe._httpx.scrape = AsyncMock(
        return_value={"html": "<html>short</html>", "title": None, "status_code": 200}
    )

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient") as mock_httpx_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value=[
                        {
                            "content": "real content " * 100,
                            "links": [],
                            "metadata": {"title": "Test"},
                        }
                    ]
                ),
            )
        )
        mock_httpx_cls.return_value = mock_client_instance

        result = await fe._scrape_website("acmedental.com.au")

    assert fe._spider_fallback_count == 1


@pytest.mark.asyncio
async def test_spider_fallback_count_increments_per_fallback():
    """_spider_fallback_count increments each time Spider is used."""
    fe = _make_enrichment()
    fe._httpx.scrape = AsyncMock(return_value=None)

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient") as mock_httpx_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_instance.post = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(
                    return_value=[
                        {
                            "content": "content " * 100,
                            "links": [],
                            "metadata": {"title": "Test"},
                        }
                    ]
                ),
            )
        )
        mock_httpx_cls.return_value = mock_client_instance

        await fe._scrape_website("domain1.com.au")
        await fe._scrape_website("domain2.com.au")

    assert fe._spider_fallback_count == 2


@pytest.mark.asyncio
async def test_usable_result_has_raw_html_key():
    """httpx path must include _raw_html in result for intelligence layer."""
    fe = _make_enrichment()
    long_html = USABLE_HTML * 10  # ensure >= 1000 chars
    httpx_result = {"html": long_html, "title": "Test", "status_code": 200}
    fe._httpx.scrape = AsyncMock(return_value=httpx_result)

    result = await fe._scrape_website("test.com.au")

    assert "_raw_html" in result
    assert result["_raw_html"] == long_html


@pytest.mark.asyncio
async def test_spider_not_called_when_httpx_succeeds():
    """Confirm Spider API endpoint is never hit when httpx returns good content."""
    fe = _make_enrichment()
    long_html = USABLE_HTML * 10
    fe._httpx.scrape = AsyncMock(
        return_value={"html": long_html, "title": "Test", "status_code": 200}
    )

    with patch("src.pipeline.free_enrichment.httpx.AsyncClient") as mock_cls:
        await fe._scrape_website("test.com.au")
        # httpx.AsyncClient should not have been instantiated (Spider uses it for POST)
        mock_cls.assert_not_called()

    assert fe._spider_fallback_count == 0
