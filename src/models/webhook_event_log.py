"""
Contract: src/models/webhook_event_log.py
Purpose: Webhook event log for idempotent Stripe event processing
Layer: 1 - models
Imports: exceptions only
Consumers: src/integrations/stripe.py

Stores every processed webhook event so duplicate deliveries are skipped.
The event_id column has a UNIQUE constraint — insert attempt for a known
event_id raises IntegrityError which callers treat as a duplicate.
"""

from datetime import UTC, datetime

from sqlalchemy import Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin


class WebhookEventLog(Base, UUIDMixin):
    """
    Idempotent log of processed webhook events.

    One row per unique Stripe (or other provider) event ID.
    The UNIQUE index on event_id prevents double-processing.
    """

    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    processed_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="processed")

    __table_args__ = (
        Index("idx_webhook_events_event_id", "event_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<WebhookEventLog(provider={self.provider!r}, "
            f"event_type={self.event_type!r}, event_id={self.event_id!r})>"
        )
