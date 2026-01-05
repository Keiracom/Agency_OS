"""
Contract: src/models/social_profile.py
Purpose: Pydantic models for social media profile data
Layer: 1 - models
Imports: exceptions only
Consumers: agents, engines
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


class LinkedInCompanyProfile(BaseModel):
    """LinkedIn company page profile data."""

    name: str | None = Field(default=None, description="Company name")
    followers: int | None = Field(default=None, description="Follower count")
    employee_count: int | None = Field(default=None, description="Employee count")
    employee_range: str | None = Field(default=None, description="Employee range (e.g., '11-50')")
    specialties: list[str] = Field(default_factory=list, description="Company specialties")
    description: str | None = Field(default=None, description="Company description")
    industry: str | None = Field(default=None, description="Industry category")
    headquarters: str | None = Field(default=None, description="Headquarters location")
    website: str | None = Field(default=None, description="Company website")
    founded_year: int | None = Field(default=None, description="Year founded")
    linkedin_url: str | None = Field(default=None, description="LinkedIn page URL")


class InstagramProfile(BaseModel):
    """Instagram profile data."""

    username: str | None = Field(default=None, description="Instagram username")
    followers: int | None = Field(default=None, description="Follower count")
    following: int | None = Field(default=None, description="Following count")
    posts_count: int | None = Field(default=None, description="Total posts")
    bio: str | None = Field(default=None, description="Profile bio")
    is_verified: bool = Field(default=False, description="Verification status")
    full_name: str | None = Field(default=None, description="Full display name")
    profile_pic_url: str | None = Field(default=None, description="Profile picture URL")
    external_url: str | None = Field(default=None, description="External link in bio")
    instagram_url: str | None = Field(default=None, description="Instagram profile URL")


class FacebookPageProfile(BaseModel):
    """Facebook page profile data."""

    name: str | None = Field(default=None, description="Page name")
    likes: int | None = Field(default=None, description="Page likes")
    followers: int | None = Field(default=None, description="Page followers")
    category: str | None = Field(default=None, description="Page category")
    about: str | None = Field(default=None, description="About section")
    rating: float | None = Field(default=None, description="Page rating (1-5)")
    review_count: int | None = Field(default=None, description="Number of reviews")
    website: str | None = Field(default=None, description="Website URL")
    phone: str | None = Field(default=None, description="Phone number")
    address: str | None = Field(default=None, description="Business address")
    facebook_url: str | None = Field(default=None, description="Facebook page URL")


class GoogleBusinessProfile(BaseModel):
    """Google Business (Google Maps) profile data."""

    name: str | None = Field(default=None, description="Business name")
    rating: float | None = Field(default=None, description="Average rating (1-5)")
    review_count: int | None = Field(default=None, description="Number of reviews")
    address: str | None = Field(default=None, description="Business address")
    phone: str | None = Field(default=None, description="Phone number")
    website: str | None = Field(default=None, description="Website URL")
    category: str | None = Field(default=None, description="Business category")
    place_id: str | None = Field(default=None, description="Google Place ID")
    google_maps_url: str | None = Field(default=None, description="Google Maps URL")
    opening_hours: list[str] | None = Field(default=None, description="Opening hours")


class SocialProfiles(BaseModel):
    """Aggregate model containing all social media profiles."""

    linkedin: LinkedInCompanyProfile | None = Field(
        default=None,
        description="LinkedIn company profile"
    )
    instagram: InstagramProfile | None = Field(
        default=None,
        description="Instagram profile"
    )
    facebook: FacebookPageProfile | None = Field(
        default=None,
        description="Facebook page profile"
    )
    google_business: GoogleBusinessProfile | None = Field(
        default=None,
        description="Google Business profile"
    )

    @computed_field
    @property
    def total_social_followers(self) -> int:
        """
        Calculate total followers across all platforms.

        Returns:
            Sum of followers from LinkedIn, Instagram, and Facebook
        """
        total = 0

        if self.linkedin and self.linkedin.followers:
            total += self.linkedin.followers

        if self.instagram and self.instagram.followers:
            total += self.instagram.followers

        if self.facebook and self.facebook.followers:
            total += self.facebook.followers

        return total

    @computed_field
    @property
    def platforms_found(self) -> list[str]:
        """
        List of platforms where profiles were found.

        Returns:
            List of platform names with data
        """
        platforms = []

        if self.linkedin:
            platforms.append("linkedin")
        if self.instagram:
            platforms.append("instagram")
        if self.facebook:
            platforms.append("facebook")
        if self.google_business:
            platforms.append("google_business")

        return platforms

    @computed_field
    @property
    def average_rating(self) -> float | None:
        """
        Calculate average rating across platforms with ratings.

        Returns:
            Average rating or None if no ratings available
        """
        ratings = []

        if self.facebook and self.facebook.rating:
            ratings.append(self.facebook.rating)
        if self.google_business and self.google_business.rating:
            ratings.append(self.google_business.rating)

        if not ratings:
            return None

        return sum(ratings) / len(ratings)

    @computed_field
    @property
    def total_reviews(self) -> int:
        """
        Calculate total reviews across platforms.

        Returns:
            Sum of review counts from Facebook and Google Business
        """
        total = 0

        if self.facebook and self.facebook.review_count:
            total += self.facebook.review_count
        if self.google_business and self.google_business.review_count:
            total += self.google_business.review_count

        return total


"""
VERIFICATION CHECKLIST:
- [x] Contract comment at top with FILE, PURPOSE, LAYER
- [x] Follows import hierarchy (Rule 12) - models layer, no engine imports
- [x] Type hints on all fields
- [x] No TODO/FIXME/pass statements
- [x] No hardcoded secrets
- [x] LinkedInCompanyProfile model
- [x] InstagramProfile model
- [x] FacebookPageProfile model
- [x] GoogleBusinessProfile model
- [x] SocialProfiles aggregate model
- [x] total_social_followers computed property
- [x] platforms_found computed property
- [x] average_rating computed property
- [x] total_reviews computed property
"""
