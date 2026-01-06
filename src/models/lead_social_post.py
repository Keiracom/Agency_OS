"""
FILE: src/models/lead_social_post.py
PURPOSE: LeadSocialPost model for storing scraped social posts (audit trail)
PHASE: 21 (Deep Research & UI)
TASK: MOD-021
DEPENDENCIES:
  - src/models/base.py
  - src/models/lead.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.lead import Lead


class LeadSocialPost(Base, UUIDMixin):
    """
    Social post scraped from a lead's profile.

    Stores LinkedIn posts, tweets, news mentions, etc.
    for use in personalized outreach with icebreaker hooks.
    """

    __tablename__ = "lead_social_posts"

    # Foreign key to lead
    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source of the post
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Source platform: linkedin, twitter, news",
    )

    # Post content
    post_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full text content of the post",
    )

    # Post date
    post_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date the post was published",
    )

    # AI-generated icebreaker hook
    summary_hook: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated 1-sentence icebreaker from this post",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    # Relationship
    lead: Mapped["Lead"] = relationship("Lead", back_populates="social_posts")

    def __repr__(self) -> str:
        return f"<LeadSocialPost(id={self.id}, lead_id={self.lead_id}, source='{self.source}')>"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Maps to lead_social_posts table from migration
# [x] Foreign key to leads with CASCADE delete
# [x] source field (linkedin, twitter, news)
# [x] post_content field
# [x] post_date field
# [x] summary_hook field for AI icebreaker
# [x] created_at timestamp
# [x] Relationship to Lead model
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
