"""
Contract: src/models/cycle.py
Purpose: Cycle state machine — cycles, cycle_prospects, outreach_actions,
         sequence_templates SQLAlchemy models.
Layer: 1 - models
Imports: exceptions only
Consumers: ALL layers
"""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text  # noqa: F401
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as UUID_DB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.client import Client


class Cycle(Base, TimestampMixin):
    """One outreach cycle for a client. Only one active cycle per client at a time."""

    __tablename__ = "cycles"

    id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    client_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    target_prospects: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_day_1_date: Mapped[date] = mapped_column(Date, nullable=False, server_default="CURRENT_DATE")
    # Valid status values: 'active', 'paused', 'ready_for_reveal', 'completed'
    # Directive #314 added 'ready_for_reveal' and 'paused' statuses
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    warmup_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="full")

    # Relationships
    prospects: Mapped[list["CycleProspect"]] = relationship("CycleProspect", back_populates="cycle", cascade="all, delete-orphan")
    actions: Mapped[list["OutreachAction"]] = relationship("OutreachAction", back_populates="cycle", cascade="all, delete-orphan")
    events: Mapped[list["CycleEvent"]] = relationship("CycleEvent", back_populates="cycle", cascade="all, delete-orphan")


class CycleProspect(Base, TimestampMixin):
    """Links a prospect to a cycle with per-prospect outreach state."""

    __tablename__ = "cycle_prospects"

    id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    cycle_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False)
    prospect_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), nullable=False)
    entered_cycle_on_day: Mapped[int] = mapped_column(Integer, nullable=False)
    outreach_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence_type: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")

    # Relationships
    cycle: Mapped["Cycle"] = relationship("Cycle", back_populates="prospects")
    actions: Mapped[list["OutreachAction"]] = relationship("OutreachAction", back_populates="cycle_prospect", cascade="all, delete-orphan")


class OutreachAction(Base):
    """Individual scheduled or fired outreach action."""

    __tablename__ = "outreach_actions"

    id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    cycle_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False)
    cycle_prospect_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), ForeignKey("cycle_prospects.id", ondelete="CASCADE"), nullable=False)
    prospect_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    skipped_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    # Relationships
    cycle: Mapped["Cycle"] = relationship("Cycle", back_populates="actions")
    cycle_prospect: Mapped["CycleProspect"] = relationship("CycleProspect", back_populates="actions")


class CycleEvent(Base):
    """Audit log for cycle state transitions. Directive #314."""

    __tablename__ = "cycle_events"

    id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    cycle_id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), ForeignKey("cycles.id", ondelete="CASCADE"), nullable=False)
    # event_type: 'started', 'paused', 'resumed', 'reveal_ready', 'revealed', 'completed'
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    # triggered_by: 'customer', 'system', 'admin', 'timeout'
    triggered_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    cycle: Mapped["Cycle"] = relationship("Cycle", back_populates="events")


class SequenceTemplate(Base, TimestampMixin):
    """JSONB-driven sequence template. Loaded by SequenceEngine."""

    __tablename__ = "sequence_templates"

    id: Mapped[UUID] = mapped_column(UUID_DB(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    sequence_type: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")
    steps: Mapped[list] = mapped_column(JSONB, nullable=False)
