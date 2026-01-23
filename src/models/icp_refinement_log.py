"""
FILE: src/models/icp_refinement_log.py
PURPOSE: Model for ICP refinement audit log (WHO pattern application tracking)
PHASE: 19 (ICP Refinement from CIS)
TASK: Item 19
DEPENDENCIES:
  - src/models/base.py
  - src/models/client.py
  - src/models/conversion_patterns.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 12: No imports from engines/integrations/orchestration

This model tracks all WHO pattern refinements applied to ICP searches.
Used for:
- Transparency (Phase H dashboard "Targeting Insights" panel)
- Audit trail (what was changed and when)
- Analytics (measure impact of refinements)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.conversion_patterns import ConversionPattern


class IcpRefinementLog(Base, UUIDMixin, TimestampMixin):
    """
    Audit log of WHO pattern refinements applied to ICP searches.

    Each record represents one search where WHO patterns were applied
    to modify the ICP criteria. Used for transparency dashboard and
    analytics on refinement effectiveness.
    """

    __tablename__ = "icp_refinement_log"

    # Foreign key to client
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to the WHO pattern that informed the refinement
    pattern_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversion_patterns.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Original ICP criteria before WHO refinement
    base_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Final criteria after WHO refinement applied
    refined_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # Array of refinement actions taken
    # [{field, action, reason, added?, prioritized?, sweet_spot?}, ...]
    refinements_applied: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    # WHO pattern confidence at time of refinement
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # When the refinement was applied
    applied_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
    )

    # Soft delete
    deleted_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        default=None,
    )

    # Relationships
    client: Mapped["Client"] = relationship(
        "Client",
        foreign_keys=[client_id],
        lazy="selectin",
    )

    pattern: Mapped["ConversionPattern"] = relationship(
        "ConversionPattern",
        foreign_keys=[pattern_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<IcpRefinementLog("
            f"id={self.id}, "
            f"client_id={self.client_id}, "
            f"confidence={self.confidence:.2f}, "
            f"applied_at={self.applied_at}"
            f")>"
        )

    @property
    def refinement_count(self) -> int:
        """Number of refinements applied in this log entry."""
        return len(self.refinements_applied) if self.refinements_applied else 0

    @property
    def fields_refined(self) -> list[str]:
        """List of field names that were refined."""
        if not self.refinements_applied:
            return []
        return [r.get("field", "") for r in self.refinements_applied if r.get("field")]


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top of file
# [x] Layer 1 model (no engine/integration/orchestration imports)
# [x] All fields have type hints
# [x] Foreign keys with proper ondelete behavior
# [x] JSONB for complex data fields
# [x] Soft delete support (deleted_at)
# [x] Relationships defined with lazy="selectin"
# [x] Helper properties for common queries
# [x] Docstrings on class and public methods
