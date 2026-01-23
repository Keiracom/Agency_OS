"""
Contract: src/models/campaign.py
Purpose: Campaign model with channel allocation percentages
Layer: 1 - models
Imports: exceptions only
Consumers: ALL layers

FILE: src/models/campaign.py
PURPOSE: Campaign model with channel allocation percentages
PHASE: 2 (Models & Schemas)
TASK: MOD-005
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 14: Soft deletes only
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, UUID as UUID_DB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    CampaignStatus,
    ChannelType,
    PermissionMode,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.campaign_suggestion import CampaignSuggestion
    from src.models.client import Client
    from src.models.lead import Lead
    from src.models.lead_pool import LeadPool
    from src.models.resource_pool import ClientResource
    from src.models.user import User


class CampaignType:
    """Campaign type values."""
    AI_SUGGESTED = "ai_suggested"
    CUSTOM = "custom"


class Campaign(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Campaign model with channel allocation.

    Campaigns define outreach sequences with configurable
    channel mix (email, SMS, LinkedIn, voice, mail).
    """

    __tablename__ = "campaigns"

    # Foreign keys
    client_id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CampaignStatus] = mapped_column(
        ENUM(CampaignStatus, name="campaign_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CampaignStatus.DRAFT,
    )

    # Pause tracking (Phase H, Item 43)
    paused_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    pause_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paused_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Campaign type and lead allocation (Phase 37)
    campaign_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CampaignType.CUSTOM,
    )
    lead_allocation_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,  # Default to 100% if single campaign
    )
    lead_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,  # Calculated from pct × client's total leads
    )
    ai_suggestion_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,  # Why AI suggested this campaign (if ai_suggested)
    )

    # Permission mode (overrides client default)
    permission_mode: Mapped[Optional[PermissionMode]] = mapped_column(
        ENUM(PermissionMode, name="permission_mode", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Target settings
    target_industries: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    target_titles: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    target_company_sizes: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )
    target_locations: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
    )

    # Channel allocation percentages (must sum to 100)
    allocation_email: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
    )
    allocation_sms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    allocation_linkedin: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    allocation_voice: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    allocation_mail: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Scheduling
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    daily_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )
    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Australia/Sydney",
    )

    # Working hours (24h format)
    work_hours_start: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(9, 0),
    )
    work_hours_end: Mapped[time] = mapped_column(
        Time,
        nullable=False,
        default=time(17, 0),
    )
    work_days: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        default=[1, 2, 3, 4, 5],  # Mon-Fri
    )

    # Metrics (denormalized for performance)
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    leads_contacted: Mapped[int] = mapped_column(Integer, default=0)
    leads_replied: Mapped[int] = mapped_column(Integer, default=0)
    leads_converted: Mapped[int] = mapped_column(Integer, default=0)

    # Sequence settings
    sequence_steps: Mapped[int] = mapped_column(Integer, default=5)
    sequence_delay_days: Mapped[int] = mapped_column(Integer, default=3)
    uses_default_sequence: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="campaigns",
    )
    creator: Mapped[Optional["User"]] = relationship("User")
    leads: Mapped[list["Lead"]] = relationship(
        "Lead",
        back_populates="campaign",
        lazy="selectin",
    )
    resources: Mapped[list["CampaignResource"]] = relationship(
        "CampaignResource",
        back_populates="campaign",
        lazy="selectin",
    )
    sequences: Mapped[list["CampaignSequence"]] = relationship(
        "CampaignSequence",
        back_populates="campaign",
        lazy="selectin",
        order_by="CampaignSequence.step_number",
    )
    pool_leads: Mapped[list["LeadPool"]] = relationship(
        "LeadPool",
        back_populates="campaign",
        foreign_keys="LeadPool.campaign_id",
        lazy="selectin",
    )
    suggestions: Mapped[list["CampaignSuggestion"]] = relationship(
        "CampaignSuggestion",
        back_populates="campaign",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "allocation_email + allocation_sms + allocation_linkedin + "
            "allocation_voice + allocation_mail = 100",
            name="valid_allocation",
        ),
        CheckConstraint("daily_limit > 0 AND daily_limit <= 500", name="valid_daily_limit"),
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status={self.status.value})>"

    @property
    def is_active(self) -> bool:
        """Check if campaign is currently active."""
        return self.status == CampaignStatus.ACTIVE and not self.is_deleted

    @property
    def total_allocation(self) -> int:
        """Calculate total allocation percentage."""
        return (
            self.allocation_email
            + self.allocation_sms
            + self.allocation_linkedin
            + self.allocation_voice
            + self.allocation_mail
        )

    @property
    def reply_rate(self) -> float:
        """Calculate reply rate percentage."""
        if self.leads_contacted == 0:
            return 0.0
        return (self.leads_replied / self.leads_contacted) * 100

    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate percentage."""
        if self.leads_contacted == 0:
            return 0.0
        return (self.leads_converted / self.leads_contacted) * 100

    @property
    def is_ai_suggested(self) -> bool:
        """Check if campaign was AI-suggested (Phase I Dashboard)."""
        return self.campaign_type == CampaignType.AI_SUGGESTED

    def get_channel_allocation(self, channel: ChannelType) -> int:
        """Get allocation percentage for a specific channel."""
        allocations = {
            ChannelType.EMAIL: self.allocation_email,
            ChannelType.SMS: self.allocation_sms,
            ChannelType.LINKEDIN: self.allocation_linkedin,
            ChannelType.VOICE: self.allocation_voice,
            ChannelType.MAIL: self.allocation_mail,
        }
        return allocations.get(channel, 0)


class CampaignResource(Base, UUIDMixin, TimestampMixin):
    """
    Campaign resource for rate limiting.

    Tracks email domains, LinkedIn seats, phone numbers
    with daily usage limits (Rule 17).
    """

    __tablename__ = "campaign_resources"

    # Foreign keys
    campaign_id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source client resource for auto-inheritance tracking
    client_resource_id: Mapped[Optional[UUID]] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("client_resources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Resource info
    channel: Mapped[ChannelType] = mapped_column(
        ENUM(ChannelType, name="channel_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    resource_id: Mapped[str] = mapped_column(Text, nullable=False)
    resource_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rate limit tracking (resource-level, Rule 17)
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_used: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_reset_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_warmed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="resources",
    )
    client_resource: Mapped[Optional["ClientResource"]] = relationship(
        "ClientResource",
        back_populates="campaign_resources",
    )

    def __repr__(self) -> str:
        return f"<CampaignResource(channel={self.channel.value}, resource={self.resource_id})>"

    @property
    def remaining(self) -> int:
        """Get remaining daily quota."""
        return max(0, self.daily_limit - self.daily_used)

    @property
    def is_available(self) -> bool:
        """Check if resource can be used."""
        return self.is_active and self.remaining > 0


class CampaignSequence(Base, UUIDMixin, TimestampMixin):
    """
    Campaign sequence step configuration.

    Defines the sequence of outreach steps with templates.
    """

    __tablename__ = "campaign_sequences"

    # Foreign keys
    campaign_id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sequence config
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[ChannelType] = mapped_column(
        ENUM(ChannelType, name="channel_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    delay_days: Mapped[int] = mapped_column(Integer, default=3)

    # Templates
    subject_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)

    # Conditional logic
    skip_if_replied: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_if_bounced: Mapped[bool] = mapped_column(Boolean, default=True)

    # Phase E: Additional sequence metadata
    purpose: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # intro, connect, value_add, pattern_interrupt, breakup, discovery
    skip_if: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # phone_missing, linkedin_url_missing, address_missing

    # Relationship
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="sequences",
    )

    def __repr__(self) -> str:
        return f"<CampaignSequence(step={self.step_number}, channel={self.channel.value})>"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Campaign with all fields from schema
# [x] Channel allocation percentages (must sum to 100)
# [x] Soft delete via SoftDeleteMixin (Rule 14)
# [x] Scheduling fields (dates, hours, work days)
# [x] Denormalized metrics
# [x] CampaignResource for resource-level rate limits (Rule 17)
# [x] CampaignSequence for multi-step sequences
# [x] Constraints for allocation sum and daily limit
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
