"""
Contract: src/services/linkedin_health_service.py
Purpose: Manage LinkedIn seat health metrics and apply safety limits
Layer: 3 - services
Imports: models, integrations
Consumers: orchestration flows, API routes
Spec: docs/architecture/distribution/LINKEDIN.md

Health Thresholds:
- Accept rate <30% (7d): Warning - reduce limit 25% (to 15/day)
- Accept rate <20% (7d): Critical - reduce limit 50% (to 10/day)
- Pending count >50: Warning - alert admin
- Pending count >80: Critical - alert admin
- Restriction detected: Pause seat (0/day), alert admin
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.linkedin_seat import LinkedInSeat, LinkedInSeatStatus
from src.models.linkedin_connection import LinkedInConnection, LinkedInConnectionStatus
from src.integrations.unipile import get_unipile_client

logger = logging.getLogger(__name__)

# Health thresholds
ACCEPT_RATE_WARNING = Decimal("0.30")  # 30%
ACCEPT_RATE_CRITICAL = Decimal("0.20")  # 20%
PENDING_WARNING_THRESHOLD = 50
PENDING_CRITICAL_THRESHOLD = 80

# Limit reductions
LIMIT_WARNING_REDUCTION = 15  # 25% reduction (from 20 to 15)
LIMIT_CRITICAL_REDUCTION = 10  # 50% reduction (from 20 to 10)

# Stale connection constants
STALE_CONNECTION_DAYS = 30  # Withdraw after 30 days pending
MAX_WITHDRAWALS_PER_RUN = 10  # Max withdrawals per seat per daily run
WITHDRAWAL_DELAY_SECONDS = 2  # Delay between withdrawals (rate limiting)


class LinkedInHealthService:
    """
    Manages LinkedIn seat health metrics.

    Monitors accept rates and pending counts to:
    1. Detect unhealthy accounts before LinkedIn flags them
    2. Apply automatic limit reductions
    3. Alert admins about critical issues
    """

    async def calculate_accept_rate(
        self,
        db: AsyncSession,
        seat_id: UUID,
        days: int = 7,
    ) -> dict[str, Any]:
        """
        Calculate accept rate for a seat over a period.

        Args:
            db: Database session
            seat_id: Seat UUID
            days: Lookback period (7 or 30)

        Returns:
            Dict with accept rate stats
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Count total requests in period
        total_stmt = (
            select(func.count(LinkedInConnection.id))
            .where(
                and_(
                    LinkedInConnection.seat_id == seat_id,
                    LinkedInConnection.requested_at >= cutoff,
                )
            )
        )
        total_result = await db.execute(total_stmt)
        total = total_result.scalar() or 0

        # Count accepted in period
        accepted_stmt = (
            select(func.count(LinkedInConnection.id))
            .where(
                and_(
                    LinkedInConnection.seat_id == seat_id,
                    LinkedInConnection.requested_at >= cutoff,
                    LinkedInConnection.status == "accepted",
                )
            )
        )
        accepted_result = await db.execute(accepted_stmt)
        accepted = accepted_result.scalar() or 0

        # Calculate rate
        rate = Decimal(accepted) / Decimal(total) if total > 0 else None

        return {
            "seat_id": str(seat_id),
            "period_days": days,
            "total_requests": total,
            "accepted": accepted,
            "accept_rate": float(rate) if rate is not None else None,
        }

    async def get_pending_count(
        self,
        db: AsyncSession,
        seat_id: UUID,
    ) -> int:
        """
        Get count of pending connection requests.

        Args:
            db: Database session
            seat_id: Seat UUID

        Returns:
            Number of pending requests
        """
        stmt = (
            select(func.count(LinkedInConnection.id))
            .where(
                and_(
                    LinkedInConnection.seat_id == seat_id,
                    LinkedInConnection.status == "pending",
                )
            )
        )
        result = await db.execute(stmt)
        return result.scalar() or 0

    async def update_seat_health(
        self,
        db: AsyncSession,
        seat: LinkedInSeat,
    ) -> dict[str, Any]:
        """
        Update health metrics for a single seat.

        Calculates accept rates, pending count, and applies limits.

        Args:
            db: Database session
            seat: LinkedIn seat to update

        Returns:
            Dict with health update results
        """
        # Calculate 7-day accept rate
        stats_7d = await self.calculate_accept_rate(db, seat.id, days=7)

        # Calculate 30-day accept rate
        stats_30d = await self.calculate_accept_rate(db, seat.id, days=30)

        # Get pending count
        pending = await self.get_pending_count(db, seat.id)

        # Update seat metrics
        old_rate_7d = float(seat.accept_rate_7d) if seat.accept_rate_7d else None
        old_override = seat.daily_limit_override

        seat.accept_rate_7d = (
            Decimal(str(stats_7d["accept_rate"]))
            if stats_7d["accept_rate"] is not None
            else None
        )
        seat.accept_rate_30d = (
            Decimal(str(stats_30d["accept_rate"]))
            if stats_30d["accept_rate"] is not None
            else None
        )
        seat.pending_count = pending

        # Determine health status and apply limits
        alerts = []
        action = "none"

        if seat.accept_rate_7d is not None:
            if seat.accept_rate_7d < ACCEPT_RATE_CRITICAL:
                seat.daily_limit_override = LIMIT_CRITICAL_REDUCTION
                action = "critical_reduction"
                alerts.append({
                    "type": "accept_rate_critical",
                    "message": f"Accept rate critically low: {float(seat.accept_rate_7d):.1%}",
                    "threshold": float(ACCEPT_RATE_CRITICAL),
                    "new_limit": LIMIT_CRITICAL_REDUCTION,
                })
            elif seat.accept_rate_7d < ACCEPT_RATE_WARNING:
                seat.daily_limit_override = LIMIT_WARNING_REDUCTION
                action = "warning_reduction"
                alerts.append({
                    "type": "accept_rate_warning",
                    "message": f"Accept rate below target: {float(seat.accept_rate_7d):.1%}",
                    "threshold": float(ACCEPT_RATE_WARNING),
                    "new_limit": LIMIT_WARNING_REDUCTION,
                })
            else:
                # Healthy - remove override (unless restricted)
                if seat.status != LinkedInSeatStatus.RESTRICTED:
                    seat.daily_limit_override = None
                    if old_override is not None:
                        action = "restored"

        # Check pending count
        if pending >= PENDING_CRITICAL_THRESHOLD:
            alerts.append({
                "type": "pending_critical",
                "message": f"Pending requests critically high: {pending}",
                "threshold": PENDING_CRITICAL_THRESHOLD,
            })
        elif pending >= PENDING_WARNING_THRESHOLD:
            alerts.append({
                "type": "pending_warning",
                "message": f"Pending requests above normal: {pending}",
                "threshold": PENDING_WARNING_THRESHOLD,
            })

        await db.commit()

        # Log alerts
        for alert in alerts:
            if "critical" in alert["type"]:
                logger.warning(f"Seat {seat.id} CRITICAL: {alert['message']}")
            else:
                logger.info(f"Seat {seat.id} warning: {alert['message']}")

        return {
            "seat_id": str(seat.id),
            "accept_rate_7d": stats_7d["accept_rate"],
            "accept_rate_30d": stats_30d["accept_rate"],
            "pending_count": pending,
            "daily_limit": seat.daily_limit,
            "action": action,
            "alerts": alerts,
            "previous_rate_7d": old_rate_7d,
            "previous_override": old_override,
        }

    async def update_all_seats_health(
        self,
        db: AsyncSession,
        client_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Update health metrics for all active seats.

        Args:
            db: Database session
            client_id: Optional client filter

        Returns:
            Dict with processing summary
        """
        # Get active seats (warmup or active)
        stmt = select(LinkedInSeat).where(
            LinkedInSeat.status.in_([
                LinkedInSeatStatus.WARMUP,
                LinkedInSeatStatus.ACTIVE,
            ])
        )

        if client_id:
            stmt = stmt.where(LinkedInSeat.client_id == client_id)

        result = await db.execute(stmt)
        seats = list(result.scalars().all())

        if not seats:
            logger.info("No active seats to update health metrics")
            return {
                "total": 0,
                "healthy": 0,
                "warning": 0,
                "critical": 0,
                "seats": [],
            }

        results = []
        healthy = 0
        warning = 0
        critical = 0

        for seat in seats:
            health_result = await self.update_seat_health(db, seat)
            results.append(health_result)

            if health_result["action"] == "critical_reduction":
                critical += 1
            elif health_result["action"] == "warning_reduction":
                warning += 1
            else:
                healthy += 1

        logger.info(
            f"Updated health for {len(seats)} seats: "
            f"{healthy} healthy, {warning} warning, {critical} critical"
        )

        return {
            "total": len(seats),
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "seats": results,
        }

    async def mark_stale_connections_ignored(
        self,
        db: AsyncSession,
        days: int = 14,
    ) -> dict[str, Any]:
        """
        Mark pending connections older than threshold as ignored.

        Per spec: 14 days pending → mark ignored.

        Args:
            db: Database session
            days: Days threshold (default 14)

        Returns:
            Dict with update count
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        stmt = (
            update(LinkedInConnection)
            .where(
                and_(
                    LinkedInConnection.status == "pending",
                    LinkedInConnection.requested_at < cutoff,
                )
            )
            .values(
                status="ignored",
                responded_at=datetime.utcnow(),
            )
            .returning(LinkedInConnection.id)
        )

        result = await db.execute(stmt)
        updated_ids = list(result.scalars().all())
        await db.commit()

        if updated_ids:
            logger.info(f"Marked {len(updated_ids)} stale connections as ignored (>{days} days)")

        return {
            "updated_count": len(updated_ids),
            "threshold_days": days,
        }

    async def withdraw_stale_requests(
        self,
        db: AsyncSession,
        days: int = STALE_CONNECTION_DAYS,
        max_per_seat: int = MAX_WITHDRAWALS_PER_RUN,
    ) -> dict[str, Any]:
        """
        Withdraw pending connections older than threshold via Unipile API.

        Per spec: 30 days pending -> withdraw request.
        Withdrawing frees up connection request slots on LinkedIn.

        This runs weekly (or can be triggered manually) and processes
        stale connections across all active seats.

        Args:
            db: Database session
            days: Days threshold for stale (default 30)
            max_per_seat: Max withdrawals per seat per run (default 10)

        Returns:
            Dict with withdrawal summary:
            - total_stale: Number of stale connections found
            - withdrawn: Number successfully withdrawn
            - failed: Number that failed to withdraw
            - by_seat: Per-seat breakdown
        """
        import asyncio

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all stale pending connections with their seats
        stmt = (
            select(LinkedInConnection)
            .join(LinkedInSeat)
            .where(
                and_(
                    LinkedInConnection.status == LinkedInConnectionStatus.PENDING,
                    LinkedInConnection.requested_at < cutoff,
                    LinkedInSeat.status.in_([
                        LinkedInSeatStatus.WARMUP,
                        LinkedInSeatStatus.ACTIVE,
                    ]),
                )
            )
            .order_by(LinkedInConnection.requested_at.asc())  # Oldest first
        )
        result = await db.execute(stmt)
        stale_connections = list(result.scalars().all())

        if not stale_connections:
            logger.info(f"No stale connections found (>{days} days)")
            return {
                "total_stale": 0,
                "withdrawn": 0,
                "failed": 0,
                "by_seat": {},
            }

        # Group by seat for processing limits
        by_seat: dict[str, list[LinkedInConnection]] = {}
        for conn in stale_connections:
            seat_id = str(conn.seat_id)
            if seat_id not in by_seat:
                by_seat[seat_id] = []
            by_seat[seat_id].append(conn)

        # Get Unipile client
        unipile = get_unipile_client()

        # Process withdrawals
        total_withdrawn = 0
        total_failed = 0
        seat_results: dict[str, dict] = {}

        for seat_id, connections in by_seat.items():
            # Get seat for account_id
            seat = connections[0].seat if connections else None
            if not seat or not seat.unipile_account_id:
                logger.warning(f"Seat {seat_id} has no Unipile account ID, skipping")
                seat_results[seat_id] = {
                    "stale": len(connections),
                    "withdrawn": 0,
                    "failed": 0,
                    "error": "no_unipile_account",
                }
                continue

            withdrawn = 0
            failed = 0

            # Process up to max_per_seat for this seat
            for conn in connections[:max_per_seat]:
                if not conn.unipile_request_id:
                    # No invitation ID stored, mark as withdrawn locally
                    conn.mark_withdrawn()
                    withdrawn += 1
                    logger.debug(f"Connection {conn.id} marked withdrawn (no invitation ID)")
                    continue

                try:
                    await unipile.withdraw_invitation(
                        account_id=seat.unipile_account_id,
                        invitation_id=conn.unipile_request_id,
                    )
                    conn.mark_withdrawn()
                    withdrawn += 1
                    logger.debug(f"Withdrew connection {conn.id} ({conn.days_pending} days old)")

                    # Rate limiting between withdrawals
                    if withdrawn < max_per_seat:
                        await asyncio.sleep(WITHDRAWAL_DELAY_SECONDS)

                except Exception as e:
                    failed += 1
                    logger.warning(f"Failed to withdraw connection {conn.id}: {e}")

            await db.commit()

            seat_results[seat_id] = {
                "stale": len(connections),
                "withdrawn": withdrawn,
                "failed": failed,
                "remaining": max(0, len(connections) - max_per_seat),
            }

            total_withdrawn += withdrawn
            total_failed += failed

        logger.info(
            f"Withdrew {total_withdrawn} stale connections (>{days} days), "
            f"{total_failed} failed, {len(stale_connections) - total_withdrawn - total_failed} remaining"
        )

        return {
            "total_stale": len(stale_connections),
            "withdrawn": total_withdrawn,
            "failed": total_failed,
            "threshold_days": days,
            "by_seat": seat_results,
        }

    async def detect_restrictions(
        self,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        Detect seats that may be restricted (no activity, errors).

        This is a safety check - actual restriction webhooks come from Unipile.

        Returns:
            List of potentially restricted seats
        """
        # Find seats that haven't had successful sends in 3+ days
        # despite being in active/warmup status
        cutoff = datetime.utcnow() - timedelta(days=3)

        # Get seats with no recent activity
        stmt = (
            select(LinkedInSeat)
            .where(
                and_(
                    LinkedInSeat.status.in_([
                        LinkedInSeatStatus.WARMUP,
                        LinkedInSeatStatus.ACTIVE,
                    ]),
                    LinkedInSeat.activated_at < cutoff,
                )
            )
        )
        result = await db.execute(stmt)
        seats = list(result.scalars().all())

        suspicious = []
        for seat in seats:
            # Check if any connections in last 3 days
            conn_stmt = (
                select(func.count(LinkedInConnection.id))
                .where(
                    and_(
                        LinkedInConnection.seat_id == seat.id,
                        LinkedInConnection.requested_at >= cutoff,
                    )
                )
            )
            conn_result = await db.execute(conn_stmt)
            recent_count = conn_result.scalar() or 0

            if recent_count == 0 and seat.daily_limit > 0:
                suspicious.append({
                    "seat_id": str(seat.id),
                    "client_id": str(seat.client_id),
                    "account_name": seat.account_name,
                    "status": seat.status,
                    "days_no_activity": 3,
                    "reason": "No connections sent despite having quota",
                })

        if suspicious:
            logger.warning(f"Found {len(suspicious)} potentially restricted seats")

        return suspicious

    async def get_health_summary(
        self,
        db: AsyncSession,
        seat_id: UUID,
    ) -> dict[str, Any]:
        """
        Get comprehensive health summary for a seat.

        Args:
            db: Database session
            seat_id: Seat UUID

        Returns:
            Dict with full health details
        """
        seat = await db.get(LinkedInSeat, seat_id)

        if not seat:
            return {"error": "seat_not_found"}

        stats_7d = await self.calculate_accept_rate(db, seat_id, days=7)
        stats_30d = await self.calculate_accept_rate(db, seat_id, days=30)
        pending = await self.get_pending_count(db, seat_id)

        # Determine health status
        health_status = "healthy"
        if seat.accept_rate_7d is not None:
            if seat.accept_rate_7d < ACCEPT_RATE_CRITICAL:
                health_status = "critical"
            elif seat.accept_rate_7d < ACCEPT_RATE_WARNING:
                health_status = "warning"

        return {
            "seat_id": str(seat.id),
            "account_name": seat.account_name,
            "status": seat.status,
            "health_status": health_status,
            "metrics": {
                "accept_rate_7d": stats_7d["accept_rate"],
                "accept_rate_30d": stats_30d["accept_rate"],
                "total_requests_7d": stats_7d["total_requests"],
                "accepted_7d": stats_7d["accepted"],
                "pending_count": pending,
            },
            "thresholds": {
                "accept_rate_warning": float(ACCEPT_RATE_WARNING),
                "accept_rate_critical": float(ACCEPT_RATE_CRITICAL),
                "pending_warning": PENDING_WARNING_THRESHOLD,
                "pending_critical": PENDING_CRITICAL_THRESHOLD,
            },
            "limits": {
                "base_limit": 20,
                "current_limit": seat.daily_limit,
                "override": seat.daily_limit_override,
            },
            "restricted_at": seat.restricted_at.isoformat() if seat.restricted_at else None,
            "restricted_reason": seat.restricted_reason,
        }


# Singleton instance
linkedin_health_service = LinkedInHealthService()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Accept rate calculation (7d, 30d)
# [x] Pending count tracking
# [x] Health thresholds from spec (30%, 20%)
# [x] Automatic limit reductions (25%, 50%)
# [x] update_seat_health - single seat
# [x] update_all_seats_health - batch processing
# [x] mark_stale_connections_ignored - 14 day timeout
# [x] withdraw_stale_requests - 30 day withdrawal (calls Unipile API)
# [x] STALE_CONNECTION_DAYS constant = 30
# [x] MAX_WITHDRAWALS_PER_RUN = 10 (daily limit per seat)
# [x] Rate limiting between withdrawals (2 second delay)
# [x] detect_restrictions - safety check
# [x] get_health_summary - detailed status
# [x] Logging throughout
# [x] Type hints on all methods
# [x] Docstrings on all methods
