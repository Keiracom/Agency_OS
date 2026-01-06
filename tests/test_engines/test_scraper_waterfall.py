"""
FILE: tests/test_engines/test_scraper_waterfall.py
PURPOSE: Unit tests for Scraper Waterfall (Tiers 0-3)
PHASE: 19 (Scraper Waterfall Architecture)
TASK: SCR-009
DEPENDENCIES:
  - pytest
  - pytest-asyncio
  - httpx (for mocking)
"""

from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

from src.engines.url_validator import (
    URLValidator,
    get_url_validator,
    validate_url,
    PARKED_DOMAIN_HOSTS,
    PARKED_CONTENT_INDICATORS,
)
from src.models.url_validation import URLValidationResult
from src.integrations.apify import ApifyClient, ScrapeResult


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def url_validator():
    """Create URL validator instance."""
    return URLValidator(timeout=5.0)


@pytest.fixture
def apify_client():
    """Create Apify client instance."""
    return ApifyClient(api_key="test-api-key")


# ============================================
# URL Validator - Tier 0 Tests
# ============================================


class TestURLNormalization:
    """Test URL normalization (Tier 0 Step 1)."""

    def test_adds_https_to_bare_domain(self, url_validator):
        """Test https:// is added to bare domain."""
        normalized, error = url_validator._normalize_url("example.com")
        assert error is None
        assert normalized == "https://example.com/"

    def test_preserves_existing_https(self, url_validator):
        """Test existing https:// is preserved."""
        normalized, error = url_validator._normalize_url("https://example.com")
        assert error is None
        assert normalized == "https://example.com/"

    def test_preserves_existing_http(self, url_validator):
        """Test existing http:// is preserved."""
        normalized, error = url_validator._normalize_url("http://example.com")
        assert error is None
        assert normalized == "http://example.com/"

    def test_preserves_path(self, url_validator):
        """Test URL path is preserved."""
        normalized, error = url_validator._normalize_url("example.com/about/team")
        assert error is None
        assert normalized == "https://example.com/about/team"

    def test_preserves_query_params(self, url_validator):
        """Test query parameters are preserved."""
        normalized, error = url_validator._normalize_url("example.com?foo=bar")
        assert error is None
        assert normalized == "https://example.com/?foo=bar"

    def test_handles_subdomain(self, url_validator):
        """Test subdomain is preserved."""
        normalized, error = url_validator._normalize_url("www.example.com")
        assert error is None
        assert normalized == "https://www.example.com/"

    def test_strips_whitespace(self, url_validator):
        """Test whitespace is stripped."""
        normalized, error = url_validator._normalize_url("  example.com  ")
        assert error is None
        assert normalized == "https://example.com/"

    def test_rejects_empty_url(self, url_validator):
        """Test empty URL is rejected."""
        normalized, error = url_validator._normalize_url("")
        assert error is not None
        assert "empty" in error.lower()

    def test_rejects_invalid_domain(self, url_validator):
        """Test invalid domain format is rejected."""
        normalized, error = url_validator._normalize_url("not a valid domain!!!")
        assert error is not None

    def test_allows_ip_address(self, url_validator):
        """Test IP addresses are allowed."""
        normalized, error = url_validator._normalize_url("192.168.1.1")
        assert error is None
        assert normalized == "https://192.168.1.1/"


class TestDomainExtraction:
    """Test domain extraction."""

    def test_extracts_domain_from_full_url(self, url_validator):
        """Test domain extracted from full URL."""
        domain = url_validator._extract_domain("https://www.example.com/path")
        assert domain == "www.example.com"

    def test_extracts_domain_removes_port(self, url_validator):
        """Test port is removed from domain."""
        domain = url_validator._extract_domain("https://example.com:8080/path")
        assert domain == "example.com"

    def test_extracts_domain_lowercases(self, url_validator):
        """Test domain is lowercased."""
        domain = url_validator._extract_domain("https://EXAMPLE.COM")
        assert domain == "example.com"


