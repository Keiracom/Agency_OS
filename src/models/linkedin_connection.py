"""
Contract: src/models/linkedin_connection.py
Purpose: LinkedIn connection tracking model
Layer: 1 - models
Imports: base only
Consumers: services, engines, orchestration
Spec: docs/architecture/distribution/LINKEDIN_DISTRIBUTION.md
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.campaign import Campaign
    from src.models.lead_pool import LeadPool
    from src.models.linkedin_seat import LinkedInSeat


class LinkedInConnectionStatus:
    """LinkedIn connection status constants."""

    PENDING = "pending"  # Request sent, awaiting response
    ACCEPTED = "accepted"  # Connection accepted
    IGNORED = "ignored"  # 14 days no response
    DECLINED = "declined"  # Explicitly declined
    WITHDRAWN = "withdrawn"  # We withdrew stale request


class LinkedInConnection(Base, UUIDMixin):
    """
    LinkedIn connection request tracking.

    Tracks the lifecycle of connection requests:
    pending → accepted/ignored/declined/withdrawn

    Timeouts:
    - 14 days pending → mark ignored
    - 30 days pending → withdraw request
    """

    __tablename__ = "linkedin_connections"

    # Foreign keys
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("lead_pool.id", ondelete="CASCADE"),
        nullable=False,
    )
    seat_id: Mapped[UUID] = mapped_column(
        ForeignKey("linkedin_seats.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id"),
        nullable=True,
    )

    # Request tracking
    unipile_request_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default=LinkedInConnectionStatus.PENDING,
        nullable=False,
    )

    # Note tracking
    note_included: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    note_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )
    profile_viewed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Follow-up tracking (3-5 days after accept)
    follow_up_scheduled_for: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    follow_up_sent_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Created timestamp
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    lead: Mapped["LeadPool"] = relationship(
        "LeadPool",
        lazy="selectin",
    )
    seat: Mapped["LinkedInSeat"] = relationship(
        "LinkedInSeat",
        back_populates="connections",
        lazy="selectin",
    )
    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<LinkedInConnection(id={self.id}, lead_id={self.lead_id}, status={self.status})>"

    @property
    def is_pending(self) -> bool:
        """Check if connection is still pending."""
        return self.status == LinkedInConnectionStatus.PENDING

    @property
    def is_accepted(self) -> bool:
        """Check if connection was accepted."""
        return self.status == LinkedInConnectionStatus.ACCEPTED

    @property
    def days_pending(self) -> int:
        """Days since request was sent."""
        if not self.is_pending:
            return 0
        delta = datetime.utcnow() - self.requested_at
        return delta.days

    @property
    def needs_follow_up(self) -> bool:
        """Check if follow-up is due."""
        if not self.is_accepted:
            return False
        if self.follow_up_sent_at is not None:
            return False
        if self.follow_up_scheduled_for is None:
            return False
        return datetime.utcnow() >= self.follow_up_scheduled_for

    def mark_accepted(self, follow_up_days: int = 4) -> None:
        """Mark connection as accepted and schedule follow-up."""
        from datetime import timedelta

        self.status = LinkedInConnectionStatus.ACCEPTED
        self.responded_at = datetime.utcnow()
        self.follow_up_scheduled_for = datetime.utcnow() + timedelta(days=follow_up_days)

    def mark_ignored(self) -> None:
        """Mark connection as ignored (14 days no response)."""
        self.status = LinkedInConnectionStatus.IGNORED
        self.responded_at = datetime.utcnow()

    def mark_declined(self) -> None:
        """Mark connection as declined."""
        self.status = LinkedInConnectionStatus.DECLINED
        self.responded_at = datetime.utcnow()

    def mark_withdrawn(self) -> None:
        """Mark connection as withdrawn (we withdrew stale request)."""
        self.status = LinkedInConnectionStatus.WITHDRAWN
        self.responded_at = datetime.utcnow()

    def mark_follow_up_sent(self) -> None:
        """Mark follow-up as sent."""
        self.follow_up_sent_at = datetime.utcnow()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] LinkedInConnection model with all fields from spec
# [x] Status constants
# [x] Unique constraint on (lead_id, seat_id) - in migration
# [x] Helper properties (is_pending, days_pending, needs_follow_up)
# [x] Helper methods (mark_accepted, mark_ignored, etc.)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
