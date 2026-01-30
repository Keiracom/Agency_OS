"""
Contract: src/models/persona.py
Purpose: Persona pool model for AI-generated sender identities
Layer: 1 - models
Imports: base only
Consumers: services, orchestration
Spec: Persona pool allocation by tier (ignition: 2, velocity: 3, dominance: 4)
"""

from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.client import Client


class PersonaStatus(str, Enum):
    """Persona lifecycle status."""

    AVAILABLE = "available"
    ALLOCATED = "allocated"
    RETIRED = "retired"


# Persona allocations per tier
PERSONA_TIER_ALLOCATIONS = {
    "ignition": 2,
    "velocity": 3,
    "dominance": 4,
}


class Persona(Base, UUIDMixin, TimestampMixin):
    """
    Persona pool for AI-generated sender identities.

    Represents professional identities that can be allocated to clients
    for use across outreach channels (email, LinkedIn, voice).

    Per-tier allocation:
    - Ignition: 2 personas
    - Velocity: 3 personas
    - Dominance: 4 personas
    """

    __tablename__ = "personas"

    # Persona identity
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    bio: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Status tracking
    status: Mapped[PersonaStatus] = mapped_column(
        ENUM(
            PersonaStatus,
            name="persona_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PersonaStatus.AVAILABLE,
        nullable=False,
    )

    # Allocation tracking
    allocated_to_client_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Domain suggestions (generated, not purchased)
    suggested_domains: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    allocated_client: Mapped["Client | None"] = relationship(
        "Client",
        foreign_keys=[allocated_to_client_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Persona(id={self.id}, name='{self.full_name}', status={self.status.value})>"

    @property
    def full_name(self) -> str:
        """Full name of the persona."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_available(self) -> bool:
        """Check if persona is available for allocation."""
        return self.status == PersonaStatus.AVAILABLE

    @property
    def is_allocated(self) -> bool:
        """Check if persona is allocated to a client."""
        return self.status == PersonaStatus.ALLOCATED


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] PersonaStatus enum
# [x] PERSONA_TIER_ALLOCATIONS constant
# [x] Persona model with all required fields
# [x] Relationship to Client
# [x] Helper properties (full_name, is_available, is_allocated)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
