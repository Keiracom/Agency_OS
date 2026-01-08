"""
FILE: src/agents/skills/social_enricher.py
TASK: ICP-SOC-002
PHASE: 18-B (ICP Enrichment)
PURPOSE: Enrich ICP with social media data from LinkedIn, Instagram, Facebook, Google

DEPENDENCIES:
- src/agents/skills/base_skill.py
- src/integrations/apify.py

EXPORTS:
- SocialEnricherSkill
- SocialProfile (output model)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from src.agents.skills.base_skill import BaseSkill, SkillRegistry, SkillResult

if TYPE_CHECKING:
    from src.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)


class LinkedInData(BaseModel):
    """LinkedIn company data."""

    url: Optional[str] = None
    followers: Optional[int] = None
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    specialties: list[str] = Field(default_factory=list)
    founded_year: Optional[int] = None


class InstagramData(BaseModel):
    """Instagram profile data."""

    url: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    bio: Optional[str] = None
    is_verified: bool = False


class FacebookData(BaseModel):
    """Facebook page data."""

    url: Optional[str] = None
    likes: Optional[int] = None
    followers: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    category: Optional[str] = None


class GoogleBusinessData(BaseModel):
    """Google Business data."""

    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None


class SocialProfile(BaseModel):
    """Combined social media profile data."""

    linkedin: Optional[LinkedInData] = None
    instagram: Optional[InstagramData] = None
    facebook: Optional[FacebookData] = None
    google_business: Optional[GoogleBusinessData] = None
    platforms_found: list[str] = Field(default_factory=list)
    total_social_followers: int = 0


class SocialEnricherSkill(BaseSkill["SocialEnricherSkill.Input", "SocialEnricherSkill.Output"]):
    """
    Enrich ICP with social media data.

    Uses Apify scrapers to fetch data from:
    - LinkedIn company page
    - Instagram profile
    - Facebook page
    - Google Business

    This data helps understand the agency's market presence
    and can be used to infer ICP characteristics.
    """

    name = "enrich_social"
    description = "Fetch social media data for ICP enrichment"

    class Input(BaseModel):
        """Input for social enrichment."""

        company_name: str = Field(description="Company name for Google Business search")
        linkedin_url: Optional[str] = Field(default=None, description="LinkedIn company URL")
        instagram_url: Optional[str] = Field(default=None, description="Instagram profile URL")
        facebook_url: Optional[str] = Field(default=None, description="Facebook page URL")
        location: str = Field(default="Australia", description="Location for Google Business search")

    class Output(BaseModel):
        """Output from social enrichment."""

        profile: SocialProfile = Field(description="Combined social profile data")

    # No AI call needed - this skill uses Apify APIs directly
    system_prompt = ""
    default_max_tokens = 0
    default_temperature = 0.0

    async def execute(
        self,
        input_data: Input,
        anthropic: "AnthropicClient",
    ) -> SkillResult[Output]:
        """
        Execute social enrichment.

        Args:
            input_data: Validated input with social URLs
            anthropic: Not used (Apify APIs instead)

        Returns:
            SkillResult containing social profile data
        """
        from src.integrations.apify import get_apify_client

        apify = get_apify_client()
        profile = SocialProfile()
        platforms_found = []
        total_followers = 0
        errors = []

        # LinkedIn
        if input_data.linkedin_url:
            try:
                logger.info(f"Fetching LinkedIn: {input_data.linkedin_url}")
                data = await apify.scrape_linkedin_company(input_data.linkedin_url)
                if data.get("found"):
                    profile.linkedin = LinkedInData(
                        url=input_data.linkedin_url,
                        followers=data.get("followers"),
                        employee_count=data.get("employee_count"),
                        employee_range=data.get("employee_range"),
                        industry=data.get("industry"),
                        headquarters=data.get("headquarters"),
                        specialties=data.get("specialties", []),
                        founded_year=data.get("founded_year"),
                    )
                    platforms_found.append("linkedin")
                    if data.get("followers"):
                        total_followers += data["followers"]
                    logger.info(f"LinkedIn: {data.get('followers')} followers, {data.get('employee_range')} employees")
            except Exception as e:
                logger.warning(f"LinkedIn enrichment failed: {e}")
                errors.append(f"linkedin: {str(e)}")

        # Instagram
        if input_data.instagram_url:
            try:
                logger.info(f"Fetching Instagram: {input_data.instagram_url}")
                data = await apify.scrape_instagram_profile(input_data.instagram_url)
                if data.get("found"):
                    profile.instagram = InstagramData(
                        url=input_data.instagram_url,
                        followers=data.get("followers"),
                        following=data.get("following"),
                        posts_count=data.get("posts_count"),
                        bio=data.get("bio"),
                        is_verified=data.get("is_verified", False),
                    )
                    platforms_found.append("instagram")
                    if data.get("followers"):
                        total_followers += data["followers"]
                    logger.info(f"Instagram: {data.get('followers')} followers")
            except Exception as e:
                logger.warning(f"Instagram enrichment failed: {e}")
                errors.append(f"instagram: {str(e)}")

        # Facebook
        if input_data.facebook_url:
            try:
                logger.info(f"Fetching Facebook: {input_data.facebook_url}")
                data = await apify.scrape_facebook_page(input_data.facebook_url)
                if data.get("found"):
                    profile.facebook = FacebookData(
                        url=input_data.facebook_url,
                        likes=data.get("likes"),
                        followers=data.get("followers"),
                        rating=data.get("rating"),
                        review_count=data.get("review_count"),
                        category=data.get("category"),
                    )
                    platforms_found.append("facebook")
                    if data.get("followers"):
                        total_followers += data["followers"]
                    logger.info(f"Facebook: {data.get('followers')} followers, {data.get('rating')} rating")
            except Exception as e:
                logger.warning(f"Facebook enrichment failed: {e}")
                errors.append(f"facebook: {str(e)}")

        # Google Business
        if input_data.company_name:
            try:
                logger.info(f"Fetching Google Business: {input_data.company_name}")
                data = await apify.scrape_google_business(
                    input_data.company_name,
                    input_data.location,
                )
                if data.get("found"):
                    profile.google_business = GoogleBusinessData(
                        rating=data.get("rating"),
                        review_count=data.get("review_count"),
                        address=data.get("address"),
                        phone=data.get("phone"),
                        category=data.get("category"),
                    )
                    platforms_found.append("google_business")
                    logger.info(f"Google Business: {data.get('rating')} rating, {data.get('review_count')} reviews")
            except Exception as e:
                logger.warning(f"Google Business enrichment failed: {e}")
                errors.append(f"google_business: {str(e)}")

        profile.platforms_found = platforms_found
        profile.total_social_followers = total_followers

        logger.info(f"Social enrichment complete: {len(platforms_found)} platforms, {total_followers:,} total followers")

        return SkillResult.ok(
            data=self.Output(profile=profile),
            confidence=1.0 if platforms_found else 0.0,
            tokens_used=0,  # No AI tokens used
            cost_aud=0.0,
            metadata={
                "platforms_found": platforms_found,
                "total_followers": total_followers,
                "errors": errors,
            },
        )


# Register skill instance
SkillRegistry.register(SocialEnricherSkill())


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
- [x] Error handling for each platform
- [x] Registered with SkillRegistry
"""
