"""
Contract: src/engines/timing.py
Purpose: Humanized timing for LinkedIn outreach
Layer: 3 - engines
Imports: models, integrations ONLY
Consumers: orchestration

Phase: Unipile Migration - Timing Randomization

This engine generates human-like delays between LinkedIn actions to:
- Prevent account flagging by LinkedIn
- Mimic natural human behavior patterns
- Respect business hours and weekends
- Prevent burst activity detection
"""

import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.config.settings import settings


class TimingEngine:
    """
    Generates human-like delays between LinkedIn actions.

    Features:
    - Beta distribution for natural delay clustering
    - Randomized daily limits (not always the same number)
    - Business hours awareness (8am-6pm local time)
    - Weekend volume reduction (50% default)
    - Per-hour burst prevention (max 8 actions/hour)
    - Start time jitter (randomized first action)
    """

    def __init__(self):
        # Load from settings (with defaults)
        self.min_delay_minutes = settings.linkedin_min_delay_minutes
        self.max_delay_minutes = settings.linkedin_max_delay_minutes
        self.min_daily = settings.linkedin_min_daily
        self.max_daily = settings.linkedin_max_daily
        self.max_per_hour = settings.linkedin_max_per_hour
        self.business_hours_start = time(settings.linkedin_business_hours_start, 0)
        self.business_hours_end = time(settings.linkedin_business_hours_end, 0)
        self.weekend_reduction = settings.linkedin_weekend_reduction

    def get_daily_limit(self) -> int:
        """
        Get randomized daily limit.

        Returns a different number each day to avoid patterns.
        Default range: 15-20 (can be increased to 80-100 with Unipile).
        """
        return random.randint(self.min_daily, self.max_daily)

    def get_delay_seconds(self) -> float:
        """
        Get humanized delay using beta distribution.

        Beta(2,5) creates a right-skewed distribution where:
        - Most delays are in the lower-middle range
        - Occasional longer delays for natural variation
        - No two delays are exactly the same

        Returns:
            Delay in seconds (default: 8-45 minutes)
        """
        # Beta distribution for natural clustering
        # Beta(2,5) is right-skewed: most values in lower-middle range
        beta_value = random.betavariate(2, 5)

        # Scale to our configured range
        range_minutes = self.max_delay_minutes - self.min_delay_minutes
        delay_minutes = self.min_delay_minutes + (beta_value * range_minutes)

        # Add small jitter (±2 minutes) for extra randomness
        jitter = random.uniform(-2, 2)
        delay_minutes = max(self.min_delay_minutes, delay_minutes + jitter)

        return delay_minutes * 60  # Return seconds

    def get_start_jitter_seconds(self) -> int:
        """
        Get randomized start time offset.

        Adds 0-120 minutes to the business hours start time
        so actions don't always begin at exactly 8am.

        Returns:
            Jitter in seconds (0 to 7200)
        """
        return random.randint(0, 120) * 60

    def get_first_action_time(self, timezone: str = "Australia/Sydney") -> datetime:
        """
        Calculate when the first action should occur today.

        Combines business hours start with random jitter.

        Args:
            timezone: User's timezone

        Returns:
            Datetime for first action
        """
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)

        # Start at business hours + jitter
        start_time = datetime.combine(
            now.date(),
            self.business_hours_start,
            tzinfo=tz,
        )

        # Add jitter
        jitter_seconds = self.get_start_jitter_seconds()
        start_time += timedelta(seconds=jitter_seconds)

        # If we're past today's start time, schedule for tomorrow
        if now > start_time:
            start_time += timedelta(days=1)

        return start_time

    def is_business_hours(self, timezone: str = "Australia/Sydney") -> bool:
        """
        Check if current time is within business hours.

        Args:
            timezone: User's timezone

        Returns:
            True if within business hours (8am-6pm by default)
        """
        tz = ZoneInfo(timezone)
        now = datetime.now(tz).time()
        return self.business_hours_start <= now <= self.business_hours_end

    def is_weekend(self, timezone: str = "Australia/Sydney") -> bool:
        """
        Check if today is a weekend.

        Args:
            timezone: User's timezone

        Returns:
            True if Saturday (5) or Sunday (6)
        """
        tz = ZoneInfo(timezone)
        return datetime.now(tz).weekday() >= 5

    def get_weekend_limit(self, base_limit: int) -> int:
        """
        Apply weekend reduction to daily limit.

        Args:
            base_limit: Normal daily limit

        Returns:
            Reduced limit for weekends (50% by default)
        """
        return int(base_limit * self.weekend_reduction)

    def get_adjusted_daily_limit(self, timezone: str = "Australia/Sydney") -> int:
        """
        Get daily limit adjusted for weekends.

        Args:
            timezone: User's timezone

        Returns:
            Daily limit (reduced on weekends)
        """
        base_limit = self.get_daily_limit()

        if self.is_weekend(timezone):
            return self.get_weekend_limit(base_limit)

        return base_limit

    def should_send_now(
        self,
        hour_count: int,
        timezone: str = "Australia/Sydney",
    ) -> tuple[bool, str | None]:
        """
        Check if we should send an action right now.

        Args:
            hour_count: Actions sent this hour
            timezone: User's timezone

        Returns:
            Tuple of (can_send, reason_if_not)
        """
        # Check business hours
        if not self.is_business_hours(timezone):
            return False, "Outside business hours"

        # Check hourly burst limit
        if hour_count >= self.max_per_hour:
            return False, f"Hourly limit reached ({self.max_per_hour})"

        return True, None

    def calculate_schedule(
        self,
        count: int,
        start_time: datetime | None = None,
        timezone: str = "Australia/Sydney",
    ) -> list[datetime]:
        """
        Pre-calculate scheduled times for multiple actions.

        This is useful for queue-based sending where we want
        to schedule all actions upfront.

        Args:
            count: Number of actions to schedule
            start_time: When to start (default: now or next business hours)
            timezone: User's timezone

        Returns:
            List of scheduled datetimes
        """
        tz = ZoneInfo(timezone)

        if start_time is None:
            if self.is_business_hours(timezone):
                start_time = datetime.now(tz)
            else:
                start_time = self.get_first_action_time(timezone)

        schedule = [start_time]

        for i in range(1, count):
            delay = self.get_delay_seconds()
            next_time = schedule[-1] + timedelta(seconds=delay)

            # Skip to next business day if outside hours
            while not self._is_during_business_hours(next_time, tz):
                next_time = self._next_business_day_start(next_time, tz)

            schedule.append(next_time)

        return schedule

    def _is_during_business_hours(self, dt: datetime, tz: ZoneInfo) -> bool:
        """Check if a specific datetime is during business hours."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)

        t = dt.time()
        weekday = dt.weekday()

        # Skip weekends entirely or apply reduction
        if weekday >= 5:  # Weekend
            # Could allow some weekend activity with reduction
            # For now, skip weekends entirely
            return False

        return self.business_hours_start <= t <= self.business_hours_end

    def _next_business_day_start(self, dt: datetime, tz: ZoneInfo) -> datetime:
        """Get the start of the next business day."""
        next_day = dt.date() + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)

        # Combine with business hours start + jitter
        start = datetime.combine(
            next_day,
            self.business_hours_start,
            tzinfo=tz,
        )

        # Add jitter
        jitter = self.get_start_jitter_seconds()
        return start + timedelta(seconds=jitter)


# Singleton instance
timing_engine = TimingEngine()


def get_timing_engine() -> TimingEngine:
    """Get the timing engine instance."""
    return timing_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] Settings-based configuration
# [x] Beta distribution for delays
# [x] Daily limit randomization
# [x] Business hours check
# [x] Weekend detection
# [x] Weekend reduction
# [x] Hourly burst prevention
# [x] Start time jitter
# [x] Schedule pre-calculation
# [x] Timezone awareness
# [x] All functions have type hints
# [x] All functions have docstrings
