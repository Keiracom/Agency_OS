"""
FILE: src/models/voice_call.py
PURPOSE: SQLAlchemy model for voice_calls table - tracks AI voice call attempts and outcomes
PHASE: 17 (Launch Prerequisites), Gap 1 Fix (CIS Audit)
TASK: VOICE-008, CIS-GAP-001
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines/integrations/orchestration
  - Rule 14: Soft deletes where applicable
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from src.models.lead_pool import LeadPool


class VoiceCallOutcome(StrEnum):
    """Voice call outcome classifications."""

    BOOKED = "BOOKED"
    CALLBACK = "CALLBACK"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    VOICEMAIL = "VOICEMAIL"
    NO_ANSWER = "NO_ANSWER"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    ESCALATION = "ESCALATION"
    ANGRY = "ANGRY"
    DNCR_BLOCKED = "DNCR_BLOCKED"
    EXCLUDED = "EXCLUDED"
    INITIATED = "INITIATED"
    FAILED = "FAILED"
    # Additional webhook event mappings
    CALL_ANSWERED = "CALL_ANSWERED"
    CALL_DECLINED = "CALL_DECLINED"
    CALL_COMPLETED = "CALL_COMPLETED"
    BUSY = "BUSY"
    WRONG_PERSON = "WRONG_PERSON"
    MEETING_BOOKED = "MEETING_BOOKED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"


class VoiceCall(Base, UUIDMixin):
    """
    Voice call record for AI outbound calls.

    Tracks each AI voice call attempt, outcome, and metrics.
    Populated by ElevenAgents webhooks and voice flow orchestration.
    """

    __tablename__ = "voice_calls"

    # ===== RELATIONSHIPS =====
    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lead_pool.id"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id"),
        nullable=True,
        index=True,
    )

    # ===== CALL IDENTIFIERS =====
    phone_number: Mapped[str] = mapped_column(Text, nullable=False)
    call_sid: Mapped[str | None] = mapped_column(Text, nullable=True)  # Twilio SID
    elevenagets_call_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, index=True
    )  # ElevenAgents call ID
    twilio_call_sid: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== CALL OUTCOME =====
    outcome: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # One of VoiceCallOutcome values
    outcome_raw: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Raw outcome from ElevenAgents
    outcome_confidence: Mapped[float | None] = mapped_column(nullable=True)

    # ===== CALL METRICS =====
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== PERSONALISATION =====
    hook_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    als_score_at_call: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # CIS Gap 1: Captured at dispatch

    # ===== FOLLOW-UP =====
    callback_scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    escalation_notified: Mapped[bool] = mapped_column(Boolean, default=False)

    # ===== COMPLIANCE =====
    compliance_dncr_checked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    compliance_hours_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recording_disclosure_delivered: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )

    # ===== WEBHOOK EVENT TRACKING (CIS Gap 1) =====
    event_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # call_answered, call_declined, etc.
    event_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # initiated, ringing, in-progress, completed, failed

    # ===== METADATA =====
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ===== TIMESTAMPS =====
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ===== RELATIONSHIPS =====
    # lead: Mapped["LeadPool"] = relationship(back_populates="voice_calls")

    def __repr__(self) -> str:
        return f"<VoiceCall(id={self.id}, outcome={self.outcome}, duration={self.duration_seconds}s)>"

    @property
    def is_positive_outcome(self) -> bool:
        """Check if outcome is positive (booked, interested, callback)."""
        return self.outcome in (
            VoiceCallOutcome.BOOKED,
            VoiceCallOutcome.INTERESTED,
            VoiceCallOutcome.CALLBACK,
            VoiceCallOutcome.MEETING_BOOKED,
            VoiceCallOutcome.CALLBACK_REQUESTED,
        )

    @property
    def is_negative_outcome(self) -> bool:
        """Check if outcome is negative (not interested, angry, unsubscribe)."""
        return self.outcome in (
            VoiceCallOutcome.NOT_INTERESTED,
            VoiceCallOutcome.ANGRY,
            VoiceCallOutcome.UNSUBSCRIBE,
            VoiceCallOutcome.WRONG_PERSON,
        )

    @property
    def is_no_contact(self) -> bool:
        """Check if call didn't result in contact."""
        return self.outcome in (
            VoiceCallOutcome.NO_ANSWER,
            VoiceCallOutcome.VOICEMAIL,
            VoiceCallOutcome.BUSY,
            VoiceCallOutcome.CALL_DECLINED,
        )

    @property
    def requires_retry(self) -> bool:
        """Check if call should be retried."""
        return self.outcome in (
            VoiceCallOutcome.NO_ANSWER,
            VoiceCallOutcome.VOICEMAIL,
            VoiceCallOutcome.BUSY,
            VoiceCallOutcome.CALLBACK,
            VoiceCallOutcome.CALLBACK_REQUESTED,
        )


class VoiceCallContext(Base, UUIDMixin):
    """
    Voice call context - stores full context sent to AI agent.

    Contains the compiled prompt context, SDK hooks, and prior
    interaction summaries used for personalisation.
    """

    __tablename__ = "voice_call_context"

    # ===== RELATIONSHIP =====
    voice_call_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("voice_calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ===== CONTEXT DATA =====
    context_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sdk_hook_selected: Mapped[str | None] = mapped_column(Text, nullable=True)
    sdk_case_study_selected: Mapped[str | None] = mapped_column(Text, nullable=True)
    prior_touchpoints_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== TIMESTAMPS =====
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<VoiceCallContext(voice_call_id={self.voice_call_id})>"


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] VoiceCall model matching database schema
# [x] VoiceCallContext model for prompt context
# [x] VoiceCallOutcome enum with all outcome types
# [x] als_score_at_call field for CIS Gap 1
# [x] event_type field for webhook events
# [x] All relationships with proper ForeignKeys
# [x] Indexes on key lookup fields
# [x] Type hints on all fields
# [x] Helper properties for outcome classification
# [x] No imports from engines/integrations/orchestration (Rule 12)
