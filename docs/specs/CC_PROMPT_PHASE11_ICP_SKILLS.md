# PHASE 11: ICP Discovery System (Skills-Based Architecture)

## OVERVIEW

Build the ICP (Ideal Customer Profile) Discovery System for Agency OS using a modular skills-based architecture. When a marketing agency signs up, they enter their website URL. The system scrapes their digital footprint and uses AI skills to extract structured ICP data.

## CRITICAL CONSTRAINTS

- Follow PROJECT_BLUEPRINT.md Part 11 exactly
- Follow import hierarchy: models → integrations → engines → orchestration → agents
- All database sessions passed via dependency injection (Rule 11)
- All Anthropic calls through spend limiter (Rule 15)
- Each skill must be independently testable
- Update PROGRESS.md after each task

## TASK EXECUTION ORDER

Execute tasks in this exact order:

---

### ICP-001: Database Migration

**File:** `supabase/migrations/012_client_icp_profile.sql`

```sql
-- Add ICP fields to clients table
ALTER TABLE clients ADD COLUMN IF NOT EXISTS website_url TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS company_description TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS services_offered TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS years_in_business INTEGER;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS team_size INTEGER;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS value_proposition TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS default_offer TEXT;

-- ICP Configuration
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_industries TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_company_sizes TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_revenue_range TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_locations TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_titles TEXT[];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_pain_points TEXT[];

-- Custom ALS weights (overrides defaults)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS als_weights JSONB DEFAULT '{}';

-- ICP extraction status
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_extracted_at TIMESTAMPTZ;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_extraction_source TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS icp_confirmed_at TIMESTAMPTZ;

-- Discovered client logos/case studies
CREATE TABLE IF NOT EXISTS client_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    company_domain TEXT,
    company_industry TEXT,
    company_size TEXT,
    company_location TEXT,
    source TEXT,
    enriched_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_portfolio_client ON client_portfolio(client_id);
```

---

### ICP-002: Skill Base Class

**File:** `src/agents/skills/__init__.py`

```python
from src.agents.skills.base_skill import BaseSkill, SkillRegistry
```

**File:** `src/agents/skills/base_skill.py`

```python
"""
FILE: src/agents/skills/base_skill.py
PURPOSE: Base class for modular agent skills
PHASE: 11 (ICP Discovery)
TASK: ICP-002
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Optional
from pydantic import BaseModel

from src.integrations.anthropic import AnthropicClient


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseSkill(ABC, Generic[InputT, OutputT]):
    """
    Base class for all agent skills.
    """
    
    name: str
    description: str
    system_prompt: str = ""
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    
    class Input(BaseModel):
        pass
    
    class Output(BaseModel):
        pass
    
    @abstractmethod
    async def execute(
        self, 
        input_data: InputT, 
        anthropic: AnthropicClient
    ) -> OutputT:
        pass
    
    def validate_input(self, data: dict) -> InputT:
        return self.Input(**data)
    
    def validate_output(self, data: dict) -> OutputT:
        return self.Output(**data)
    
    async def _call_claude(
        self,
        anthropic: AnthropicClient,
        user_message: str,
        response_model: Optional[type[BaseModel]] = None
    ) -> Any:
        response = await anthropic.complete(
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
            model=self.model,
            max_tokens=self.max_tokens,
            response_model=response_model or self.Output
        )
        return response


class SkillRegistry:
    """Registry for discovering and loading skills."""
    
    _skills: dict[str, BaseSkill] = {}
    
    @classmethod
    def register(cls, skill: BaseSkill) -> BaseSkill:
        cls._skills[skill.name] = skill
        return skill
    
    @classmethod
    def get(cls, name: str) -> BaseSkill:
        if name not in cls._skills:
            raise KeyError(f"Skill '{name}' not found")
        return cls._skills[name]
    
    @classmethod
    def all(cls) -> list[BaseSkill]:
        return list(cls._skills.values())
```

---

### ICP-003: Website Parser Skill

**File:** `src/agents/skills/website_parser.py`

