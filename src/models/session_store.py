"""
Contract: src/models/session_store.py
Purpose: SQLAlchemy models for Drevon PR-A session store (5 tables).
Layer: 1 - models
Imports: stdlib + src.models.base
Consumers: src/session_store/recorder.py (write paths), Drevon PR-B/C/D (read paths)
Migration: supabase/migrations/20260511_drevon_session_store.sql
Spec: Drevon PR-A — Dave directive 2026-05-11, Elliot dispatch ts 1778540XXX
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, SoftDeleteMixin, UUIDMixin


class Session(Base, UUIDMixin, SoftDeleteMixin):
    """One row per Claude Code process lifetime.

    `session_uuid` is Claude Code's --session-id, used by PR-C UUID resumption.
    `status` text enum: 'active' | 'closed' | 'stuck'.
    """

    __tablename__ = "sessions"

    callsign: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    working_directory: Mapped[str] = mapped_column(Text, nullable=False)
    tmux_session: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    model_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Message(Base, UUIDMixin, SoftDeleteMixin):
    """User/assistant message within a session.

    `role` text enum: 'user' | 'assistant' | 'system'.
    `message_index` is 0-based ordering within the session.
    Content may be stored as hash-only for large transcripts.
    """

    __tablename__ = "messages"

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    message_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Turn(Base, UUIDMixin, SoftDeleteMixin):
    """Atomic assistant turn (one user message → tool calls → response).

    `status` text enum: 'in_progress' | 'completed' | 'error'.
    Cost columns populated by Stop hook (per-turn rollup).
    """

    __tablename__ = "turns"

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    trigger_message_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_aud: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)


class TurnLog(Base, UUIDMixin, SoftDeleteMixin):
    """Individual tool invocation within a turn.

    `tool_name`: 'Bash' | 'Read' | 'Edit' | 'Write' | ... | 'Agent' | 'mcp__*'.
    `exit_status` text enum: 'success' | 'error' | 'denied' | 'timeout'.
    """

    __tablename__ = "turn_logs"

    turn_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("turns.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tool_args_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tool_args_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_result_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TurnFile(Base, UUIDMixin, SoftDeleteMixin):
    """File created/modified/read during a turn_log.

    `operation` text enum: 'read' | 'write' | 'edit' | 'delete' | 'create'.
    """

    __tablename__ = "turn_files"

    turn_log_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("turn_logs.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    bytes_written: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bytes_read: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lines_added: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lines_removed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
