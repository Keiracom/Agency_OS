"""
Contract: src/services/domain_capacity_service.py
Purpose: Get current capacity for domains based on health and usage
Layer: 3 - services
Imports: models only
Consumers: orchestration, outreach flow
Spec: docs/architecture/distribution/EMAIL_DISTRIBUTION.md

This service:
1. Gets current daily capacity for a domain (health-adjusted)
2. Tracks today's usage vs capacity
3. Reserves 10% response buffer
4. Selects best domain for sending (round-robin with health awareness)
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.resource_pool import (
    ClientResource,
    HealthStatus,
    ResourcePool,
    ResourceType,
)

# Response buffer: 10% of capacity reserved for reply-to-reply emails
RESPONSE_BUFFER_PERCENT = 0.10


class DomainCapacityResult:
    """Result of a domain capacity check."""

    def __init__(
        self,
        domain: str,
        resource_pool_id: UUID,
        daily_limit: int,
        used_today: int,
        remaining: int,
        response_buffer: int,
        available_for_outbound: int,
        health_status: HealthStatus,
        is_available: bool,
    ):
        self.domain = domain
        self.resource_pool_id = resource_pool_id
        self.daily_limit = daily_limit
        self.used_today = used_today
        self.remaining = remaining
        self.response_buffer = response_buffer
        self.available_for_outbound = available_for_outbound
        self.health_status = health_status
        self.is_available = is_available

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "resource_pool_id": str(self.resource_pool_id),
            "daily_limit": self.daily_limit,
            "used_today": self.used_today,
            "remaining": self.remaining,
            "response_buffer": self.response_buffer,
            "available_for_outbound": self.available_for_outbound,
            "health_status": self.health_status.value,
            "is_available": self.is_available,
        }


class DomainCapacityService:
    """
    Service for getting domain capacity based on health and usage.

    Capacity Calculation:
    - Base: 50/day for fully warmed, healthy domains
    - Health reduction: 35/day for warning, 0/day for critical
    - Response buffer: 10% reserved for reply-to-reply emails
    """

    async def get_domain_capacity(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
    ) -> DomainCapacityResult:
        """
        Get current capacity for a domain.

        Args:
            db: Database session
            resource_pool_id: UUID of the resource pool entry

        Returns:
            DomainCapacityResult with capacity and usage info
        """
        # Get the resource
        resource = await db.get(ResourcePool, resource_pool_id)
        if not resource or resource.resource_type != ResourceType.EMAIL_DOMAIN:
            raise ValueError(f"Resource {resource_pool_id} is not an email domain")

        # Get daily limit from resource (includes health-based reduction)
        daily_limit = resource.get_daily_limit()

        # Count today's sends
        used_today = await self._count_domain_sends_today(
            db, resource.resource_value
        )

        # Calculate remaining
        remaining = max(0, daily_limit - used_today)

        # Calculate response buffer (10% of daily limit)
        response_buffer = int(daily_limit * RESPONSE_BUFFER_PERCENT)

        # Available for outbound = remaining - buffer
        available_for_outbound = max(0, remaining - response_buffer)

        # Determine if available for sending
        health_status = HealthStatus(resource.health_status)
        is_available = (
            health_status != HealthStatus.CRITICAL
            and available_for_outbound > 0
        )

        return DomainCapacityResult(
            domain=resource.resource_value,
            resource_pool_id=resource.id,
            daily_limit=daily_limit,
            used_today=used_today,
            remaining=remaining,
            response_buffer=response_buffer,
            available_for_outbound=available_for_outbound,
            health_status=health_status,
            is_available=is_available,
        )

    async def _count_domain_sends_today(
        self,
        db: AsyncSession,
        domain: str,
    ) -> int:
        """Count emails sent today for a domain."""
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        stmt = (
            select(func.count(Activity.id))
            .where(
                and_(
                    Activity.sender_domain == domain,
                    Activity.action == "sent",
                    Activity.channel == "email",
                    Activity.created_at >= today_start,
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def get_client_domain_capacities(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> list[DomainCapacityResult]:
        """
        Get capacity for all domains assigned to a client.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            List of DomainCapacityResult for client's domains
        """
        # Get client's email domains
        stmt = (
            select(ResourcePool)
            .join(ClientResource)
            .where(
                and_(
                    ClientResource.client_id == client_id,
                    ClientResource.released_at.is_(None),
                    ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN,
                )
            )
        )
        result = await db.execute(stmt)
        domains = result.scalars().all()

        capacities = []
        for domain in domains:
            capacity = await self.get_domain_capacity(db, domain.id)
            capacities.append(capacity)

        return capacities

    async def get_total_client_capacity(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> dict:
        """
        Get total email capacity for a client across all domains.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Dict with aggregated capacity info
        """
        capacities = await self.get_client_domain_capacities(db, client_id)

        total_daily_limit = sum(c.daily_limit for c in capacities)
        total_used_today = sum(c.used_today for c in capacities)
        total_remaining = sum(c.remaining for c in capacities)
        total_response_buffer = sum(c.response_buffer for c in capacities)
        total_available = sum(c.available_for_outbound for c in capacities)

        # Count domains by health
        healthy_count = sum(
            1 for c in capacities if c.health_status == HealthStatus.GOOD
        )
        warning_count = sum(
            1 for c in capacities if c.health_status == HealthStatus.WARNING
        )
        critical_count = sum(
            1 for c in capacities if c.health_status == HealthStatus.CRITICAL
        )

        return {
            "client_id": str(client_id),
            "domain_count": len(capacities),
            "total_daily_limit": total_daily_limit,
            "total_used_today": total_used_today,
            "total_remaining": total_remaining,
            "total_response_buffer": total_response_buffer,
            "total_available_for_outbound": total_available,
            "healthy_domains": healthy_count,
            "warning_domains": warning_count,
            "critical_domains": critical_count,
            "domains": [c.to_dict() for c in capacities],
        }

    async def select_best_domain(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> DomainCapacityResult | None:
        """
        Select the best domain for sending.

        Selection criteria:
        1. Must be healthy (not critical)
        2. Must have available capacity
        3. Prefers domains with more remaining capacity (load balancing)

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Best domain for sending, or None if no capacity
        """
        capacities = await self.get_client_domain_capacities(db, client_id)

        # Filter to available domains
        available = [c for c in capacities if c.is_available]

        if not available:
            return None

        # Sort by available capacity (highest first) for load balancing
        available.sort(key=lambda c: c.available_for_outbound, reverse=True)

        return available[0]

    async def can_send_email(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> tuple[bool, str]:
        """
        Check if client can send an email right now.

        Args:
            db: Database session
            client_id: Client UUID

        Returns:
            Tuple of (can_send, reason_if_not)
        """
        best = await self.select_best_domain(db, client_id)

        if not best:
            return False, "No domains with available capacity"

        return True, f"Available via {best.domain}"


# Singleton instance
_domain_capacity_service: DomainCapacityService | None = None


def get_domain_capacity_service() -> DomainCapacityService:
    """Get the domain capacity service singleton."""
    global _domain_capacity_service
    if _domain_capacity_service is None:
        _domain_capacity_service = DomainCapacityService()
    return _domain_capacity_service


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] get_domain_capacity() for single domain
# [x] get_client_domain_capacities() for all client domains
# [x] get_total_client_capacity() for aggregated view
# [x] select_best_domain() for domain selection
# [x] can_send_email() for send check
# [x] _count_domain_sends_today() helper
# [x] RESPONSE_BUFFER_PERCENT constant (10%)
# [x] DomainCapacityResult data class
# [x] Singleton pattern for service access
# [x] All functions have type hints and docstrings