```python
"""
FILE: src/agents/skills/website_parser.py
PURPOSE: Parse raw website HTML into structured content
PHASE: 11 (ICP Discovery)
TASK: ICP-003
"""

from typing import Optional
from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.integrations.anthropic import AnthropicClient


class PageContent(BaseModel):
    url: str
    title: Optional[str] = None
    page_type: str
    headings: list[str] = []
    paragraphs: list[str] = []
    links: list[str] = []
    images: list[str] = []


class WebsiteParserSkill(BaseSkill):
    name = "parse_website"
    description = "Extract structured content from raw website HTML"
    
    class Input(BaseModel):
        html: str
        url: str
    
    class Output(BaseModel):
        pages: list[PageContent]
        company_name: Optional[str] = None
        navigation: list[str] = []
        primary_phone: Optional[str] = None
        primary_email: Optional[str] = None
        social_links: dict[str, str] = {}
    
    system_prompt = """You are a website content parser for marketing agency analysis.

EXTRACT:
1. Company name - from logo alt text, title tag, about page, footer
2. Page type - classify as: home, about, services, contact, case_study, blog, portfolio, team, other
3. Navigation - main menu items
4. Headings - all h1, h2, h3 text
5. Paragraphs - main content paragraphs (skip boilerplate)
6. Contact info - phone, email
7. Social links - LinkedIn, Facebook, Instagram, Twitter URLs

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "WebsiteParserSkill.Input", 
        anthropic: AnthropicClient
    ) -> "WebsiteParserSkill.Output":
        html = input_data.html[:100000] if len(input_data.html) > 100000 else input_data.html
        
        user_message = f"""Parse this website HTML and extract structured content.

URL: {input_data.url}

HTML:
{html}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(WebsiteParserSkill())
```

---

### ICP-004: Service Extractor Skill

**File:** `src/agents/skills/service_extractor.py`

```python
"""
FILE: src/agents/skills/service_extractor.py
PURPOSE: Extract services offered by a marketing agency
PHASE: 11 (ICP Discovery)
TASK: ICP-004
"""

from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.agents.skills.website_parser import PageContent
from src.integrations.anthropic import AnthropicClient


class ServiceExtractorSkill(BaseSkill):
    name = "extract_services"
    description = "Identify services a marketing agency offers"
    
    class Input(BaseModel):
        pages: list[PageContent]
    
    class Output(BaseModel):
        services: list[str]
        primary_services: list[str]
        secondary_services: list[str]
        service_descriptions: dict[str, str]
        confidence: float
        source_pages: list[str]
    
    system_prompt = """You are analyzing a marketing agency's website to identify their services.

COMMON MARKETING AGENCY SERVICES:
- SEO / Search Engine Optimization
- PPC / Paid Advertising / Google Ads
- Social Media Marketing
- Content Marketing
- Email Marketing
- Web Design / Web Development
- Branding / Brand Strategy
- PR / Public Relations
- Video Production
- Graphic Design

RULES:
1. Look for explicit "Services" pages first
2. Primary services = prominently featured
3. Secondary services = mentioned but not featured
4. Only include services they EXPLICITLY offer

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "ServiceExtractorSkill.Input", 
        anthropic: AnthropicClient
    ) -> "ServiceExtractorSkill.Output":
        content_parts = []
        for page in input_data.pages:
            content_parts.append(f"=== PAGE: {page.url} (type: {page.page_type}) ===")
            content_parts.append(f"Headings: {', '.join(page.headings)}")
            content_parts.append(f"Content: {' '.join(page.paragraphs[:10])}")
        
        content = "\n\n".join(content_parts)
        
        user_message = f"""Extract services from this marketing agency website.

{content}

Return JSON with services, primary_services, secondary_services, service_descriptions, confidence, source_pages."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(ServiceExtractorSkill())
```

---

### ICP-005: Value Prop Extractor Skill

**File:** `src/agents/skills/value_prop_extractor.py`

