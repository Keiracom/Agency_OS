"""
Contract: src/models/sdk_usage_log.py
Purpose: SQLAlchemy model for SDK usage tracking
Layer: 1 - models
Imports: exceptions ONLY
Consumers: sdk_brain, engines, api
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.lead import Lead
    from src.models.campaign import Campaign
    from src.models.user import User


class SDKUsageLog(Base):
    """
    Tracks SDK Brain usage for cost control and analytics.

    Records every SDK agent execution with:
    - Token usage and costs (AUD)
    - Execution metrics (turns, duration)
    - Tool calls made
    - Success/failure status
    """

    __tablename__ = "sdk_usage_log"

    # Primary key
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Context
    client_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Agent info
    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: icp_extraction, enrichment, email, voice_kb, objection",
    )
    model_used: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Model ID: claude-sonnet-4-20250514, etc.",
    )

    # Cost tracking (AUD)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cached_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_aud: Mapped[float] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=0,
        comment="Total cost in Australian dollars",
    )

    # Execution metrics
    turns_used: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_calls: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of tool calls made during execution",
    )

    # Status
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    client: Mapped["Client"] = relationship(back_populates="sdk_usage_logs")
    lead: Mapped["Lead | None"] = relationship(back_populates="sdk_usage_logs")

    def __repr__(self) -> str:
        return f"<SDKUsageLog {self.agent_type} ${self.cost_aud:.4f}>"

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.input_tokens + self.output_tokens

    @property
    def cache_hit_rate(self) -> float:
        """Percentage of input tokens that were cached."""
        if self.input_tokens == 0:
            return 0.0
        return (self.cached_tokens / self.input_tokens) * 100
