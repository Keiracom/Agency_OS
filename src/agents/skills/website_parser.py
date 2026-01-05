"""
FILE: src/agents/skills/website_parser.py
TASK: ICP-003
PHASE: 11 (ICP Discovery System)
PURPOSE: Parse raw website HTML into structured page content for downstream skills

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/integrations/anthropic.py

EXPORTS:
- WebsiteParserSkill
- PageContent (output model)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient


class PageContent(BaseModel):
    """
    Structured content extracted from a single page.

    Represents the essential information from a webpage
    in a format suitable for further analysis.
    """

    url: str = Field(description="Page URL")
    title: str = Field(description="Page title")
    page_type: str = Field(
        description="Type of page: home, about, services, portfolio, case_studies, contact, blog, team, careers, other"
    )
    headings: list[str] = Field(
        default_factory=list,
        description="Main headings from the page (H1, H2)"
    )
    content_summary: str = Field(
        description="Summary of main content (max 500 chars)"
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="Key bullet points or highlights"
    )
    images_described: list[str] = Field(
        default_factory=list,
        description="Descriptions of important images (logos, team photos, etc.)"
    )
    ctas: list[str] = Field(
        default_factory=list,
        description="Call-to-action buttons/links found"
    )
    has_testimonials: bool = Field(
        default=False,
        description="Whether page contains testimonials"
    )
    has_case_studies: bool = Field(
        default=False,
        description="Whether page contains case studies"
    )
    has_client_logos: bool = Field(
        default=False,
        description="Whether page contains client logos"
    )
    social_links: dict[str, str] = Field(
        default_factory=dict,
        description="Social media links found on page: {linkedin, instagram, facebook, twitter}"
    )


class WebsiteParserSkill(BaseSkill["WebsiteParserSkill.Input", "WebsiteParserSkill.Output"]):
    """
    Parse raw website HTML into structured page content.

    This skill takes raw HTML content and extracts:
    - Company name and branding
    - Navigation structure
    - Page-by-page content breakdown
    - Key elements (testimonials, logos, CTAs)

    The output is used by downstream skills for:
    - Service extraction
    - Value proposition analysis
    - Portfolio discovery
    - Industry classification
    """

    name = "parse_website"
    description = "Extract structured content from raw website HTML for ICP analysis"

    class Input(BaseModel):
        """Input for website parsing."""

        html: str = Field(
            description="Raw HTML content of the website (may be concatenated multi-page)"
        )
        url: str = Field(
            description="Base URL of the website"
        )
        page_urls: list[str] = Field(
            default_factory=list,
            description="List of page URLs included in the HTML (if multi-page scrape)"
        )

    class Output(BaseModel):
        """Output from website parsing."""

        company_name: str = Field(
            description="Detected company/agency name"
        )
        domain: str = Field(
            description="Website domain"
        )
        navigation: list[str] = Field(
            default_factory=list,
            description="Main navigation items found"
        )
        pages: list[PageContent] = Field(
            default_factory=list,
            description="Structured content from each page"
        )
        meta_description: str = Field(
            default="",
            description="Site meta description if found"
        )
        social_links: list[str] = Field(
            default_factory=list,
            description="Social media links found (LinkedIn, Twitter, etc.)"
        )
        contact_info: dict = Field(
            default_factory=dict,
            description="Contact information found (email, phone, address)"
        )

    system_prompt = """You are a website content analyst specializing in marketing agency websites.
Your task is to parse raw HTML and extract structured information.

EXTRACTION GUIDELINES:
1. Identify the company name from logo, title, or prominent branding
2. Extract the main navigation structure
3. For each identifiable page section, extract:
   - Page type (home, about, services, portfolio, case_studies, contact, blog, team, careers, other)
   - Main headings and content summary
   - Key points and highlights
   - CTAs and important elements
   - Social links found on that page (usually in header/footer)
4. Note presence of testimonials, case studies, and client logos
5. Extract social links and contact information

SOCIAL LINKS EXTRACTION:
- Look for social media links in header and footer sections
- Extract LinkedIn company page URL (linkedin.com/company/...)
- Extract Instagram profile URL (instagram.com/...)
- Extract Facebook page URL (facebook.com/...)
- Extract Twitter/X profile URL (twitter.com/... or x.com/...)
- For each page, include a social_links dict with the platform as key and URL as value
- Also aggregate all social links at the top level