```python
"""
FILE: src/agents/skills/value_prop_extractor.py
PURPOSE: Extract value proposition and key messaging
PHASE: 11 (ICP Discovery)
TASK: ICP-005
"""

from typing import Optional
from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.agents.skills.website_parser import PageContent
from src.integrations.anthropic import AnthropicClient


class ValuePropExtractorSkill(BaseSkill):
    name = "extract_value_prop"
    description = "Find the agency's value proposition and key messaging"
    
    class Input(BaseModel):
        pages: list[PageContent]
    
    class Output(BaseModel):
        value_proposition: str
        tagline: Optional[str] = None
        differentiators: list[str]
        promised_outcomes: list[str]
        proof_points: list[str]
        tone: str
        confidence: float
    
    system_prompt = """You are analyzing a marketing agency's website to extract their value proposition.

LOOK FOR:
1. Homepage hero headline
2. Taglines
3. "Why us" sections
4. Differentiators
5. Promised outcomes
6. Proof points - stats, awards

TONE: professional, casual, bold, technical

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "ValuePropExtractorSkill.Input", 
        anthropic: AnthropicClient
    ) -> "ValuePropExtractorSkill.Output":
        priority_pages = [p for p in input_data.pages if p.page_type in ('home', 'about')]
        ordered_pages = priority_pages + input_data.pages[:3]
        
        content_parts = []
        for page in ordered_pages[:5]:
            content_parts.append(f"=== {page.page_type.upper()} PAGE ===")
            content_parts.append(f"Headings: {', '.join(page.headings)}")
            content_parts.append(f"Content: {' '.join(page.paragraphs[:5])}")
        
        content = "\n\n".join(content_parts)
        
        user_message = f"""Extract the value proposition from this agency website.

{content}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(ValuePropExtractorSkill())
```

---

### ICP-006: Portfolio Extractor Skill

**File:** `src/agents/skills/portfolio_extractor.py`

```python
"""
FILE: src/agents/skills/portfolio_extractor.py
PURPOSE: Extract client logos, case studies, testimonials
PHASE: 11 (ICP Discovery)
TASK: ICP-006
"""

from typing import Optional
from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.agents.skills.website_parser import PageContent
from src.integrations.anthropic import AnthropicClient


class PortfolioCompany(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    source: str
    context: Optional[str] = None


class PortfolioExtractorSkill(BaseSkill):
    name = "extract_portfolio"
    description = "Find client logos, case studies, and testimonials"
    
    class Input(BaseModel):
        pages: list[PageContent]
    
    class Output(BaseModel):
        companies: list[PortfolioCompany]
        total_clients_claimed: Optional[int] = None
        notable_clients: list[str] = []
        industries_served: list[str] = []
        confidence: float
    
    system_prompt = """You are extracting client/portfolio information from a marketing agency website.

LOOK FOR:
1. Logo walls - extract company names from image alt text
2. Case study pages - extract client names
3. Testimonials - extract company names
4. Claims like "500+ clients served"

RULES:
- Only extract REAL company names, not placeholders
- Note the source: 'logo', 'case_study', or 'testimonial'

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "PortfolioExtractorSkill.Input", 
        anthropic: AnthropicClient
    ) -> "PortfolioExtractorSkill.Output":
        portfolio_pages = [p for p in input_data.pages 
                          if p.page_type in ('case_study', 'portfolio', 'home')]
        
        content_parts = []
        for page in portfolio_pages[:5]:
            content_parts.append(f"=== {page.page_type.upper()} PAGE ===")
            content_parts.append(f"Headings: {', '.join(page.headings)}")
            content_parts.append(f"Content: {' '.join(page.paragraphs[:8])}")
            content_parts.append(f"Images: {', '.join(page.images)}")
        
        content = "\n\n".join(content_parts)
        
        user_message = f"""Extract portfolio/client information.

{content}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(PortfolioExtractorSkill())
```

---

### ICP-007: Industry Classifier Skill

**File:** `src/agents/skills/industry_classifier.py`

```python
"""
FILE: src/agents/skills/industry_classifier.py
PURPOSE: Classify target industries from services and portfolio
PHASE: 11 (ICP Discovery)
TASK: ICP-007
"""

from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.agents.skills.portfolio_extractor import PortfolioCompany
from src.integrations.anthropic import AnthropicClient


class IndustryClassifierSkill(BaseSkill):
    name = "classify_industries"
    description = "Determine target industries from services and portfolio"
    
    class Input(BaseModel):
        services: list[str]
        portfolio: list[PortfolioCompany]
        industries_mentioned: list[str] = []
    
    class Output(BaseModel):
        primary_industries: list[str]
        secondary_industries: list[str]
        industry_signals: dict[str, list[str]]
        is_industry_specialist: bool
        is_generalist: bool
        confidence: float
    
    system_prompt = """You are classifying which industries a marketing agency targets.

STANDARD INDUSTRIES:
- Ecommerce / Retail
- SaaS / Technology
- Healthcare / Medical
- Financial Services
- Real Estate
- Professional Services
- Manufacturing
- Hospitality / Travel
- Education
- B2B Services

RULES:
1. Primary = 3+ portfolio clients OR explicitly stated
2. Specialist = 60%+ clients in 1-2 industries
3. Generalist = clients across 4+ industries

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "IndustryClassifierSkill.Input", 
        anthropic: AnthropicClient
    ) -> "IndustryClassifierSkill.Output":
        services_str = ", ".join(input_data.services)
        portfolio_str = "\n".join([f"- {c.company_name}" for c in input_data.portfolio[:20]])
        
        user_message = f"""Classify target industries.

SERVICES: {services_str}

PORTFOLIO:
{portfolio_str}

MENTIONED: {', '.join(input_data.industries_mentioned)}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(IndustryClassifierSkill())
```

