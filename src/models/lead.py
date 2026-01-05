"""
FILE: src/models/lead.py
PURPOSE: Lead model with ALS fields and suppression tables
PHASE: 2 (Models & Schemas)
TASK: MOD-006
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 14: Soft deletes only
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
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
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID as PGUUID
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
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)

    # === ALS Score Components (100 points max) ===
    als_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    als_tier: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    als_data_quality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max 20
    als_authority: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max 25
    als_company_fit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max 25
    als_timing: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max 15
    als_risk: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Max 15

    # === Organization Data ===
    organization_industry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization_employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organization_country: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization_founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    organization_is_hiring: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    organization_latest_funding_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    organization_website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    organization_linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === Person Data ===
    employment_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    personal_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seniority_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # === Status & Tracking ===
    status: Mapped[LeadStatus] = mapped_column(
        ENUM(LeadStatus, name="lead_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=LeadStatus.NEW,
    )
    current_sequence_step: Mapped[int] = mapped_column(Integer, default=0)
    next_outreach_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)

    # === Enrichment Metadata ===
    enrichment_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    enrichment_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    enrichment_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # === Compliance ===
    dncr_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    dncr_result: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    email_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    phone_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # === Engagement Tracking ===
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_replied_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_opened_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_clicked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    bounce_count: Mapped[int] = mapped_column(Integer, default=0)

    # === Assigned Resources ===
    assigned_email_resource: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_linkedin_seat: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_phone_resource: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="leads")
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="leads")

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
    source: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    added_by: Mapped[Optional[UUID]] = mapped_column(
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
    added_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
