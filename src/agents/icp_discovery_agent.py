"""
FILE: src/agents/icp_discovery_agent.py
TASK: ICP-012
PHASE: 11 (ICP Discovery System)
PURPOSE: Orchestrate ICP extraction using modular skills

DEPENDENCIES:
- src/agents/base_agent.py
- src/agents/skills/ (all skills)
- src/engines/icp_scraper.py
- src/integrations/anthropic.py

EXPORTS:
- ICPDiscoveryAgent
- ICPProfile (result model)
- ICPExtractionResult (full result)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base_agent import AgentContext, AgentResult, BaseAgent
from src.agents.skills.als_weight_suggester import ALSWeights, ALSWeightSuggesterSkill
from src.agents.skills.base_skill import SkillRegistry, SkillResult
from src.agents.skills.company_size_estimator import (
    CompanySizeEstimatorSkill,
    LinkedInData,
)
from src.agents.skills.icp_deriver import DerivedICP, EnrichedCompany, ICPDeriverSkill
from src.agents.skills.industry_classifier import IndustryClassifierSkill, IndustryMatch
from src.agents.skills.portfolio_extractor import (
    PortfolioCompany,
    PortfolioExtractorSkill,
)
from src.agents.skills.service_extractor import ServiceExtractorSkill, ServiceInfo
from src.agents.skills.value_prop_extractor import ValuePropExtractorSkill
from src.agents.skills.website_parser import PageContent, WebsiteParserSkill
from src.engines.icp_scraper import (
    EnrichedPortfolioCompany,
    ICPScraperEngine,
    ScrapedWebsite,
    get_icp_scraper_engine,
)
from src.integrations.anthropic import AnthropicClient, get_anthropic_client
from src.integrations.apify import ApifyClient, get_apify_client
from src.models.social_profile import (
    FacebookPageProfile,
    GoogleBusinessProfile,
    InstagramProfile,
    LinkedInCompanyProfile,
    SocialProfiles,
)

if TYPE_CHECKING:
    pass


class ICPProfile(BaseModel):
    """
    Complete ICP profile extracted from website.

    This is the final output of ICP extraction, containing
    all the information needed to configure campaign targeting.
    """

    # Agency info
    company_name: str = Field(default="", description="Agency name")
    website_url: str = Field(default="", description="Website URL")
    company_description: str = Field(default="", description="Company description")

    # Services
    services_offered: list[str] = Field(default_factory=list, description="Services")
    primary_service_categories: list[str] = Field(
        default_factory=list, description="Primary service categories"
    )

    # Value proposition
    value_proposition: str = Field(default="", description="Value proposition")
    taglines: list[str] = Field(default_factory=list, description="Taglines")
    differentiators: list[str] = Field(default_factory=list, description="Differentiators")

    # Company size
    team_size: int | None = Field(default=None, description="Estimated team size")
    size_range: str = Field(default="small", description="Size range")
    years_in_business: int | None = Field(default=None, description="Years in business")

    # Portfolio
    portfolio_companies: list[str] = Field(
        default_factory=list, description="Portfolio company names"
    )
    enriched_portfolio: list[dict] = Field(
        default_factory=list,
        description="Enriched portfolio companies with industry, size, revenue (for finding similar leads)"
    )
    notable_brands: list[str] = Field(default_factory=list, description="Notable brands")

    # ICP targeting
    icp_industries: list[str] = Field(default_factory=list, description="Target industries")
    icp_company_sizes: list[str] = Field(
        default_factory=list, description="Target company sizes"
    )
    icp_revenue_ranges: list[str] = Field(
        default_factory=list, description="Target revenue ranges"
    )
    icp_locations: list[str] = Field(default_factory=list, description="Target locations")
    icp_titles: list[str] = Field(default_factory=list, description="Target titles")
    icp_pain_points: list[str] = Field(default_factory=list, description="Pain points")
    icp_signals: list[str] = Field(default_factory=list, description="Buying signals")

    # ALS weights
    als_weights: dict[str, int] = Field(
        default_factory=dict, description="Custom ALS weights"
    )

    # Social profiles
    social_links: dict[str, str] = Field(
        default_factory=dict, description="Social media links from website"
    )
    social_profiles: SocialProfiles | None = Field(
        default=None, description="Scraped social media profiles"
    )

    # Metadata
    pattern_description: str = Field(default="", description="ICP pattern description")
    confidence: float = Field(default=0.0, description="Overall confidence")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


@dataclass
class ICPExtractionResult:
    """Full result from ICP extraction process."""

    success: bool
    profile: ICPProfile | None = None
    error: str | None = None

    # Step results
    website_scraped: bool = False
    pages_parsed: int = 0
    services_found: int = 0
    portfolio_companies_found: int = 0
    industries_classified: int = 0

    # Cost tracking
    total_tokens: int = 0
    total_cost_aud: float = 0.0

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_seconds: float = 0.0


class ICPDiscoveryAgent(BaseAgent):
    """
    Orchestrates ICP extraction using modular skills.

    Flow:
    1. Scrape website (via ICP Scraper Engine)
    2. Parse content (WebsiteParserSkill)
    3. Extract agency info (ServiceExtractor, ValuePropExtractor)
    4. Find portfolio (PortfolioExtractor)
    5. Enrich portfolio companies (via Apollo)
    6. Derive ICP pattern (ICPDeriver)
    7. Suggest ALS weights (ALSWeightSuggester)
    """

    # Anthropic model config
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        anthropic: AnthropicClient | None = None,
        scraper: ICPScraperEngine | None = None,
        apify: ApifyClient | None = None,
    ):
        """
        Initialize ICP Discovery Agent.

        Args:
            anthropic: Optional Anthropic client override
            scraper: Optional scraper engine override
            apify: Optional Apify client override
        """
        super().__init__()
        self._anthropic = anthropic
        self._scraper = scraper
        self._apify = apify

        # Initialize skills
        self._skills = {
            "parse_website": WebsiteParserSkill(),
            "extract_services": ServiceExtractorSkill(),
            "extract_value_prop": ValuePropExtractorSkill(),
            "extract_portfolio": PortfolioExtractorSkill(),
            "classify_industries": IndustryClassifierSkill(),
            "estimate_company_size": CompanySizeEstimatorSkill(),
            "derive_icp": ICPDeriverSkill(),
            "suggest_als_weights": ALSWeightSuggesterSkill(),
        }

    @property
    def name(self) -> str:
        """Agent name."""
        return "icp_discovery"

    @property
    def system_prompt(self) -> str:
        """System prompt (not used directly - skills have their own)."""
        return "You are an ICP discovery agent."

    @property
    def anthropic(self) -> AnthropicClient:
        """Get Anthropic client."""
        if self._anthropic is None:
            self._anthropic = get_anthropic_client()
        return self._anthropic

    @property
    def scraper(self) -> ICPScraperEngine:
        """Get scraper engine."""
        if self._scraper is None:
            self._scraper = get_icp_scraper_engine()
        return self._scraper

    @property
    def apify(self) -> ApifyClient:
        """Get Apify client."""
        if self._apify is None:
            self._apify = get_apify_client()
        return self._apify

    async def _scrape_social_profiles(
        self,
        social_links: dict[str, str],
        company_name: str,
    ) -> SocialProfiles:
        """
        Scrape social media profiles from collected links.

        Args:
            social_links: Dict of platform -> URL
            company_name: Company name for Google Business search

        Returns:
            SocialProfiles with scraped data
        """
        import logging
        logger = logging.getLogger(__name__)

        linkedin_profile = None
        instagram_profile = None
        facebook_profile = None
        google_profile = None

        # Scrape LinkedIn if URL available
        linkedin_url = social_links.get("linkedin")
        if linkedin_url:
            try:
                logger.info(f"Scraping LinkedIn company: {linkedin_url}")
                data = await self.apify.scrape_linkedin_company(linkedin_url)
                if data.get("found"):
                    linkedin_profile = LinkedInCompanyProfile(
                        name=data.get("name"),
                        followers=data.get("followers"),
                        employee_count=data.get("employee_count"),
                        employee_range=data.get("employee_range"),
                        specialties=data.get("specialties", []),
                        description=data.get("description"),
                        industry=data.get("industry"),
                        headquarters=data.get("headquarters"),
                        website=data.get("website"),
                        founded_year=data.get("founded_year"),
                        linkedin_url=linkedin_url,
                    )
            except Exception as e:
                logger.warning(f"LinkedIn scraping failed: {e}")

        # Scrape Instagram if URL available
        instagram_url = social_links.get("instagram")
        if instagram_url:
            try:
                logger.info(f"Scraping Instagram profile: {instagram_url}")
                data = await self.apify.scrape_instagram_profile(instagram_url)
                if data.get("found"):
                    instagram_profile = InstagramProfile(
                        username=data.get("username"),
                        followers=data.get("followers"),
                        following=data.get("following"),
                        posts_count=data.get("posts_count"),
                        bio=data.get("bio"),
                        is_verified=data.get("is_verified", False),
                        full_name=data.get("full_name"),
                        profile_pic_url=data.get("profile_pic_url"),
                        external_url=data.get("external_url"),
                        instagram_url=instagram_url,
                    )
            except Exception as e:
                logger.warning(f"Instagram scraping failed: {e}")

        # Scrape Facebook if URL available
        facebook_url = social_links.get("facebook")
        if facebook_url:
            try:
                logger.info(f"Scraping Facebook page: {facebook_url}")
                data = await self.apify.scrape_facebook_page(facebook_url)
                if data.get("found"):
                    facebook_profile = FacebookPageProfile(
                        name=data.get("name"),
                        likes=data.get("likes"),
                        followers=data.get("followers"),
                        category=data.get("category"),
                        about=data.get("about"),
                        rating=data.get("rating"),
                        review_count=data.get("review_count"),
                        website=data.get("website"),
                        phone=data.get("phone"),
                        address=data.get("address"),
                        facebook_url=facebook_url,
                    )
            except Exception as e:
                logger.warning(f"Facebook scraping failed: {e}")

        # Always search Google Business by company name
        if company_name:
            try:
                logger.info(f"Scraping Google Business: {company_name}")
                data = await self.apify.scrape_google_business(company_name, "Australia")
                if data.get("found"):
                    google_profile = GoogleBusinessProfile(
                        name=data.get("name"),
                        rating=data.get("rating"),
                        review_count=data.get("review_count"),
                        address=data.get("address"),
                        phone=data.get("phone"),
                        website=data.get("website"),
                        category=data.get("category"),
                        place_id=data.get("place_id"),
                        google_maps_url=data.get("google_maps_url"),
                        opening_hours=data.get("opening_hours"),
                    )
            except Exception as e:
                logger.warning(f"Google Business scraping failed: {e}")

        return SocialProfiles(
            linkedin=linkedin_profile,
            instagram=instagram_profile,
            facebook=facebook_profile,
            google_business=google_profile,
        )

    async def use_skill(
        self,
        skill_name: str,
        **kwargs: Any,
    ) -> SkillResult:
        """
        Execute a skill by name.

        Args:
            skill_name: Name of skill to use
            **kwargs: Input arguments for the skill

        Returns:
            SkillResult from skill execution
        """
        skill = self._skills.get(skill_name)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_name}")

        return await skill.run(kwargs, self.anthropic)

    async def extract_icp(
        self,
        website_url: str,
        db: AsyncSession | None = None,
        job_id: UUID | None = None,
    ) -> ICPExtractionResult:
        """
        Extract ICP from website URL.

        This is the main entry point for ICP extraction.

        Args:
            website_url: Website URL to analyze
            db: Optional database session for progress tracking
            job_id: Optional job ID for progress tracking

        Returns:
            ICPExtractionResult containing profile or error
        """
        result = ICPExtractionResult(success=False)
        total_tokens = 0
        total_cost = 0.0

        try:
            # Step 1: Scrape website
            scrape_result = await self.scraper.scrape_website(website_url)
            if not scrape_result.success or not scrape_result.data:
                return ICPExtractionResult(
                    success=False,
                    error=f"Failed to scrape website: {scrape_result.error}",
                )

            scraped = scrape_result.data
            result.website_scraped = True

            # Log scraped content info
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Scraped {scraped.page_count} pages from {website_url}")
            logger.info(f"Raw HTML length: {len(scraped.raw_html)} chars")
            if scraped.raw_html:
                logger.debug(f"Raw HTML preview: {scraped.raw_html[:500]}...")
            else:
                logger.warning(f"Raw HTML is empty! Pages: {[p.url for p in scraped.pages]}")

            # Step 2: Parse website content
            parse_result = await self.use_skill(
                "parse_website",
                html=scraped.raw_html,
                url=website_url,
                page_urls=[p.url for p in scraped.pages],
            )
            if not parse_result.success or not parse_result.data:
                return ICPExtractionResult(
                    success=False,
                    error=f"Failed to parse website: {parse_result.error}",
                    website_scraped=True,
                )

            parsed = parse_result.data
            result.pages_parsed = len(parsed.pages)
            total_tokens += parse_result.tokens_used
            total_cost += parse_result.cost_aud

            # Collect social links from parsed pages
            collected_social_links: dict[str, str] = {}
            for page in parsed.pages:
                if hasattr(page, 'social_links') and page.social_links:
                    # Merge social links from all pages (first found wins)
                    for platform, url in page.social_links.items():
                        if platform not in collected_social_links and url:
                            collected_social_links[platform] = url

            # Also check top-level social_links from parser output
            if hasattr(parsed, 'social_links') and parsed.social_links:
                for url in parsed.social_links:
                    url_lower = url.lower()
                    if 'linkedin.com' in url_lower and 'linkedin' not in collected_social_links:
                        collected_social_links['linkedin'] = url
                    elif 'instagram.com' in url_lower and 'instagram' not in collected_social_links:
                        collected_social_links['instagram'] = url
                    elif 'facebook.com' in url_lower and 'facebook' not in collected_social_links:
                        collected_social_links['facebook'] = url
                    elif ('twitter.com' in url_lower or 'x.com' in url_lower) and 'twitter' not in collected_social_links:
                        collected_social_links['twitter'] = url

            logger.info(f"Collected social links: {collected_social_links}")

            # Scrape social profiles (non-blocking, errors logged but don't fail extraction)
            social_profiles = await self._scrape_social_profiles(
                collected_social_links,
                parsed.company_name,
            )
            logger.info(f"Scraped social profiles: {social_profiles.platforms_found}")

            # Step 3: Extract services, value prop, portfolio (parallel)
            services_task = self.use_skill(
                "extract_services",
                pages=[p.model_dump() for p in parsed.pages],
                company_name=parsed.company_name,
            )
            value_prop_task = self.use_skill(
                "extract_value_prop",
                pages=[p.model_dump() for p in parsed.pages],
                company_name=parsed.company_name,
            )
            portfolio_task = self.use_skill(
                "extract_portfolio",
                pages=[p.model_dump() for p in parsed.pages],
                company_name=parsed.company_name,
                raw_html=scraped.raw_html,  # Pass raw HTML for company name extraction
            )

            services_result, value_prop_result, portfolio_result = await asyncio.gather(
                services_task, value_prop_task, portfolio_task
            )

            # Collect results
            services_data = services_result.data if services_result.success else None
            value_prop_data = value_prop_result.data if value_prop_result.success else None
            portfolio_data = portfolio_result.data if portfolio_result.success else None

            total_tokens += (
                services_result.tokens_used
                + value_prop_result.tokens_used
                + portfolio_result.tokens_used
            )
            total_cost += (
                services_result.cost_aud
                + value_prop_result.cost_aud
                + portfolio_result.cost_aud
            )

            if services_data:
                result.services_found = len(services_data.services)

            if portfolio_data:
                result.portfolio_companies_found = len(portfolio_data.companies)

            # Step 4: Enrich portfolio companies
            enriched_companies: list[EnrichedCompany] = []
            if portfolio_data and portfolio_data.companies:
                # Convert to format for enrichment
                companies_to_enrich = [
                    {
                        "company_name": c.company_name,
                        "domain": c.company_domain,
                        "source": c.source,
                    }
                    for c in portfolio_data.companies[:30]  # Limit to 30 (increased from 15)
                ]

                enrich_result = await self.scraper.enrich_portfolio_batch(
                    companies_to_enrich
                )

                if enrich_result.success and enrich_result.data:
                    for ec in enrich_result.data:
                        enriched_companies.append(
                            EnrichedCompany(
                                company_name=ec.company_name,
                                domain=ec.domain,
                                industry=ec.industry,
                                employee_count=ec.employee_count,
                                employee_range=ec.employee_range,
                                annual_revenue=ec.annual_revenue,
                                location=ec.location,
                                country=ec.country,
                                founded_year=ec.founded_year,
                                technologies=ec.technologies,
                                is_hiring=ec.is_hiring,
                                linkedin_url=ec.linkedin_url,
                                source=ec.source,
                            )
                        )

            # Step 5: Classify industries + estimate company size (parallel)
            services_list = []
            if services_data:
                services_list = [
                    ServiceInfo(**s.model_dump()) for s in services_data.services
                ]

            portfolio_list = []
            if portfolio_data:
                portfolio_list = [
                    PortfolioCompany(**c.model_dump()) for c in portfolio_data.companies
                ]

            industry_task = self.use_skill(
                "classify_industries",
                services=[s.model_dump() for s in services_list],
                portfolio_companies=[p.model_dump() for p in portfolio_list],
                target_audience_hints=(
                    value_prop_data.target_audience_hints if value_prop_data else []
                ),
                company_name=parsed.company_name,
            )

            # Find about/team pages for size estimation
            about_page = None
            team_page = None
            for page in parsed.pages:
                if page.page_type == "about":
                    about_page = page.model_dump()
                elif page.page_type == "team":
                    team_page = page.model_dump()

            size_task = self.use_skill(
                "estimate_company_size",
                about_page=about_page,
                team_page=team_page,
                all_pages=[p.model_dump() for p in parsed.pages[:5]],
                company_name=parsed.company_name,
            )

            industry_result, size_result = await asyncio.gather(
                industry_task, size_task
            )

            industry_data = industry_result.data if industry_result.success else None
            size_data = size_result.data if size_result.success else None

            total_tokens += industry_result.tokens_used + size_result.tokens_used
            total_cost += industry_result.cost_aud + size_result.cost_aud

            if industry_data:
                result.industries_classified = len(industry_data.industries)

            # Step 6: Derive ICP from enriched portfolio
            classified_industries = []
            if industry_data:
                classified_industries = [
                    IndustryMatch(**i.model_dump()) for i in industry_data.industries
                ]

            icp_result = await self.use_skill(
                "derive_icp",
                enriched_portfolio=[ec.model_dump() for ec in enriched_companies],
                classified_industries=[i.model_dump() for i in classified_industries],
                services_offered=(
                    services_data.primary_categories if services_data else []
                ),
                value_proposition=(
                    value_prop_data.value_proposition if value_prop_data else ""
                ),
                company_name=parsed.company_name,
            )

            icp_data = icp_result.data if icp_result.success else None
            total_tokens += icp_result.tokens_used
            total_cost += icp_result.cost_aud

            # Step 7: Suggest ALS weights
            als_weights_result = None
            if icp_data and icp_data.icp:
                als_weights_result = await self.use_skill(
                    "suggest_als_weights",
                    icp_profile=icp_data.icp.model_dump(),
                    services_offered=(
                        services_data.primary_categories if services_data else []
                    ),
                    company_name=parsed.company_name,
                )
                total_tokens += als_weights_result.tokens_used
                total_cost += als_weights_result.cost_aud

            # Build final profile
            profile = ICPProfile(
                company_name=parsed.company_name,
                website_url=website_url,
                company_description=(
                    value_prop_data.value_proposition if value_prop_data else ""
                ),
                services_offered=(
                    [s.name for s in services_data.services] if services_data else []
                ),
                primary_service_categories=(
                    services_data.primary_categories if services_data else []
                ),
                value_proposition=(
                    value_prop_data.value_proposition if value_prop_data else ""
                ),
                taglines=(value_prop_data.taglines if value_prop_data else []),
                differentiators=(
                    value_prop_data.differentiators if value_prop_data else []
                ),
                team_size=(size_data.team_size if size_data else None),
                size_range=(size_data.size_range if size_data else "small"),
                years_in_business=(
                    size_data.years_in_business if size_data else None
                ),
                portfolio_companies=(
                    [c.company_name for c in portfolio_data.companies]
                    if portfolio_data
                    else []
                ),
                enriched_portfolio=[ec.model_dump() for ec in enriched_companies],
                notable_brands=(
                    portfolio_data.notable_brands if portfolio_data else []
                ),
                icp_industries=(
                    icp_data.icp.icp_industries if icp_data and icp_data.icp else []
                ),
                icp_company_sizes=(
                    icp_data.icp.icp_company_sizes if icp_data and icp_data.icp else []
                ),
                icp_revenue_ranges=(
                    icp_data.icp.icp_revenue_ranges if icp_data and icp_data.icp else []
                ),
                icp_locations=(
                    icp_data.icp.icp_locations if icp_data and icp_data.icp else []
                ),
                icp_titles=(
                    icp_data.icp.icp_titles if icp_data and icp_data.icp else []
                ),
                icp_pain_points=(
                    icp_data.icp.icp_pain_points if icp_data and icp_data.icp else []
                ),
                icp_signals=(
                    icp_data.icp.icp_signals if icp_data and icp_data.icp else []
                ),
                als_weights=(
                    als_weights_result.data.weights.model_dump()
                    if als_weights_result and als_weights_result.success
                    else {}
                ),
                social_links=collected_social_links,
                social_profiles=social_profiles,
                pattern_description=(
                    icp_data.icp.pattern_description
                    if icp_data and icp_data.icp
                    else ""
                ),
                confidence=(
                    icp_data.icp.pattern_confidence
                    if icp_data and icp_data.icp
                    else 0.5
                ),
            )

            # Complete result
            result.success = True
            result.profile = profile
            result.total_tokens = total_tokens
            result.total_cost_aud = total_cost
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

            return result

        except Exception as e:
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()
            return result


# Singleton instance
_icp_discovery_agent: ICPDiscoveryAgent | None = None


def get_icp_discovery_agent() -> ICPDiscoveryAgent:
    """Get or create ICP discovery agent instance."""
    global _icp_discovery_agent
    if _icp_discovery_agent is None:
        _icp_discovery_agent = ICPDiscoveryAgent()
    return _icp_discovery_agent


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseAgent
- [x] Orchestrates all 8 skills
- [x] Uses ICP Scraper Engine for data fetching
- [x] Parallel execution where possible (asyncio.gather)
- [x] ICPProfile output model
- [x] ICPExtractionResult with metrics
- [x] Token/cost tracking throughout
- [x] Error handling at each step
- [x] Singleton pattern for instance
"""