---

### ICP-008: Company Size Estimator Skill

**File:** `src/agents/skills/company_size_estimator.py`

```python
"""
FILE: src/agents/skills/company_size_estimator.py
PURPOSE: Estimate agency team size
PHASE: 11 (ICP Discovery)
TASK: ICP-008
"""

from typing import Optional
from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.agents.skills.website_parser import PageContent
from src.integrations.anthropic import AnthropicClient


class LinkedInData(BaseModel):
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None


class CompanySizeEstimatorSkill(BaseSkill):
    name = "estimate_company_size"
    description = "Estimate agency team size from website and LinkedIn"
    
    class Input(BaseModel):
        pages: list[PageContent]
        linkedin_data: Optional[LinkedInData] = None
    
    class Output(BaseModel):
        team_size: Optional[int] = None
        size_range: str
        years_in_business: Optional[int] = None
        locations: list[str] = []
        estimation_method: str
        confidence: float
    
    system_prompt = """You are estimating a marketing agency's team size.

SIGNALS:
1. Team page - count visible members
2. LinkedIn employee count
3. "About us" mentions
4. Office locations (multiple = larger)

SIZE RANGES: 1-10, 11-50, 51-200, 201-500, 500+

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "CompanySizeEstimatorSkill.Input", 
        anthropic: AnthropicClient
    ) -> "CompanySizeEstimatorSkill.Output":
        relevant_pages = [p for p in input_data.pages if p.page_type in ('about', 'team', 'home')]
        
        content_parts = []
        for page in relevant_pages[:3]:
            content_parts.append(f"=== {page.page_type.upper()} ===")
            content_parts.append(f"Content: {' '.join(page.paragraphs[:5])}")
        
        linkedin_info = ""
        if input_data.linkedin_data:
            linkedin_info = f"\nLINKEDIN: {input_data.linkedin_data.employee_count} employees, founded {input_data.linkedin_data.founded_year}"
        
        user_message = f"""Estimate team size.

{chr(10).join(content_parts)}
{linkedin_info}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(CompanySizeEstimatorSkill())
```

---

### ICP-009: ICP Deriver Skill

**File:** `src/agents/skills/icp_deriver.py`

```python
"""
FILE: src/agents/skills/icp_deriver.py
PURPOSE: Derive ICP from enriched portfolio
PHASE: 11 (ICP Discovery)
TASK: ICP-009
"""

from typing import Optional
from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.integrations.anthropic import AnthropicClient


class EnrichedCompany(BaseModel):
    company_name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    annual_revenue: Optional[str] = None
    location: Optional[str] = None
    founded_year: Optional[int] = None


class ICPDeriverSkill(BaseSkill):
    name = "derive_icp"
    description = "Derive ICP pattern from enriched portfolio"
    
    class Input(BaseModel):
        enriched_portfolio: list[EnrichedCompany]
        services: list[str] = []
    
    class Output(BaseModel):
        icp_industries: list[str]
        icp_company_sizes: list[str]
        icp_revenue_range: Optional[str] = None
        icp_locations: list[str]
        icp_titles: list[str]
        pattern_description: str
        confidence: float
    
    system_prompt = """You are deriving an ICP from portfolio analysis.

FIND PATTERNS IN:
- Industry (most common)
- Company size (most common range)
- Location (geographic concentration)

SUGGEST TITLES based on services:
- SEO/Content → Marketing Manager, CMO
- Web Design → CEO, Marketing Director
- PPC → Performance Marketing Manager

PATTERN FORMAT:
"Your ideal clients are [SIZE] [INDUSTRY] companies in [LOCATION]"

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "ICPDeriverSkill.Input", 
        anthropic: AnthropicClient
    ) -> "ICPDeriverSkill.Output":
        portfolio_lines = [
            f"- {c.company_name}: {c.industry}, {c.employee_range}, {c.location}"
            for c in input_data.enriched_portfolio[:30]
        ]
        
        user_message = f"""Derive ICP from portfolio.

PORTFOLIO:
{chr(10).join(portfolio_lines)}

SERVICES: {', '.join(input_data.services)}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(ICPDeriverSkill())
```

