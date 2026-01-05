"""
FILE: src/models/activity.py
PURPOSE: Activity model with message ID for email threading
PHASE: 2 (Models & Schemas)
TASK: MOD-007
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 18: Email threading via In-Reply-To headers
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM, INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    ChannelType,
    IntentType,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.campaign import Campaign
    from src.models.client import Client
    from src.models.lead import Lead


class Activity(Base, UUIDMixin):
    """
    Activity log for outreach and engagement.

    Tracks all interactions with leads including sends,
    opens, clicks, replies, and bounces.
    """

    __tablename__ = "activities"

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
    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=False,
        index=True,
    )

    # Channel and action
    channel: Mapped[ChannelType] = mapped_column(
        ENUM(ChannelType, name="channel_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # sent, delivered, opened, clicked, replied, bounced, unsubscribed, converted

    # === Email Threading (Rule 18) ===
    provider_message_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    thread_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )
    in_reply_to: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # === Content Reference ===
    sequence_step: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === Provider Details ===
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # === Engagement Metadata ===
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Link tracking
    link_clicked: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    geo_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    geo_city: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # === Intent (for replies) ===
    intent: Mapped[Optional[IntentType]] = mapped_column(
        ENUM(IntentType, name="intent_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # === Timestamps ===
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, channel={self.channel.value}, action='{self.action}')>"

    @property
    def is_engagement(self) -> bool:
        """Check if this is an engagement activity (open, click, reply)."""
        return self.action in ("opened", "clicked", "replied")

    @property
    def is_positive(self) -> bool:
        """Check if this is a positive signal."""
        return self.action in ("opened", "clicked", "replied", "converted")

    @property
    def is_negative(self) -> bool:
        """Check if this is a negative signal."""
        return self.action in ("bounced", "unsubscribed")


class ActivityStats(Base, UUIDMixin):
    """
    Aggregated activity statistics.

    Denormalized stats for performance. Updated by triggers.
    """

    __tablename__ = "activity_stats"

    # Foreign keys
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=True,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )

    # Counts by channel - Email
    email_sent: Mapped[int] = mapped_column(Integer, default=0)
    email_delivered: Mapped[int] = mapped_column(Integer, default=0)
    email_opened: Mapped[int] = mapped_column(Integer, default=0)
    email_clicked: Mapped[int] = mapped_column(Integer, default=0)
    email_replied: Mapped[int] = mapped_column(Integer, default=0)
    email_bounced: Mapped[int] = mapped_column(Integer, default=0)

    # Counts by channel - SMS
    sms_sent: Mapped[int] = mapped_column(Integer, default=0)
    sms_delivered: Mapped[int] = mapped_column(Integer, default=0)
    sms_replied: Mapped[int] = mapped_column(Integer, default=0)

    # Counts by channel - LinkedIn
    linkedin_sent: Mapped[int] = mapped_column(Integer, default=0)
    linkedin_accepted: Mapped[int] = mapped_column(Integer, default=0)
    linkedin_replied: Mapped[int] = mapped_column(Integer, default=0)

    # Counts by channel - Voice
    voice_called: Mapped[int] = mapped_column(Integer, default=0)
    voice_answered: Mapped[int] = mapped_column(Integer, default=0)
    voice_voicemail: Mapped[int] = mapped_column(Integer, default=0)

    # Counts by channel - Mail
    mail_sent: Mapped[int] = mapped_column(Integer, default=0)
    mail_delivered: Mapped[int] = mapped_column(Integer, default=0)

    # Aggregates
    total_sent: Mapped[int] = mapped_column(Integer, default=0)
    total_replied: Mapped[int] = mapped_column(Integer, default=0)
    total_converted: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<ActivityStats(client_id={self.client_id}, date={self.date})>"

    @property
    def open_rate(self) -> float:
        """Calculate email open rate."""
        if self.email_delivered == 0:
            return 0.0
        return (self.email_opened / self.email_delivered) * 100

    @property
    def click_rate(self) -> float:
        """Calculate email click rate."""
        if self.email_opened == 0:
            return 0.0
        return (self.email_clicked / self.email_opened) * 100

    @property
    def reply_rate(self) -> float:
        """Calculate overall reply rate."""
        if self.total_sent == 0:
            return 0.0
        return (self.total_replied / self.total_sent) * 100


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Activity with all fields from PART 5
# [x] provider_message_id for email threading (Rule 18)
# [x] thread_id and in_reply_to for conversation tracking
# [x] Intent classification fields
# [x] ActivityStats for aggregated metrics
# [x] Rate calculation properties
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
