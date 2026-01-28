"""
FILE: src/models/lead_pool.py
PURPOSE: Lead Pool model - central repository for all leads
PHASE: 24A (Lead Pool Architecture), updated Phase 37
DEPENDENCIES:
  - src/models/base.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines/integrations/orchestration
PHASE 37 CHANGES:
  - Added client_id for direct client ownership
  - Added campaign_id for direct campaign assignment
  - Added als_score, als_tier, als_components
  - Added outreach tracking fields
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.campaign import Campaign
    from src.models.client import Client


class PoolStatus:
    """Pool status enum values."""
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    CONVERTED = "converted"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    INVALID = "invalid"


class EmailStatus:
    """Email verification status values."""
    VERIFIED = "verified"
    GUESSED = "guessed"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"


class LeadPool(Base, UUIDMixin, TimestampMixin):
    """
    Lead Pool model - platform-wide lead repository.

    Leads are sourced FOR clients based on their ICP.
    client_id = NULL means lead is available for sourcing.
    client_id = UUID means lead is owned by that client.
    """

    __tablename__ = "lead_pool"

    # ===== CLIENT OWNERSHIP (Phase 37) =====
    client_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ===== UNIQUE IDENTIFIERS =====
    apollo_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== PERSON DATA =====
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    seniority: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    twitter_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    personal_email: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Person Location
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Departments
    departments: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # Employment History
    employment_history: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    current_role_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ===== ORGANISATION DATA =====
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    company_domain: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    company_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Company Firmographics
    company_industry: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    company_sub_industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    company_revenue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_revenue_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_country: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    company_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_postal_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Company Signals
    company_is_hiring: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    company_latest_funding_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_latest_funding_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    company_total_funding: Mapped[int | None] = mapped_column(Integer, nullable=True)
    company_technologies: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    company_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    # ===== ENRICHMENT METADATA =====
    email_status: Mapped[str | None] = mapped_column(
        String(20),
        default=EmailStatus.UNKNOWN,
        nullable=True,
    )
    enrichment_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrichment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # DataForSEO Metrics
    dataforseo_domain_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataforseo_organic_traffic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataforseo_backlinks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataforseo_spam_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dataforseo_enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # ===== POOL STATUS =====
    pool_status: Mapped[str] = mapped_column(
        String(20),
        default=PoolStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    # Global flags
    is_bounced: Mapped[bool] = mapped_column(Boolean, default=False)
    bounced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    unsubscribe_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compliance
    dncr_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    dncr_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dncr_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # ===== ALS SCORING (Phase 37) =====
    als_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    als_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    als_components: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # ===== OUTREACH TRACKING (Phase 37) =====
    first_contacted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_contacted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    total_touches: Mapped[int] = mapped_column(Integer, default=0)
    channels_used: Mapped[list[str] | None] = mapped_column(ARRAY(Text), default=list)
    has_replied: Mapped[bool] = mapped_column(Boolean, default=False)
    replied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reply_intent: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== RELATIONSHIPS =====
    client: Mapped[Optional["Client"]] = relationship(
        "Client",
        back_populates="pool_leads",
        foreign_keys=[client_id],
    )
    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign",
        back_populates="pool_leads",
        foreign_keys=[campaign_id],
    )

    # ===== CONSTRAINTS =====
    __table_args__ = (
        CheckConstraint(
            "als_tier IS NULL OR als_tier IN ('hot', 'warm', 'cool', 'cold', 'dead')",
            name="valid_als_tier",
        ),
        CheckConstraint(
            "als_score IS NULL OR (als_score >= 0 AND als_score <= 100)",
            name="valid_als_score",
        ),
    )

    def __repr__(self) -> str:
        return f"<LeadPool(id={self.id}, email='{self.email}', client_id={self.client_id})>"

    @property
    def full_name(self) -> str:
        """Get full name from first and last name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or ""

    @property
    def is_available(self) -> bool:
        """Check if lead is available for assignment."""
        return (
            self.pool_status == PoolStatus.AVAILABLE
            and self.client_id is None
            and not self.is_bounced
            and not self.is_unsubscribed
        )

    @property
    def is_assigned(self) -> bool:
        """Check if lead is assigned to a client."""
        return self.client_id is not None

    @property
    def is_contactable(self) -> bool:
        """Check if lead can be contacted."""
        return (
            not self.is_bounced
            and not self.is_unsubscribed
            and self.email_status != EmailStatus.INVALID
            and not (self.dncr_checked and self.dncr_result)
        )

    def get_als_tier(self) -> str:
        """Get ALS tier based on score."""
        if self.als_score is None:
            return "unscored"
        if self.als_score >= 85:
            return "hot"
        if self.als_score >= 60:
            return "warm"
        if self.als_score >= 35:
            return "cool"
        if self.als_score >= 20:
            return "cold"
        return "dead"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] All 40+ Apollo fields from original lead_pool schema
# [x] client_id for direct ownership (Phase 37)
# [x] campaign_id for direct assignment (Phase 37)
# [x] als_score, als_tier, als_components (Phase 37)
# [x] Outreach tracking fields (Phase 37)
# [x] Pool status and email status enums
# [x] Global flags (bounced, unsubscribed)
# [x] Compliance fields (DNCR)
# [x] Helper properties (is_available, is_assigned, is_contactable)
# [x] Constraints for ALS values
# [x] No imports from engines/integrations/orchestration (Rule 12)