---

### ICP-010: ALS Weight Suggester Skill

**File:** `src/agents/skills/als_weight_suggester.py`

```python
"""
FILE: src/agents/skills/als_weight_suggester.py
PURPOSE: Suggest custom ALS weights based on ICP
PHASE: 11 (ICP Discovery)
TASK: ICP-010
"""

from pydantic import BaseModel

from src.agents.skills.base_skill import BaseSkill, SkillRegistry
from src.integrations.anthropic import AnthropicClient


class ICPProfile(BaseModel):
    services_offered: list[str] = []
    icp_industries: list[str] = []
    icp_company_sizes: list[str] = []
    icp_locations: list[str] = []
    icp_titles: list[str] = []


class ALSWeightSuggesterSkill(BaseSkill):
    name = "suggest_als_weights"
    description = "Suggest custom ALS weights based on ICP"
    
    class Input(BaseModel):
        icp_profile: ICPProfile
    
    class Output(BaseModel):
        weights: dict[str, int]
        reasoning: str
        total_points: int
    
    system_prompt = """You are configuring custom ALS weights.

DEFAULT WEIGHTS (100 total):
- data_quality: 20
- authority: 25
- company_fit: 25
- timing: 15
- risk: 15

ADJUST BASED ON ICP:
- Industry specialist → increase industry_match
- Specific sizes → increase size_match
- Location focused → increase location_match
- C-suite targets → increase authority

Total must equal 100.

Return valid JSON matching the Output schema."""

    async def execute(
        self, 
        input_data: "ALSWeightSuggesterSkill.Input", 
        anthropic: AnthropicClient
    ) -> "ALSWeightSuggesterSkill.Output":
        icp = input_data.icp_profile
        
        user_message = f"""Suggest ALS weights for:

Services: {', '.join(icp.services_offered)}
Industries: {', '.join(icp.icp_industries)}
Sizes: {', '.join(icp.icp_company_sizes)}
Locations: {', '.join(icp.icp_locations)}
Titles: {', '.join(icp.icp_titles)}

Return JSON matching the Output schema."""

        return await self._call_claude(anthropic, user_message)


SkillRegistry.register(ALSWeightSuggesterSkill())
```

---

### ICP-011: ICP Scraper Engine

**File:** `src/engines/icp_scraper.py`

```python
"""
FILE: src/engines/icp_scraper.py
PURPOSE: Coordinate multi-source scraping for ICP extraction
PHASE: 11 (ICP Discovery)
TASK: ICP-011
"""

from typing import Optional

from src.engines.base import BaseEngine
from src.integrations.apify import ApifyClient
from src.integrations.apollo import ApolloClient
from src.agents.skills.portfolio_extractor import PortfolioCompany
from src.agents.skills.icp_deriver import EnrichedCompany
from src.agents.skills.company_size_estimator import LinkedInData


class ICPScraperEngine(BaseEngine):
    """
    Coordinate scraping from multiple sources.
    Data fetching only - AI analysis done by skills.
    """
    
    def __init__(self, apify: ApifyClient, apollo: ApolloClient):
        self.apify = apify
        self.apollo = apollo
    
    async def scrape_website(self, url: str) -> str:
        """Scrape website HTML via Apify."""
        result = await self.apify.scrape_website(url)
        return result.get("html", "")
    
    async def get_linkedin_data(
        self, 
        company_name: str, 
        domain: Optional[str] = None
    ) -> Optional[LinkedInData]:
        """Get LinkedIn company data via Apollo."""
        try:
            result = await self.apollo.enrich_company(name=company_name, domain=domain)
            if result:
                return LinkedInData(
                    employee_count=result.get("employee_count"),
                    employee_range=result.get("employee_range"),
                    founded_year=result.get("founded_year"),
                    headquarters=result.get("headquarters"),
                )
        except Exception:
            pass
        return None
    
    async def enrich_portfolio(
        self, 
        companies: list[PortfolioCompany]
    ) -> list[EnrichedCompany]:
        """Enrich portfolio companies via Apollo."""
        enriched = []
        
        for company in companies[:20]:
            try:
                result = await self.apollo.enrich_company(
                    name=company.company_name,
                    domain=company.company_domain
                )
                if result:
                    enriched.append(EnrichedCompany(
                        company_name=company.company_name,
                        domain=result.get("domain"),
                        industry=result.get("industry"),
                        employee_count=result.get("employee_count"),
                        employee_range=result.get("employee_range"),
                        location=result.get("headquarters"),
                    ))
                else:
                    enriched.append(EnrichedCompany(company_name=company.company_name))
            except Exception:
                enriched.append(EnrichedCompany(company_name=company.company_name))
        
        return enriched
```

