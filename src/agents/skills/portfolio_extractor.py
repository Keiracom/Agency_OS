"""
FILE: src/agents/skills/portfolio_extractor.py
TASK: ICP-006, ICP-FIX-001
PHASE: 11 (ICP Discovery System), 18-B (ICP Enrichment Fix)
PURPOSE: Extract client logos, case studies, and testimonials from agency website

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/agents/skills/website_parser.py (for PageContent)
- src/integrations/anthropic.py

EXPORTS:
- PortfolioExtractorSkill
- PortfolioCompany (output model)

FIXES (Phase 18-B):
- ICP-FIX-001: Increased max_chars from 30KB to 100KB to prevent data loss
- ICP-FIX-004: Added DEBUG logging for extraction pipeline visibility
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult
from src.agents.skills.website_parser import PageContent

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


def _extract_portfolio_sections(raw_html: str, max_chars: int = 100000) -> str:
    """
    Extract relevant sections from raw HTML for portfolio extraction.

    Focuses on testimonials, case studies, client logos, and about sections
    to find company names without sending the full 400KB+ HTML.

    Args:
        raw_html: Full raw HTML from website scrape
        max_chars: Maximum characters to return (increased from 30KB to 100KB in ICP-FIX-001)

    Returns:
        Extracted sections with context markers
    """
    if not raw_html:
        logger.debug("_extract_portfolio_sections: No raw HTML provided")
        return ""

    logger.debug(f"_extract_portfolio_sections: Processing {len(raw_html):,} chars of raw HTML (limit: {max_chars:,})")

    sections = []

    # Pattern definitions for relevant sections
    patterns = [
        # Testimonials
        (r'(?i)<(?:div|section)[^>]*(?:testimonial|review|quote|feedback)[^>]*>.*?</(?:div|section)>', 'TESTIMONIALS'),
        (r'(?i)<blockquote[^>]*>.*?</blockquote>', 'QUOTE'),
        # Case studies
        (r'(?i)<(?:div|section|article)[^>]*(?:case.?study|portfolio|work|project)[^>]*>.*?</(?:div|section|article)>', 'CASE_STUDIES'),
        # Client logos
        (r'(?i)<(?:div|section)[^>]*(?:client|partner|logo|trusted|brand)[^>]*>.*?</(?:div|section)>', 'CLIENT_LOGOS'),
        # Image alt text (often contains client names)
        (r'<img[^>]*alt=["\']([^"\']+)["\'][^>]*>', 'IMAGE_ALT'),
        # About/team sections for context
        (r'(?i)<(?:div|section)[^>]*(?:about|team|story)[^>]*>.*?</(?:div|section)>', 'ABOUT'),
    ]

    # Extract matching sections
    for pattern, label in patterns:
        try:
            matches = re.findall(pattern, raw_html, re.DOTALL)
            for match in matches[:10]:  # Limit matches per pattern
                if isinstance(match, str) and len(match) > 50:
                    # Clean up HTML but preserve text
                    text = re.sub(r'<[^>]+>', ' ', match)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text and len(text) > 20:
                        sections.append(f"[{label}]\n{text[:2000]}\n")
        except re.error:
            continue

    # Also extract all image alt texts (client logos often hidden in alt)
    alt_pattern = r'<img[^>]*alt=["\']([^"\']{3,100})["\'][^>]*>'
    alt_texts = re.findall(alt_pattern, raw_html, re.IGNORECASE)
    if alt_texts:
        unique_alts = list(set(alt_texts))[:50]
        sections.append(f"[IMAGE_ALTS]\n{', '.join(unique_alts)}\n")

    # ICP-FIX-007: Extract company names from case study/portfolio URLs
    # Many sites have URLs like /case-study/company-name/ or /work/client-name/
    url_patterns = [
        r'href="[^"]*(?:case-study|case-studies|portfolio|our-work|work|clients?)/([a-zA-Z0-9-]+)/?["\']',
        r'href=\'[^\']*(?:case-study|case-studies|portfolio|our-work|work|clients?)/([a-zA-Z0-9-]+)/?["\']',
    ]

    url_companies = []
    for pattern in url_patterns:
        try:
            matches = re.findall(pattern, raw_html, re.IGNORECASE)
            for slug in matches:
                # Convert slug to company name: "kustom-timber" → "Kustom Timber"
                if slug and len(slug) > 2 and slug not in ["index", "page", "all", "view"]:
                    company_name = " ".join(word.capitalize() for word in slug.split("-"))
                    url_companies.append(company_name)
        except re.error:
            continue

    if url_companies:
        unique_url_companies = list(set(url_companies))[:50]
        logger.debug(f"Extracted {len(unique_url_companies)} companies from URLs: {unique_url_companies[:10]}")
        sections.append(f"[CASE_STUDY_URLS]\n{', '.join(unique_url_companies)}\n")

    # Extract any names that look like company names from the full text
    # This catches mentions in prose that might not be in specific sections
    company_patterns = [
        r'(?:worked with|client|partner|helped|trusted by|featuring)[:\s]+([A-Z][a-zA-Z\s&]+(?:Pty Ltd|Ltd|Inc|Corp|Co\.?)?)',
        r'(?:testimonial from|quote from|says)[:\s]+([A-Z][a-zA-Z\s]+)',
    ]

    for pattern in company_patterns:
        try:
            matches = re.findall(pattern, raw_html)
            if matches:
                unique_matches = list(set(m.strip() for m in matches if len(m.strip()) > 2))[:30]
                if unique_matches:
                    sections.append(f"[MENTIONED_COMPANIES]\n{', '.join(unique_matches)}\n")
        except re.error:
            continue

    result = "\n---\n".join(sections)

    # Truncate if too long
    if len(result) > max_chars:
        logger.warning(
            f"_extract_portfolio_sections: Result truncated from {len(result):,} to {max_chars:,} chars"
        )
        result = result[:max_chars] + "\n\n[CONTENT TRUNCATED]"

    logger.debug(
        f"_extract_portfolio_sections: Extracted {len(sections)} sections, {len(result):,} chars total"
    )
    return result


class PortfolioCompany(BaseModel):
    """
    Information about a client company from portfolio.

    Represents a company mentioned in case studies,
    client logos, or testimonials.
    """

    company_name: str = Field(description="Company name")
    company_domain: str | None = Field(
        default=None,
        description="Company website domain if identifiable"
    )
    source: str = Field(
        description="How discovered: logo, case_study, testimonial, client_list"
    )
    industry_hint: str | None = Field(
        default=None,
        description="Industry if mentioned or inferable"
    )
    testimonial_person: str | None = Field(
        default=None,
        description="Person who gave testimonial (if applicable)"
    )
    testimonial_title: str | None = Field(
        default=None,
        description="Title of testimonial person"
    )
    testimonial_text: str | None = Field(
        default=None,
        description="Testimonial content (if available)"
    )
    case_study_summary: str | None = Field(
        default=None,
        description="Brief summary of case study (if applicable)"
    )
    results_mentioned: list[str] = Field(
        default_factory=list,
        description="Results or metrics mentioned"
    )


class PortfolioExtractorSkill(BaseSkill["PortfolioExtractorSkill.Input", "PortfolioExtractorSkill.Output"]):
    """
    Extract client portfolio from website content.

    This skill identifies:
    - Client logos displayed
    - Case studies with company names
    - Testimonials with company/person info
    - Results and metrics mentioned

    The portfolio data is crucial for deriving ICP,
    as existing clients reveal the agency's ideal targets.
    """

    name = "extract_portfolio"
    description = "Find client logos, case studies, and testimonials from website"

    class Input(BaseModel):
        """Input for portfolio extraction."""

        pages: list[PageContent] = Field(
            description="Parsed page content from website"
        )
        company_name: str = Field(
            default="",
            description="Agency name for context"
        )
        raw_html: str = Field(
            default="",
            description="Raw HTML content for extracting company names from testimonials/case studies"
        )

    class Output(BaseModel):
        """Output from portfolio extraction."""

        companies: list[PortfolioCompany] = Field(
            default_factory=list,
            description="Companies identified from portfolio"
        )
        total_clients_claimed: int | None = Field(
            default=None,
            description="Number of clients claimed (if mentioned, e.g., '100+ clients')"
        )
        notable_brands: list[str] = Field(
            default_factory=list,
            description="Well-known brand names identified"
        )
        industries_represented: list[str] = Field(
            default_factory=list,
            description="Industries found in portfolio"
        )
        source_distribution: dict = Field(
            default_factory=dict,
            description="Count by source: {logo: X, case_study: Y, testimonial: Z}"
        )
        confidence: float = Field(
            default=0.0,
            description="Confidence in extraction (0.0-1.0)"
        )

    system_prompt = """You are a portfolio analyst extracting client information from agency websites.

