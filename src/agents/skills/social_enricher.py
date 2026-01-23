"""
Contract: src/agents/skills/social_enricher.py
Purpose: Extract additional portfolio companies from agency social media profiles
Layer: 4 - agents/skills
Imports: agents.skills.base_skill, integrations
Consumers: ICP discovery agent

FILE: src/agents/skills/social_enricher.py
TASK: ICP-SOC-002 (Repurposed)
PHASE: 18-B (ICP Enrichment)
PURPOSE: Extract additional portfolio companies from agency social media profiles

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/integrations/apify.py
- src/integrations/anthropic.py

EXPORTS:
- SocialClientExtractorSkill
- ExtractedClients (output model)

HOW IT HELPS FIND LEADS:
1. Scrapes agency's LinkedIn description, Instagram bio, Facebook about
2. Uses Claude to extract client/company names mentioned
3. Returns additional portfolio companies to enrich via Apollo
4. More portfolio data -> Better ICP derivation -> More accurate lead targeting
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)


class ExtractedClient(BaseModel):
    """A client/company extracted from social media text."""

    company_name: str = Field(description="Company name")
    source: str = Field(description="Where it was found: linkedin, instagram, facebook, google")
    context: str = Field(default="", description="Surrounding context (e.g., 'case study', 'testimonial')")
    confidence: float = Field(default=0.8, description="Confidence this is a real client (0.0-1.0)")


class SocialTextContent(BaseModel):
    """Text content collected from social profiles."""

    linkedin_description: Optional[str] = None
    linkedin_specialties: list[str] = Field(default_factory=list)
    instagram_bio: Optional[str] = None
    facebook_about: Optional[str] = None
    google_category: Optional[str] = None


class SocialClientExtractorSkill(BaseSkill["SocialClientExtractorSkill.Input", "SocialClientExtractorSkill.Output"]):
    """
    Extract portfolio company names from agency social media profiles.

    This skill:
    1. Fetches social profile data (descriptions, bios) via Apify
    2. Uses Claude to identify company/client names mentioned
    3. Returns additional portfolio companies for Apollo enrichment

    Use case: Agency LinkedIn descriptions often mention key clients:
    "We've helped brands like Nike, Coca-Cola, and local businesses..."
    → Extracts ["Nike", "Coca-Cola"] as additional portfolio companies
    """

    name = "extract_social_clients"
    description = "Extract client/company names from agency social media profiles"

    class Input(BaseModel):
        """Input for social client extraction."""

        company_name: str = Field(description="Agency name")
        # Option 1: Provide pre-scraped text content (avoids re-scraping)
        linkedin_description: Optional[str] = Field(default=None, description="Pre-scraped LinkedIn description")
        linkedin_specialties: list[str] = Field(default_factory=list, description="Pre-scraped LinkedIn specialties")
        instagram_bio: Optional[str] = Field(default=None, description="Pre-scraped Instagram bio")
        facebook_about: Optional[str] = Field(default=None, description="Pre-scraped Facebook about")
        # Option 2: Provide URLs to scrape (only used if pre-scraped content not provided)
        linkedin_url: Optional[str] = Field(default=None, description="LinkedIn company URL (fallback)")
        instagram_url: Optional[str] = Field(default=None, description="Instagram profile URL (fallback)")
        facebook_url: Optional[str] = Field(default=None, description="Facebook page URL (fallback)")
        location: str = Field(default="Australia", description="Location for Google Business search")
        existing_portfolio: list[str] = Field(
            default_factory=list,
            description="Already known portfolio companies (to avoid duplicates)"
        )

    class Output(BaseModel):
        """Output from social client extraction."""

        extracted_clients: list[ExtractedClient] = Field(
            default_factory=list,
            description="Client companies extracted from social profiles"
        )
        social_content: SocialTextContent = Field(
            default_factory=SocialTextContent,
            description="Raw text content collected from social profiles"
        )
        new_companies_count: int = Field(
            default=0,
            description="Number of new companies found (not in existing portfolio)"
        )

    system_prompt = """You are an expert at extracting company/client names from marketing text.

TASK: Extract company names that appear to be CLIENTS of this agency from their social media descriptions.