---

### ICP-012: ICP Discovery Agent

**File:** `src/agents/icp_discovery_agent.py`

```python
"""
FILE: src/agents/icp_discovery_agent.py
PURPOSE: Orchestrate ICP extraction using modular skills
PHASE: 11 (ICP Discovery)
TASK: ICP-012
"""

import asyncio
from typing import Optional
from pydantic import BaseModel

from src.agents.base_agent import BaseAgent
from src.agents.skills.base_skill import SkillRegistry
from src.agents.skills.portfolio_extractor import PortfolioCompany
from src.agents.skills.icp_deriver import EnrichedCompany
from src.agents.skills.als_weight_suggester import ICPProfile
from src.engines.icp_scraper import ICPScraperEngine
from src.integrations.anthropic import AnthropicClient


class FullICPProfile(BaseModel):
    company_name: Optional[str] = None
    services_offered: list[str] = []
    value_proposition: Optional[str] = None
    team_size: Optional[int] = None
    size_range: Optional[str] = None
    years_in_business: Optional[int] = None
    locations: list[str] = []
    icp_industries: list[str] = []
    icp_company_sizes: list[str] = []
    icp_revenue_range: Optional[str] = None
    icp_locations: list[str] = []
    icp_titles: list[str] = []
    pattern_description: Optional[str] = None
    portfolio_companies: list[PortfolioCompany] = []
    enriched_portfolio: list[EnrichedCompany] = []
    als_weights: dict[str, int] = {}
    extraction_confidence: float = 0.0
    data_sources: list[str] = []


class ICPDiscoveryAgent(BaseAgent):
    """Orchestrate ICP extraction using modular skills."""
    
    def __init__(self, scraper: ICPScraperEngine, anthropic: AnthropicClient):
        self.scraper = scraper
        self.anthropic = anthropic
        self.skills = {
            "parse_website": SkillRegistry.get("parse_website"),
            "extract_services": SkillRegistry.get("extract_services"),
            "extract_value_prop": SkillRegistry.get("extract_value_prop"),
            "extract_portfolio": SkillRegistry.get("extract_portfolio"),
            "classify_industries": SkillRegistry.get("classify_industries"),
            "estimate_company_size": SkillRegistry.get("estimate_company_size"),
            "derive_icp": SkillRegistry.get("derive_icp"),
            "suggest_als_weights": SkillRegistry.get("suggest_als_weights"),
        }
    
    async def use_skill(self, skill_name: str, **kwargs):
        skill = self.skills[skill_name]
        input_data = skill.validate_input(kwargs)
        return await skill.execute(input_data, self.anthropic)
    
    async def extract_icp(self, website_url: str) -> FullICPProfile:
        data_sources = ["website"]
        
        # 1. Scrape
        raw_html = await self.scraper.scrape_website(website_url)
        
        # 2. Parse
        parsed = await self.use_skill("parse_website", html=raw_html, url=website_url)
        
        # 3. LinkedIn data
        linkedin_data = None
        if parsed.company_name:
            domain = website_url.replace("https://", "").replace("http://", "").split("/")[0]
            linkedin_data = await self.scraper.get_linkedin_data(parsed.company_name, domain)
            if linkedin_data:
                data_sources.append("linkedin")
        
        # 4. Extract (parallel)
        services_result, value_prop_result, portfolio_result, size_result = await asyncio.gather(
            self.use_skill("extract_services", pages=parsed.pages),
            self.use_skill("extract_value_prop", pages=parsed.pages),
            self.use_skill("extract_portfolio", pages=parsed.pages),
            self.use_skill("estimate_company_size", pages=parsed.pages, linkedin_data=linkedin_data),
        )
        
        # 5. Enrich portfolio
        enriched_portfolio = []
        if portfolio_result.companies:
            enriched_portfolio = await self.scraper.enrich_portfolio(portfolio_result.companies)
            if enriched_portfolio:
                data_sources.append("apollo")
        
        # 6. Classify industries
        industries_result = await self.use_skill("classify_industries",
            services=services_result.services,
            portfolio=portfolio_result.companies,
            industries_mentioned=portfolio_result.industries_served
        )
        
        # 7. Derive ICP
        icp_result = await self.use_skill("derive_icp",
            enriched_portfolio=enriched_portfolio,
            services=services_result.services
        )
        
        # 8. Suggest weights
        icp_for_weights = ICPProfile(
            services_offered=services_result.services,
            icp_industries=icp_result.icp_industries,
            icp_company_sizes=icp_result.icp_company_sizes,
            icp_locations=icp_result.icp_locations,
            icp_titles=icp_result.icp_titles,
        )
        weights_result = await self.use_skill("suggest_als_weights", icp_profile=icp_for_weights)
        
        # Calculate confidence
        confidences = [
            services_result.confidence,
            value_prop_result.confidence,
            portfolio_result.confidence,
            size_result.confidence,
            industries_result.confidence,
            icp_result.confidence,
        ]
        avg_confidence = sum(confidences) / len(confidences)
        
        return FullICPProfile(
            company_name=parsed.company_name,
            services_offered=services_result.services,
            value_proposition=value_prop_result.value_proposition,
            team_size=size_result.team_size,
            size_range=size_result.size_range,
            years_in_business=size_result.years_in_business,
            locations=size_result.locations,
            icp_industries=icp_result.icp_industries,
            icp_company_sizes=icp_result.icp_company_sizes,
            icp_revenue_range=icp_result.icp_revenue_range,
            icp_locations=icp_result.icp_locations,
            icp_titles=icp_result.icp_titles,
            pattern_description=icp_result.pattern_description,
            portfolio_companies=portfolio_result.companies,
            enriched_portfolio=enriched_portfolio,
            als_weights=weights_result.weights,
            extraction_confidence=avg_confidence,
            data_sources=data_sources,
        )
```

