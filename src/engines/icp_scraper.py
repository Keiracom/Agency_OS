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

from src.engines.base import BaseEngine, EngineResult
from src.engines.url_validator import URLValidator, get_url_validator
from src.exceptions import EngineError, ValidationError
from src.integrations.apify import get_apify_client, ScrapeResult
from src.integrations.apollo import get_apollo_client

if TYPE_CHECKING:
    from src.integrations.apify import ApifyClient
    from src.integrations.apollo import ApolloClient

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
        url_validator: "URLValidator | None" = None,
    ):
        """
        Initialize with optional client overrides for testing.

        Args:
            apify_client: Optional Apify client override
            apollo_client: Optional Apollo client override
            url_validator: Optional URL validator override
        """
        self._apify = apify_client
        self._apollo = apollo_client
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
        # Use prefer_playwright=True for ICP extraction because:
        # - Agency sites are typically JS-rendered (React, Vue, etc.)
        # - Portfolio/testimonial data is often in dynamic sections
        # - Cheerio would miss case studies, client logos, testimonials
        try:
            scrape_result: ScrapeResult = await self.apify.scrape_website_with_waterfall(
                canonical_url, max_pages=max_pages, prefer_playwright=True
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
            scraped = ScrapedWebsite(
                url=url,
                domain=domain,
                pages=pages,
                raw_html="\n\n---PAGE BREAK---\n\n".join(all_html) if all_html else scrape_result.raw_html,
                page_count=len(pages),
                tier_used=scrape_result.tier_used,
                needs_fallback=False,
                canonical_url=canonical_url,
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
            # Use Apollo to search for company
            search_query = domain if domain else company_name

            # Apollo organization search
            org_data = await self.apollo.search_organizations(
                query=search_query,
                limit=1,
            )

            if not org_data or len(org_data) == 0:
                return EngineResult.ok(
                    data=LinkedInCompanyData(company_name=company_name),
                    metadata={"found": False},
                )

            org = org_data[0]

            linkedin_data = LinkedInCompanyData(
                company_name=org.get("name", company_name),
                employee_count=org.get("employee_count"),
                employee_range=org.get("employee_count_range"),
                headquarters=org.get("headquarters_address"),
                founded_year=org.get("founded_year"),
                industry=org.get("industry"),
                specialties=org.get("specialties", []),
                linkedin_url=org.get("linkedin_url"),
            )

            return EngineResult.ok(
                data=linkedin_data,
                metadata={"found": True, "source": "apollo"},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"LinkedIn company lookup failed: {str(e)}",
                metadata={"company_name": company_name},
            )

    async def enrich_portfolio_company(
        self,
        company_name: str,
        domain: str | None = None,
        source: str = "portfolio",
    ) -> EngineResult[EnrichedPortfolioCompany]:
        """
        Enrich a single portfolio company via Apollo.

        Args:
            company_name: Company name
            domain: Optional company domain
            source: How this company was found

        Returns:
            EngineResult containing enriched company data
        """
        try:
            # Try domain-based lookup first
            search_query = domain if domain else company_name

            org_data = await self.apollo.search_organizations(
                query=search_query,
                limit=1,
            )

            if not org_data or len(org_data) == 0:
                # Return basic data if not found
                return EngineResult.ok(
                    data=EnrichedPortfolioCompany(
                        company_name=company_name,
                        domain=domain,
                        source=source,
                    ),
                    metadata={"enriched": False},
                )

            org = org_data[0]

            enriched = EnrichedPortfolioCompany(
                company_name=org.get("name", company_name),
                domain=org.get("domain", domain),
                industry=org.get("industry"),
                employee_count=org.get("employee_count"),
                employee_range=org.get("employee_count_range"),
                annual_revenue=org.get("annual_revenue_range"),
                location=org.get("headquarters_address"),
                country=org.get("country"),
                founded_year=org.get("founded_year"),
                technologies=org.get("technologies", [])[:10],  # Limit to 10
                is_hiring=org.get("is_hiring"),
                linkedin_url=org.get("linkedin_url"),
                source=source,
            )

            return EngineResult.ok(
                data=enriched,
                metadata={"enriched": True, "source": "apollo"},
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Company enrichment failed: {str(e)}",
                metadata={"company_name": company_name},
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