CRITICAL: Your primary goal is to extract EVERY company name mentioned in testimonials, case studies, and client sections.
The raw HTML sections provided contain the actual text where company names appear - extract them ALL.

EXTRACTION GUIDELINES:

1. CLIENT LOGOS (Source: "logo"):
   - Look for "Our Clients", "Trusted by", logo grids
   - Extract company names from IMAGE_ALTS section (alt text often contains logo names)
   - IMPORTANT: Image alt text like "Vermeer logo" means the client is "Vermeer"

2. CASE STUDIES (Source: "case_study"):
   - Look for "Work", "Portfolio", "Case Studies" pages
   - Extract EVERY company name mentioned in case study sections
   - Note industry and results if available
   - Names often appear as headings or in attribution

3. TESTIMONIALS (Source: "testimonial"):
   - Extract company names from attribution lines (e.g., "John Smith, CEO at Acme Corp")
   - Look for patterns: "- Name, Title, Company" or "Name from Company"
   - Extract testimonial_person, testimonial_title, and company_name
   - CRITICAL: The company name is the CLIENT, extract it even if only partially visible

4. CASE_STUDY_URLS (ICP-FIX-007):
   - The RAW HTML SECTIONS may contain a [CASE_STUDY_URLS] section
   - These are company names extracted from case study/portfolio URLs
   - URLs like /case-study/kustom-timber/ become "Kustom Timber"
   - CRITICAL: Add ALL companies from this section - they are confirmed clients
   - Set source="case_study" for these companies

