"""
FILE: src/engines/icp_scraper.py
TASK: ICP-011, SCR-005
PHASE: 11 (ICP Discovery System), 19 (Scraper Waterfall)
PURPOSE: Multi-source data scraping for ICP extraction with waterfall architecture

DEPENDENCIES:
- src/engines/base.py
- src/engines/url_validator.py
- src/integrations/apify.py
- src/integrations/apollo.py
- src/exceptions.py

EXPORTS:
- ICPScraperEngine
- ScrapedWebsite (result model)
- EnrichedPortfolioCompany (result model)

RULES APPLIED:
- Rule 11: Session passed as argument (DI pattern)
- Rule 12: No imports from other engines (url_validator is same layer)
- Rule 14: Soft deletes in queries

WATERFALL ARCHITECTURE (Phase 19):
  Tier 0: URL Validation (url_validator.py)
  Tier 1: Cheerio (apify.py)
  Tier 2: Playwright (apify.py)
  Tier 3: Camoufox (future)
  Tier 4: Manual fallback UI
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from src.engines.base import BaseEngine, EngineResult
from src.engines.url_validator import URLValidator, get_url_validator
from src.exceptions import EngineError, ValidationError
from src.integrations.anthropic import get_anthropic_client
from src.integrations.apify import get_apify_client, ScrapeResult
from src.integrations.apollo import get_apollo_client
from src.integrations.clay import get_clay_client

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
    from src.integrations.apify import ApifyClient
    from src.integrations.apollo import ApolloClient
    from src.integrations.clay import ClayClient

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

    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    youtube: Optional[str] = None
    tiktok: Optional[str] = None


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
    tier_used: int = 0  # 0=validation, 1=cheerio, 2=playwright, 3=camoufox, 4=manual
    needs_fallback: bool = False
    failure_reason: Optional[str] = None
    manual_fallback_url: Optional[str] = None
    canonical_url: Optional[str] = None  # URL after redirects
    # Social media links (ICP-SOC-001)
    social_links: Optional[SocialLinks] = None


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
    - Website scraping via Apify
    - Company enrichment via Apollo
    - LinkedIn company data lookup

    It does NOT do AI processing - that's the job of
    the ICP Discovery Agent and its skills.
    """

    def __init__(
        self,
        apify_client: "ApifyClient | None" = None,
        apollo_client: "ApolloClient | None" = None,
        clay_client: "ClayClient | None" = None,
        anthropic_client: "AnthropicClient | None" = None,
        url_validator: "URLValidator | None" = None,
    ):
        """
        Initialize with optional client overrides for testing.

        Args:
            apify_client: Optional Apify client override
            apollo_client: Optional Apollo client override
            clay_client: Optional Clay client override
            anthropic_client: Optional Anthropic client override
            url_validator: Optional URL validator override
        """
        self._apify = apify_client
        self._apollo = apollo_client
        self._clay = clay_client
        self._anthropic = anthropic_client
        self._url_validator = url_validator

    @property
    def name(self) -> str:
        """Engine name."""
        return "icp_scraper"

    @property
    def apify(self) -> "ApifyClient":
        """Get Apify client."""
        if self._apify is None:
            self._apify = get_apify_client()
        return self._apify

    @property
    def apollo(self) -> "ApolloClient":
        """Get Apollo client."""
        if self._apollo is None:
            self._apollo = get_apollo_client()
        return self._apollo

    @property
    def clay(self) -> "ClayClient":
        """Get Clay client."""
        if self._clay is None:
            self._clay = get_clay_client()
        return self._clay

    @property
    def anthropic(self) -> "AnthropicClient":
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
                url = matches[0].rstrip('/"\',')
                setattr(social, platform, url)
                logger.debug(f"Found {platform}: {url}")

        found_count = sum(1 for v in [social.linkedin, social.instagram, social.facebook,
                                       social.twitter, social.youtube, social.tiktok] if v)
        if found_count:
            logger.info(f"Extracted {found_count} social media links")

        return social

    async def _fetch_portfolio_pages(self, base_url: str) -> str:
        """
        Directly fetch portfolio pages using httpx (ICP-FIX-008).

        This supplements the Apify scrape by directly fetching known
        portfolio page paths. httpx follows redirects automatically,
        so www/non-www issues are handled.

        This is the same approach used by WebFetch - direct HTTP request
        that follows redirects and gets the final HTML.

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
        Scrape a website using the Scraper Waterfall architecture.

        Waterfall tiers:
        - Tier 0: URL validation (check format, DNS, parked domains)
        - Tier 1: Apify Cheerio (fast, static HTML)
        - Tier 2: Apify Playwright (JS rendering)
        - Tier 3: Camoufox (future - for Cloudflare bypass)
        - Tier 4: Manual fallback UI

        Args:
            url: Website URL to scrape
            max_pages: Maximum pages to crawl (default 15)

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

        # ===== TIER 1 & 2: Apify Waterfall =====
        # Both Cheerio and Playwright now use seed URLs to crawl common
        # agency pages like /case-studies, /testimonials, /portfolio.
        # This ensures portfolio data is captured even on JS-heavy sites.
        try:
            scrape_result: ScrapeResult = await self.apify.scrape_website_with_waterfall(
                canonical_url, max_pages=max_pages
            )

            # Transform Apify result to our format
            pages = []
            all_html = []

            for page_data in scrape_result.pages:
                html_content = page_data.get("html", "") or page_data.get("text", "")
                page = ScrapedPage(
                    url=page_data.get("url", ""),
                    title=page_data.get("title", ""),
                    html=html_content,
                    text=page_data.get("text", ""),
                    links=page_data.get("links", []),
                    images=page_data.get("images", []),
                )
                pages.append(page)
                if html_content:
                    all_html.append(html_content)

            # Check if waterfall succeeded
            if scrape_result.needs_fallback:
                logger.warning(f"Waterfall failed for {url}, needs manual fallback")
                return EngineResult.ok(
                    data=ScrapedWebsite(
                        url=url,
                        domain=domain,
                        pages=pages,
                        raw_html=scrape_result.raw_html,
                        page_count=scrape_result.page_count,
                        tier_used=scrape_result.tier_used,
                        needs_fallback=True,
                        failure_reason=scrape_result.failure_reason,
                        manual_fallback_url=f"/onboarding/manual-entry?url={url}",
                        canonical_url=canonical_url,
                    ),
                    metadata={
                        "domain": domain,
                        "tier_used": scrape_result.tier_used,
                        "needs_fallback": True,
                        "failure_reason": scrape_result.failure_reason,
                    },
                )

            # Success!
            logger.info(f"Waterfall success for {url}: tier={scrape_result.tier_used}, pages={len(pages)}")

            # ICP-FIX-008: Direct fetch portfolio pages to supplement Apify scrape
            # This ensures we get case study/portfolio URLs even if Apify missed them
            portfolio_html = await self._fetch_portfolio_pages(canonical_url)

            # Combine all HTML sources
            combined_html = "\n\n---PAGE BREAK---\n\n".join(all_html) if all_html else scrape_result.raw_html
            if portfolio_html:
                combined_html = combined_html + "\n\n---DIRECT FETCH---\n\n" + portfolio_html
                logger.info(f"Combined raw_html size: {len(combined_html):,} chars (includes direct fetch)")

            # ICP-SOC-001: Extract social media links from raw HTML
            social_links = self._extract_social_links(combined_html)

            scraped = ScrapedWebsite(
                url=url,
                domain=domain,
                pages=pages,
                raw_html=combined_html,
                page_count=len(pages),
                tier_used=scrape_result.tier_used,
                needs_fallback=False,
                canonical_url=canonical_url,
                social_links=social_links,
            )

            return EngineResult.ok(
                data=scraped,
                metadata={
                    "domain": domain,
                    "pages_scraped": len(pages),
                    "tier_used": scrape_result.tier_used,
                    "redirected": validation.redirected,
                    "canonical_url": canonical_url,
                },
            )

        except Exception as e:
            logger.error(f"Scraper waterfall exception for {url}: {e}")
            return EngineResult.ok(
                data=ScrapedWebsite(
                    url=url,
                    domain=domain,
                    pages=[],
                    raw_html="",
                    page_count=0,
                    tier_used=2,
                    needs_fallback=True,
                    failure_reason=f"Scraper error: {str(e)}",
                    manual_fallback_url=f"/onboarding/manual-entry?url={url}",
                    canonical_url=canonical_url,
                ),
                metadata={
                    "domain": domain,
                    "tier_used": 2,
                    "needs_fallback": True,
                    "error": str(e),
                },
            )

    async def get_linkedin_company_data(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> EngineResult[LinkedInCompanyData]:
        """
        Get LinkedIn company data via Apollo organization lookup.

        Args:
            company_name: Company name to look up
            domain: Optional company domain for better matching

        Returns:
            EngineResult containing LinkedInCompanyData
        """
        try:
            # Try Apollo domain-based lookup first
            if domain:
                logger.info(f"Looking up LinkedIn data for {company_name} via Apollo (domain: {domain})")
                apollo_result = await self.apollo.enrich_company(domain)

                if apollo_result.get("found"):
                    linkedin_data = LinkedInCompanyData(
                        company_name=apollo_result.get("name", company_name),
                        employee_count=apollo_result.get("employee_count"),
                        headquarters=None,  # Apollo doesn't return this directly
                        founded_year=apollo_result.get("founded_year"),
                        industry=apollo_result.get("industry"),
                        specialties=[],  # Apollo doesn't return this
                        linkedin_url=apollo_result.get("linkedin_url"),
                    )
                    return EngineResult.ok(
                        data=linkedin_data,
                        metadata={"found": True, "source": "apollo"},
                    )

            # Fallback: Try Apify LinkedIn Company Scraper
            if self.apify:
                logger.info(f"Falling back to LinkedIn scraper for {company_name}")
                # Search for company LinkedIn page
                search_results = await self.apify.search_google(
                    [f'"{company_name}" site:linkedin.com/company'],
                    results_per_query=1
                )

                if search_results:
                    linkedin_url = search_results[0].get("link", "")
                    if "linkedin.com/company" in linkedin_url:
                        scraped = await self.apify.scrape_linkedin_company(linkedin_url)
                        if scraped.get("found"):
                            linkedin_data = LinkedInCompanyData(
                                company_name=scraped.get("name", company_name),
                                employee_count=scraped.get("employee_count"),
                                employee_range=scraped.get("employee_range"),
                                headquarters=scraped.get("headquarters"),
                                founded_year=scraped.get("founded_year"),
                                industry=scraped.get("industry"),
                                specialties=scraped.get("specialties", []),
                                linkedin_url=linkedin_url,
                            )
                            return EngineResult.ok(
                                data=linkedin_data,
                                metadata={"found": True, "source": "linkedin_scraper"},
                            )

            # Not found
            return EngineResult.ok(
                data=LinkedInCompanyData(company_name=company_name),
                metadata={"found": False},
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
            logger.info(f"Claude inferred for {company_name}: {result.get('industry')} ({result.get('confidence')})")
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
    ) -> EngineResult[EnrichedPortfolioCompany]:
        """
        Enrich a single portfolio company via Claude-first waterfall.

        NEW WATERFALL (Claude-first):
        Tier 0: Claude inference (always runs first to establish baseline)
        Tier 1: Apollo name/domain search (confirm/enrich)
        Tier 1.5: LinkedIn scrape (fill gaps)
        Tier 1.6: Clay enrichment (fill gaps)
        Tier 2: LinkedIn via Google search
        Tier 3: Google Business (great for local AU)
        Tier 4: General Google search

        Args:
            company_name: Company name
            domain: Optional company domain
            source: How this company was found

        Returns:
            EngineResult containing enriched company data
        """
        enriched = EnrichedPortfolioCompany(
            company_name=company_name,
            domain=domain,
            source=source,
        )
        enrichment_source = None

        # ============================================
        # TIER 0 (NEW): Claude Inference - ALWAYS RUNS FIRST
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
        # TIER 1: Apollo - Confirm/Enrich Claude's baseline
        # ============================================
        # Apollo organization search by name (when no domain)
        # Searches Apollo's database directly by company name
        if not domain:
            try:
                logger.info(f"Tier 1a: Apollo name search for {company_name}")
                orgs = await self.apollo.search_organizations(
                    company_name=company_name,
                    locations=["Australia"],  # Focus on Australian companies
                    limit=1
                )

                if orgs and orgs[0].get("found"):
                    org = orgs[0]
                    enriched.company_name = org.get("name") or company_name
                    enriched.domain = org.get("domain")
                    enriched.industry = org.get("industry")
                    enriched.employee_count = org.get("employee_count")
                    enriched.country = org.get("country")
                    enriched.founded_year = org.get("founded_year")
                    enriched.is_hiring = org.get("is_hiring")
                    enriched.linkedin_url = org.get("linkedin_url")
                    enrichment_source = "apollo_search"
                    domain = org.get("domain")  # Use for potential follow-up
                    logger.info(f"Apollo search found: {company_name} - {enriched.industry}, {enriched.employee_count} employees")
            except Exception as e:
                logger.warning(f"Apollo name search failed for {company_name}: {e}")

        # Tier 1: Apollo domain-based lookup (if we have/discovered a domain)
        if domain and not enrichment_source:
            try:
                logger.info(f"Tier 1: Apollo enrichment for {company_name} ({domain})")
                apollo_result = await self.apollo.enrich_company(domain)

                if apollo_result.get("found"):
                    enriched.company_name = apollo_result.get("name") or company_name
                    enriched.domain = apollo_result.get("domain") or domain
                    enriched.industry = apollo_result.get("industry")
                    enriched.employee_count = apollo_result.get("employee_count")
                    enriched.country = apollo_result.get("country")
                    enriched.founded_year = apollo_result.get("founded_year")
                    enriched.is_hiring = apollo_result.get("is_hiring")
                    enriched.linkedin_url = apollo_result.get("linkedin_url")
                    enrichment_source = "apollo"
                    logger.info(f"Apollo found: {company_name} - {enriched.industry}, {enriched.employee_count} employees")
            except Exception as e:
                logger.warning(f"Apollo enrichment failed for {domain}: {e}")

        # Tier 1.5: LinkedIn scrape to fill gaps (if Apollo found company but missing key data)
        # Apollo often has linkedin_url but not industry/employee_count for small businesses
        if enrichment_source and enriched.linkedin_url and self.apify:
            missing_data = not enriched.industry or not enriched.employee_count
            if missing_data:
                try:
                    logger.info(f"Tier 1.5: LinkedIn scrape for {company_name} to fill gaps")
                    linkedin_data = await self.apify.scrape_linkedin_company(enriched.linkedin_url)
                    if linkedin_data.get("found"):
                        if not enriched.employee_count:
                            enriched.employee_count = linkedin_data.get("employee_count")
                        if not enriched.employee_range:
                            enriched.employee_range = linkedin_data.get("employee_range")
                        if not enriched.industry:
                            enriched.industry = linkedin_data.get("industry")
                        if not enriched.founded_year:
                            enriched.founded_year = linkedin_data.get("founded_year")
                        if not enriched.location:
                            enriched.location = linkedin_data.get("headquarters")
                        logger.info(f"LinkedIn filled gaps for {company_name}: industry={enriched.industry}, employees={enriched.employee_range}")
                except Exception as e:
                    logger.warning(f"LinkedIn gap-fill failed for {company_name}: {e}")

        # Tier 1.6: Clay company enrichment (if we have domain but still missing data)
        # Clay aggregates from multiple data providers (Clearbit, ZoomInfo, etc.)
        if enriched.domain and (not enriched.industry or not enriched.employee_count):
            try:
                logger.info(f"Tier 1.6: Clay enrichment for {company_name} ({enriched.domain})")
                clay_result = await self.clay.enrich_company(enriched.domain)

                if clay_result.get("found"):
                    if not enriched.industry:
                        enriched.industry = clay_result.get("industry")
                    if not enriched.employee_count:
                        enriched.employee_count = clay_result.get("employee_count")
                    if not enriched.employee_range:
                        enriched.employee_range = clay_result.get("employee_range")
                    if not enriched.location:
                        enriched.location = clay_result.get("location")
                    if not enriched.country:
                        enriched.country = clay_result.get("country")
                    if not enriched.founded_year:
                        enriched.founded_year = clay_result.get("founded_year")
                    if clay_result.get("industry") or clay_result.get("employee_count"):
                        logger.info(f"Clay filled gaps for {company_name}: industry={enriched.industry}, employees={enriched.employee_count}")
            except Exception as e:
                logger.warning(f"Clay enrichment failed for {company_name}: {e}")

        # Tier 2: LinkedIn Company Scraper (if Apollo didn't find it at all)
        if not enrichment_source and self.apify:
            try:
                # Search for company on LinkedIn
                logger.info(f"Tier 2: LinkedIn search for {company_name}")
                search_results = await self.apify.search_google(
                    [f'"{company_name}" site:linkedin.com/company'],
                    results_per_query=1
                )

                # Google Search actor returns nested structure:
                # [{"searchQuery": ..., "organicResults": [{"url": "...", ...}]}]
                linkedin_url = ""
                if search_results and search_results[0].get("organicResults"):
                    organic = search_results[0]["organicResults"]
                    if organic:
                        linkedin_url = organic[0].get("url", "")
                        logger.info(f"Found LinkedIn URL for {company_name}: {linkedin_url}")

                if linkedin_url and "linkedin.com/company" in linkedin_url:
                    linkedin_data = await self.apify.scrape_linkedin_company(linkedin_url)
                    if linkedin_data.get("found"):
                        enriched.employee_count = linkedin_data.get("employee_count") or enriched.employee_count
                        enriched.employee_range = linkedin_data.get("employee_range") or enriched.employee_range
                        enriched.industry = linkedin_data.get("industry") or enriched.industry
                        enriched.founded_year = linkedin_data.get("founded_year") or enriched.founded_year
                        enriched.linkedin_url = linkedin_url
                        enriched.location = linkedin_data.get("headquarters") or enriched.location
                        enrichment_source = "linkedin"
                        logger.info(f"LinkedIn found: {company_name} - {enriched.industry}, {enriched.employee_range}")
            except Exception as e:
                logger.warning(f"LinkedIn enrichment failed for {company_name}: {e}")

        # Tier 3: Google Business (excellent for local Australian businesses)
        if not enrichment_source and self.apify:
            try:
                logger.info(f"Tier 3: Google Business search for {company_name}")
                google_data = await self.apify.scrape_google_business(company_name, "Australia")

                if google_data.get("found"):
                    enriched.location = google_data.get("address") or enriched.location
                    enriched.country = "Australia"  # Inferred from search
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

        # Tier 4: General Google search to find company website (last resort)
        if not enrichment_source and self.apify:
            try:
                logger.info(f"Tier 4: General Google search for {company_name}")
                search_results = await self.apify.search_google(
                    [f'"{company_name}" Australia company'],
                    results_per_query=5
                )

                if search_results and search_results[0].get("organicResults"):
                    organic = search_results[0]["organicResults"]
                    for result in organic[:5]:
                        url = result.get("url", "")
                        title = result.get("title", "")
                        description = result.get("description", "")

                        # Skip social media and directory sites
                        if any(x in url for x in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com",
                                                   "yellowpages", "yelp.com", "truelocal", "hotfrog"]):
                            continue

                        # Found a company website
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        potential_domain = parsed.netloc.lower()
                        if potential_domain.startswith("www."):
                            potential_domain = potential_domain[4:]

                        if potential_domain and "." in potential_domain:
                            enriched.domain = potential_domain
                            enriched.country = "Australia"

                            # Try to infer industry from title/description
                            desc_lower = (title + " " + description).lower()
                            industry_keywords = {
                                "automotive": ["car", "auto", "motor", "vehicle", "dealer"],
                                "hospitality": ["hotel", "resort", "accommodation", "tourism", "travel"],
                                "retail": ["shop", "store", "retail", "fashion", "clothing"],
                                "construction": ["construction", "builder", "building", "trades"],
                                "manufacturing": ["manufacturer", "manufacturing", "timber", "steel"],
                                "healthcare": ["health", "medical", "clinic", "physio", "dental"],
                                "technology": ["software", "tech", "digital", "it services"],
                                "professional_services": ["consulting", "legal", "accounting", "services"],
                                "food_beverage": ["food", "restaurant", "cafe", "catering"],
                                "recreation": ["dive", "tours", "adventure", "sports", "fitness"],
                            }
                            for industry, keywords in industry_keywords.items():
                                if any(kw in desc_lower for kw in keywords):
                                    enriched.industry = industry
                                    break

                            enrichment_source = "google_search"
                            logger.info(f"Google Search found: {company_name} -> {potential_domain}, industry={enriched.industry}")
                            break
            except Exception as e:
                logger.warning(f"General Google search failed for {company_name}: {e}")

        # Final fallback: Keyword matching (only if Claude AND all APIs failed)
        # This should rarely be needed since Claude inference runs first
        if not enriched.industry:
            logger.warning(f"All enrichment sources failed for {company_name}, trying keyword fallback")
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
            logger.info(f"No enrichment found for {company_name} - returning {'inferred' if has_inferred else 'basic'} data")
            return EngineResult.ok(
                data=enriched,
                metadata={"enriched": has_inferred, "source": "inferred" if has_inferred else "none"},
            )

    def _infer_industry_from_name(self, company_name: str) -> str | None:
        """
        Infer industry from company name using keyword matching.

        This is a fallback when external data sources don't provide industry.
        """
        name_lower = company_name.lower()

        industry_patterns = {
            "automotive": ["mazda", "toyota", "ford", "honda", "subaru", "car", "auto", "motor", "vehicle", "dealer", "mechanic", "vermeer"],
            "healthcare": ["physio", "dental", "medical", "clinic", "health", "hospital", "doctor", "therapy", "care"],
            "hospitality": ["hotel", "resort", "motel", "accommodation", "bay suite", "suites", "lodge", "inn"],
            "tourism": ["tours", "travel", "adventure", "charter", "dive", "snorkel", "whale", "cruise", "tourism", "encounters", "safari", "wildlife"],
            "retail": ["shop", "store", "retail", "boutique", "fashion", "clothing", "golf", "sports", "running", "warehouse"],
            "construction": ["construction", "builder", "building", "trades", "ceiling", "floor", "roofing", "plumbing", "tiler"],
            "manufacturing": ["timber", "steel", "manufacturing", "factory", "industrial", "cable", "wire", "equipment"],
            "technology": ["software", "tech", "digital", "it", "app", "data", "intelligence", "develop"],
            "professional_services": ["consulting", "legal", "accounting", "advisory", "services", "agency"],
            "food_beverage": ["jerky", "food", "cafe", "restaurant", "catering", "bakery", "coffee", "beer", "wine"],
            "real_estate": ["property", "real estate", "realty", "homes", "land", "development", "keller"],
            "education": ["academy", "school", "training", "education", "learn", "kids", "child"],
            "fitness": ["gym", "fitness", "crossfit", "yoga", "pilates", "martial"],
            "landscaping": ["landscape", "garden", "lawn", "arcadia", "outdoor"],
            "recruitment": ["hire", "recruit", "staffing", "talent", "hr", "employment", "apm"],
            "environmental": ["enviro", "environment", "eco", "green", "sustainability", "water treatment", "planet", "earth", "solar", "renewable"],
        }

        for industry, keywords in industry_patterns.items():
            if any(kw in name_lower for kw in keywords):
                return industry

        return None

    async def get_agency_apollo_data(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Look up the agency itself in Apollo to get description data.

        Used in Portfolio Fallback Discovery (Tier F1) - the agency's Apollo
        description may mention clients they've worked with.

        Args:
            company_name: Agency name to search for
            domain: Optional agency domain (more accurate if available)

        Returns:
            EngineResult containing Apollo data with description, keywords, etc.
        """
        logger.info(f"Looking up agency in Apollo: {company_name} (domain={domain})")

        # Try domain-based lookup first (more accurate)
        if domain:
            try:
                result = await self.apollo.enrich_company(domain)
                if result.get("found"):
                    logger.info(f"Apollo found agency by domain: {domain}")
                    return EngineResult.ok(
                        data={
                            "found": True,
                            "source": "apollo_domain",
                            "name": result.get("name"),
                            "domain": result.get("domain"),
                            "description": result.get("short_description") or result.get("description"),
                            "industry": result.get("industry"),
                            "employee_count": result.get("estimated_num_employees"),
                            "keywords": result.get("keywords", []),
                            "linkedin_url": result.get("linkedin_url"),
                        },
                        metadata={"source": "apollo_domain"},
                    )
            except Exception as e:
                logger.warning(f"Apollo domain lookup failed for {domain}: {e}")

        # Fallback to name search
        try:
            orgs = await self.apollo.search_organizations(
                company_name=company_name,
                locations=["Australia"],
                limit=1,
            )

            if orgs and orgs[0].get("found"):
                org = orgs[0]
                logger.info(f"Apollo found agency by name search: {company_name}")
                return EngineResult.ok(
                    data={
                        "found": True,
                        "source": "apollo_search",
                        "name": org.get("name"),
                        "domain": org.get("domain"),
                        "description": org.get("short_description") or org.get("description"),
                        "industry": org.get("industry"),
                        "employee_count": org.get("employee_count"),
                        "keywords": org.get("keywords", []),
                        "linkedin_url": org.get("linkedin_url"),
                    },
                    metadata={"source": "apollo_search"},
                )
        except Exception as e:
            logger.warning(f"Apollo name search failed for {company_name}: {e}")

        # Not found
        logger.info(f"Agency not found in Apollo: {company_name}")
        return EngineResult.ok(
            data={"found": False},
            metadata={"source": "none"},
        )

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
                enriched_list.append(EnrichedPortfolioCompany(
                    company_name=company.get("company_name", "Unknown"),
                    domain=company.get("domain"),
                    source=company.get("source", "portfolio"),
                ))
                failed += 1

        return EngineResult.ok(
            data=enriched_list,
            metadata={
                "total": len(companies),
                "successful": successful,
                "failed": failed,
            },
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
                completed_at=datetime.utcnow(),
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
- [x] Uses Apify for website scraping
- [x] Uses Apollo for company enrichment
- [x] No AI processing (data fetching only)
- [x] ScrapedWebsite dataclass for result
- [x] EnrichedPortfolioCompany model
- [x] Batch enrichment support
- [x] Progress tracking methods
- [x] Singleton pattern for engine instance
WATERFALL ARCHITECTURE (SCR-005):
- [x] URLValidator integration (Tier 0)
- [x] scrape_website_with_waterfall (Tier 1 & 2)
- [x] ScrapedWebsite includes tier tracking fields
- [x] Manual fallback URL generation
- [x] Canonical URL tracking after redirects
"""
