"""
FILE: src/models/digest_log.py
PURPOSE: Digest log model for tracking sent digest emails
PHASE: H (Client Transparency)
TASK: Item 44 - Daily Digest Email
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 14: Soft deletes only
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as UUID_DB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.client import Client


class DigestLog(Base, UUIDMixin, TimestampMixin):
    """
    Tracks daily/weekly digest emails sent to clients.

    Phase H, Item 44: Daily Digest Email
    - Records metrics snapshot at time of digest
    - Tracks delivery status and engagement
    - Stores content summary for reference
    """

    __tablename__ = "digest_logs"

    # Client reference
    client_id: Mapped[UUID] = mapped_column(
        UUID_DB(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Digest metadata
    digest_date: Mapped[date] = mapped_column(Date, nullable=False)
    digest_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="daily",
    )

    # Recipients (list of email addresses)
    recipients: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Content snapshot - metrics at time of digest
    metrics_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Content summary - what content was sent
    content_summary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # Delivery status
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Engagement tracking
    opened_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    clicked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # Relationships
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="digest_logs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DigestLog(id={self.id}, client_id={self.client_id}, date={self.digest_date}, status={self.status})>"

    @property
    def is_sent(self) -> bool:
        """Check if digest was successfully sent."""
        return self.status == "sent"

    @property
    def was_opened(self) -> bool:
        """Check if digest was opened."""
        return self.opened_at is not None


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] TimestampMixin for created_at/updated_at
# [x] Client relationship with cascade delete
# [x] JSONB for metrics and content snapshots
# [x] Status tracking for delivery
# [x] Engagement tracking (opens, clicks)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
