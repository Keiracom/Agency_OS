"""
Contract: src/models/mailbox_pool.py
Purpose: SQLAlchemy model for the mailbox pool backing MailboxRotator.
Layer: 1 - models
Imports: stdlib + src.models.base
Consumers: outreach orchestration, MailboxRotator storage adapters
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class MailboxPool(Base, TimestampMixin):
    """Mailbox pool entry for LRU rotation and warming-day tracking."""

    __tablename__ = "mailbox_pool"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    mailbox_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    client_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="email")
    last_send_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    daily_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warming_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    healthy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("idx_mailbox_pool_client_channel", "client_id", "channel"),
        Index("idx_mailbox_pool_lru", "last_send_at"),
    )
