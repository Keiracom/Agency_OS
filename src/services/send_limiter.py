"""
Contract: src/services/send_limiter.py
Purpose: Protect mailbox warmup with daily send limits during TEST_MODE
Layer: 3 - services
Imports: config, models
Consumers: channel engines

FILE: src/services/send_limiter.py
PURPOSE: Protect mailbox warmup with daily send limits during TEST_MODE
PHASE: 21 (E2E Testing)
TASK: TEST-006
DEPENDENCIES:
  - src/config/settings.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.activity import Activity


class SendLimiter:
    """
    Enforces daily send limits during TEST_MODE.

    This protects mailbox warmup by limiting sends per day during testing.
    When TEST_MODE is False, no limits are enforced.
    """

    async def check_email_limit(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> tuple[bool, int]:
        """
        Check if client is under daily email limit.

        Args:
            db: Database session (passed by caller)
            client_id: Client UUID to check

        Returns:
            tuple: (is_allowed, current_count)
                - is_allowed: True if under limit or TEST_MODE is off
                - current_count: Number of emails sent today
        """
        if not settings.TEST_MODE:
            return True, 0  # No limit in production

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        stmt = (
            select(func.count(Activity.id))
            .where(Activity.client_id == client_id)
            .where(Activity.channel == "email")
            .where(Activity.action == "sent")
            .where(Activity.created_at >= today_start)
        )

        result = await db.execute(stmt)
        count = result.scalar() or 0

        is_allowed = count < settings.TEST_DAILY_EMAIL_LIMIT

        return is_allowed, count

    async def get_remaining_quota(
        self,
        db: AsyncSession,
        client_id: UUID,
    ) -> int:
        """
        Get remaining email quota for the day.

        Args:
            db: Database session (passed by caller)
            client_id: Client UUID to check

        Returns:
            Number of emails remaining (0 if at limit, -1 if no limit)
        """
        if not settings.TEST_MODE:
            return -1  # No limit in production

        _, current_count = await self.check_email_limit(db, client_id)
        return max(0, settings.TEST_DAILY_EMAIL_LIMIT - current_count)


# Singleton instance
send_limiter = SendLimiter()


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] Respects TEST_MODE setting
# [x] Daily limit from settings (15 default)
# [x] Returns tuple for consistency with rate_limiter
# [x] Singleton instance for easy import
