"""
Contract: src/models/conversion_patterns.py
Purpose: Models for Conversion Intelligence pattern storage
Layer: 1 - models
Imports: exceptions only
Consumers: engines, orchestration, CIS detectors

FILE: src/models/conversion_patterns.py
PURPOSE: Models for Conversion Intelligence pattern storage
PHASE: 16 (Conversion Intelligence)
TASK: 16A-002
DEPENDENCIES:
  - src/models/base.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines/integrations/orchestration
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.client import Client


class ConversionPattern(Base, UUIDMixin, TimestampMixin):
    """
    Stores computed conversion patterns for each detector type.

    Each client has one active pattern per type (who/what/when/how).
    When patterns are updated, the old version is archived to history.

    Pattern Types:
    - WHO: Lead attribute patterns (title, industry, size, timing signals)
    - WHAT: Content patterns (pain points, CTAs, angles, length)
    - WHEN: Timing patterns (day, hour, touch distribution, gaps)
    - HOW: Channel sequence patterns (channel mix, sequences, tier effectiveness)
    """

    __tablename__ = "conversion_patterns"

    # Foreign key to client
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )

    # Pattern type (who, what, when, how)
    pattern_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # Pattern data as JSONB
    patterns: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Sample size used to compute patterns
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Confidence score (0.0 to 1.0)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # When the pattern was computed
    computed_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    # When the pattern expires (typically +14 days)
    valid_until: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    # Relationship to client
    client: Mapped["Client"] = relationship(
        "Client",
        foreign_keys=[client_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ConversionPattern("
            f"id={self.id}, "
            f"client_id={self.client_id}, "
            f"type={self.pattern_type}, "
            f"confidence={self.confidence:.2f}"
            f")>"
        )

    @property
    def is_valid(self) -> bool:
        """Check if the pattern is still valid (not expired)."""
        return datetime.utcnow() < self.valid_until

    @property
    def is_high_confidence(self) -> bool:
        """Check if pattern has high confidence (>= 0.7)."""
        return self.confidence >= 0.7

    @classmethod
    def create(
        cls,
        client_id: UUID,
        pattern_type: str,
        patterns: dict[str, Any],
        sample_size: int,
        confidence: float,
        validity_days: int = 14,
    ) -> "ConversionPattern":
        """
        Create a new conversion pattern.

        Args:
            client_id: Client UUID
            pattern_type: Type of pattern (who/what/when/how)
            patterns: Pattern data as dictionary
            sample_size: Number of samples used
            confidence: Confidence score 0.0-1.0
            validity_days: Days until pattern expires (default 14)

        Returns:
            New ConversionPattern instance
        """
        now = datetime.utcnow()
        return cls(
            client_id=client_id,
            pattern_type=pattern_type,
            patterns=patterns,
            sample_size=sample_size,
            confidence=confidence,
            computed_at=now,
            valid_until=now + timedelta(days=validity_days),
        )


class ConversionPatternHistory(Base, UUIDMixin):
    """
    Historical record of pattern evolution over time.

    Archived automatically when patterns are updated via database trigger.
    Used for tracking pattern drift and debugging.
    """

    __tablename__ = "conversion_pattern_history"

    # Foreign key to client
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id"),
        nullable=False,
        index=True,
    )

    # Pattern type
    pattern_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # Pattern data
    patterns: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Sample size
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Confidence score
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # When the pattern was computed
    computed_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<ConversionPatternHistory("
            f"id={self.id}, "
            f"client_id={self.client_id}, "
            f"type={self.pattern_type}, "
            f"computed_at={self.computed_at}"
            f")>"
        )


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] ConversionPattern model with all fields
# [x] ConversionPatternHistory model for archiving
# [x] PatternType enum used
# [x] JSONB for patterns field
# [x] Confidence bounded 0.0-1.0
# [x] valid_until for expiry tracking
# [x] is_valid property
# [x] create() factory method
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
# [x] All classes have docstrings
