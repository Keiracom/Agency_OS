"""
FILE: tests/test_engines/test_icp_scraper_tiers.py
PURPOSE: Unit tests for ICP Scraper waterfall Tier 2 (Jina) + Tier 3 (Bright Data)
PHASE: 19 (Scraper Waterfall - Directive #186)
TASK: DIR-186
DEPENDENCIES:
  - pytest
  - pytest-asyncio
  - unittest.mock
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.engines.icp_scraper import ICPScraperEngine, ScrapedWebsite
from src.engines.base import EngineResult
from src.models.url_validation import URLValidationResult


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

LONG_MARKDOWN = "# Company Title\n\n" + "This is test content about the company. " * 20
LONG_HTML = "<html><body>" + "<p>Test content paragraph.</p>" * 50 + "</body></html>"


def _make_url_valid(canonical_url: str = "https://example.com/") -> URLValidationResult:
    """Return a successful URLValidationResult."""
    return URLValidationResult(
        valid=True,
        canonical_url=canonical_url,
        redirected=False,
        status_code=200,
        domain="example.com",
    )


def _make_response(status_code: int, text: str) -> MagicMock:
    """Build a minimal httpx.Response mock."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.text = text
    return mock


@pytest.fixture
def scraper():
    """Create ICPScraperEngine with Camoufox disabled (normal prod state)."""
    mock_url_validator = MagicMock()
    s = ICPScraperEngine(url_validator=mock_url_validator)
    return s


# ---------------------------------------------------------------------------
# Tier 2: Jina AI Reader
# ---------------------------------------------------------------------------


class TestJinaTier:
    """Tier 2 — Jina AI Reader."""

    @pytest.mark.asyncio
    async def test_jina_success_returns_tier2(self, scraper):
        """Jina 200 + long markdown → EngineResult with tier_used=2."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        jina_response = _make_response(200, LONG_MARKDOWN)

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls:

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=jina_response)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        assert isinstance(result, EngineResult)
        assert result.data.tier_used == 2
        assert result.data.needs_fallback is False
        assert result.metadata["jina_used"] is True
        assert len(result.data.raw_html) >= 200

    @pytest.mark.asyncio
    async def test_jina_short_content_falls_through(self, scraper):
        """Jina 200 but short content (<200 chars) → falls to next tier."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        # Jina returns too-short content; BD also insufficient
        short_response = _make_response(200, "Too short")
        bd_response = _make_response(200, "x" * 10)

        async def fake_get(*args, **kwargs):
            return short_response

        async def fake_post(*args, **kwargs):
            return bd_response

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch.dict("os.environ", {"BRIGHTDATA_API_KEY": "test-key"}):

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=fake_get)
            mock_ctx.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        # Should reach manual fallback (tier 4)
        assert result.data.needs_fallback is True

    @pytest.mark.asyncio
    async def test_jina_exception_falls_through(self, scraper):
        """Jina raises exception → falls to Tier 3."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        bd_response = _make_response(200, LONG_HTML)

        async def fake_get(*args, **kwargs):
            raise httpx.RequestError("connection refused")

        async def fake_post(*args, **kwargs):
            return bd_response

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch.dict("os.environ", {"BRIGHTDATA_API_KEY": "test-key"}):

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=fake_get)
            mock_ctx.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        # Jina failed, Bright Data should have succeeded
        assert result.data.tier_used == 3
        assert result.data.needs_fallback is False


# ---------------------------------------------------------------------------
# Tier 3: Bright Data Web Unlocker
# ---------------------------------------------------------------------------


class TestBrightDataTier:
    """Tier 3 — Bright Data Web Unlocker."""

    @pytest.mark.asyncio
    async def test_brightdata_success_returns_tier3(self, scraper):
        """Bright Data 200 + long HTML after Jina failure → tier_used=3."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        jina_response = _make_response(200, "too short")
        bd_response = _make_response(200, LONG_HTML)

        async def fake_get(*args, **kwargs):
            return jina_response

        async def fake_post(*args, **kwargs):
            return bd_response

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch.dict("os.environ", {"BRIGHTDATA_API_KEY": "fake-bd-key"}):

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=fake_get)
            mock_ctx.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        assert result.data.tier_used == 3
        assert result.data.needs_fallback is False
        assert result.metadata["brightdata_used"] is True

    @pytest.mark.asyncio
    async def test_brightdata_skipped_when_no_api_key(self, scraper):
        """Bright Data is skipped entirely when BRIGHTDATA_API_KEY is missing."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        jina_response = _make_response(200, "too short")

        async def fake_get(*args, **kwargs):
            return jina_response

        import os
        original = os.environ.pop("BRIGHTDATA_API_KEY", None)
        try:
            with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
                 patch("httpx.AsyncClient") as mock_client_cls:

                mock_ctx = AsyncMock()
                mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
                mock_ctx.__aexit__ = AsyncMock(return_value=False)
                mock_ctx.get = AsyncMock(side_effect=fake_get)
                mock_client_cls.return_value = mock_ctx

                result = await scraper.scrape_website("https://example.com/")
        finally:
            if original:
                os.environ["BRIGHTDATA_API_KEY"] = original

        # Should fall to manual fallback (tier 4)
        assert result.data.needs_fallback is True

    @pytest.mark.asyncio
    async def test_brightdata_short_content_falls_to_manual(self, scraper):
        """Bright Data returns <500 chars → falls to manual fallback."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        jina_response = _make_response(500, "Jina error")
        bd_response = _make_response(200, "<html>short</html>")

        async def fake_get(*args, **kwargs):
            return jina_response

        async def fake_post(*args, **kwargs):
            return bd_response

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch.dict("os.environ", {"BRIGHTDATA_API_KEY": "fake-bd-key"}):

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=fake_get)
            mock_ctx.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        assert result.data.needs_fallback is True
        assert result.data.tier_used == 4


