"""
Contract: src/services/voice_retry_service.py
Purpose: Schedule voice call retries based on call outcome
Layer: 2 - services
Imports: models only
Consumers: voice engine, orchestration

Blueprint requirement:
- Busy: Retry in 2 hours
- No Answer: Retry next business day (Mon-Fri)
- Maximum 3 retries per lead/campaign combination
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.activity import Activity
from src.models.base import ChannelType

logger = logging.getLogger(__name__)


# Retry configuration constants
RETRY_DELAYS = {
    "busy": timedelta(hours=2),
    "no-answer": timedelta(days=1),  # Will be adjusted to next business day
    "no_answer": timedelta(days=1),  # Alternative format
}

MAX_RETRIES = 3

# Outcomes that trigger retry scheduling
RETRYABLE_OUTCOMES = {"busy", "no-answer", "no_answer", "machine_end_beep", "voicemail"}


class VoiceRetryService:
    """
    Service for scheduling voice call retries based on call outcomes.

    Implements blueprint requirements:
    - Busy: Retry in 2 hours
    - No Answer: Retry next business day (9 AM)
    - Max 3 retries per lead/campaign

    Usage:
        service = VoiceRetryService(db)
        result = await service.schedule_retry(activity_id, "busy")
        if result["scheduled"]:
            # retry_at datetime is in result["retry_at"]
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize voice retry service.

        Args:
            db: Database session
        """
        self.db = db

    async def schedule_retry(
        self,
        activity_id: UUID,
        outcome: str,
    ) -> dict:
        """
        Schedule a voice call retry based on outcome.

        Args:
            activity_id: Activity UUID of the completed call
            outcome: Call outcome (busy, no-answer, etc.)

        Returns:
            dict with:
                - scheduled: bool - Whether retry was scheduled
                - retry_at: datetime or None - When to retry
                - reason: str - Outcome or why not scheduled
                - attempt_number: int - Current attempt count
        """
        # Normalize outcome
        outcome_lower = outcome.lower().replace("_", "-")

        # Fetch the activity
        stmt = select(Activity).where(
            and_(
                Activity.id == activity_id,
                Activity.channel == ChannelType.VOICE,
            )
        )
        result = await self.db.execute(stmt)
        activity = result.scalar_one_or_none()

        if not activity:
            logger.warning(f"Activity {activity_id} not found for retry scheduling")
            return {
                "scheduled": False,
                "retry_at": None,
                "reason": "activity_not_found",
                "attempt_number": 0,
            }

        # Check if outcome is retryable
        if outcome_lower not in RETRYABLE_OUTCOMES and outcome not in RETRYABLE_OUTCOMES:
            logger.debug(f"Outcome '{outcome}' is not retryable")
            return {
                "scheduled": False,
                "retry_at": None,
                "reason": "not_retryable",
                "attempt_number": 0,
            }

        # Count existing retry attempts for this lead/campaign
        attempt_count = await self._count_voice_attempts(
            lead_id=activity.lead_id,
            campaign_id=activity.campaign_id,
        )

        if attempt_count >= MAX_RETRIES:
            logger.info(
                f"Max retries ({MAX_RETRIES}) reached for lead {activity.lead_id} "
                f"in campaign {activity.campaign_id}"
            )
            return {
                "scheduled": False,
                "retry_at": None,
                "reason": "max_retries_reached",
                "attempt_number": attempt_count,
            }

        # Calculate retry time based on outcome
        retry_at = self._calculate_retry_time(outcome_lower)

        # Store retry information in activity metadata
        existing_metadata = activity.metadata if isinstance(activity.metadata, dict) else {}
        current_metadata: dict[str, Any] = dict(existing_metadata)
        current_metadata["voice_retry"] = {
            "scheduled": True,
            "retry_at": retry_at.isoformat(),
            "outcome": outcome,
            "attempt_number": attempt_count + 1,
        }

        # Update the activity with retry metadata
        existing_extra = activity.extra_data if isinstance(activity.extra_data, dict) else {}
        update_stmt = (
            update(Activity)
            .where(Activity.id == activity_id)
            .values(
                metadata=current_metadata,
                extra_data={
                    **existing_extra,
                    "voice_retry_at": retry_at.isoformat(),
                    "voice_retry_outcome": outcome,
                },
            )
        )
        await self.db.execute(update_stmt)
        await self.db.commit()

        logger.info(
            f"Scheduled voice retry for lead {activity.lead_id}: "
            f"outcome={outcome}, retry_at={retry_at}, attempt={attempt_count + 1}/{MAX_RETRIES}"
        )

        return {
            "scheduled": True,
            "retry_at": retry_at,
            "reason": outcome,
            "attempt_number": attempt_count + 1,
            "lead_id": str(activity.lead_id),
            "campaign_id": str(activity.campaign_id),
        }

    async def get_pending_retries(
        self,
        client_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get voice calls that are due for retry.

        Args:
            client_id: Optional filter by client
            limit: Maximum number of results

        Returns:
            List of activities due for retry
        """
        now = datetime.utcnow()

        # Query for activities with pending voice retries
        conditions = [
            Activity.channel == ChannelType.VOICE,
            Activity.extra_data["voice_retry_at"].is_not(None),
        ]

        if client_id:
            conditions.append(Activity.client_id == client_id)

        stmt = (
            select(Activity)
            .where(and_(*conditions))
            .order_by(Activity.created_at.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        activities = result.scalars().all()

        # Filter to only those due for retry
        pending = []
        for activity in activities:
            retry_at_str = activity.extra_data.get("voice_retry_at")
            if retry_at_str:
                retry_at = datetime.fromisoformat(retry_at_str)
                if retry_at <= now:
                    # Check if retry already processed
                    if not activity.extra_data.get("voice_retry_processed"):
                        pending.append(
                            {
                                "activity_id": str(activity.id),
                                "lead_id": str(activity.lead_id),
                                "campaign_id": str(activity.campaign_id),
                                "client_id": str(activity.client_id),
                                "retry_at": retry_at,
                                "outcome": activity.extra_data.get("voice_retry_outcome"),
                            }
                        )

        return pending

    async def mark_retry_processed(
        self,
        activity_id: UUID,
    ) -> None:
        """
        Mark a retry as processed (called after re-initiating the call).

        Args:
            activity_id: Activity UUID
        """
        stmt = select(Activity).where(Activity.id == activity_id)
        result = await self.db.execute(stmt)
        activity = result.scalar_one_or_none()

        if activity:
            existing_extra = activity.extra_data if isinstance(activity.extra_data, dict) else {}
            extra_data: dict[str, Any] = dict(existing_extra)
            extra_data["voice_retry_processed"] = True
            extra_data["voice_retry_processed_at"] = datetime.utcnow().isoformat()

            update_stmt = (
                update(Activity).where(Activity.id == activity_id).values(extra_data=extra_data)
            )
            await self.db.execute(update_stmt)
            await self.db.commit()

            logger.info(f"Marked voice retry as processed for activity {activity_id}")

    async def _count_voice_attempts(
        self,
        lead_id: UUID,
        campaign_id: UUID,
    ) -> int:
        """
        Count voice call attempts for a lead in a campaign.

        Args:
            lead_id: Lead UUID
            campaign_id: Campaign UUID

        Returns:
            Number of voice call attempts
        """
        stmt = select(func.count()).where(
            and_(
                Activity.lead_id == lead_id,
                Activity.campaign_id == campaign_id,
                Activity.channel == ChannelType.VOICE,
                Activity.action == "sent",  # Count initiated calls
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    def _calculate_retry_time(self, outcome: str) -> datetime:
        """
        Calculate the retry time based on outcome.

        Args:
            outcome: Normalized call outcome

        Returns:
            datetime for when to retry
        """
        now = datetime.utcnow()

        if outcome == "busy":
            # Busy: Retry in 2 hours
            return now + RETRY_DELAYS["busy"]
        else:
            # No answer / voicemail: Retry next business day at 9 AM
            return self._next_business_day(now)

    def _next_business_day(self, from_time: datetime) -> datetime:
        """
        Get the next business day at 9 AM.

        Business days are Monday (0) through Friday (4).

        Args:
            from_time: Starting datetime

        Returns:
            Next business day at 9 AM
        """
        next_day = from_time + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
            next_day += timedelta(days=1)

        # Set to 9 AM
        return next_day.replace(hour=9, minute=0, second=0, microsecond=0)


# Singleton instance holder
_voice_retry_service: VoiceRetryService | None = None


def get_voice_retry_service(db: AsyncSession) -> VoiceRetryService:
    """
    Get or create VoiceRetryService instance.

    Note: Unlike other services, this requires a db session per call
    since it's used within webhook handlers.

    Args:
        db: Database session

    Returns:
        VoiceRetryService instance
    """
    return VoiceRetryService(db)


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Layer 2 - services (imports models only)
# [x] RETRY_DELAYS constant: busy=2hr, no_answer=1day
# [x] MAX_RETRIES constant = 3
# [x] schedule_retry() function implemented
# [x] _next_business_day() for Mon-Fri calculation
# [x] get_pending_retries() for outreach flow pickup
# [x] mark_retry_processed() to prevent duplicate retries
# [x] Stores retry info in activity metadata and extra_data
# [x] All functions have type hints
# [x] All functions have docstrings
