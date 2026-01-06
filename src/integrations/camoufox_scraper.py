"""
Contract: src/integrations/camoufox_scraper.py
Purpose: Anti-detection browser scraper for Cloudflare-protected sites (Tier 3)
Layer: 2 - integrations
Imports: models only
Consumers: icp_scraper.py, orchestration

TIER 3 of Scraper Waterfall:
- Uses Camoufox (Firefox-based anti-detect browser)
- Requires residential proxy for clean IP reputation
- Handles Cloudflare Turnstile and aggressive bot detection
- Cost: ~$0.02-0.05/page | Time: 20-45s | Success: ~95%
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Default timeouts
DEFAULT_TIMEOUT_MS = 45000
CLOUDFLARE_WAIT_MS = 10000

# Blocked page indicators
BLOCKED_INDICATORS = [
    "access denied",
    "ray id:",
    "please wait while we verify",
    "checking your browser",
    "just a moment...",
    "enable javascript and cookies",
    "attention required",
    "please complete the security check",
    "blocked",
    "captcha",
]


@dataclass
class CamoufoxScrapeResult:
    """Result from Camoufox scraping."""

    url: str
    raw_html: str = ""
    title: str = ""
    page_count: int = 0
    tier_used: int = 3
    needs_fallback: bool = False
    failure_reason: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if scrape succeeded."""
        return len(self.raw_html) >= 500 and not self.needs_fallback


