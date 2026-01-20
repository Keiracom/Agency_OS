"""
Contract: src/models/resource_pool.py
Purpose: Resource pool models for platform-level resource allocation
Layer: 1 - models
Imports: base only
Consumers: services, orchestration
Spec: docs/architecture/distribution/RESOURCE_POOL.md, EMAIL_DISTRIBUTION.md

Phase D additions:
- Domain health tracking fields (bounce_rate, complaint_rate, health_status)
- Health-based daily limit override
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Integer, Numeric, String, Text, ForeignKey
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


class HealthStatus(str, Enum):
    """Domain health status based on bounce/complaint rates."""
    GOOD = "good"          # <2% bounce, <0.05% complaint → 50/day
    WARNING = "warning"    # 2-5% bounce, 0.05-0.1% complaint → 35/day
    CRITICAL = "critical"  # >5% bounce, >0.1% complaint → 0/day (paused)


# ============================================
# HEALTH THRESHOLDS (per EMAIL_DISTRIBUTION.md)
# ============================================

HEALTH_THRESHOLDS = {
    "bounce": {
        "good": 0.02,      # <2%
        "warning": 0.05,   # 2-5%
        # >5% = critical
    },
    "complaint": {
        "good": 0.0005,    # <0.05%
        "warning": 0.001,  # 0.05-0.1%
        # >0.1% = critical
    },
}

HEALTH_DAILY_LIMITS = {
    HealthStatus.GOOD: 50,
    HealthStatus.WARNING: 35,
    HealthStatus.CRITICAL: 0,
}


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

    # === Health Tracking (Phase D - EMAIL_DISTRIBUTION.md) ===
    # 30-day rolling metrics
    sends_30d: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    bounces_30d: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    complaints_30d: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Calculated rates (updated by domain_health_service)
    bounce_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4),
        default=0,
        nullable=True,
    )
    complaint_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 5),
        default=0,
        nullable=True,
    )

    # Health status: good, warning, critical
    health_status: Mapped[str] = mapped_column(
        String(20),
        default=HealthStatus.GOOD.value,
        nullable=False,
    )

    # Daily limit override (for health-based reduction)
    # NULL = use default warmup-based limit
    daily_limit_override: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    # Last health check timestamp
    health_checked_at: Mapped[Optional[datetime]] = mapped_column(
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
        Get daily limit based on resource type, warmup status, and health.

        Email domains: Health override takes precedence, then warmup-based
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
        """
        Get daily email limit based on health status and warmup.

        Priority:
        1. Health-based override (if set)
        2. Warmup-based limit (if not fully warmed)
        3. Full capacity (50/day)
        """
        # Health override takes precedence
        if self.daily_limit_override is not None:
            return self.daily_limit_override

        # Check health status for fully warmed domains
        if self.warmup_completed_at:
            return HEALTH_DAILY_LIMITS.get(
                HealthStatus(self.health_status),
                50
            )

        # Not started warmup
        if not self.warmup_started_at:
            return 5

        # Warmup in progress
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

    @property
    def is_healthy(self) -> bool:
        """Check if domain has healthy bounce/complaint rates."""
        return self.health_status == HealthStatus.GOOD.value

    @property
    def is_paused(self) -> bool:
        """Check if domain is paused due to critical health."""
        return self.health_status == HealthStatus.CRITICAL.value

    def update_health_metrics(
        self,
        sends: int,
        bounces: int,
        complaints: int,
    ) -> None:
        """
        Update health metrics and recalculate status.

        Called by domain_health_service after aggregating 30-day metrics.
        """
        self.sends_30d = sends
        self.bounces_30d = bounces
        self.complaints_30d = complaints

        # Calculate rates
        if sends > 0:
            self.bounce_rate = Decimal(str(bounces / sends))
            self.complaint_rate = Decimal(str(complaints / sends))
        else:
            self.bounce_rate = Decimal("0")
            self.complaint_rate = Decimal("0")

        # Determine health status
        bounce_float = float(self.bounce_rate) if self.bounce_rate else 0
        complaint_float = float(self.complaint_rate) if self.complaint_rate else 0

        if bounce_float > HEALTH_THRESHOLDS["bounce"]["warning"] or \
           complaint_float > HEALTH_THRESHOLDS["complaint"]["warning"]:
            self.health_status = HealthStatus.CRITICAL.value
            self.daily_limit_override = 0
        elif bounce_float > HEALTH_THRESHOLDS["bounce"]["good"] or \
             complaint_float > HEALTH_THRESHOLDS["complaint"]["good"]:
            self.health_status = HealthStatus.WARNING.value
            self.daily_limit_override = 35
        else:
            self.health_status = HealthStatus.GOOD.value
            self.daily_limit_override = None  # Use default

        self.health_checked_at = datetime.utcnow()


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
# [x] HealthStatus enum (Phase D)
# [x] TIER_ALLOCATIONS constant
# [x] HEALTH_THRESHOLDS constant (Phase D)
# [x] HEALTH_DAILY_LIMITS constant (Phase D)
# [x] ResourcePool model with all fields from spec
# [x] Health tracking fields (sends_30d, bounces_30d, etc.) (Phase D)
# [x] ClientResource model with all fields from spec
# [x] Relationships defined
# [x] Helper properties (is_available, is_warmed, is_healthy, is_paused)
# [x] Daily limit calculation with warmup + health override
# [x] update_health_metrics() method (Phase D)
# [x] No imports from engines/integrations/orchestration (Rule 12)
# [x] All fields have type hints