---

### ICP-013: Onboarding API Routes

**File:** `src/api/routes/onboarding.py`

Create endpoints:
- POST `/api/v1/onboarding/analyze` - Start extraction job
- GET `/api/v1/onboarding/status/{job_id}` - Check status
- GET `/api/v1/onboarding/result/{job_id}` - Get result
- POST `/api/v1/onboarding/confirm` - Confirm ICP
- GET `/api/v1/clients/{id}/icp` - Get client ICP
- PUT `/api/v1/clients/{id}/icp` - Update client ICP

Register in `src/api/main.py`.

---

### ICP-014: Onboarding Flow

**File:** `src/orchestration/flows/onboarding_flow.py`

Prefect flow for async ICP extraction.

---

### ICP-015: Onboarding UI

**File:** `frontend/app/onboarding/page.tsx`

1. Website URL input
2. Loading with progress
3. Confirm/edit ICP
4. Save → dashboard

---

### ICP-016 & ICP-017: Already Complete

Verify existing pages work with new backend.

---

### ICP-018: Skill Unit Tests

**Directory:** `tests/test_skills/`

Test each skill independently.

---

## FILES TO CREATE

1. `supabase/migrations/012_client_icp_profile.sql`
2. `src/agents/skills/__init__.py`
3. `src/agents/skills/base_skill.py`
4. `src/agents/skills/website_parser.py`
5. `src/agents/skills/service_extractor.py`
6. `src/agents/skills/value_prop_extractor.py`
7. `src/agents/skills/portfolio_extractor.py`
8. `src/agents/skills/industry_classifier.py`
9. `src/agents/skills/company_size_estimator.py`
10. `src/agents/skills/icp_deriver.py`
11. `src/agents/skills/als_weight_suggester.py`
12. `src/engines/icp_scraper.py`
13. `src/agents/icp_discovery_agent.py`
14. `src/api/routes/onboarding.py`
15. `src/orchestration/flows/onboarding_flow.py`
16. `frontend/app/onboarding/page.tsx`
17. `tests/test_skills/*.py`

## VERIFICATION CHECKLIST

- [ ] Migration applies
- [ ] All 8 skills registered
- [ ] ICP Scraper Engine fetches data
- [ ] ICP Discovery Agent orchestrates skills
- [ ] API endpoints work
- [ ] Prefect flow runs
- [ ] Onboarding UI works
- [ ] Skills have unit tests
