"""
Contract: src/services/linkedin_warmup_service.py
Purpose: Manage LinkedIn seat warmup status transitions
Layer: 3 - services
Imports: models, integrations
Consumers: orchestration flows, API routes
Spec: docs/architecture/distribution/LINKEDIN.md

Warmup Schedule (2-week ramp):
- Days 1-3: 5 connections/day
- Days 4-7: 10 connections/day
- Days 8-11: 15 connections/day
- Days 12+: 20 connections/day (full capacity)

After day 12, seat transitions from WARMUP to ACTIVE status.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.linkedin_seat import (
    LINKEDIN_WARMUP_SCHEDULE,
    LinkedInSeat,
    LinkedInSeatStatus,
)

logger = logging.getLogger(__name__)

# Day at which warmup completes
WARMUP_COMPLETE_DAY = 12


class LinkedInWarmupService:
    """
    Manages LinkedIn seat warmup status.

    New seats ramp up gradually over 2 weeks to avoid LinkedIn flags:
    - Days 1-3: 5/day (establishing activity pattern)
    - Days 4-7: 10/day (increasing engagement)
    - Days 8-11: 15/day (approaching full capacity)
    - Days 12+: 20/day (full capacity, mark as ACTIVE)
    """

    async def get_seats_in_warmup(
        self,
        db: AsyncSession,
        client_id: UUID | None = None,
    ) -> list[LinkedInSeat]:
        """
        Get all seats currently in warmup status.

        Args:
            db: Database session
            client_id: Optional client filter

        Returns:
            List of seats in warmup
        """
        stmt = select(LinkedInSeat).where(
            LinkedInSeat.status == LinkedInSeatStatus.WARMUP
        )

        if client_id:
            stmt = stmt.where(LinkedInSeat.client_id == client_id)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def check_warmup_completion(
        self,
        db: AsyncSession,
        seat: LinkedInSeat,
    ) -> dict[str, Any]:
        """
        Check if a seat has completed warmup and transition if ready.

        Args:
            db: Database session
            seat: LinkedIn seat to check

        Returns:
            Dict with warmup status info
        """
        if seat.status != LinkedInSeatStatus.WARMUP:
            return {
                "seat_id": str(seat.id),
                "status": seat.status,
                "action": "skip",
                "reason": "not_in_warmup",
            }

        days_active = seat.days_active
        current_limit = seat.daily_limit

        # Check if warmup complete (day 12+)
        if days_active >= WARMUP_COMPLETE_DAY:
            seat.status = LinkedInSeatStatus.ACTIVE
            seat.warmup_completed_at = datetime.utcnow()
            await db.commit()

            logger.info(
                f"Seat {seat.id} completed warmup after {days_active} days, "
                f"now ACTIVE with limit {current_limit}/day"
            )

            return {
                "seat_id": str(seat.id),
                "status": LinkedInSeatStatus.ACTIVE,
                "action": "completed",
                "days_active": days_active,
                "daily_limit": current_limit,
            }

        # Still in warmup - report progress
        return {
            "seat_id": str(seat.id),
            "status": LinkedInSeatStatus.WARMUP,
            "action": "continue",
            "days_active": days_active,
            "days_remaining": WARMUP_COMPLETE_DAY - days_active,
            "daily_limit": current_limit,
        }

    async def process_all_warmups(
        self,
        db: AsyncSession,
        client_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Process warmup status for all seats in warmup.

        Should be called daily to transition completed warmups to ACTIVE.

        Args:
            db: Database session
            client_id: Optional client filter

        Returns:
            Dict with processing summary
        """
        seats = await self.get_seats_in_warmup(db, client_id)

        if not seats:
            logger.info("No seats in warmup to process")
            return {
                "total": 0,
                "completed": 0,
                "continuing": 0,
                "seats": [],
            }

        results = []
        completed_count = 0
        continuing_count = 0

        for seat in seats:
            result = await self.check_warmup_completion(db, seat)
            results.append(result)

            if result["action"] == "completed":
                completed_count += 1
            else:
                continuing_count += 1

        logger.info(
            f"Processed {len(seats)} seats in warmup: "
            f"{completed_count} completed, {continuing_count} continuing"
        )

        return {
            "total": len(seats),
            "completed": completed_count,
            "continuing": continuing_count,
            "seats": results,
        }

    async def get_warmup_status(
        self,
        db: AsyncSession,
        seat_id: UUID,
    ) -> dict[str, Any]:
        """
        Get detailed warmup status for a specific seat.

        Args:
            db: Database session
            seat_id: Seat UUID

        Returns:
            Dict with warmup details
        """
        seat = await db.get(LinkedInSeat, seat_id)

        if not seat:
            return {"error": "seat_not_found"}

        days_active = seat.days_active
        current_limit = seat.daily_limit

        # Determine warmup phase
        phase = None
        for start, end, _limit in LINKEDIN_WARMUP_SCHEDULE:
            if start <= days_active <= end:
                phase = f"days_{start}_{end}"
                break

        return {
            "seat_id": str(seat.id),
            "status": seat.status,
            "activated_at": seat.activated_at.isoformat() if seat.activated_at else None,
            "days_active": days_active,
            "warmup_complete": seat.status == LinkedInSeatStatus.ACTIVE,
            "warmup_completed_at": (
                seat.warmup_completed_at.isoformat()
                if seat.warmup_completed_at
                else None
            ),
            "current_phase": phase,
            "daily_limit": current_limit,
            "max_limit": 20,
            "days_until_full_capacity": max(0, WARMUP_COMPLETE_DAY - days_active),
            "schedule": [
                {"days": f"{s}-{e}", "limit": l}
                for s, e, l in LINKEDIN_WARMUP_SCHEDULE
            ],
        }

    async def reset_warmup(
        self,
        db: AsyncSession,
        seat_id: UUID,
    ) -> dict[str, Any]:
        """
        Reset a seat's warmup (e.g., after restriction recovery).

        Args:
            db: Database session
            seat_id: Seat UUID

        Returns:
            Dict with reset result
        """
        seat = await db.get(LinkedInSeat, seat_id)

        if not seat:
            return {"error": "seat_not_found"}

        old_status = seat.status
        seat.status = LinkedInSeatStatus.WARMUP
        seat.activated_at = datetime.utcnow()
        seat.warmup_completed_at = None
        seat.restricted_at = None
        seat.restricted_reason = None
        seat.daily_limit_override = None

        await db.commit()

        logger.info(f"Reset warmup for seat {seat_id} (was {old_status})")

        return {
            "seat_id": str(seat.id),
            "status": LinkedInSeatStatus.WARMUP,
            "action": "reset",
            "previous_status": old_status,
            "daily_limit": seat.daily_limit,
        }


# Singleton instance
linkedin_warmup_service = LinkedInWarmupService()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Warmup schedule from spec (5→10→15→20)
# [x] WARMUP → ACTIVE transition at day 12
# [x] get_seats_in_warmup - filter by status
# [x] check_warmup_completion - single seat check
# [x] process_all_warmups - batch processing
# [x] get_warmup_status - detailed status
# [x] reset_warmup - for restriction recovery
# [x] Logging throughout
# [x] Type hints on all methods
# [x] Docstrings on all methods