OUTPUT FORMAT:
Return valid JSON matching this structure:
{
    "company_name": "Agency Name",
    "domain": "example.com",
    "navigation": ["Home", "About", "Services", "Work", "Contact"],
    "pages": [
        {
            "url": "https://example.com/",
            "title": "Home",
            "page_type": "home",
            "headings": ["We Build Brands", "Our Services"],
            "content_summary": "Brief summary of page content...",
            "key_points": ["Point 1", "Point 2"],
            "images_described": ["Company logo", "Team photo"],
            "ctas": ["Get Started", "Contact Us"],
            "has_testimonials": true,
            "has_case_studies": false,
            "has_client_logos": true,
            "social_links": {
                "linkedin": "https://linkedin.com/company/agencyname",
                "instagram": "https://instagram.com/agencyname",
                "facebook": "https://facebook.com/agencyname",
                "twitter": "https://twitter.com/agencyname"
            }
        }
    ],
    "meta_description": "Site description...",
    "social_links": ["https://linkedin.com/company/...", "https://twitter.com/..."],
    "contact_info": {
        "email": "hello@example.com",
        "phone": "+61 2 1234 5678",
        "address": "Sydney, Australia"
    }
}

IMPORTANT:
- Extract actual content, not placeholder text
- If a field cannot be determined, use reasonable defaults
- Limit content_summary to 500 characters
- Be thorough but concise in your extraction
- Social links may only appear on certain pages (usually home) - extract them where found"""

    default_max_tokens = 4096  # Larger output for comprehensive parsing
    default_temperature = 0.3  # Lower temperature for accurate extraction

    def build_prompt(self, input_data: Input) -> str:
        """Build the prompt for website parsing."""
        page_list = ""
        if input_data.page_urls:
            page_list = f"\n\nPages included:\n" + "\n".join(
                f"- {url}" for url in input_data.page_urls
            )

        # Truncate HTML if too long (Claude has context limits)
        html = input_data.html
        if len(html) > 100000:
            html = html[:100000] + "\n\n[CONTENT TRUNCATED]"

        return f"""Parse the following website HTML and extract structured content.

Website URL: {input_data.url}
{page_list}

HTML CONTENT:
{html}

Extract all relevant information following the guidelines. Return valid JSON."""

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute website parsing.

        Args:
            input_data: Validated input with HTML and URL
            anthropic: Anthropic client for AI calls

        Returns:
            SkillResult containing parsed website content
        """
        # Check for empty HTML before calling AI
        if not input_data.html or len(input_data.html.strip()) < 100:
            return SkillResult.fail(
                error="Website returned no HTML content. The site may require JavaScript rendering or have anti-bot protection.",
                metadata={"url": input_data.url, "html_length": len(input_data.html) if input_data.html else 0},
            )

        prompt = self.build_prompt(input_data)

        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            # Convert pages to PageContent objects
            pages = []
            for page_data in parsed.get("pages", []):
                pages.append(PageContent(**page_data))

            output = self.Output(
                company_name=parsed.get("company_name", "Unknown"),
                domain=parsed.get("domain", input_data.url.split("/")[2] if "/" in input_data.url else input_data.url),
                navigation=parsed.get("navigation", []),
                pages=pages,
                meta_description=parsed.get("meta_description", ""),
                social_links=parsed.get("social_links", []),
                contact_info=parsed.get("contact_info", {}),
            )

            return SkillResult.ok(
                data=output,
                confidence=0.85,  # Website parsing is generally reliable
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "pages_parsed": len(pages),
                    "has_navigation": len(output.navigation) > 0,
                },
            )

        except Exception as e:
            return SkillResult.fail(
                error=f"Website parsing failed: {str(e)}",
                metadata={"url": input_data.url},
            )


# Register skill instance
SkillRegistry.register(WebsiteParserSkill())


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
- [x] build_prompt method for custom prompt construction
- [x] execute method with full implementation
- [x] Error handling with SkillResult.fail
- [x] Registered with SkillRegistry
- [x] PageContent model exported for other skills
"""
