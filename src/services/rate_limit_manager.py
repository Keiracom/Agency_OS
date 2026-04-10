"""
Contract: src/services/rate_limit_manager.py
Purpose: Multi-channel rate limit enforcement with activity-aware LinkedIn budgeting
Layer: services
Imports: models, integrations
Consumers: orchestration only
"""
from datetime import datetime, timezone, timedelta
from typing import Optional


class RateLimitManager:
    """Enforces per-channel per-customer per-day rate limits."""

    # Base daily limits per channel per customer
    CHANNEL_LIMITS = {
        'email': 100,           # per burner domain, sum across all domains
        'linkedin_connect': 60, # per connected account per day
        'linkedin_message': 80, # per connected account per day
        'voice': 30,            # per customer per day
        'sms': 0,               # paused
    }

    # Weekly volume distribution (Mon=0 through Fri=4)
    WEEKLY_MULTIPLIERS = {
        0: 1.20,  # Monday
        1: 1.10,  # Tuesday
        2: 1.05,  # Wednesday
        3: 1.05,  # Thursday
        4: 0.60,  # Friday
    }

    # Warmup modifiers for LinkedIn
    WARMUP_MODIFIERS = {
        'full': {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0},
        'first_cycle_rampup': {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.0},
        'dormant_reactivation': {1: 0.3, 2: 0.3, 3: 0.3, 4: 0.3},
    }

    async def get_remaining_budget(
        self,
        client_id: str,
        channel: str,
        target_date: datetime,
        warmup_mode: str = 'full',
        cycle_week: int = 1,
        db=None,
    ) -> int:
        """Calculate remaining actions allowed for this channel today."""

        base_limit = self.CHANNEL_LIMITS.get(channel, 0)
        if base_limit == 0:
            return 0

        # Apply day-of-week multiplier
        dow = target_date.weekday()
        if dow >= 5:  # Weekend
            return 0
        day_multiplier = self.WEEKLY_MULTIPLIERS.get(dow, 1.0)

        # Apply warmup modifier for LinkedIn channels
        if 'linkedin' in channel:
            warmup_map = self.WARMUP_MODIFIERS.get(warmup_mode, {})
            warmup_mult = warmup_map.get(min(cycle_week, 4), 1.0)
            base_limit = int(base_limit * warmup_mult)

        # Apply day-of-week distribution
        adjusted_limit = int(base_limit * day_multiplier)

        # Count actions already fired/scheduled for today
        if db:
            fired_today = await self._count_actions_today(client_id, channel, target_date, db)
        else:
            fired_today = 0

        remaining = max(0, adjusted_limit - fired_today)
        return remaining

    async def get_linkedin_budget_with_manual_activity(
        self,
        client_id: str,
        channel: str,
        target_date: datetime,
        manual_actions_24h: int = 0,
        warmup_mode: str = 'full',
        cycle_week: int = 1,
        db=None,
    ) -> int:
        """Activity-aware LinkedIn budgeting."""

        base_budget = await self.get_remaining_budget(
            client_id, channel, target_date, warmup_mode, cycle_week, db
        )

        # Subtract manual activity
        adjusted = max(0, base_budget - manual_actions_24h)

        # If customer very active (40+), back off completely for 6 hours
        if manual_actions_24h >= 40:
            return 0  # Back off entirely

        return adjusted

    async def can_fire(
        self,
        client_id: str,
        channel: str,
        target_date: datetime,
        warmup_mode: str = 'full',
        cycle_week: int = 1,
        db=None,
    ) -> tuple[bool, str]:
        """Check if an action can fire right now. Returns (allowed, reason)."""

        remaining = await self.get_remaining_budget(
            client_id, channel, target_date, warmup_mode, cycle_week, db
        )

        if remaining <= 0:
            return False, f"Daily {channel} limit reached"

        # Additional LinkedIn spacing check
        if 'linkedin' in channel:
            last_action = await self._get_last_linkedin_action(client_id, db) if db else None
            if last_action:
                seconds_since = (datetime.now(timezone.utc) - last_action).total_seconds()
                if seconds_since < 90:
                    return False, f"LinkedIn minimum spacing (90s), last was {int(seconds_since)}s ago"

        # Voice spacing check
        if channel == 'voice':
            last_call = await self._get_last_voice_action(client_id, db) if db else None
            if last_call:
                minutes_since = (datetime.now(timezone.utc) - last_call).total_seconds() / 60
                if minutes_since < 10:
                    return False, f"Voice minimum spacing (10min), last was {int(minutes_since)}min ago"

        return True, "OK"

    async def _count_actions_today(self, client_id, channel, target_date, db):
        """Count actions already fired today for this client+channel."""
        # Query outreach_actions table
        start_of_day = target_date.replace(hour=0, minute=0, second=0)
        end_of_day = start_of_day + timedelta(days=1)
        # Stubbed — production query:
        # SELECT count(*) FROM outreach_actions
        # WHERE client_id = client_id AND channel = channel
        # AND fired_at >= start_of_day AND fired_at < end_of_day
        # AND status IN ('fired', 'scheduled')
        return 0

    async def _get_last_linkedin_action(self, client_id, db):
        """Get timestamp of last LinkedIn action for this client."""
        return None

    async def _get_last_voice_action(self, client_id, db):
        """Get timestamp of last voice action for this client."""
        return None