5. MENTIONED_COMPANIES:
   - The RAW HTML SECTIONS may contain a [MENTIONED_COMPANIES] section
   - These are companies explicitly mentioned in the text - add them all

6. INDUSTRIES:
   - Infer industry from company names and context
   - Common: mining, construction, healthcare, retail, manufacturing, professional_services, real_estate, education, automotive

7. NOTABLE BRANDS:
   - Flag well-known companies (Fortune 500, household names, major Australian companies)
   - Include large Australian companies (BHP, Telstra, Woolworths, etc.)

IMPORTANT REMINDERS:
- Extract ALL company names, even if you only have partial information
- A name like "APM" or "Vermeer" is a valid company name - include it
- If a testimonial mentions a person's company, that company is a CLIENT
- Better to include a company with minimal info than to miss it entirely

OUTPUT FORMAT:
Return valid JSON:
{
    "companies": [
        {
            "company_name": "Vermeer",
            "company_domain": null,
            "source": "testimonial",
            "industry_hint": "mining",
            "testimonial_person": "John Smith",
            "testimonial_title": "Marketing Manager",
            "testimonial_text": "Dilate helped us achieve...",
            "case_study_summary": null,
            "results_mentioned": []
        },
        {
            "company_name": "Kustom Timber",
            "company_domain": "kustomtimber.com.au",
            "source": "case_study",
            "industry_hint": "manufacturing",
            "testimonial_person": null,
            "testimonial_title": null,
            "testimonial_text": null,
            "case_study_summary": "Increased online leads by 300%",
            "results_mentioned": ["300% lead increase"]
        }
    ],
    "total_clients_claimed": 150,
    "notable_brands": ["APM", "Vermeer"],
    "industries_represented": ["mining", "manufacturing", "retail", "construction"],
    "source_distribution": {
        "logo": 8,
        "case_study": 4,
        "testimonial": 6
    },
    "confidence": 0.85
}"""

    default_max_tokens = 3072
    default_temperature = 0.3

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for portfolio extraction."""
        pages_text = []
        for page in input_data.pages:
            # Include more detail for portfolio-relevant pages
            if page.page_type in ["portfolio", "case_studies", "home", "about"]:
                page_info = f"""
PAGE: {page.page_type.upper()} ({page.url})
Title: {page.title}
Headings: {', '.join(page.headings)}
Summary: {page.content_summary}
Key Points: {', '.join(page.key_points)}
Images: {', '.join(page.images_described)}
Has Client Logos: {page.has_client_logos}
Has Case Studies: {page.has_case_studies}
Has Testimonials: {page.has_testimonials}
"""
                pages_text.append(page_info)
            elif page.has_testimonials or page.has_client_logos or page.has_case_studies:
                page_info = f"""
PAGE: {page.page_type.upper()}
Summary: {page.content_summary}
Has Client Logos: {page.has_client_logos}
Has Case Studies: {page.has_case_studies}
Has Testimonials: {page.has_testimonials}
"""
                pages_text.append(page_info)

        if not pages_text:
            # Fallback to all pages if no relevant ones found
            for page in input_data.pages[:5]:
                pages_text.append(f"""
PAGE: {page.page_type.upper()}
Summary: {page.content_summary}
Key Points: {', '.join(page.key_points)}
""")

        context = f"Agency: {input_data.company_name}\n\n" if input_data.company_name else ""

        # Extract relevant sections from raw HTML
        raw_html_sections = ""
        if input_data.raw_html:
            extracted = _extract_portfolio_sections(input_data.raw_html)
            if extracted:
                raw_html_sections = f"""

=== RAW HTML SECTIONS (Contains actual company names) ===
{extracted}
=== END RAW HTML SECTIONS ===

IMPORTANT: The sections above contain the ACTUAL TEXT from testimonials, case studies, and client logos.
Extract ALL company names you find in these sections. These are the real client names!
"""

        return f"""{context}Extract client portfolio information from this website content:

{'---'.join(pages_text)}
{raw_html_sections}
Identify all clients, case studies, and testimonials. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute portfolio extraction.

        Args:
            input_data: Validated input with parsed pages
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing extracted portfolio
        """
        if not input_data.pages:
            return SkillResult.fail(
                error="No pages provided for portfolio extraction",
                metadata={"pages_count": 0},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Convert companies to PortfolioCompany objects
            companies = []
            for company_data in parsed.get("companies", []):
                companies.append(PortfolioCompany(**company_data))

            output = self.Output(
                companies=companies,
                total_clients_claimed=parsed.get("total_clients_claimed"),
                notable_brands=parsed.get("notable_brands", []),
                industries_represented=parsed.get("industries_represented", []),
                source_distribution=parsed.get("source_distribution", {}),
                confidence=parsed.get("confidence", 0.7),
            )

            return SkillResult.ok(
                data=output,
                confidence=output.confidence,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "companies_found": len(companies),
                    "case_studies": len([c for c in companies if c.source == "case_study"]),
                    "testimonials": len([c for c in companies if c.source == "testimonial"]),
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Portfolio extraction failed: {str(e)}",
                metadata={"pages_analyzed": len(input_data.pages)},
            )


# Register skill instance
SkillRegistry.register(PortfolioExtractorSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output Pydantic models defined
- [x] System prompt with clear instructions
- [x] Source types defined (logo, case_study, testimonial)
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
- [x] PortfolioCompany model exported
"""
