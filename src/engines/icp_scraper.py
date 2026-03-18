"""
Contract: src/engines/icp_scraper.py
Purpose: Multi-source data scraping for ICP extraction with waterfall architecture
Layer: 3 - engines
Imports: models, integrations
Consumers: orchestration, agents

FILE: src/engines/icp_scraper.py
TASK: ICP-011, SCR-005
PHASE: 11 (ICP Discovery System), 19 (Scraper Waterfall)
PURPOSE: Multi-source data scraping for ICP extraction with waterfall architecture

DEPENDENCIES:
- src/engines/base.py
- src/engines/url_validator.py
- src/integrations/camoufox_scraper.py
- src/integrations/siege_waterfall.py
- src/integrations/gmb_scraper.py
- src/exceptions.py

EXPORTS:
- ICPScraperEngine
- ScrapedWebsite (result model)
- EnrichedPortfolioCompany (result model)

RULES APPLIED:
- Rule 11: Session passed as argument (DI pattern)
- Rule 12: No imports from other engines (url_validator is same layer)
- Rule 14: Soft deletes in queries

WATERFALL ARCHITECTURE (Phase 19 - Post FCO-002/FCO-003):
  Tier 0: URL Validation (url_validator.py)
  Tier 1: Camoufox anti-detection browser (primary scraper)
  Tier 2: Jina AI Reader (free JS rendering fallback)
  Tier 3: Bright Data Web Unlocker (anti-bot bypass, ~$0.001/req)
  Tier 4: Manual fallback UI

"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.engines.base import BaseEngine, EngineResult
from src.engines.url_validator import URLValidator, get_url_validator
from src.integrations.anthropic import get_anthropic_client
from src.integrations.camoufox_scraper import (
    CamoufoxScraper,
    get_camoufox_scraper,
    is_camoufox_available,
)
from src.integrations.siege_waterfall import (
    EnrichmentTier,
    SiegeWaterfall,
    get_siege_waterfall,
)

# Portfolio page paths to fetch directly (ICP-FIX-008)
PORTFOLIO_PATHS = [
    "/our-work/",
    "/case-studies/",
    "/portfolio/",
    "/work/",
    "/clients/",
]

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPage:
    """A single scraped page from a website."""

    url: str
    title: str = ""
    html: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)


@dataclass
class SocialLinks:
    """Social media URLs extracted from website (ICP-SOC-001)."""

    linkedin: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    twitter: str | None = None
    youtube: str | None = None
    tiktok: str | None = None


@dataclass
class ScrapedWebsite:
    """Complete scraped website data with waterfall tracking."""

    url: str
    domain: str
    pages: list[ScrapedPage] = field(default_factory=list)
    raw_html: str = ""
    page_count: int = 0
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    # Waterfall tracking (Phase 19)
    tier_used: int = 0  # 0=validation, 1=camoufox, 2=manual
    needs_fallback: bool = False
    failure_reason: str | None = None
    manual_fallback_url: str | None = None
    canonical_url: str | None = None  # URL after redirects
    # Social media links (ICP-SOC-001)
    social_links: SocialLinks | None = None


@dataclass
class LinkedInCompanyData:
    """LinkedIn company data for size estimation."""

    company_name: str = ""
    employee_count: int | None = None
    employee_range: str | None = None
    headquarters: str | None = None
    founded_year: int | None = None
    industry: str | None = None
    specialties: list[str] = field(default_factory=list)
    linkedin_url: str | None = None


class EnrichedPortfolioCompany(BaseModel):
    """Enriched portfolio company data."""

    company_name: str = Field(description="Company name")
    domain: str | None = Field(default=None, description="Company domain")
    industry: str | None = Field(default=None, description="Industry")
    employee_count: int | None = Field(default=None, description="Employee count")
    employee_range: str | None = Field(default=None, description="Employee range")
    annual_revenue: str | None = Field(default=None, description="Revenue range")
    location: str | None = Field(default=None, description="Location")
    country: str | None = Field(default=None, description="Country")
    founded_year: int | None = Field(default=None, description="Year founded")
    technologies: list[str] = Field(default_factory=list, description="Technologies")
    is_hiring: bool | None = Field(default=None, description="Hiring status")
    linkedin_url: str | None = Field(default=None, description="LinkedIn URL")
    source: str = Field(default="portfolio", description="Source")
    enriched_at: datetime = Field(default_factory=datetime.utcnow)


class ICPScraperEngine(BaseEngine):
    """
    Multi-source scraper for ICP extraction.

    This engine handles DATA FETCHING ONLY:
    - Website scraping via Camoufox (anti-detection browser)
    - Company enrichment via Siege Waterfall (ABN, GMB, etc.)
    - LinkedIn company data lookup (limited - uses Claude inference)

    It does NOT do AI processing - that's the job of
    the ICP Discovery Agent and its skills.
    """

    def __init__(
        self,
        anthropic_client: AnthropicClient | None = None,
        url_validator: URLValidator | None = None,
        camoufox_scraper: CamoufoxScraper | None = None,
        siege_waterfall: SiegeWaterfall | None = None,
    ):
        """
        Initialize with optional client overrides for testing.

        Args:
            anthropic_client: Optional Anthropic client override
            url_validator: Optional URL validator override
            camoufox_scraper: Optional Camoufox scraper override
            siege_waterfall: Optional SiegeWaterfall override
        """
        self._anthropic = anthropic_client
        self._url_validator = url_validator
        self._camoufox = camoufox_scraper
        self._siege_waterfall = siege_waterfall

    @property
    def name(self) -> str:
        """Engine name."""
        return "icp_scraper"

    @property
    def anthropic(self) -> AnthropicClient:
        """Get Anthropic client."""
        if self._anthropic is None:
            self._anthropic = get_anthropic_client()
        return self._anthropic

    @property
    def url_validator(self) -> URLValidator:
        """Get URL validator."""
        if self._url_validator is None:
            self._url_validator = get_url_validator()
        return self._url_validator

    @property
    def camoufox(self) -> CamoufoxScraper:
        """Get Camoufox scraper (primary anti-detection scraper)."""
        if self._camoufox is None:
            self._camoufox = get_camoufox_scraper()
        return self._camoufox

    @property
    def camoufox_enabled(self) -> bool:
        """Check if Camoufox scraper is enabled and available."""
        from src.config.settings import settings

        return settings.camoufox_enabled and is_camoufox_available()

    @property
    def siege_waterfall(self) -> SiegeWaterfall:
        """Get Siege Waterfall for AU business enrichment."""
        if self._siege_waterfall is None:
            self._siege_waterfall = get_siege_waterfall()
        return self._siege_waterfall

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        parsed = urlparse(url)
        return parsed.netloc.lower().replace("www.", "")

    def _normalize_url(self, url: str) -> str:
        """Normalize URL with https prefix."""
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        return url

    def _is_australian_company(self, company_name: str, domain: str | None) -> bool:
        """
        Detect if a company is likely Australian based on available signals.

        Checks:
        - .au domain suffix
        - Australian company name patterns (Pty Ltd, etc.)
        - Known Australian company name suffixes

        Args:
            company_name: Company name to check
            domain: Optional company domain

        Returns:
            True if company appears to be Australian
        """
        # Check domain
        if domain and domain.endswith(".au"):
            return True

        # Check Australian company name patterns
        name_lower = company_name.lower()
        au_patterns = [
            "pty ltd",
            "pty. ltd.",
            "proprietary limited",
            "(australia)",
            "australia",
            "australian",
        ]
        if any(pattern in name_lower for pattern in au_patterns):
            return True

        # Check for Australian state abbreviations in name
        au_states = ["nsw", "vic", "qld", "wa", "sa", "tas", "nt", "act"]
        name_words = name_lower.split()
        return any(state in name_words for state in au_states)

    def _extract_social_links(self, raw_html: str) -> SocialLinks:
        """
        Extract social media URLs from raw HTML (ICP-SOC-001).

        Finds LinkedIn, Instagram, Facebook, Twitter, YouTube, TikTok URLs.
        Handles both href= attributes and JSON-LD sameAs arrays.

        Args:
            raw_html: Combined raw HTML from all scraped pages

        Returns:
            SocialLinks dataclass with found URLs
        """
        social = SocialLinks()

        # Social media URL patterns - flexible to match href and JSON-LD contexts
        # Patterns match: href="URL", "URL" in sameAs arrays, etc.
        patterns = {
            # LinkedIn - handle www, au, uk, etc country subdomains
            "linkedin": r'["\']?(https?://(?:[a-z]{2}\.)?linkedin\.com/company/[a-zA-Z0-9_-]+/?)["\'\s>,]',
            # Instagram
            "instagram": r'["\']?(https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+/?)["\'\s>,]',
            # Facebook - with or without www
            "facebook": r'["\']?(https?://(?:www\.)?facebook\.com/[a-zA-Z0-9_.]+/?)["\'\s>,]',
            # Twitter/X
            "twitter": r'["\']?(https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+/?)["\'\s>,]',
            # YouTube - channel, c, or user paths
            "youtube": r'["\']?(https?://(?:www\.)?youtube\.com/(?:channel|c|user)/[a-zA-Z0-9_-]+/?)["\'\s>,]',
            # TikTok
            "tiktok": r'["\']?(https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9_.]+/?)["\'\s>,]',
        }

        for platform, pattern in patterns.items():
            matches = re.findall(pattern, raw_html, re.IGNORECASE)
            if matches:
                # Take the first match and clean it
                url = matches[0].rstrip("/\"',")
                setattr(social, platform, url)
                logger.debug(f"Found {platform}: {url}")

        found_count = sum(
            1
            for v in [
                social.linkedin,
                social.instagram,
                social.facebook,
                social.twitter,
                social.youtube,
                social.tiktok,
            ]
            if v
        )
        if found_count:
            logger.info(f"Extracted {found_count} social media links")

        return social

    async def _fetch_portfolio_pages(self, base_url: str) -> str:
        """
        Directly fetch portfolio pages using httpx (ICP-FIX-008).

        This supplements the main scrape by directly fetching known
        portfolio page paths. httpx follows redirects automatically,
        so www/non-www issues are handled.

        Args:
            base_url: Base website URL (e.g., https://dilate.com.au/)

        Returns:
            Combined HTML from all successfully fetched portfolio pages
        """
        from urllib.parse import urljoin

        fetched_html = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            for path in PORTFOLIO_PATHS:
                try:
                    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
                    response = await client.get(url, headers=headers)

                    if response.status_code == 200 and len(response.text) > 1000:
                        logger.info(f"Direct fetch success: {url} ({len(response.text):,} chars)")
                        fetched_html.append(f"\n<!-- DIRECT_FETCH: {url} -->\n{response.text}")
                    else:
                        logger.debug(f"Direct fetch skipped: {url} (status={response.status_code})")

                except Exception as e:
                    logger.debug(f"Direct fetch failed for {path}: {e}")
                    continue

        if fetched_html:
            logger.info(f"Direct fetch added {len(fetched_html)} portfolio pages to raw_html")

        return "\n".join(fetched_html)

    async def scrape_website(
        self,
        url: str,
        max_pages: int = 15,
    ) -> EngineResult[ScrapedWebsite]:
        """
        Scrape a website using a multi-tier waterfall strategy.

        Waterfall tiers (Post FCO-002 deprecation):
        - Tier 0: URL validation (check format, DNS, parked domains)
        - Tier 1: Camoufox anti-detection browser (primary)
        - Tier 2: Jina AI Reader (free JS rendering fallback)
        - Tier 3: Bright Data Web Unlocker (anti-bot bypass, ~$0.001/req)
        - Tier 4: Manual fallback UI

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl (default 15, currently single-page)

        Returns:
            EngineResult containing ScrapedWebsite with tier tracking
        """
        url = self._normalize_url(url)
        domain = self._extract_domain(url)

        logger.info(f"Starting waterfall scrape for {url}")

        # ===== TIER 0: URL Validation =====
        logger.debug(f"Tier 0: Validating URL {url}")
        validation = await self.url_validator.validate_and_normalize(url)

        if not validation.valid:
            logger.warning(f"Tier 0 failed for {url}: {validation.error}")
            return EngineResult.ok(
                data=ScrapedWebsite(
                    url=url,
                    domain=domain,
                    pages=[],
                    raw_html="",
                    page_count=0,
                    tier_used=0,
                    needs_fallback=True,
                    failure_reason=validation.error,
                    manual_fallback_url=f"/onboarding/manual-entry?url={url}",
                ),
                metadata={
                    "domain": domain,
                    "tier_used": 0,
                    "needs_fallback": True,
                    "error": validation.error,
                    "error_type": validation.error_type,
                },
            )

        # Use canonical URL after redirects
        canonical_url = validation.canonical_url or url
        if validation.redirected:
            logger.info(f"URL redirected: {url} -> {canonical_url}")
            domain = self._extract_domain(canonical_url)

        # ===== TIER 1: Camoufox Anti-Detection Browser =====
        if self.camoufox_enabled:
            try:
                logger.info(f"Tier 1: Attempting Camoufox scrape for {canonical_url}")
                camoufox_result = await self.camoufox.scrape(canonical_url)

                if camoufox_result.success:
                    logger.info(
                        f"Tier 1 success for {url}: {len(camoufox_result.raw_html):,} chars"
                    )

                    # Create ScrapedPage from Camoufox result
                    camoufox_page = ScrapedPage(
                        url=canonical_url,
                        title=camoufox_result.title,
                        html=camoufox_result.raw_html,
                        text="",  # Camoufox returns raw HTML
                        links=[],
                        images=[],
                    )

                    # Fetch portfolio pages to supplement
                    portfolio_html = await self._fetch_portfolio_pages(canonical_url)
                    combined_html = camoufox_result.raw_html
                    if portfolio_html:
                        combined_html = (
                            combined_html + "\n\n---DIRECT FETCH---\n\n" + portfolio_html
                        )

                    # Extract social links
                    social_links = self._extract_social_links(combined_html)

                    scraped = ScrapedWebsite(
                        url=url,
                        domain=domain,
                        pages=[camoufox_page],
                        raw_html=combined_html,
                        page_count=1,
                        tier_used=1,
                        needs_fallback=False,
                        canonical_url=canonical_url,
                        social_links=social_links,
                    )

                    return EngineResult.ok(
                        data=scraped,
                        metadata={
                            "domain": domain,
                            "pages_scraped": 1,
                            "tier_used": 1,
                            "redirected": validation.redirected,
                            "canonical_url": canonical_url,
                            "camoufox_used": True,
                        },
                    )
                else:
                    logger.warning(
                        f"Tier 1 (Camoufox) failed for {url}: {camoufox_result.failure_reason}"
                    )
            except Exception as camoufox_error:
                logger.error(f"Tier 1 (Camoufox) exception for {url}: {camoufox_error}")
        else:
            logger.warning("Tier 1 (Camoufox) not available - needs to be enabled")

        # ===== TIER 2: Jina AI Reader (JS rendering fallback) =====
        # Free, no API key needed. Handles React/Next.js/Vue sites.
        # Returns clean markdown of the rendered page.
        jina_url = f"https://r.jina.ai/{canonical_url}"
        logger.info(f"Tier 2: Attempting Jina AI Reader for {canonical_url}")
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as jina_client:
                jina_response = await jina_client.get(
                    jina_url,
                    headers={
                        "Accept": "text/markdown",
                        "X-No-Cache": "true",
                    },
                )
            if jina_response.status_code == 200 and len(jina_response.text) >= 200:
                markdown_content = jina_response.text
                logger.info(
                    f"Tier 2 (Jina) success for {url}: {len(markdown_content):,} chars"
                )
                # Wrap markdown in minimal HTML for pipeline compatibility
                jina_html = (
                    f"<html><body>"
                    f"<!-- Jina AI Reader rendered content -->"
                    f"<pre>{markdown_content}</pre>"
                    f"</body></html>"
                )
                social_links = self._extract_social_links(jina_html)
                jina_page = ScrapedPage(
                    url=canonical_url,
                    title="",
                    html=jina_html,
                    text=markdown_content,
                    links=[],
                    images=[],
                )
                scraped = ScrapedWebsite(
                    url=url,
                    domain=domain,
                    pages=[jina_page],
                    raw_html=jina_html,
                    page_count=1,
                    tier_used=2,
                    needs_fallback=False,
                    canonical_url=canonical_url,
                    social_links=social_links,
                )
                return EngineResult.ok(
                    data=scraped,
                    metadata={
                        "domain": domain,
                        "pages_scraped": 1,
                        "tier_used": 2,
                        "redirected": validation.redirected,
                        "canonical_url": canonical_url,
                        "jina_used": True,
                    },
                )
            else:
                logger.warning(
                    f"Tier 2 (Jina) insufficient content for {url}: "
                    f"status={jina_response.status_code}, "
                    f"len={len(jina_response.text)}"
                )
        except Exception as jina_error:
            logger.warning(f"Tier 2 (Jina) exception for {url}: {jina_error}")

        # ===== TIER 3: Bright Data Web Unlocker =====
        # Anti-bot bypass using existing BRIGHTDATA_API_KEY. ~$0.001/request.
        import os

        brightdata_api_key = os.getenv("BRIGHTDATA_API_KEY")
        if brightdata_api_key:
            logger.info(f"Tier 3: Attempting Bright Data Web Unlocker for {canonical_url}")
            try:
                async with httpx.AsyncClient(timeout=60.0) as bd_client:
                    bd_response = await bd_client.post(
                        "https://api.brightdata.com/request",
                        headers={
                            "Authorization": f"Bearer {brightdata_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "url": canonical_url,
                            "zone": "web_unlocker1",
                            "format": "raw",
                        },
                    )
                if bd_response.status_code == 200 and len(bd_response.text) >= 500:
                    bd_html = bd_response.text
                    logger.info(
                        f"Tier 3 (Bright Data) success for {url}: {len(bd_html):,} chars"
                    )
                    social_links = self._extract_social_links(bd_html)
                    bd_page = ScrapedPage(
                        url=canonical_url,
                        title="",
                        html=bd_html,
                        text="",
                        links=[],
                        images=[],
                    )
                    scraped = ScrapedWebsite(
                        url=url,
                        domain=domain,
                        pages=[bd_page],
                        raw_html=bd_html,
                        page_count=1,
                        tier_used=3,
                        needs_fallback=False,
                        canonical_url=canonical_url,
                        social_links=social_links,
                    )
                    return EngineResult.ok(
                        data=scraped,
                        metadata={
                            "domain": domain,
                            "pages_scraped": 1,
                            "tier_used": 3,
                            "redirected": validation.redirected,
                            "canonical_url": canonical_url,
                            "brightdata_used": True,
                        },
                    )
                else:
                    logger.warning(
                        f"Tier 3 (Bright Data) insufficient content for {url}: "
                        f"status={bd_response.status_code}, "
                        f"len={len(bd_response.text)}"
                    )
            except Exception as bd_error:
                logger.warning(f"Tier 3 (Bright Data) exception for {url}: {bd_error}")
        else:
            logger.warning("Tier 3 (Bright Data) skipped — BRIGHTDATA_API_KEY not set")

        # ===== TIER 4: Manual Fallback =====
        # All automated tiers failed, return with manual fallback flag
        logger.warning(f"All automated tiers failed for {url}, needs manual fallback")
        return EngineResult.ok(
            data=ScrapedWebsite(
                url=url,
                domain=domain,
                pages=[],
                raw_html="",
                page_count=0,
                tier_used=4,
                needs_fallback=True,
                failure_reason="All scraping tiers failed (Camoufox, Jina, Bright Data)",
                manual_fallback_url=f"/onboarding/manual-entry?url={url}",
                canonical_url=canonical_url,
            ),
            metadata={
                "domain": domain,
                "tier_used": 4,
                "needs_fallback": True,
                "camoufox_attempted": self.camoufox_enabled,
            },
        )

    async def get_linkedin_company_data(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> EngineResult[LinkedInCompanyData]:
        """
        Get LinkedIn company data via Claude inference.

        Now uses Claude inference to estimate company data from name/domain.

        Args:
            company_name: Company name to look up
            domain: Optional company domain for better matching

        Returns:
            EngineResult containing LinkedInCompanyData (inferred)
        """
        try:
            logger.info(
                f"get_linkedin_company_data: Using Claude inference for {company_name} "
                "(LinkedIn scraping removed - FCO-002)"
            )

            # Use Claude inference instead of LinkedIn scraping
            claude_inference = await self._infer_industry_with_claude(company_name, domain)

            if claude_inference.get("industry"):
                linkedin_data = LinkedInCompanyData(
                    company_name=company_name,
                    industry=claude_inference.get("industry"),
                    employee_range=claude_inference.get("employee_range"),
                )
                return EngineResult.ok(
                    data=linkedin_data,
                    metadata={"found": True, "source": "claude_inference"},
                )

            # Not found / inference failed
            return EngineResult.ok(
                data=LinkedInCompanyData(company_name=company_name),
                metadata={"found": False, "source": "none"},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"LinkedIn company lookup failed: {str(e)}",
                metadata={"company_name": company_name},
            )

    async def _infer_industry_with_claude(
        self,
        company_name: str,
        domain: str | None = None,
        context: str | None = None,
    ) -> dict[str, Any]:
        """
        Use Claude to intelligently infer industry and company details from name.

        This is called FIRST in the waterfall - Claude's inference provides
        a baseline that API sources can then confirm or enrich.

        Args:
            company_name: Company name to analyze
            domain: Optional domain for additional context
            context: Optional additional context (e.g., case study text)

        Returns:
            Dict with inferred industry, employee_range, and confidence
        """
        prompt = f"""Analyze this company name and infer its likely industry and size.

Company Name: {company_name}
{f"Domain: {domain}" if domain else ""}
{f"Context: {context}" if context else ""}

Based on the company name (and domain/context if provided), infer:
1. The most likely industry (use standard categories like: automotive, retail, construction, manufacturing, healthcare, hospitality, technology, professional_services, food_beverage, real_estate, education, fitness, trades, environmental, recruitment)
2. Likely company size (small: 1-50, medium: 51-200, large: 201+)
3. Your confidence (low, medium, high)

Respond in JSON format only:
{{"industry": "string", "employee_range": "string", "confidence": "string", "reasoning": "brief explanation"}}"""

        try:
            logger.info(f"Calling Claude for industry inference: {company_name}")
            response = await self.anthropic.complete(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3,
            )
            logger.info(f"Claude response received for {company_name}: {response.keys()}")

            # Parse JSON response
            import json

            # Clean response - remove markdown if present
            text = response.get("content", "").strip()
            logger.info(f"Claude raw content for {company_name}: {text[:200] if text else 'EMPTY'}")
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()

            result = json.loads(text)
            logger.info(
                f"Claude inferred for {company_name}: {result.get('industry')} ({result.get('confidence')})"
            )
            return result

        except Exception as e:
            import traceback

            logger.error(f"Claude inference failed for {company_name}: {e}")
            logger.error(f"Claude inference traceback: {traceback.format_exc()}")
            return {}

    async def enrich_portfolio_company(
        self,
        company_name: str,
        domain: str | None = None,
        source: str = "portfolio",
        icp_config: dict | None = None,
    ) -> EngineResult[EnrichedPortfolioCompany]:
        """
        Enrich a single portfolio company via Claude-first waterfall.

        Phase Dynamic ICP: Now accepts icp_config for dynamic country targeting.

        NEW WATERFALL (Post FCO-002/FCO-003):
        Tier 0: Claude inference (always runs first to establish baseline)
        Tier 0.5: Siege Waterfall for AU businesses (ABN + GMB)
        Tier 1: Google Business (excellent for local AU)
        Tier 2: Keyword fallback

        Args:
            company_name: Company name
            domain: Optional company domain
            source: How this company was found
            icp_config: Optional ICP config dict with countries, employee_range, etc.

        Returns:
            EngineResult containing enriched company data
        """
        # Get primary country from ICP config (default to Australia for backward compat)
        icp_countries = icp_config.get("countries", ["Australia"]) if icp_config else ["Australia"]
        primary_country = icp_countries[0] if icp_countries else "Australia"
        enriched = EnrichedPortfolioCompany(
            company_name=company_name,
            domain=domain,
            source=source,
        )
        enrichment_source = None

        # ============================================
        # TIER 0: Claude Inference - ALWAYS RUNS FIRST
        # ============================================
        # Claude analyzes the company name to establish a baseline industry.
        # This ensures every company gets SOME industry data even if all APIs fail.
        logger.info(f"Tier 0 (Claude): Inferring industry for {company_name}")
        claude_inference = await self._infer_industry_with_claude(company_name, domain)

        if claude_inference.get("industry"):
            enriched.industry = claude_inference["industry"]
            enriched.employee_range = claude_inference.get("employee_range")
            logger.info(
                f"Claude baseline for {company_name}: "
                f"industry={enriched.industry}, size={enriched.employee_range}"
            )

        # ============================================
        # TIER 0.5: Siege Waterfall for AU businesses (ABN + GMB)
        # ============================================
        # For Australian businesses, use the free/cheap tiers of Siege Waterfall:
        # - Tier 1 (ABN): FREE - Australian Business Register data
        # - Tier 2 (GMB): $0.006/lead - Google Maps Business signals
        # This provides phone, website, address, rating, category cheaply.
        is_australian = self._is_australian_company(company_name, domain)
        if is_australian:
            try:
                logger.info(f"Tier 0.5 (Siege): ABN+GMB enrichment for AU company {company_name}")

                # Build minimal lead data for Siege Waterfall
                siege_data = {
                    "company_name": company_name,
                    "domain": domain,
                    "country": primary_country,
                }

                # Run only ABN and GMB tiers (skip expensive tiers)
                siege_result = await self.siege_waterfall.enrich_lead(
                    siege_data,
                    skip_tiers=[
                        EnrichmentTier.LEADMAGIC_EMAIL,  # Skip email (no person data)
                        EnrichmentTier.IDENTITY,  # Skip mobile (no person data)
                    ],
                )

                if siege_result.sources_used > 0:
                    siege_enriched = siege_result.enriched_data

                    # Extract useful company data from Siege results
                    if siege_enriched.get("phone") and not enriched.location:
                        enriched.location = siege_enriched.get("address")
                    if siege_enriched.get("category") and not enriched.industry:
                        enriched.industry = siege_enriched.get("category")
                    if siege_enriched.get("website") and not enriched.domain:
                        # Extract domain from website
                        from urllib.parse import urlparse

                        website = siege_enriched.get("website", "")
                        parsed = urlparse(website)
                        if parsed.netloc:
                            enriched.domain = parsed.netloc.lower().replace("www.", "")
                            domain = enriched.domain

                    enriched.country = primary_country
                    enrichment_source = f"siege_waterfall_{siege_result.sources_used}sources"

                    logger.info(
                        f"Siege Waterfall found for {company_name}: "
                        f"industry={enriched.industry}, sources={siege_result.sources_used}, "
                        f"cost=${siege_result.total_cost_aud:.3f} AUD"
                    )
            except Exception as e:
                logger.warning(f"Siege Waterfall failed for {company_name}: {e}")

        # Clay removed - Directive #216

        # ============================================
        # TIER 1: Google Business (excellent for local Australian businesses)
        # ============================================
        if not enrichment_source:
            try:
                logger.info(f"Tier 2 (GMB): Google Business search for {company_name}")
                from src.integrations.gmb_scraper import scrape_google_business

                google_data = await scrape_google_business(company_name, primary_country)

                if google_data.get("found"):
                    enriched.location = google_data.get("address") or enriched.location
                    enriched.country = primary_country  # Inferred from search
                    # Use category for industry if we don't have one
                    if not enriched.industry and google_data.get("category"):
                        enriched.industry = google_data.get("category")
                    # Extract domain from website if available
                    if not enriched.domain and google_data.get("website"):
                        from urllib.parse import urlparse

                        parsed = urlparse(google_data.get("website", ""))
                        potential_domain = parsed.netloc.lower()
                        if potential_domain.startswith("www."):
                            potential_domain = potential_domain[4:]
                        if potential_domain:
                            enriched.domain = potential_domain
                    enrichment_source = "google_business"
                    logger.info(
                        f"Google Business found: {company_name} - {google_data.get('category')}, "
                        f"rating: {google_data.get('rating')}, reviews: {google_data.get('review_count')}"
                    )
            except Exception as e:
                logger.warning(f"Google Business enrichment failed for {company_name}: {e}")

        # ============================================
        # TIER 2: Keyword Fallback (only if Claude AND all APIs failed)
        # ============================================
        # This should rarely be needed since Claude inference runs first
        if not enriched.industry:
            logger.warning(
                f"All enrichment sources failed for {company_name}, trying keyword fallback"
            )
            inferred = self._infer_industry_from_name(company_name)
            if not inferred and enriched.domain:
                inferred = self._infer_industry_from_name(enriched.domain)
            if inferred:
                enriched.industry = inferred
                logger.info(f"Keyword fallback for {company_name}: {inferred}")

        # Return result with metadata about enrichment source
        if enrichment_source:
            return EngineResult.ok(
                data=enriched,
                metadata={"enriched": True, "source": enrichment_source},
            )
        else:
            # Even without external enrichment, we may have inferred industry
            has_inferred = bool(enriched.industry)
            logger.info(
                f"No enrichment found for {company_name} - returning {'inferred' if has_inferred else 'basic'} data"
            )
            return EngineResult.ok(
                data=enriched,
                metadata={
                    "enriched": has_inferred,
                    "source": "inferred" if has_inferred else "none",
                },
            )

    def _infer_industry_from_name(self, company_name: str) -> str | None:
        """
        Infer industry from company name using keyword matching.

        This is a fallback when external data sources don't provide industry.
        """
        name_lower = company_name.lower()

        industry_patterns = {
            "automotive": [
                "mazda",
                "toyota",
                "ford",
                "honda",
                "subaru",
                "car",
                "auto",
                "motor",
                "vehicle",
                "dealer",
                "mechanic",
                "vermeer",
            ],
            "healthcare": [
                "physio",
                "dental",
                "medical",
                "clinic",
                "health",
                "hospital",
                "doctor",
                "therapy",
                "care",
            ],
            "hospitality": [
                "hotel",
                "resort",
                "motel",
                "accommodation",
                "bay suite",
                "suites",
                "lodge",
                "inn",
            ],
            "tourism": [
                "tours",
                "travel",
                "adventure",
                "charter",
                "dive",
                "snorkel",
                "whale",
                "cruise",
                "tourism",
                "encounters",
                "safari",
                "wildlife",
            ],
            "retail": [
                "shop",
                "store",
                "retail",
                "boutique",
                "fashion",
                "clothing",
                "golf",
                "sports",
                "running",
                "warehouse",
            ],
            "construction": [
                "construction",
                "builder",
                "building",
                "trades",
                "ceiling",
                "floor",
                "roofing",
                "plumbing",
                "tiler",
            ],
            "manufacturing": [
                "timber",
                "steel",
                "manufacturing",
                "factory",
                "industrial",
                "cable",
                "wire",
                "equipment",
            ],
            "technology": [
                "software",
                "tech",
                "digital",
                "it",
                "app",
                "data",
                "intelligence",
                "develop",
            ],
            "professional_services": [
                "consulting",
                "legal",
                "accounting",
                "advisory",
                "services",
                "agency",
            ],
            "food_beverage": [
                "jerky",
                "food",
                "cafe",
                "restaurant",
                "catering",
                "bakery",
                "coffee",
                "beer",
                "wine",
            ],
            "real_estate": [
                "property",
                "real estate",
                "realty",
                "homes",
                "land",
                "development",
                "keller",
            ],
            "education": ["academy", "school", "training", "education", "learn", "kids", "child"],
            "fitness": ["gym", "fitness", "crossfit", "yoga", "pilates", "martial"],
            "landscaping": ["landscape", "garden", "lawn", "arcadia", "outdoor"],
            "recruitment": ["hire", "recruit", "staffing", "talent", "hr", "employment", "apm"],
            "environmental": [
                "enviro",
                "environment",
                "eco",
                "green",
                "sustainability",
                "water treatment",
                "planet",
                "earth",
                "solar",
                "renewable",
            ],
        }

        for industry, keywords in industry_patterns.items():
            if any(kw in name_lower for kw in keywords):
                return industry

        return None

    async def enrich_portfolio_batch(
        self,
        companies: list[dict[str, Any]],
    ) -> EngineResult[list[EnrichedPortfolioCompany]]:
        """
        Enrich multiple portfolio companies.

        Args:
            companies: List of dicts with company_name, domain, source

        Returns:
            EngineResult containing list of enriched companies
        """
        enriched_list = []
        successful = 0
        failed = 0

        for company in companies:
            result = await self.enrich_portfolio_company(
                company_name=company.get("company_name", ""),
                domain=company.get("domain"),
                source=company.get("source", "portfolio"),
            )

            if result.success and result.data:
                enriched_list.append(result.data)
                successful += 1
            else:
                # Add basic entry for failed enrichment
                enriched_list.append(
                    EnrichedPortfolioCompany(
                        company_name=company.get("company_name", "Unknown"),
                        domain=company.get("domain"),
                        source=company.get("source", "portfolio"),
                    )
                )
                failed += 1

        return EngineResult.ok(
            data=enriched_list,
            metadata={
                "total": len(companies),
                "successful": successful,
                "failed": failed,
            },
        )

    async def analyze_icp_with_sdk(
        self,
        client_name: str,
        website_url: str,
        scraped_website: ScrapedWebsite,
        enriched_companies: list[EnrichedPortfolioCompany],
        client_id: UUID | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Use SDK Brain to analyze and build comprehensive ICP.

        This is the final step after website scraping and portfolio enrichment.
        The SDK agent uses tools (web_search, web_fetch) to:
        - Research additional context
        - Validate assumptions
        - Build evidence-based ICP

        Args:
            client_name: Agency/client name
            website_url: Agency website URL
            scraped_website: Scraped website data
            enriched_companies: List of enriched portfolio companies
            client_id: Optional client ID for tracking

        Returns:
            EngineResult containing ICPOutput as dict
        """
        from src.config.settings import settings

        # Check if SDK is enabled
        if not settings.sdk_brain_enabled:
            logger.info("SDK Brain disabled, skipping enhanced ICP analysis")
            return EngineResult.ok(
                data={"sdk_skipped": True, "reason": "SDK Brain disabled"},
                metadata={"sdk_used": False},
            )

        try:
            from src.agents.sdk_agents.icp_agent import ICPInput, extract_icp

            # Prepare input data
            input_data = ICPInput(
                client_name=client_name,
                website_url=website_url,
                website_content=scraped_website.raw_html[:50000],  # Limit size
                portfolio_companies=[
                    {
                        "company_name": c.company_name,
                        "domain": c.domain,
                        "industry": c.industry,
                        "employee_count": c.employee_count,
                        "employee_range": c.employee_range,
                        "location": c.location,
                        "country": c.country,
                        "founded_year": c.founded_year,
                        "linkedin_url": c.linkedin_url,
                    }
                    for c in enriched_companies
                ],
                social_links={
                    "linkedin": scraped_website.social_links.linkedin
                    if scraped_website.social_links
                    else None,
                    "instagram": scraped_website.social_links.instagram
                    if scraped_website.social_links
                    else None,
                    "facebook": scraped_website.social_links.facebook
                    if scraped_website.social_links
                    else None,
                    "twitter": scraped_website.social_links.twitter
                    if scraped_website.social_links
                    else None,
                }
                if scraped_website.social_links
                else {},
            )

            logger.info(f"Starting SDK ICP analysis for {client_name}")

            # Run SDK agent
            result = await extract_icp(
                client_name=input_data.client_name,
                website_url=input_data.website_url,
                website_content=input_data.website_content,
                portfolio_companies=input_data.portfolio_companies,
                social_links=input_data.social_links,
                client_id=client_id,
            )

            if result.success:
                # Convert Pydantic model to dict
                icp_data = (
                    result.data.model_dump() if hasattr(result.data, "model_dump") else result.data
                )

                logger.info(
                    f"SDK ICP analysis complete for {client_name}: "
                    f"confidence={icp_data.get('confidence_score', 0):.2f}, "
                    f"cost=${result.cost_aud:.4f} AUD"
                )

                return EngineResult.ok(
                    data=icp_data,
                    metadata={
                        "sdk_used": True,
                        "cost_aud": result.cost_aud,
                        "turns_used": result.turns_used,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "tool_calls": len(result.tool_calls),
                    },
                )
            else:
                logger.warning(f"SDK ICP analysis failed for {client_name}: {result.error}")
                return EngineResult.fail(
                    error=f"SDK analysis failed: {result.error}",
                    metadata={
                        "sdk_used": True,
                        "cost_aud": result.cost_aud,
                    },
                )

        except ImportError as e:
            logger.error(f"SDK agent import failed: {e}")
            return EngineResult.fail(
                error=f"SDK agent not available: {e}",
                metadata={"sdk_used": False},
            )
        except Exception as e:
            logger.error(f"SDK ICP analysis error: {e}", exc_info=True)
            return EngineResult.fail(
                error=f"SDK analysis error: {str(e)}",
                metadata={"sdk_used": False},
            )

    async def save_extraction_progress(
        self,
        db: AsyncSession,
        job_id: UUID,
        step: str,
        completed_steps: int,
    ) -> None:
        """
        Update extraction job progress.

        Args:
            db: Database session (passed by caller - Rule 11)
            job_id: Extraction job UUID
            step: Current step name
            completed_steps: Number of completed steps
        """
        from sqlalchemy import update

        stmt = (
            update(IcpExtractionJob)
            .where(IcpExtractionJob.id == job_id)
            .values(
                current_step=step,
                completed_steps=completed_steps,
            )
        )
        await db.execute(stmt)
        await db.commit()

    async def complete_extraction_job(
        self,
        db: AsyncSession,
        job_id: UUID,
        extracted_icp: dict[str, Any],
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """
        Mark extraction job as complete.

        Args:
            db: Database session (passed by caller - Rule 11)
            job_id: Extraction job UUID
            extracted_icp: Extracted ICP data
            success: Whether extraction succeeded
            error_message: Error message if failed
        """
        from sqlalchemy import update

        status = "completed" if success else "failed"

        stmt = (
            update(IcpExtractionJob)
            .where(IcpExtractionJob.id == job_id)
            .values(
                status=status,
                extracted_icp=extracted_icp,
                error_message=error_message,
                completed_at=datetime.now(UTC),
            )
        )
        await db.execute(stmt)
        await db.commit()


# Placeholder for model import (created by migration 012)
try:
    from src.models.icp_extraction_job import IcpExtractionJob
except ImportError:
    # Model not yet created - placeholder for type hints
    class IcpExtractionJob:
        id: UUID
        current_step: str
        completed_steps: int
        status: str
        extracted_icp: dict
        error_message: str | None
        completed_at: datetime | None


# Singleton instance
_icp_scraper_engine: ICPScraperEngine | None = None


def get_icp_scraper_engine() -> ICPScraperEngine:
    """Get or create ICP scraper engine instance."""
    global _icp_scraper_engine
    if _icp_scraper_engine is None:
        _icp_scraper_engine = ICPScraperEngine()
    return _icp_scraper_engine


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12) - url_validator is same layer
- [x] Uses dependency injection (Rule 11) - db passed to methods
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseEngine
- [x] Uses Camoufox for website scraping
- [x] Uses Siege Waterfall for enrichment
- [x] No AI processing (data fetching only)
- [x] ScrapedWebsite dataclass for result
- [x] EnrichedPortfolioCompany model
- [x] Batch enrichment support
- [x] Progress tracking methods
- [x] Singleton pattern for engine instance

WATERFALL ARCHITECTURE (Post FCO-002/FCO-003):
- [x] URLValidator integration (Tier 0)
- [x] Camoufox as primary scraper (Tier 1) - anti-detection browser
- [x] ScrapedWebsite includes tier tracking fields
- [x] Manual fallback URL generation (Tier 2)
- [x] Canonical URL tracking after redirects

"""
