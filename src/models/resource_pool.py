"""
Contract: src/models/resource_pool.py
Purpose: Resource pool models for platform-level resource allocation
Layer: 1 - models
Imports: base only
Consumers: services, orchestration
Spec: docs/architecture/distribution/RESOURCE_POOL.md
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import (
    Base,
    TimestampMixin,
    UUIDMixin,
)

if TYPE_CHECKING:
    from src.models.client import Client


# ============================================
# ENUMS
# ============================================


class ResourceType(str, Enum):
    """Resource types available in the pool."""
    EMAIL_DOMAIN = "email_domain"
    PHONE_NUMBER = "phone_number"
    LINKEDIN_SEAT = "linkedin_seat"


class ResourceStatus(str, Enum):
    """Resource lifecycle status."""
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    WARMING = "warming"
    RETIRED = "retired"


# ============================================
# TIER ALLOCATIONS (CEO Decisions 2026-01-20)
# ============================================

TIER_ALLOCATIONS = {
    "ignition": {
        ResourceType.EMAIL_DOMAIN: 3,
        ResourceType.PHONE_NUMBER: 1,
        ResourceType.LINKEDIN_SEAT: 4,
    },
    "velocity": {
        ResourceType.EMAIL_DOMAIN: 5,
        ResourceType.PHONE_NUMBER: 2,
        ResourceType.LINKEDIN_SEAT: 7,
    },
    "dominance": {
        ResourceType.EMAIL_DOMAIN: 9,
        ResourceType.PHONE_NUMBER: 3,
        ResourceType.LINKEDIN_SEAT: 14,
    },
}

# Mailboxes per domain (2 per domain)
MAILBOXES_PER_DOMAIN = 2


# ============================================
# MODELS
# ============================================


class ResourcePool(Base, UUIDMixin, TimestampMixin):
    """
    Platform-level resource pool.

    Represents email domains, phone numbers, and LinkedIn seats
    that can be allocated to clients based on their subscription tier.
    """

    __tablename__ = "resource_pool"

    # Resource identification
    resource_type: Mapped[ResourceType] = mapped_column(
        ENUM(ResourceType, name="resource_type", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    resource_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    resource_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Capacity tracking (for shared resources)
    max_clients: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    current_clients: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Status
    status: Mapped[ResourceStatus] = mapped_column(
        ENUM(ResourceStatus, name="resource_status", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ResourceStatus.AVAILABLE,
        nullable=False,
    )

    # Warmup tracking (for email domains)
    warmup_started_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )
    warmup_completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )
    reputation_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Provider metadata
    provider: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    provider_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    provider_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        nullable=True,
    )

    # Relationships
    client_resources: Mapped[list["ClientResource"]] = relationship(
        "ClientResource",
        back_populates="resource",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ResourcePool(id={self.id}, type={self.resource_type.value}, value='{self.resource_value}')>"

    @property
    def is_available(self) -> bool:
        """Check if resource is available for assignment."""
        return (
            self.status in (ResourceStatus.AVAILABLE, ResourceStatus.ASSIGNED)
            and self.current_clients < self.max_clients
        )

    @property
    def is_warmed(self) -> bool:
        """Check if resource has completed warmup (email domains)."""
        return self.warmup_completed_at is not None

    def get_daily_limit(self) -> int:
        """
        Get daily limit based on resource type and warmup status.

        Email domains: 5-50 based on warmup progress
        Phone numbers: 50 calls/day
        LinkedIn seats: 20 connections/day (handled by seat service)
        """
        if self.resource_type == ResourceType.EMAIL_DOMAIN:
            return self._get_email_daily_limit()
        elif self.resource_type == ResourceType.PHONE_NUMBER:
            return 50
        elif self.resource_type == ResourceType.LINKEDIN_SEAT:
            return 20
        return 0

    def _get_email_daily_limit(self) -> int:
        """Get daily email limit based on warmup status."""
        if self.warmup_completed_at:
            return 50  # Full capacity

        if not self.warmup_started_at:
            return 5  # Not started

        days_warming = (datetime.utcnow() - self.warmup_started_at).days

        if days_warming < 4:
            return 5
        elif days_warming < 8:
            return 10
        elif days_warming < 15:
            return 20
        elif days_warming < 22:
            return 35
        else:
            return 50


class ClientResource(Base, UUIDMixin, TimestampMixin):
    """
    Client-level resource assignment.

    Links clients to resources from the pool. Tracks usage
    and allows for release on churn.
    """

    __tablename__ = "client_resources"

    # Foreign keys
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_pool_id: Mapped[UUID] = mapped_column(
        ForeignKey("resource_pool.id"),
        nullable=False,
    )

    # Assignment tracking
    assigned_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    # Usage tracking
    total_sends: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    # Relationships
    client: Mapped["Client"] = relationship(
        "Client",
        back_populates="resources",
        lazy="selectin",
    )
    resource: Mapped["ResourcePool"] = relationship(
        "ResourcePool",
        back_populates="client_resources",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ClientResource(client_id={self.client_id}, resource_id={self.resource_pool_id})>"

    @property
    def is_active(self) -> bool:
        """Check if assignment is still active."""
        return self.released_at is None

    @property
    def resource_type(self) -> ResourceType:
        """Get the resource type from the linked pool resource."""
        return self.resource.resource_type

    @property
    def resource_value(self) -> str:
        """Get the resource value from the linked pool resource."""
        return self.resource.resource_value

    def get_daily_limit(self) -> int:
        """Get daily limit for this resource."""
        return self.resource.get_daily_limit()

    def record_usage(self) -> None:
        """Record a usage of this resource."""
        self.total_sends += 1
        self.last_used_at = datetime.utcnow()

    def release(self) -> None:
        """Release this resource assignment."""
        self.released_at = datetime.utcnow()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] ResourceType enum
# [x] ResourceStatus enum
# [x] TIER_ALLOCATIONS constant
# [x] ResourcePool model with all fields from spec
# [x] ClientResource model with all fields from spec
# [x] Relationships defined
# [x] Helper properties (is_available, is_warmed)
# [x] Daily limit calculation with warmup schedule
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