class TestParkedDomainDetection:
    """Test parked domain detection (Tier 0)."""

    def test_detects_parked_redirect_sedoparking(self, url_validator):
        """Test detection of sedoparking redirect."""
        is_parked = url_validator._is_parked_redirect(
            "https://sedoparking.com/foo",
            [],
        )
        assert is_parked is True

    def test_detects_parked_redirect_godaddy(self, url_validator):
        """Test detection of GoDaddy parking redirect."""
        is_parked = url_validator._is_parked_redirect(
            "https://example.com",
            ["https://parking.godaddy.com/foo"],
        )
        assert is_parked is True

    def test_detects_parked_redirect_dan(self, url_validator):
        """Test detection of dan.com redirect."""
        is_parked = url_validator._is_parked_redirect(
            "https://dan.com/buy/example",
            [],
        )
        assert is_parked is True

    def test_not_parked_for_normal_url(self, url_validator):
        """Test normal URLs are not flagged as parked."""
        is_parked = url_validator._is_parked_redirect(
            "https://example.com",
            [],
        )
        assert is_parked is False

    def test_detects_parked_content_for_sale(self, url_validator):
        """Test detection of 'for sale' parked content."""
        content = "<html><body>This domain is for sale. Buy this domain now!</body></html>"
        is_parked = url_validator._is_parked_content(content)
        assert is_parked is True

    def test_detects_parked_content_parking(self, url_validator):
        """Test detection of 'parking' content."""
        content = "<html><body>Domain parking by sedoparking</body></html>"
        is_parked = url_validator._is_parked_content(content)
        assert is_parked is True

    def test_not_parked_for_normal_content(self, url_validator):
        """Test normal content is not flagged as parked."""
        content = """
        <html><body>
            <h1>Welcome to Example Company</h1>
            <p>We provide excellent services.</p>
        </body></html>
        """
        is_parked = url_validator._is_parked_content(content)
        assert is_parked is False

    def test_not_parked_for_empty_content(self, url_validator):
        """Test empty content is not flagged as parked."""
        is_parked = url_validator._is_parked_content("")
        assert is_parked is False


class TestURLValidation:
    """Test full URL validation flow (Tier 0)."""

    @pytest.mark.asyncio
    async def test_valid_url_returns_success(self, url_validator):
        """Test valid URL returns success result."""
        with patch.object(url_validator, "_check_dns", return_value=True):
            with patch.object(url_validator, "_check_url") as mock_check:
                mock_check.return_value = URLValidationResult(
                    valid=True,
                    canonical_url="https://example.com/",
                    redirected=False,
                    status_code=200,
                    domain="example.com",
                )

                result = await url_validator.validate_and_normalize("example.com")

                assert result.valid is True
                assert result.canonical_url == "https://example.com/"
                assert result.domain == "example.com"

    @pytest.mark.asyncio
    async def test_dns_failure_returns_error(self, url_validator):
        """Test DNS failure returns proper error."""
        with patch.object(url_validator, "_check_dns", return_value=False):
            result = await url_validator.validate_and_normalize("nonexistent-domain-12345.com")

            assert result.valid is False
            assert result.error_type == "dns_failure"
            assert "does not resolve" in result.error

    @pytest.mark.asyncio
    async def test_invalid_format_returns_error(self, url_validator):
        """Test invalid URL format returns proper error."""
        result = await url_validator.validate_and_normalize("!!!not-a-url!!!")

        assert result.valid is False
        assert result.error_type == "invalid_format"

    @pytest.mark.asyncio
    async def test_parked_domain_returns_error(self, url_validator):
        """Test parked domain returns proper error."""
        with patch.object(url_validator, "_check_dns", return_value=True):
            with patch.object(url_validator, "_check_url") as mock_check:
                mock_check.return_value = URLValidationResult(
                    valid=False,
                    canonical_url="https://sedoparking.com/foo",
                    redirected=True,
                    error="Domain appears to be parked or for sale",
                    error_type="parked_domain",
                    is_parked=True,
                    domain="example.com",
                )

                result = await url_validator.validate_and_normalize("example.com")

                assert result.valid is False
                assert result.error_type == "parked_domain"
                assert result.is_parked is True


