"""
Contract: src/models/approval.py
Purpose: SQLAlchemy model for the approvals workflow — operator-gated outreach
         messages pending a human decision before dispatch.
Layer: 1 - models
Imports: stdlib + src.models.base
Consumers: src/api/routes/approvals.py
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    EDITED = "edit_applied"  # matches existing route output and DB enum value


TERMINAL_STATUSES = frozenset(
    {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
    }
)


class Approval(Base, TimestampMixin):
    """Approval workflow row — one outreach message awaiting human decision."""

    __tablename__ = "approvals"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    prospect_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="email")
    draft_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    draft_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(
            ApprovalStatus,
            name="approval_status",
            values_callable=lambda e: [s.value for s in e],
        ),
        nullable=False,
        default=ApprovalStatus.PENDING,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("idx_approvals_client_status", "client_id", "status"),
        Index("idx_approvals_prospect", "prospect_id"),
    )

    def is_terminal(self) -> bool:
        """Return True if the approval is in an immutable terminal state."""
        return self.status in TERMINAL_STATUSES
