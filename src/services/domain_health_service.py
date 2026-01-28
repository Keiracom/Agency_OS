"""
Contract: src/services/domain_health_service.py
Purpose: Monitor and update domain health metrics (bounce/complaint rates)
Layer: 3 - services
Imports: models only
Consumers: orchestration, scheduled jobs
Spec: docs/architecture/distribution/EMAIL_DISTRIBUTION.md

This service:
1. Calculates 30-day rolling health metrics from activities
2. Updates ResourcePool health status (good/warning/critical)
3. Triggers alerts for degraded domains
4. Provides health check for individual domains
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.resource_pool import (
    HEALTH_DAILY_LIMITS,
    HEALTH_THRESHOLDS,
    HealthStatus,
    ResourcePool,
    ResourceType,
)


class DomainHealthResult:
    """Result of a domain health check."""

    def __init__(
        self,
        domain: str,
        sends_30d: int,
        bounces_30d: int,
        complaints_30d: int,
        bounce_rate: float,
        complaint_rate: float,
        status: HealthStatus,
        daily_limit: int,
        action: str,
    ):
        self.domain = domain
        self.sends_30d = sends_30d
        self.bounces_30d = bounces_30d
        self.complaints_30d = complaints_30d
        self.bounce_rate = bounce_rate
        self.complaint_rate = complaint_rate
        self.status = status
        self.daily_limit = daily_limit
        self.action = action

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "sends_30d": self.sends_30d,
            "bounces_30d": self.bounces_30d,
            "complaints_30d": self.complaints_30d,
            "bounce_rate": self.bounce_rate,
            "complaint_rate": self.complaint_rate,
            "status": self.status.value,
            "daily_limit": self.daily_limit,
            "action": self.action,
        }


class DomainHealthService:
    """
    Service for monitoring and updating domain health metrics.

    Health Status Thresholds (per EMAIL_DISTRIBUTION.md):
    - Good: <2% bounce, <0.05% complaint → 50/day
    - Warning: 2-5% bounce, 0.05-0.1% complaint → 35/day + alert
    - Critical: >5% bounce, >0.1% complaint → 0/day (paused) + alert
    """

    async def check_domain_health(
        self,
        db: AsyncSession,
        domain: str,
    ) -> DomainHealthResult:
        """
        Check health metrics for a specific domain.

        Calculates 30-day rolling metrics from activities table.

        Args:
            db: Database session
            domain: Domain to check (e.g., 'outreach-mail.com')

        Returns:
            DomainHealthResult with metrics and recommended action
        """
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Get send count
        sends_stmt = select(func.count(Activity.id)).where(
            and_(
                Activity.sender_domain == domain,
                Activity.action == "sent",
                Activity.channel == "email",
                Activity.created_at >= thirty_days_ago,
            )
        )
        sends_result = await db.execute(sends_stmt)
        sends_30d = sends_result.scalar() or 0

        # Get bounce count
        bounces_stmt = select(func.count(Activity.id)).where(
            and_(
                Activity.sender_domain == domain,
                Activity.action == "bounced",
                Activity.channel == "email",
                Activity.created_at >= thirty_days_ago,
            )
        )
        bounces_result = await db.execute(bounces_stmt)
        bounces_30d = bounces_result.scalar() or 0

        # Get complaint count
        complaints_stmt = select(func.count(Activity.id)).where(
            and_(
                Activity.sender_domain == domain,
                Activity.action == "complained",
                Activity.channel == "email",
                Activity.created_at >= thirty_days_ago,
            )
        )
        complaints_result = await db.execute(complaints_stmt)
        complaints_30d = complaints_result.scalar() or 0

        # Calculate rates
        bounce_rate = bounces_30d / sends_30d if sends_30d > 0 else 0
        complaint_rate = complaints_30d / sends_30d if sends_30d > 0 else 0

        # Determine status and action
        status, action = self._determine_status(bounce_rate, complaint_rate)
        daily_limit = HEALTH_DAILY_LIMITS[status]

        return DomainHealthResult(
            domain=domain,
            sends_30d=sends_30d,
            bounces_30d=bounces_30d,
            complaints_30d=complaints_30d,
            bounce_rate=bounce_rate,
            complaint_rate=complaint_rate,
            status=status,
            daily_limit=daily_limit,
            action=action,
        )

    def _determine_status(
        self,
        bounce_rate: float,
        complaint_rate: float,
    ) -> tuple[HealthStatus, str]:
        """
        Determine health status from rates.

        Returns:
            Tuple of (HealthStatus, action_string)
        """
        # Critical: >5% bounce OR >0.1% complaint
        if (
            bounce_rate > HEALTH_THRESHOLDS["bounce"]["warning"]
            or complaint_rate > HEALTH_THRESHOLDS["complaint"]["warning"]
        ):
            return HealthStatus.CRITICAL, "pause"

        # Warning: 2-5% bounce OR 0.05-0.1% complaint
        if (
            bounce_rate > HEALTH_THRESHOLDS["bounce"]["good"]
            or complaint_rate > HEALTH_THRESHOLDS["complaint"]["good"]
        ):
            return HealthStatus.WARNING, "reduce_limit"

        # Good
        return HealthStatus.GOOD, "none"

    async def update_domain_health(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
    ) -> DomainHealthResult:
        """
        Update health metrics for a domain in the resource pool.

        Args:
            db: Database session
            resource_pool_id: UUID of the resource pool entry

        Returns:
            DomainHealthResult with updated metrics
        """
        # Get the resource
        resource = await db.get(ResourcePool, resource_pool_id)
        if not resource or resource.resource_type != ResourceType.EMAIL_DOMAIN:
            raise ValueError(f"Resource {resource_pool_id} is not an email domain")

        # Check health
        result = await self.check_domain_health(db, resource.resource_value)

        # Update the resource
        resource.update_health_metrics(
            sends=result.sends_30d,
            bounces=result.bounces_30d,
            complaints=result.complaints_30d,
        )

        await db.commit()

        return result

    async def update_all_domain_health(
        self,
        db: AsyncSession,
    ) -> list[DomainHealthResult]:
        """
        Update health metrics for all email domains in the pool.

        Called by scheduled job (e.g., daily at midnight).

        Args:
            db: Database session

        Returns:
            List of DomainHealthResult for all domains
        """
        # Get all email domains
        stmt = select(ResourcePool).where(ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN)
        result = await db.execute(stmt)
        domains = result.scalars().all()

        results = []
        for domain in domains:
            health_result = await self.check_domain_health(db, domain.resource_value)

            # Update the resource
            domain.update_health_metrics(
                sends=health_result.sends_30d,
                bounces=health_result.bounces_30d,
                complaints=health_result.complaints_30d,
            )

            results.append(health_result)

        await db.commit()

        return results

    async def get_unhealthy_domains(
        self,
        db: AsyncSession,
    ) -> list[ResourcePool]:
        """
        Get all domains with warning or critical health status.

        Args:
            db: Database session

        Returns:
            List of ResourcePool entries with degraded health
        """
        stmt = select(ResourcePool).where(
            and_(
                ResourcePool.resource_type == ResourceType.EMAIL_DOMAIN,
                ResourcePool.health_status.in_(
                    [
                        HealthStatus.WARNING.value,
                        HealthStatus.CRITICAL.value,
                    ]
                ),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def restore_domain_health(
        self,
        db: AsyncSession,
        resource_pool_id: UUID,
    ) -> bool:
        """
        Attempt to restore a domain from warning/critical to good.

        Called after investigating and fixing issues.
        Re-evaluates health metrics - if improved, restores capacity.

        Args:
            db: Database session
            resource_pool_id: UUID of the resource pool entry

        Returns:
            True if health was restored to good
        """
        result = await self.update_domain_health(db, resource_pool_id)
        return result.status == HealthStatus.GOOD


# Singleton instance
_domain_health_service: DomainHealthService | None = None


def get_domain_health_service() -> DomainHealthService:
    """Get the domain health service singleton."""
    global _domain_health_service
    if _domain_health_service is None:
        _domain_health_service = DomainHealthService()
    return _domain_health_service


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] check_domain_health() for individual domain check
# [x] update_domain_health() for single domain update
# [x] update_all_domain_health() for batch update
# [x] get_unhealthy_domains() for monitoring
# [x] restore_domain_health() for recovery
# [x] DomainHealthResult data class
# [x] _determine_status() uses HEALTH_THRESHOLDS
# [x] Singleton pattern for service access
# [x] All functions have type hints and docstrings
