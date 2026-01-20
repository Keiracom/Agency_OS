"""
Contract: src/models/client_persona.py
Purpose: Client persona model for sender identities across channels
Layer: 1 - models
Imports: base only
Consumers: services, engines, orchestration
Spec: docs/architecture/distribution/EMAIL_DISTRIBUTION.md (ED-008)
"""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.client import Client


class ClientPersona(Base, UUIDMixin, TimestampMixin):
    """
    Client persona for sender identity.

    Each persona represents a "sender identity" that the AI uses across channels:
    - Email: From name, signature
    - LinkedIn: Account mapping
    - Voice: AI voice persona
    - SMS: Sender name in message

    Per-tier allocation:
    - Ignition: 2 personas
    - Velocity: 3 personas
    - Dominance: 4 personas
    """

    __tablename__ = "client_personas"

    # Foreign key
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Persona identity
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Display settings
    display_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    photo_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    calendar_link: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Channel assignments (resource IDs)
    assigned_mailbox_ids: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        default=list,
        nullable=True,
    )
    assigned_phone_ids: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        default=list,
        nullable=True,
    )
    assigned_linkedin_seat_ids: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)),
        default=list,
        nullable=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="personas",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ClientPersona(id={self.id}, name='{self.full_name}', client_id={self.client_id})>"

    @property
    def full_name(self) -> str:
        """Full name of the persona."""
        return f"{self.first_name} {self.last_name}"

    @property
    def formatted_display_name(self) -> str:
        """
        Display name for emails.

        Returns display_name if set, otherwise "First from Company" format.
        """
        if self.display_name:
            return self.display_name
        return f"{self.first_name} from {self.client.name if self.client else 'our team'}"

    @property
    def signature_name(self) -> str:
        """Name for email signature (full name with title if available)."""
        if self.title:
            return f"{self.full_name}, {self.title}"
        return self.full_name

    def generate_signature(self, include_phone: bool = True, include_calendar: bool = True) -> str:
        """
        Generate email signature for this persona.

        Uses client branding if available.

        Args:
            include_phone: Include phone number in signature
            include_calendar: Include calendar link in signature

        Returns:
            HTML signature string
        """
        parts = [f"<p><strong>{self.full_name}</strong>"]

        if self.title:
            parts.append(f"<br>{self.title}")

        if self.client:
            company_name = self.client.name
            if self.client.branding and self.client.branding.get("company_name"):
                company_name = self.client.branding["company_name"]
            parts.append(f"<br>{company_name}")

        parts.append("</p>")

        contact_parts = []
        if include_phone and self.phone:
            contact_parts.append(f"P: {self.phone}")
        if include_calendar and self.calendar_link:
            contact_parts.append(f'<a href="{self.calendar_link}">Book a meeting</a>')

        if contact_parts:
            parts.append(f"<p>{' | '.join(contact_parts)}</p>")

        return "\n".join(parts)


# ============================================
# TIER ALLOCATIONS
# ============================================

PERSONA_ALLOCATIONS = {
    "ignition": 2,
    "velocity": 3,
    "dominance": 4,
}


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] ClientPersona model with all fields from spec
# [x] Relationship to Client
# [x] Helper properties (full_name, formatted_display_name)
# [x] generate_signature method
# [x] PERSONA_ALLOCATIONS constant
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