# ---------------------------------------------------------------------------
# Full Waterfall Integration Tests
# ---------------------------------------------------------------------------


class TestFullWaterfall:
    """End-to-end waterfall: Camoufox disabled → Jina → BD → manual."""

    @pytest.mark.asyncio
    async def test_waterfall_camoufox_disabled_jina_wins(self, scraper):
        """Camoufox off → Jina returns content → stops at Tier 2."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        jina_response = _make_response(200, LONG_MARKDOWN)

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls:

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(return_value=jina_response)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        assert result.data.tier_used == 2

    @pytest.mark.asyncio
    async def test_waterfall_jina_fails_brightdata_wins(self, scraper):
        """Camoufox off → Jina fails → Bright Data returns HTML → stops at Tier 3."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        jina_response = _make_response(200, "x" * 10)  # Too short
        bd_response = _make_response(200, LONG_HTML)

        async def fake_get(*args, **kwargs):
            return jina_response

        async def fake_post(*args, **kwargs):
            return bd_response

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch.dict("os.environ", {"BRIGHTDATA_API_KEY": "fake-bd-key"}):

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=fake_get)
            mock_ctx.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        assert result.data.tier_used == 3
        assert result.data.needs_fallback is False

    @pytest.mark.asyncio
    async def test_waterfall_all_automated_fail_returns_manual(self, scraper):
        """All tiers fail → tier_used=4, needs_fallback=True."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=_make_url_valid()
        )

        fail_response = _make_response(200, "short")

        async def fake_get(*args, **kwargs):
            return fail_response

        async def fake_post(*args, **kwargs):
            return fail_response

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls, \
             patch.dict("os.environ", {"BRIGHTDATA_API_KEY": "fake-bd-key"}):

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=fake_get)
            mock_ctx.post = AsyncMock(side_effect=fake_post)
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://example.com/")

        assert result.data.needs_fallback is True
        assert result.data.tier_used == 4
        assert "/onboarding/manual-entry" in result.data.manual_fallback_url

    @pytest.mark.asyncio
    async def test_tier0_invalid_url_returns_early(self, scraper):
        """Invalid URL → fails at Tier 0, never reaches Jina."""
        scraper._url_validator.validate_and_normalize = AsyncMock(
            return_value=URLValidationResult(
                valid=False,
                canonical_url=None,
                redirected=False,
                error="DNS does not resolve",
                error_type="dns_failure",
                domain="bad-domain.invalid",
            )
        )

        with patch.object(type(scraper), "camoufox_enabled", new_callable=lambda: property(lambda self: False)), \
             patch("httpx.AsyncClient") as mock_client_cls:

            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.get = AsyncMock(side_effect=AssertionError("should not call Jina"))
            mock_client_cls.return_value = mock_ctx

            result = await scraper.scrape_website("https://bad-domain.invalid/")

        assert result.data.tier_used == 0
        assert result.data.needs_fallback is True
        assert result.data.failure_reason is not None


# ---------------------------------------------------------------------------
# VERIFICATION CHECKLIST
# ---------------------------------------------------------------------------
# [x] Tier 2 Jina: 200 + long markdown → success (tier_used=2)
# [x] Tier 2 Jina: 200 + short content → falls through to Tier 3
# [x] Tier 2 Jina: exception → falls through to Tier 3
# [x] Tier 3 BD: success after Jina failure → tier_used=3
# [x] Tier 3 BD: skipped when BRIGHTDATA_API_KEY missing
# [x] Tier 3 BD: short content → falls to manual fallback (tier 4)
# [x] Full waterfall: Camoufox off → Jina wins at Tier 2
# [x] Full waterfall: Jina fails → BD wins at Tier 3
# [x] Full waterfall: all fail → manual fallback (tier 4)
# [x] Tier 0: invalid URL → early exit before Jina