class CamoufoxScraper:
    """
    Anti-detection browser scraper using Camoufox.

    Camoufox is a Firefox-based browser that evades bot detection
    by mimicking real browser fingerprints. Combined with residential
    proxies, it can bypass Cloudflare and similar protections.

    This is Tier 3 of the Scraper Waterfall - used when Apify
    Cheerio and Playwright both fail.
    """

    def __init__(
        self,
        proxy_host: Optional[str] = None,
        proxy_port: Optional[int] = None,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
    ):
        """
        Initialize Camoufox scraper with optional proxy configuration.

        Args:
            proxy_host: Residential proxy hostname
            proxy_port: Proxy port
            proxy_username: Proxy auth username
            proxy_password: Proxy auth password
        """
        self.proxy_host = proxy_host or getattr(settings, 'residential_proxy_host', None)
        self.proxy_port = proxy_port or getattr(settings, 'residential_proxy_port', None)
        self.proxy_username = proxy_username or getattr(settings, 'residential_proxy_username', None)
        self.proxy_password = proxy_password or getattr(settings, 'residential_proxy_password', None)

        self._proxy_config = self._build_proxy_config()

    def _build_proxy_config(self) -> Optional[dict[str, Any]]:
        """Build proxy configuration dict for Camoufox."""
        if not self.proxy_host or not self.proxy_port:
            return None

        config = {
            "server": f"http://{self.proxy_host}:{self.proxy_port}",
        }

        if self.proxy_username and self.proxy_password:
            config["username"] = self.proxy_username
            config["password"] = self.proxy_password

        return config

    @property
    def is_configured(self) -> bool:
        """Check if Camoufox is properly configured with proxy."""
        return self._proxy_config is not None

    async def scrape(
        self,
        url: str,
        wait_for_cloudflare: bool = True,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> CamoufoxScrapeResult:
        """
        Scrape a protected website using Camoufox.

        Steps:
        1. Launch anti-detect Firefox browser
        2. Navigate to URL
        3. Wait for Cloudflare challenge if detected
        4. Extract page content

        Args:
            url: URL to scrape
            wait_for_cloudflare: Whether to wait for Cloudflare challenges
            timeout_ms: Navigation timeout in milliseconds

        Returns:
            CamoufoxScrapeResult with scraped content or failure info
        """
        logger.info(f"Tier 3: Starting Camoufox scrape for {url}")

        # Check if camoufox is available
        try:
            from camoufox.async_api import AsyncCamoufox
        except ImportError:
            logger.warning("Camoufox not installed - Tier 3 unavailable")
            return CamoufoxScrapeResult(
                url=url,
                raw_html="",
                tier_used=3,
                needs_fallback=True,
                failure_reason="Camoufox not installed. Install with: pip install camoufox[geoip]",
            )

        if not self.is_configured:
            logger.warning("Camoufox proxy not configured - attempting without proxy")

        try:
            async with AsyncCamoufox(
                headless=True,
                proxy=self._proxy_config,
            ) as browser:
                page = await browser.new_page()

                try:
                    # Navigate with extended timeout for challenges
                    logger.debug(f"Navigating to {url}")
                    await page.goto(
                        url,
                        wait_until="networkidle",
                        timeout=timeout_ms,
                    )

                    # Wait for potential Cloudflare challenge
                    if wait_for_cloudflare:
                        await self._wait_for_cloudflare(page)

                    # Extract content
                    html = await page.content()
                    title = await page.title()

                    # Validate we got real content
                    if len(html) < 500:
                        logger.warning(f"Camoufox got short content ({len(html)} chars)")
                        return CamoufoxScrapeResult(
                            url=url,
                            raw_html=html,
                            title=title,
                            tier_used=3,
                            needs_fallback=True,
                            failure_reason=f"Content too short ({len(html)} chars)",
                        )

                    if self._is_blocked_page(html):
                        logger.warning(f"Camoufox detected blocked page for {url}")
                        return CamoufoxScrapeResult(
                            url=url,
                            raw_html=html,
                            title=title,
                            tier_used=3,
                            needs_fallback=True,
                            failure_reason="Blocked page detected",
                        )

                    logger.info(f"Tier 3 success for {url}: {len(html)} chars")
                    return CamoufoxScrapeResult(
                        url=url,
                        raw_html=html,
                        title=title,
                        page_count=1,
                        tier_used=3,
                        needs_fallback=False,
                    )

                except asyncio.TimeoutError:
                    logger.warning(f"Camoufox timeout for {url}")
                    return CamoufoxScrapeResult(
                        url=url,
                        tier_used=3,
                        needs_fallback=True,
                        failure_reason=f"Navigation timeout ({timeout_ms}ms)",
                    )
                except Exception as e:
                    logger.error(f"Camoufox page error for {url}: {e}")
                    return CamoufoxScrapeResult(
                        url=url,
                        tier_used=3,
                        needs_fallback=True,
                        failure_reason=f"Page error: {str(e)}",
                    )

        except Exception as e:
            logger.error(f"Camoufox browser error: {e}")
            return CamoufoxScrapeResult(
                url=url,
                tier_used=3,
                needs_fallback=True,
                failure_reason=f"Browser error: {str(e)}",
            )

    async def _wait_for_cloudflare(
        self,
        page: Any,
        max_wait_ms: int = CLOUDFLARE_WAIT_MS,
    ) -> None:
        """
        Wait for Cloudflare challenge to complete.

        Detects common Cloudflare challenge selectors and waits
        for them to disappear before proceeding.

        Args:
            page: Playwright page object
            max_wait_ms: Maximum time to wait for challenge
        """
        cloudflare_selectors = [
            "#challenge-running",
            "#challenge-stage",
            ".cf-browser-verification",
            "#cf-challenge-running",
            ".cf-im-under-attack",
            "#trk_jschal_js",
        ]

        for selector in cloudflare_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    logger.debug(f"Cloudflare challenge detected: {selector}")
                    # Wait for challenge to disappear
                    await page.wait_for_selector(
                        selector,
                        state="hidden",
                        timeout=max_wait_ms,
                    )
                    # Extra wait for page load after challenge
                    await page.wait_for_timeout(2000)
                    logger.debug("Cloudflare challenge completed")
                    return
            except Exception:
                # Selector not found or timeout - continue
                pass

    def _is_blocked_page(self, html: str) -> bool:
        """
        Detect if we received a blocked/error page.

        Args:
            html: Page HTML content

        Returns:
            True if page appears to be blocked
        """
        if not html:
            return True

        html_lower = html.lower()

        # Count blocked indicators
        matches = sum(
            1 for indicator in BLOCKED_INDICATORS
            if indicator in html_lower
        )

        # Multiple indicators = likely blocked
        return matches >= 2


# Singleton instance
_camoufox_scraper: Optional[CamoufoxScraper] = None


def get_camoufox_scraper() -> CamoufoxScraper:
    """Get or create Camoufox scraper instance."""
    global _camoufox_scraper
    if _camoufox_scraper is None:
        _camoufox_scraper = CamoufoxScraper()
    return _camoufox_scraper


def is_camoufox_available() -> bool:
    """
    Check if Camoufox is installed and available.

    Returns:
        True if camoufox package is installed
    """
    try:
        import camoufox  # noqa: F401
        return True
    except ImportError:
        return False


def is_camoufox_configured() -> bool:
    """
    Check if Camoufox is configured with proxy.

    Returns:
        True if proxy settings are configured
    """
    scraper = get_camoufox_scraper()
    return scraper.is_configured
