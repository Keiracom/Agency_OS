"""
Contract: src/models/campaign_suggestion.py
Purpose: Campaign suggestion model for CIS-driven campaign evolution
Layer: 1 - models
Imports: exceptions only
Consumers: services, orchestration
Phase: Phase D - Item 18
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class SuggestionType(str, Enum):
    """Types of campaign suggestions."""
    CREATE_CAMPAIGN = "create_campaign"
    PAUSE_CAMPAIGN = "pause_campaign"
    ADJUST_ALLOCATION = "adjust_allocation"
    REFINE_TARGETING = "refine_targeting"
    CHANGE_CHANNEL_MIX = "change_channel_mix"
    UPDATE_CONTENT = "update_content"
    ADJUST_TIMING = "adjust_timing"


class SuggestionStatus(str, Enum):
    """Suggestion lifecycle status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    EXPIRED = "expired"


class CampaignSuggestion(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Campaign suggestion from CIS pattern analysis.

    Suggestions are generated weekly after pattern learning
    and require client approval before being applied.
    """

    __tablename__ = "campaign_suggestions"

    # Ownership
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,  # NULL for create_campaign suggestions
        index=True,
    )

    # Suggestion details
    suggestion_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SuggestionStatus.PENDING.value,
    )

    # Analysis data
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    recommended_action: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Confidence and priority
    confidence: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
    )

    # Pattern source
    pattern_types: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        default=list,
    )
    pattern_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Metrics
    current_metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    projected_improvement: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Lifecycle
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.utcnow() + timedelta(days=14),
    )

    # Client feedback
    client_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="campaign_suggestions")
    campaign = relationship("Campaign", back_populates="suggestions")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="check_confidence_range",
        ),
        CheckConstraint(
            "priority >= 1 AND priority <= 100",
            name="check_priority_range",
        ),
        Index(
            "idx_campaign_suggestions_pending",
            "client_id",
            "status",
            postgresql_where=text("status = 'pending' AND deleted_at IS NULL"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CampaignSuggestion {self.suggestion_type} "
            f"status={self.status} confidence={self.confidence}>"
        )

    @property
    def is_expired(self) -> bool:
        """Check if suggestion has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_actionable(self) -> bool:
        """Check if suggestion can be acted upon."""
        return (
            self.status == SuggestionStatus.PENDING.value
            and not self.is_expired
            and self.deleted_at is None
        )

    def approve(self, user_id: UUID, notes: str | None = None) -> None:
        """Approve this suggestion."""
        self.status = SuggestionStatus.APPROVED.value
        self.reviewed_at = datetime.utcnow()
        self.reviewed_by = user_id
        if notes:
            self.client_notes = notes

    def reject(self, user_id: UUID, reason: str | None = None) -> None:
        """Reject this suggestion."""
        self.status = SuggestionStatus.REJECTED.value
        self.reviewed_at = datetime.utcnow()
        self.reviewed_by = user_id
        if reason:
            self.rejection_reason = reason

    def mark_applied(self) -> None:
        """Mark suggestion as applied."""
        self.status = SuggestionStatus.APPLIED.value
        self.applied_at = datetime.utcnow()


class CampaignSuggestionHistory(Base, UUIDMixin):
    """Audit trail for suggestion status changes."""

    __tablename__ = "campaign_suggestion_history"

    suggestion_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaign_suggestions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_status: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    # Relationship
    suggestion = relationship("CampaignSuggestion", backref="history")


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Layer 1 placement
# [x] UUIDMixin, TimestampMixin, SoftDeleteMixin
# [x] All fields from migration
# [x] Proper type hints
# [x] Relationships defined
# [x] Constraints defined
# [x] Helper methods (approve, reject, mark_applied)
# [x] Properties (is_expired, is_actionable)
# [x] History model for audit trail
