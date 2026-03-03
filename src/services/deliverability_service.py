"""
Contract: src/services/deliverability_service.py
Purpose: Email deliverability monitoring and warmup status tracking
Layer: 3 - services
Imports: integrations
Consumers: orchestration, API routes, dashboard

FILE: src/services/deliverability_service.py
PURPOSE: Monitor warmup status, health scores, and domain reputation
PHASE: Directive 048 (Part G)
TASK: DELIV-001
DEPENDENCIES:
  - src/integrations/warmforge.py
  - src/integrations/salesforge.py
  - src/services/alert_service.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Expose structured data for dashboard consumption

REQUIREMENTS:
1. Query and report current warmup status for all domains
2. Confirm Warmforge warmup is active and progressing
3. Expose warmup status, daily send limit, health score per domain
"""

import json
import logging
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

WARMUP_HEALTH_THRESHOLD = 70.0  # Minimum acceptable health score
WARMUP_STAGES = ["initializing", "ramping", "stable", "paused", "completed"]


# =============================================================================
# DELIVERABILITY SERVICE
# =============================================================================


class DeliverabilityService:
    """
    Service for monitoring email deliverability and warmup status.

    Provides:
    - Warmup status reports for all domains
    - Health score tracking
    - Integration with Warmforge/Mailforge
    - Dashboard-ready data feeds
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize Deliverability Service.

        Args:
            session: Async database session
        """
        self.session = session

    async def get_warmup_status_report(
        self,
        client_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Query and report current warmup status for all configured domains.

        Shows warmup_started_at, warmup_completed_at, daily send limit,
        and estimated health score per domain.

        Args:
            client_id: Optional filter by client

        Returns:
            Report with all domain warmup statuses
        """
        try:
            # Get domain status from database
            query = text("""
                SELECT
                    dws.client_id,
                    c.business_name,
                    dws.domain,
                    dws.provider,
                    dws.warmup_started_at,
                    dws.warmup_completed_at,
                    dws.warmup_stage,
                    dws.daily_send_limit,
                    dws.current_send_count,
                    dws.health_score,
                    dws.reputation_score,
                    dws.bounce_rate,
                    dws.spam_rate,
                    dws.open_rate,
                    dws.last_checked_at,
                    dws.last_send_at,
                    dws.provider_data
                FROM domain_warmup_status dws
                LEFT JOIN clients c ON dws.client_id = c.id
                WHERE (:client_id IS NULL OR dws.client_id = :client_id)
                ORDER BY dws.health_score ASC NULLS LAST
            """)

            result = await self.session.execute(
                query,
                {"client_id": str(client_id) if client_id else None},
            )
            rows = result.fetchall()

            domains = []
            total_domains = 0
            healthy_domains = 0
            warming_domains = 0
            paused_domains = 0

            for row in rows:
                total_domains += 1
                health = row.health_score or 0

                if health >= WARMUP_HEALTH_THRESHOLD:
                    healthy_domains += 1

                if row.warmup_stage == "ramping":
                    warming_domains += 1
                elif row.warmup_stage == "paused":
                    paused_domains += 1

                domains.append(
                    {
                        "client_id": str(row.client_id),
                        "business_name": row.business_name,
                        "domain": row.domain,
                        "provider": row.provider,
                        "warmup_started_at": row.warmup_started_at.isoformat()
                        if row.warmup_started_at
                        else None,
                        "warmup_completed_at": row.warmup_completed_at.isoformat()
                        if row.warmup_completed_at
                        else None,
                        "warmup_stage": row.warmup_stage,
                        "daily_send_limit": row.daily_send_limit,
                        "current_send_count": row.current_send_count,
                        "health_score": float(row.health_score) if row.health_score else None,
                        "reputation_score": float(row.reputation_score)
                        if row.reputation_score
                        else None,
                        "bounce_rate": float(row.bounce_rate) if row.bounce_rate else None,
                        "spam_rate": float(row.spam_rate) if row.spam_rate else None,
                        "open_rate": float(row.open_rate) if row.open_rate else None,
                        "is_healthy": health >= WARMUP_HEALTH_THRESHOLD,
                        "last_checked_at": row.last_checked_at.isoformat()
                        if row.last_checked_at
                        else None,
                        "last_send_at": row.last_send_at.isoformat() if row.last_send_at else None,
                    }
                )

            return {
                "report_generated_at": datetime.now(UTC).isoformat(),
                "total_domains": total_domains,
                "healthy_domains": healthy_domains,
                "warming_domains": warming_domains,
                "paused_domains": paused_domains,
                "health_threshold": WARMUP_HEALTH_THRESHOLD,
                "domains": domains,
            }

        except Exception as e:
            logger.error(f"Failed to get warmup status report: {e}")
            return {
                "error": str(e),
                "report_generated_at": datetime.now(UTC).isoformat(),
                "domains": [],
            }

    async def sync_warmforge_status(
        self,
        client_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Sync warmup status from Warmforge API.

        Queries Warmforge for current status and updates local database.

        Args:
            client_id: Optional filter by client

        Returns:
            Sync result with updated domains
        """
        try:
            from src.integrations.warmforge import get_warmforge_client

            warmforge = get_warmforge_client()

            # Get all accounts from Warmforge
            accounts = await warmforge.list_accounts()

            updated = 0
            errors = []

            for account in accounts:
                try:
                    domain = account.get("domain") or account.get("email", "").split("@")[-1]

                    if not domain:
                        continue

                    # Get detailed status
                    status = await warmforge.get_account_status(account.get("id"))

                    # Map warmup stage
                    warmup_stage = "stable"
                    if status.get("is_warming"):
                        warmup_stage = "ramping"
                    elif status.get("is_paused"):
                        warmup_stage = "paused"
                    elif status.get("warmup_completed"):
                        warmup_stage = "completed"

                    # Update database
                    await self.session.execute(
                        text("""
                            INSERT INTO domain_warmup_status (
                                client_id, domain, provider,
                                warmup_started_at, warmup_completed_at,
                                warmup_stage, daily_send_limit,
                                health_score, reputation_score,
                                bounce_rate, spam_rate, open_rate,
                                provider_account_id, provider_data,
                                last_checked_at
                            ) VALUES (
                                :client_id, :domain, 'warmforge',
                                :warmup_started, :warmup_completed,
                                :stage, :daily_limit,
                                :health, :reputation,
                                :bounce, :spam, :open_rate,
                                :provider_id, :provider_data,
                                NOW()
                            )
                            ON CONFLICT (client_id, domain) DO UPDATE
                            SET warmup_stage = :stage,
                                daily_send_limit = :daily_limit,
                                health_score = :health,
                                reputation_score = :reputation,
                                bounce_rate = :bounce,
                                spam_rate = :spam,
                                open_rate = :open_rate,
                                provider_data = :provider_data,
                                last_checked_at = NOW(),
                                updated_at = NOW()
                        """),
                        {
                            "client_id": str(client_id) if client_id else None,
                            "domain": domain,
                            "warmup_started": status.get("warmup_started_at"),
                            "warmup_completed": status.get("warmup_completed_at"),
                            "stage": warmup_stage,
                            "daily_limit": status.get("daily_limit", 10),
                            "health": status.get("health_score"),
                            "reputation": status.get("reputation_score"),
                            "bounce": status.get("bounce_rate"),
                            "spam": status.get("spam_rate"),
                            "open_rate": status.get("open_rate"),
                            "provider_id": str(account.get("id")),
                            "provider_data": json.dumps(status),
                        },
                    )
                    updated += 1

                except Exception as e:
                    errors.append({"domain": account.get("domain"), "error": str(e)})

            await self.session.commit()

            return {
                "success": True,
                "updated_domains": updated,
                "errors": errors,
                "synced_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to sync Warmforge status: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def check_warmup_health_alerts(
        self,
        client_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Check for domains with health scores below threshold and create alerts.

        Args:
            client_id: Optional filter by client

        Returns:
            List of alerts created
        """
        from src.services.alert_service import get_alert_service

        alerts_created = []

        try:
            # Find unhealthy domains
            result = await self.session.execute(
                text("""
                    SELECT client_id, domain, health_score
                    FROM domain_warmup_status
                    WHERE health_score < :threshold
                    AND (:client_id IS NULL OR client_id = :client_id)
                """),
                {
                    "threshold": WARMUP_HEALTH_THRESHOLD,
                    "client_id": str(client_id) if client_id else None,
                },
            )
            rows = result.fetchall()

            alert_service = get_alert_service(self.session)

            for row in rows:
                alert_id = await alert_service.alert_warmup_health_low(
                    client_id=UUID(str(row.client_id)),
                    domain=row.domain,
                    health_score=float(row.health_score) if row.health_score else 0,
                    threshold=WARMUP_HEALTH_THRESHOLD,
                )

                if alert_id:
                    alerts_created.append(
                        {
                            "client_id": str(row.client_id),
                            "domain": row.domain,
                            "health_score": float(row.health_score) if row.health_score else 0,
                            "alert_id": str(alert_id),
                        }
                    )

            return alerts_created

        except Exception as e:
            logger.error(f"Failed to check warmup health alerts: {e}")
            return []

    async def get_deliverability_data_feed(
        self,
        client_id: UUID,
    ) -> dict[str, Any]:
        """
        Get structured deliverability data for dashboard consumption.

        Exposes warmup status, daily send limit, and health score per domain
        in a format ready for dashboard rendering.

        Args:
            client_id: Client UUID

        Returns:
            Structured data feed for dashboard
        """
        report = await self.get_warmup_status_report(client_id)

        # Transform for dashboard consumption
        return {
            "client_id": str(client_id),
            "generated_at": report.get("report_generated_at"),
            "summary": {
                "total_domains": report.get("total_domains", 0),
                "healthy_domains": report.get("healthy_domains", 0),
                "warming_domains": report.get("warming_domains", 0),
                "paused_domains": report.get("paused_domains", 0),
                "overall_health": (
                    (report.get("healthy_domains", 0) / report.get("total_domains", 1)) * 100
                    if report.get("total_domains", 0) > 0
                    else 0
                ),
            },
            "domains": [
                {
                    "domain": d["domain"],
                    "status": d["warmup_stage"],
                    "health_score": d["health_score"],
                    "is_healthy": d["is_healthy"],
                    "daily_limit": d["daily_send_limit"],
                    "sends_today": d["current_send_count"],
                    "utilization": (
                        (d["current_send_count"] / d["daily_send_limit"]) * 100
                        if d["daily_send_limit"] > 0
                        else 0
                    ),
                    "metrics": {
                        "bounce_rate": d["bounce_rate"],
                        "spam_rate": d["spam_rate"],
                        "open_rate": d["open_rate"],
                    },
                    "last_activity": d["last_send_at"],
                }
                for d in report.get("domains", [])
            ],
        }


# =============================================================================
# SINGLETON & HELPERS
# =============================================================================


def get_deliverability_service(session: AsyncSession) -> DeliverabilityService:
    """Get deliverability service instance for the given session."""
    return DeliverabilityService(session)


async def get_warmup_report(session: AsyncSession, client_id: UUID | None = None) -> dict:
    """Convenience function to get warmup report."""
    service = get_deliverability_service(session)
    return await service.get_warmup_status_report(client_id)


# =============================================================================
# VERIFICATION CHECKLIST
# =============================================================================
# [x] Contract comment at top
# [x] get_warmup_status_report - shows all domain statuses
# [x] warmup_started_at, warmup_completed_at per domain
# [x] daily_send_limit per domain
# [x] health_score (estimated) per domain
# [x] sync_warmforge_status - sync from Warmforge API
# [x] check_warmup_health_alerts - create alerts for unhealthy domains
# [x] get_deliverability_data_feed - dashboard-ready format
# [x] All methods async with type hints
# [x] All methods have docstrings