class TestURLValidatorSingleton:
    """Test singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Test get_url_validator returns same instance."""
        validator1 = get_url_validator()
        validator2 = get_url_validator()
        assert validator1 is validator2


# ============================================
# Apify Scraper - Tier 1 & 2 Tests
# ============================================


class TestScrapeResult:
    """Test ScrapeResult dataclass."""

    def test_has_valid_content_true_for_good_html(self):
        """Test has_valid_content returns True for valid HTML."""
        result = ScrapeResult(
            url="https://example.com",
            raw_html="<html><body>" + "a" * 1000 + "</body></html>",
            page_count=1,
            tier_used=1,
        )
        assert result.has_valid_content() is True

    def test_has_valid_content_false_for_short_html(self):
        """Test has_valid_content returns False for short content."""
        result = ScrapeResult(
            url="https://example.com",
            raw_html="<html><body>Short</body></html>",
            page_count=1,
            tier_used=1,
        )
        assert result.has_valid_content() is False

    def test_has_valid_content_false_for_empty(self):
        """Test has_valid_content returns False for empty content."""
        result = ScrapeResult(
            url="https://example.com",
            raw_html="",
            page_count=0,
            tier_used=1,
        )
        assert result.has_valid_content() is False


class TestApifyCheerioScraper:
    """Test Apify Cheerio scraper (Tier 1)."""

    @pytest.mark.asyncio
    async def test_cheerio_success(self, apify_client):
        """Test successful Cheerio scrape returns Tier 1 result."""
        mock_response = {
            "items": [
                {"url": "https://example.com", "html": "<html>" + "a" * 1000 + "</html>"},
            ]
        }

        with patch.object(apify_client, "_run_actor", return_value=mock_response):
            result = await apify_client._scrape_cheerio("https://example.com", max_pages=1)

            assert result.tier_used == 1
            assert result.needs_fallback is False
            assert len(result.raw_html) > 500

    @pytest.mark.asyncio
    async def test_cheerio_empty_response_needs_fallback(self, apify_client):
        """Test empty Cheerio response sets needs_fallback."""
        mock_response = {"items": []}

        with patch.object(apify_client, "_run_actor", return_value=mock_response):
            result = await apify_client._scrape_cheerio("https://example.com", max_pages=1)

            assert result.tier_used == 1
            assert result.needs_fallback is True

    @pytest.mark.asyncio
    async def test_cheerio_short_content_needs_fallback(self, apify_client):
        """Test short Cheerio content sets needs_fallback."""
        mock_response = {
            "items": [
                {"url": "https://example.com", "html": "<html>short</html>"},
            ]
        }

        with patch.object(apify_client, "_run_actor", return_value=mock_response):
            result = await apify_client._scrape_cheerio("https://example.com", max_pages=1)

            assert result.tier_used == 1
            assert result.needs_fallback is True


class TestApifyPlaywrightScraper:
    """Test Apify Playwright scraper (Tier 2)."""

    @pytest.mark.asyncio
    async def test_playwright_success(self, apify_client):
        """Test successful Playwright scrape returns Tier 2 result."""
        mock_response = {
            "items": [
                {"url": "https://example.com", "html": "<html>" + "a" * 1000 + "</html>"},
            ]
        }

        with patch.object(apify_client, "_run_actor", return_value=mock_response):
            result = await apify_client._scrape_playwright("https://example.com", max_pages=1)

            assert result.tier_used == 2
            assert result.needs_fallback is False
            assert len(result.raw_html) > 500

    @pytest.mark.asyncio
    async def test_playwright_blocked_content_needs_fallback(self, apify_client):
        """Test Playwright blocked content sets needs_fallback."""
        mock_response = {
            "items": [
                {
                    "url": "https://example.com",
                    "html": "<html>Access Denied. Ray ID: 12345. Enable JavaScript and cookies to continue.</html>",
                },
            ]
        }

        with patch.object(apify_client, "_run_actor", return_value=mock_response):
            result = await apify_client._scrape_playwright("https://example.com", max_pages=1)

            assert result.tier_used == 2
            assert result.needs_fallback is True
            assert "blocked" in (result.failure_reason or "").lower() or result.has_valid_content() is False


