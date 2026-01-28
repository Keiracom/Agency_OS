"""
Contract: src/models/lead.py
Purpose: Lead model with ALS fields and suppression tables
Layer: 1 - models
Imports: exceptions only
Consumers: ALL layers

FILE: src/models/lead.py
PURPOSE: Lead model with ALS fields and suppression tables
PHASE: 2 (Models & Schemas), modified Phase 24C, 24D
TASK: MOD-006, ENGAGE-005, THREAD-006
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 14: Soft deletes only
  - Rule 12: No imports from engines/integrations/orchestration
PHASE 24C CHANGES:
  - Added timezone for lead timezone tracking
  - Added timezone_offset for UTC offset calculation
PHASE 24D CHANGES:
  - Added rejection_reason for tracking why leads reject
  - Added rejection_notes and rejection_at
  - Added objections_raised for objection history
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    LeadStatus,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.campaign import Campaign
    from src.models.client import Client
    from src.models.lead_social_post import LeadSocialPost


class Lead(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Lead model with ALS (Agency Lead Score) fields.

    Represents a prospective customer with enrichment data
    and scoring components.
    """

    __tablename__ = "leads"

    # Foreign keys
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id"),
        nullable=False,
        index=True,
    )

    # Contact information
    email: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)

    # === ALS Score Components (100 points max) ===
    als_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    als_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    als_data_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Max 20
    als_authority: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Max 25
    als_company_fit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Max 25
    als_timing: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Max 15
    als_risk: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Max 15

    # === Organization Data ===
    organization_industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organization_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    organization_is_hiring: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    organization_latest_funding_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    organization_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Person Data ===
    employment_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    personal_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    seniority_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # === Status & Tracking ===
    status: Mapped[LeadStatus] = mapped_column(
        ENUM(LeadStatus, name="lead_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=LeadStatus.NEW,
    )
    current_sequence_step: Mapped[int] = mapped_column(Integer, default=0)
    next_outreach_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)

    # === Enrichment Metadata ===
    enrichment_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enrichment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    enrichment_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # === Deep Research (Phase 21) ===
    deep_research_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=True)
    deep_research_run_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # === SDK Enrichment (Hot Leads - ALS 85+) ===
    sdk_enrichment: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sdk_signals: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)
    sdk_cost_aud: Mapped[float | None] = mapped_column(Float, nullable=True)
    sdk_enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    sdk_voice_kb: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sdk_email_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # === Compliance ===
    dncr_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    dncr_result: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    email_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    phone_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # === Engagement Tracking ===
    last_contacted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_replied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_clicked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    bounce_count: Mapped[int] = mapped_column(Integer, default=0)

    # === Phase 24D: Rejection Tracking ===
    # Note: rejection_reason is a PostgreSQL ENUM type created in migration 027
    rejection_reason: Mapped[str | None] = mapped_column(
        ENUM(
            'timing_not_now', 'budget_constraints', 'using_competitor',
            'not_decision_maker', 'no_need', 'bad_experience', 'too_busy',
            'not_interested_generic', 'do_not_contact', 'wrong_contact',
            'company_policy', 'other',
            name='rejection_reason_type',
            create_constraint=False,  # Type already exists in DB
        ),
        nullable=True
    )
    rejection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_at: Mapped[datetime | None] = mapped_column(nullable=True)
    objections_raised: Mapped[list | None] = mapped_column(ARRAY(Text), nullable=True)

    # === Phase 24C: Timezone Tracking (from location data) ===
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)  # UTC offset in minutes

    # === Assigned Resources ===
    assigned_email_resource: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_linkedin_seat: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_phone_resource: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="leads")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="leads")
    social_posts: Mapped[list["LeadSocialPost"]] = relationship(
        "LeadSocialPost",
        back_populates="lead",
        cascade="all, delete-orphan",
    )

    # Constraints - compound uniqueness per client
    __table_args__ = (
        UniqueConstraint("client_id", "email", name="unique_lead_per_client"),
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, email='{self.email}', als_score={self.als_score})>"

    @property
    def full_name(self) -> str:
        """Get full name from first and last name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or ""

    @property
    def is_enriched(self) -> bool:
        """Check if lead has been enriched."""
        return self.enrichment_source is not None

    @property
    def is_scorable(self) -> bool:
        """Check if lead has enough data for scoring."""
        return all([
            self.email,
            self.first_name,
            self.last_name,
            self.company,
        ])

    @property
    def is_contactable(self) -> bool:
        """Check if lead can be contacted."""
        return (
            self.status not in (LeadStatus.UNSUBSCRIBED, LeadStatus.BOUNCED)
            and not self.is_deleted
            and not (self.dncr_checked and self.dncr_result)
        )

    def get_als_tier(self) -> str:
        """
        Get ALS tier based on score.

        Returns tier: hot (85+), warm (60-84), cool (35-59), cold (20-34), dead (<20)
        """
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


class GlobalSuppression(Base, UUIDMixin):
    """
    Global suppression list (platform-wide).

    Emails on this list are never contacted by any client.
    """

    __tablename__ = "global_suppression"

    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<GlobalSuppression(email='{self.email}', reason='{self.reason}')>"


class ClientSuppression(Base, UUIDMixin):
    """
    Client-specific suppression list.

    Emails on this list are not contacted by this specific client.
    """

    __tablename__ = "client_suppression"

    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    added_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint("client_id", "email", name="unique_client_suppression"),
    )

    def __repr__(self) -> str:
        return f"<ClientSuppression(client_id={self.client_id}, email='{self.email}')>"


class DomainSuppression(Base, UUIDMixin):
    """
    Domain suppression list (competitors, blacklisted domains).
    """

    __tablename__ = "domain_suppression"

    domain: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    added_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<DomainSuppression(domain='{self.domain}', reason='{self.reason}')>"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Lead with all ALS fields from PART 5
# [x] Compound uniqueness: client_id + email
# [x] Soft delete via SoftDeleteMixin (Rule 14)
# [x] ALS score components (data_quality, authority, company_fit, timing, risk)
# [x] Organization data fields
# [x] DNCR compliance fields
# [x] Enrichment metadata (source, confidence, version)
# [x] GlobalSuppression table
# [x] ClientSuppression table
# [x] DomainSuppression table
# [x] Helper properties (is_enriched, is_contactable, get_als_tier)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
# [x] Phase 24D: rejection_reason for tracking (THREAD-006)
# [x] Phase 24D: rejection_notes and rejection_at
# [x] Phase 24D: objections_raised for history