LOOK FOR:
- Client names in testimonials: "Helped X achieve..."
- Case study mentions: "Our work with Y..."
- Client lists: "Trusted by A, B, C..."
- Partnership mentions: "Partnering with..."
- Logo/brand references: "Brands we've worked with..."

DO NOT EXTRACT:
- The agency's own name
- Generic terms (small businesses, startups, enterprises)
- Service descriptions
- Tool/software names (unless they're clients)
- Industry categories

OUTPUT FORMAT (JSON):
{
    "clients": [
        {"name": "Company Name", "context": "case study", "confidence": 0.9},
        {"name": "Another Co", "context": "testimonial", "confidence": 0.7}
    ]
}

Be conservative - only extract names that clearly appear to be clients, not just mentioned companies."""

    default_max_tokens = 1000
    default_temperature = 0.1

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute social client extraction.

        1. Use pre-scraped content if available, otherwise fetch from Apify
        2. Use Claude to extract client names from text content
        3. Return new companies not already in portfolio
        """
        from src.integrations.apify import get_apify_client

        social_content = SocialTextContent()
        all_text_parts = []
        errors = []

        # Check if we have pre-scraped content
        has_prescraped = (
            input_data.linkedin_description
            or input_data.linkedin_specialties
            or input_data.instagram_bio
            or input_data.facebook_about
        )

        if has_prescraped:
            # Use pre-scraped content (no API calls needed)
            logger.info("Using pre-scraped social content for client extraction")

            if input_data.linkedin_description:
                social_content.linkedin_description = input_data.linkedin_description
                all_text_parts.append(f"LINKEDIN DESCRIPTION:\n{input_data.linkedin_description}")

            if input_data.linkedin_specialties:
                social_content.linkedin_specialties = input_data.linkedin_specialties
                all_text_parts.append(f"LINKEDIN SPECIALTIES:\n{', '.join(input_data.linkedin_specialties)}")

            if input_data.instagram_bio:
                social_content.instagram_bio = input_data.instagram_bio
                all_text_parts.append(f"INSTAGRAM BIO:\n{input_data.instagram_bio}")

            if input_data.facebook_about:
                social_content.facebook_about = input_data.facebook_about
                all_text_parts.append(f"FACEBOOK ABOUT:\n{input_data.facebook_about}")
        else:
            # Fallback: Fetch from Apify if URLs provided
            apify = get_apify_client()

            # Fetch LinkedIn
            if input_data.linkedin_url:
                try:
                    logger.info(f"Fetching LinkedIn for client extraction: {input_data.linkedin_url}")
                    data = await apify.scrape_linkedin_company(input_data.linkedin_url)
                    if data.get("found"):
                        description = data.get("description", "")
                        specialties = data.get("specialties", [])
                        social_content.linkedin_description = description
                        social_content.linkedin_specialties = specialties
                        if description:
                            all_text_parts.append(f"LINKEDIN DESCRIPTION:\n{description}")
                        if specialties:
                            all_text_parts.append(f"LINKEDIN SPECIALTIES:\n{', '.join(specialties)}")
                        logger.info(f"LinkedIn: {len(description)} chars description, {len(specialties)} specialties")
                except Exception as e:
                    logger.warning(f"LinkedIn fetch failed: {e}")
                    errors.append(f"linkedin: {str(e)}")

            # Fetch Instagram
            if input_data.instagram_url:
                try:
                    logger.info(f"Fetching Instagram for client extraction: {input_data.instagram_url}")
                    data = await apify.scrape_instagram_profile(input_data.instagram_url)
                    if data.get("found"):
                        bio = data.get("bio", "")
                        social_content.instagram_bio = bio
                        if bio:
                            all_text_parts.append(f"INSTAGRAM BIO:\n{bio}")
                        logger.info(f"Instagram: {len(bio)} chars bio")
                except Exception as e:
                    logger.warning(f"Instagram fetch failed: {e}")
                    errors.append(f"instagram: {str(e)}")

            # Fetch Facebook
            if input_data.facebook_url:
                try:
                    logger.info(f"Fetching Facebook for client extraction: {input_data.facebook_url}")
                    data = await apify.scrape_facebook_page(input_data.facebook_url)
                    if data.get("found"):
                        about = data.get("about", "") or data.get("description", "")
                        social_content.facebook_about = about
                        if about:
                            all_text_parts.append(f"FACEBOOK ABOUT:\n{about}")
                        logger.info(f"Facebook: {len(about)} chars about")
                except Exception as e:
                    logger.warning(f"Facebook fetch failed: {e}")
                    errors.append(f"facebook: {str(e)}")

        # If no text content found, return empty result
        if not all_text_parts:
            logger.info("No social text content found for client extraction")
            return SkillResult.ok(
                data=self.Output(
                    extracted_clients=[],
                    social_content=social_content,
                    new_companies_count=0,
                ),
                confidence=0.0,
                tokens_used=0,
                cost_aud=0.0,
                metadata={"errors": errors, "text_sources": 0},
            )

        # Build prompt for Claude
        combined_text = "\n\n".join(all_text_parts)
        prompt = f"""Agency: {input_data.company_name}

{combined_text}

Extract any client/company names mentioned. Return JSON with "clients" array."""

        # Call Claude to extract client names
        try:
            parsed, tokens, cost = await self._call_ai(anthropic, prompt)

            raw_clients = parsed.get("clients", [])
            extracted_clients = []

            # Normalize existing portfolio for comparison
            existing_normalized = {
                self._normalize_name(name) for name in input_data.existing_portfolio
            }

            for client in raw_clients:
                name = client.get("name", "").strip()
                if not name or len(name) < 2:
                    continue

                # Skip if already in portfolio
                if self._normalize_name(name) in existing_normalized:
                    continue

                # Determine source based on where name might have appeared
                source = self._guess_source(name, social_content)

                extracted_clients.append(ExtractedClient(
                    company_name=name,
                    source=source,
                    context=client.get("context", ""),
                    confidence=client.get("confidence", 0.8),
                ))

            new_count = len(extracted_clients)
            logger.info(f"Extracted {new_count} new client names from social profiles")

            return SkillResult.ok(
                data=self.Output(
                    extracted_clients=extracted_clients,
                    social_content=social_content,
                    new_companies_count=new_count,
                ),
                confidence=0.8 if new_count > 0 else 0.3,
                tokens_used=tokens,
                cost_aud=cost,
                metadata={
                    "errors": errors,
                    "text_sources": len(all_text_parts),
                    "raw_clients_found": len(raw_clients),
                    "new_clients_after_dedup": new_count,
                },
            )

        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            return SkillResult.fail(
                error=f"Client extraction failed: {str(e)}",
                metadata={"errors": errors + [str(e)]},
            )

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for comparison."""
        # Remove common suffixes and normalize
        name = name.lower().strip()
        name = re.sub(r'\s+(pty|ltd|inc|llc|co|corp|company|limited)\.?$', '', name)
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

    def _guess_source(self, name: str, content: SocialTextContent) -> str:
        """Guess which social platform the name came from."""
        name_lower = name.lower()

        if content.linkedin_description and name_lower in content.linkedin_description.lower():
            return "linkedin"
        if content.instagram_bio and name_lower in content.instagram_bio.lower():
            return "instagram"
        if content.facebook_about and name_lower in content.facebook_about.lower():
            return "facebook"

        # Default to linkedin as most likely source for B2B clients
        return "linkedin"


# Register skill instance
SkillRegistry.register(SocialClientExtractorSkill())


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, TASK, PHASE, PURPOSE
- [x] Follows import hierarchy (Rule 12)
- [x] Type hints on all functions
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] Extends BaseSkill with proper generics
- [x] Input/Output Pydantic models defined
- [x] Uses existing Apify methods
- [x] Uses Claude for intelligent extraction
- [x] Deduplicates against existing portfolio
- [x] Error handling for each platform
- [x] Registered with SkillRegistry

USE CASE FLOW:
1. ICP extraction gets portfolio companies from website
2. SocialClientExtractorSkill finds MORE companies from social profiles
3. All companies get enriched via Apollo
4. ICPDeriver analyzes enriched companies → derives ICP
5. ICP used to find similar leads via Apollo search
"""
