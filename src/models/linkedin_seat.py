"""
Contract: src/models/linkedin_seat.py
Purpose: LinkedIn seat model for multi-seat support per client
Layer: 1 - models
Imports: base only
Consumers: services, engines, orchestration
Spec: docs/architecture/distribution/LINKEDIN_DISTRIBUTION.md
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.client_persona import ClientPersona
    from src.models.linkedin_connection import LinkedInConnection
    from src.models.resource_pool import ClientResource


class LinkedInSeatStatus:
    """LinkedIn seat status constants."""
    PENDING = "pending"           # Awaiting client connection
    AWAITING_2FA = "awaiting_2fa" # 2FA code needed
    WARMUP = "warmup"             # In 2-week ramp
    ACTIVE = "active"             # Full capacity
    RESTRICTED = "restricted"     # LinkedIn flagged
    DISCONNECTED = "disconnected" # Client removed


# Warmup schedule: (start_day, end_day, daily_limit)
LINKEDIN_WARMUP_SCHEDULE = [
    (1, 3, 5),
    (4, 7, 10),
    (8, 11, 15),
    (12, 999, 20),
]


class LinkedInSeat(Base, UUIDMixin, TimestampMixin):
    """
    LinkedIn seat for client's connected account.

    Each seat represents a LinkedIn account connected by the client.
    Supports multi-seat per client (4/7/14 per tier).

    Tier allocations:
    - Ignition: 4 seats (80/day capacity)
    - Velocity: 7 seats (140/day capacity)
    - Dominance: 14 seats (280/day capacity)
    """

    __tablename__ = "linkedin_seats"

    # Foreign keys
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("client_resources.id"),
        nullable=True,
    )
    persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("client_personas.id"),
        nullable=True,
    )

    # Provider connection (internal, not exposed to client)
    unipile_account_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Account info (from provider, displayed to client)
    account_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    account_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    profile_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=LinkedInSeatStatus.PENDING,
        nullable=False,
    )

    # Connection flow (for 2FA handling)
    pending_connection_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Warmup tracking
    activated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    warmup_completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Capacity override (health-based reduction)
    daily_limit_override: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Health metrics
    accept_rate_7d: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    accept_rate_30d: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    pending_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Restriction tracking
    restricted_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    restricted_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="linkedin_seats",
        lazy="selectin",
    )
    resource: Mapped[Optional["ClientResource"]] = relationship(
        "ClientResource",
        lazy="selectin",
    )
    persona: Mapped[Optional["ClientPersona"]] = relationship(
        "ClientPersona",
        lazy="selectin",
    )
    connections: Mapped[list["LinkedInConnection"]] = relationship(
        "LinkedInConnection",
        back_populates="seat",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<LinkedInSeat(id={self.id}, account='{self.account_name}', status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if seat can send connections."""
        return self.status in (LinkedInSeatStatus.WARMUP, LinkedInSeatStatus.ACTIVE)

    @property
    def days_active(self) -> int:
        """Days since activation."""
        if not self.activated_at:
            return 0
        delta = datetime.utcnow() - self.activated_at
        return delta.days + 1

    @property
    def daily_limit(self) -> int:
        """Get daily limit based on warmup status and health."""
        # Override takes precedence
        if self.daily_limit_override is not None:
            return self.daily_limit_override

        # Restricted = 0
        if self.status == LinkedInSeatStatus.RESTRICTED:
            return 0

        # Not activated = 0
        if not self.activated_at:
            return 0

        # Apply warmup schedule
        days = self.days_active
        for start, end, limit in LINKEDIN_WARMUP_SCHEDULE:
            if start <= days <= end:
                return limit

        return 20  # Default max

    @property
    def is_healthy(self) -> bool:
        """Check if seat has healthy accept rate."""
        if self.accept_rate_7d is None:
            return True  # No data yet
        return float(self.accept_rate_7d) >= 0.30

    @property
    def is_critical(self) -> bool:
        """Check if seat has critically low accept rate."""
        if self.accept_rate_7d is None:
            return False
        return float(self.accept_rate_7d) < 0.20

    def mark_connected(
        self,
        unipile_account_id: str,
        account_email: str,
        account_name: str,
        profile_url: str | None = None,
    ) -> None:
        """Mark seat as connected and start warmup."""
        self.unipile_account_id = unipile_account_id
        self.account_email = account_email
        self.account_name = account_name
        self.profile_url = profile_url
        self.status = LinkedInSeatStatus.WARMUP
        self.activated_at = datetime.utcnow()
        self.pending_connection_id = None

    def mark_restricted(self, reason: str) -> None:
        """Mark seat as restricted by LinkedIn."""
        self.status = LinkedInSeatStatus.RESTRICTED
        self.restricted_at = datetime.utcnow()
        self.restricted_reason = reason
        self.daily_limit_override = 0

    def apply_health_reduction(self) -> None:
        """Apply health-based limit reduction."""
        if self.is_critical:
            self.daily_limit_override = 10  # 50% reduction
        elif not self.is_healthy:
            self.daily_limit_override = 15  # 25% reduction
        else:
            self.daily_limit_override = None  # Reset


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] LinkedInSeat model with all fields from spec
# [x] Status constants
# [x] Warmup schedule constant
# [x] daily_limit property with warmup logic
# [x] Health check properties
# [x] Helper methods (mark_connected, mark_restricted)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
