"""
Contract: src/models/client_intelligence.py
Purpose: Store scraped client data for SDK personalization
Layer: 1 - models
Imports: base only
Consumers: engines, orchestration
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DECIMAL, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.client import Client


class ClientIntelligence(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Scraped client data for SDK personalization.

    Stores data from multiple sources:
    - Website (tagline, case studies, testimonials)
    - Social media (LinkedIn, Twitter, Facebook, Instagram)
    - Review platforms (G2, Capterra, Trustpilot, Google)
    - Extracted proof points for SDK use
    """

    __tablename__ = "client_intelligence"

    # Foreign key to client
    client_id: Mapped["str"] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )

    # === WEBSITE DATA ===
    website_tagline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website_value_prop: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website_services: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{name, description}]
    website_case_studies: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{title, client_name, industry, result_metrics, summary}]
    website_testimonials: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{quote, author, title, company}]
    website_team_bios: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{name, title, linkedin_url, bio}]
    website_blog_topics: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    website_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === LINKEDIN COMPANY ===
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_follower_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    linkedin_employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    linkedin_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_specialties: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    linkedin_recent_posts: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{text, date, engagement}]
    linkedin_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === TWITTER/X ===
    twitter_handle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twitter_follower_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    twitter_bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twitter_recent_posts: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{text, date, likes, retweets}]
    twitter_topics: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    twitter_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === FACEBOOK ===
    facebook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    facebook_follower_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    facebook_about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    facebook_recent_posts: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    facebook_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === INSTAGRAM ===
    instagram_handle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instagram_follower_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    instagram_bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instagram_recent_posts: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{caption, date, likes}]
    instagram_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === REVIEW PLATFORMS ===
    # G2
    g2_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    g2_rating: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(2, 1), nullable=True)
    g2_review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    g2_top_reviews: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{rating, title, pros, cons, reviewer}]
    g2_ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    g2_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Capterra
    capterra_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    capterra_rating: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(2, 1), nullable=True)
    capterra_review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    capterra_top_reviews: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    capterra_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Trustpilot
    trustpilot_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trustpilot_rating: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(2, 1), nullable=True)
    trustpilot_review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trustpilot_top_reviews: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    trustpilot_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Google Business
    google_business_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_rating: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(2, 1), nullable=True)
    google_review_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    google_top_reviews: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    google_scraped_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === EXTRACTED PROOF POINTS ===
    proof_metrics: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{metric, context, source}]
    proof_clients: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    proof_industries: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    common_pain_points: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )
    differentiators: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)

    # === SCRAPING METADATA ===
    total_scrape_cost_aud: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4), nullable=True, default=Decimal("0")
    )
    last_full_scrape_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    scrape_errors: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True, default=list
    )  # [{source, error, timestamp}]

    def __repr__(self) -> str:
        return f"<ClientIntelligence(client_id={self.client_id}, last_scrape={self.last_full_scrape_at})>"

    @property
    def has_website_data(self) -> bool:
        """Check if website data has been scraped."""
        return self.website_scraped_at is not None

    @property
    def has_social_data(self) -> bool:
        """Check if any social media data has been scraped."""
        return any([
            self.linkedin_scraped_at,
            self.twitter_scraped_at,
            self.facebook_scraped_at,
            self.instagram_scraped_at,
        ])

    @property
    def has_review_data(self) -> bool:
        """Check if any review platform data has been scraped."""
        return any([
            self.g2_scraped_at,
            self.capterra_scraped_at,
            self.trustpilot_scraped_at,
            self.google_scraped_at,
        ])

    @property
    def needs_refresh(self) -> bool:
        """Check if data is stale (older than 30 days)."""
        if not self.last_full_scrape_at:
            return True
        days_since_scrape = (datetime.utcnow() - self.last_full_scrape_at).days
        return days_since_scrape > 30

    def get_proof_summary(self) -> dict[str, Any]:
        """Get a summary of proof points for SDK agents."""
        return {
            "metrics": self.proof_metrics or [],
            "clients": self.proof_clients or [],
            "industries": self.proof_industries or [],
            "pain_points": self.common_pain_points or [],
            "differentiators": self.differentiators or [],
            "testimonials": (self.website_testimonials or [])[:3],
            "case_studies": (self.website_case_studies or [])[:3],
            "ratings": {
                "g2": {"rating": float(self.g2_rating) if self.g2_rating else None, "count": self.g2_review_count},
                "capterra": {"rating": float(self.capterra_rating) if self.capterra_rating else None, "count": self.capterra_review_count},
                "trustpilot": {"rating": float(self.trustpilot_rating) if self.trustpilot_rating else None, "count": self.trustpilot_review_count},
                "google": {"rating": float(self.google_rating) if self.google_rating else None, "count": self.google_review_count},
            },
        }


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] All scraped data fields (website, social, reviews)
# [x] Extracted proof points for SDK use
# [x] Scraping metadata and cost tracking
# [x] Soft delete via SoftDeleteMixin (Rule 14)
# [x] Helper properties (has_website_data, needs_refresh, etc.)
# [x] get_proof_summary method for SDK agents
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