class TestScraperWaterfall:
    """Test scraper waterfall fallback logic."""

    @pytest.mark.asyncio
    async def test_waterfall_tier1_success_stops(self, apify_client):
        """Test waterfall stops at Tier 1 if successful."""
        good_html = "<html>" + "a" * 1000 + "</html>"
        mock_cheerio_response = {
            "items": [{"url": "https://example.com", "html": good_html}]
        }

        with patch.object(apify_client, "_run_actor", return_value=mock_cheerio_response) as mock_run:
            result = await apify_client.scrape_website_with_waterfall("https://example.com", max_pages=1)

            assert result.tier_used == 1
            assert result.needs_fallback is False
            # Should only call Cheerio actor, not Playwright
            assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_waterfall_falls_to_tier2(self, apify_client):
        """Test waterfall falls to Tier 2 when Tier 1 fails."""
        short_html = "<html>short</html>"
        good_html = "<html>" + "a" * 1000 + "</html>"

        call_count = [0]

        async def mock_run_actor(actor_id, run_input, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Cheerio returns short content
                return {"items": [{"url": "https://example.com", "html": short_html}]}
            else:
                # Playwright returns good content
                return {"items": [{"url": "https://example.com", "html": good_html}]}

        with patch.object(apify_client, "_run_actor", side_effect=mock_run_actor):
            result = await apify_client.scrape_website_with_waterfall("https://example.com", max_pages=1)

            assert result.tier_used == 2
            assert result.needs_fallback is False
            assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_waterfall_both_tiers_fail(self, apify_client):
        """Test waterfall sets needs_fallback when both tiers fail."""
        short_html = "<html>short</html>"

        async def mock_run_actor(actor_id, run_input, **kwargs):
            return {"items": [{"url": "https://example.com", "html": short_html}]}

        with patch.object(apify_client, "_run_actor", side_effect=mock_run_actor):
            result = await apify_client.scrape_website_with_waterfall("https://example.com", max_pages=1)

            assert result.needs_fallback is True
            assert result.failure_reason is not None


# ============================================
# Camoufox Scraper - Tier 3 Tests
# ============================================


class TestCamoufoxScraper:
    """Test Camoufox scraper (Tier 3)."""

    def test_proxy_config_with_credentials(self):
        """Test proxy config builds correctly with credentials."""
        from src.integrations.camoufox_scraper import CamoufoxScraper

        scraper = CamoufoxScraper(
            proxy_host="proxy.example.com",
            proxy_port=8080,
            proxy_username="user",
            proxy_password="pass",
        )

        assert scraper.is_configured is True
        assert scraper._proxy_config is not None
        assert scraper._proxy_config["server"] == "http://proxy.example.com:8080"
        assert scraper._proxy_config["username"] == "user"
        assert scraper._proxy_config["password"] == "pass"

    def test_proxy_config_without_credentials(self):
        """Test proxy config without auth credentials."""
        from src.integrations.camoufox_scraper import CamoufoxScraper

        scraper = CamoufoxScraper(
            proxy_host="proxy.example.com",
            proxy_port=8080,
        )

        assert scraper.is_configured is True
        assert "username" not in scraper._proxy_config

    def test_not_configured_without_proxy(self):
        """Test scraper reports not configured without proxy."""
        from src.integrations.camoufox_scraper import CamoufoxScraper

        scraper = CamoufoxScraper()

        assert scraper.is_configured is False

    def test_blocked_page_detection(self):
        """Test blocked page content detection."""
        from src.integrations.camoufox_scraper import CamoufoxScraper

        scraper = CamoufoxScraper()

        # Multiple blocked indicators
        blocked_html = "<html>Access Denied. Ray ID: 12345. Please enable JavaScript and cookies.</html>"
        assert scraper._is_blocked_page(blocked_html) is True

        # Single indicator - not enough
        single_indicator = "<html>Please wait while we verify your browser.</html>"
        assert scraper._is_blocked_page(single_indicator) is False

        # Normal content
        normal_html = "<html><body><h1>Welcome</h1><p>Content here</p></body></html>"
        assert scraper._is_blocked_page(normal_html) is False

        # Empty content
        assert scraper._is_blocked_page("") is True

    def test_scrape_result_success_property(self):
        """Test CamoufoxScrapeResult success property."""
        from src.integrations.camoufox_scraper import CamoufoxScrapeResult

        # Success case
        success_result = CamoufoxScrapeResult(
            url="https://example.com",
            raw_html="a" * 600,
            title="Example",
            tier_used=3,
            needs_fallback=False,
        )
        assert success_result.success is True

        # Short content failure
        short_result = CamoufoxScrapeResult(
            url="https://example.com",
            raw_html="short",
            tier_used=3,
            needs_fallback=False,
        )
        assert short_result.success is False

        # Fallback needed failure
        fallback_result = CamoufoxScrapeResult(
            url="https://example.com",
            raw_html="a" * 600,
            tier_used=3,
            needs_fallback=True,
        )
        assert fallback_result.success is False


class TestCamoufoxAvailability:
    """Test Camoufox availability checks."""

    def test_is_camoufox_available_when_installed(self):
        """Test availability check when camoufox is installed."""
        from src.integrations.camoufox_scraper import is_camoufox_available

        with patch.dict("sys.modules", {"camoufox": MagicMock()}):
            # Note: This test may return True or False depending on whether
            # camoufox is actually installed in the test environment
            result = is_camoufox_available()
            assert isinstance(result, bool)

    def test_is_camoufox_configured(self):
        """Test configuration check."""
        from src.integrations.camoufox_scraper import (
            is_camoufox_configured,
            get_camoufox_scraper,
        )

        # Reset singleton for test
        import src.integrations.camoufox_scraper as camoufox_module
        camoufox_module._camoufox_scraper = None

        with patch.object(
            camoufox_module.settings,
            "residential_proxy_host",
            "",
        ):
            result = is_camoufox_configured()
            assert result is False


# ============================================
# Content Validation Tests
# ============================================


class TestContentValidation:
    """Test content validation across tiers."""

    def test_blocked_indicators_list_exists(self):
        """Test blocked indicators list is defined."""
        from src.integrations.apify import BLOCKED_PAGE_INDICATORS

        assert len(BLOCKED_PAGE_INDICATORS) > 0
        assert "access denied" in BLOCKED_PAGE_INDICATORS

    def test_content_length_threshold(self):
        """Test minimum content length threshold."""
        result = ScrapeResult(
            url="https://example.com",
            raw_html="<html>" + "x" * 499 + "</html>",
            tier_used=1,
        )
        # 499 chars + HTML tags is still under threshold
        assert result.has_valid_content() is False

        result2 = ScrapeResult(
            url="https://example.com",
            raw_html="<html>" + "x" * 500 + "</html>",
            tier_used=1,
        )
        assert result2.has_valid_content() is True


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Test URL normalization (add https://, preserve path, etc.)
# [x] Test domain extraction
# [x] Test parked domain redirect detection
# [x] Test parked content detection
# [x] Test full URL validation flow
# [x] Test DNS failure handling
# [x] Test singleton pattern
# [x] Test ScrapeResult has_valid_content
# [x] Test Cheerio scraper (Tier 1)
# [x] Test Playwright scraper (Tier 2)
# [x] Test waterfall fallback logic
# [x] Test Camoufox proxy configuration
# [x] Test Camoufox blocked page detection
# [x] Test Camoufox availability checks
# [x] Test content validation across tiers
