"""
Contract: src/models/vendor_usage_log.py
Purpose: SQLAlchemy model for non-token vendor usage tracking (E1 R3)
Layer: 1 - models
Imports: exceptions ONLY
Consumers: src/integrations/{dataforseo, leadmagic, contactout, brightdata}, services
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base

if TYPE_CHECKING:
    pass


class VendorUsageLog(Base):
    """E1 R3: per-call cost ledger for non-token vendors.

    Mirrors SDKUsageLog shape but with vendor-shaped fields. New vendor =
    data, not migration: just write a new ``vendor`` string. Pairs with the
    spike doc at docs/audits/elliot/e1_r3_vendor_cost_spike_2026-05-09.md.
    """

    __tablename__ = "vendor_usage_log"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

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

    vendor: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Vendor identifier: dataforseo, leadmagic, contactout, brightdata",
    )
    endpoint: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Vendor endpoint or operation name",
    )

    units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    units_unit: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="api_calls",
        comment="Unit type: records | credits | api_calls",
    )

    cost_aud: Mapped[float] = mapped_column(
        Numeric(10, 6),
        nullable=False,
        default=0,
        comment="Total cost in AUD (USD × settings.aud_per_usd at write time)",
    )

    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<VendorUsageLog {self.vendor}/{self.endpoint} ${self.cost_aud:.4f}>"
