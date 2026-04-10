"""
Contract: src/services/time_window_engine.py
Purpose: Per-channel time window randomisation with LinkedIn anti-detection gaps.
         Converts prospect-local window into UTC datetime for storage.
Layer: services
Imports: stdlib, pytz
Consumers: sequence_engine
"""
import random
from datetime import date, datetime, time, timedelta, timezone

import pytz


WINDOWS: dict[str, tuple[time, time]] = {
    "morning_email": (time(8, 0), time(10, 0)),
    "morning_linkedin": (time(10, 0), time(12, 0)),
    "afternoon_linkedin": (time(13, 0), time(15, 0)),
    "afternoon_voice": (time(13, 0), time(15, 0)),
    "afternoon_voice_peak": (time(15, 0), time(17, 0)),
    "late_morning_linkedin": (time(10, 30), time(11, 30)),
}

LINKEDIN_CHANNELS = {"linkedin_connect", "linkedin_message"}


class TimeWindowEngine:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def get_time(
        self,
        window: str,
        target_date: date,
        prospect_timezone: str,
        channel: str,
    ) -> datetime:
        """Return a randomised UTC timestamp within the window for the prospect's timezone."""
        start_t, end_t = WINDOWS[window]
        tz = pytz.timezone(prospect_timezone or "Australia/Sydney")

        if channel in LINKEDIN_CHANNELS:
            # Fuzz window edges ±15 min for LinkedIn anti-detection
            start_offset = self._rng.randint(-15, 15)
            end_offset = self._rng.randint(-15, 15)
            start_dt = datetime.combine(target_date, start_t) + timedelta(minutes=start_offset)
            end_dt = datetime.combine(target_date, end_t) + timedelta(minutes=end_offset)
        else:
            start_dt = datetime.combine(target_date, start_t)
            end_dt = datetime.combine(target_date, end_t)

        total_seconds = int((end_dt - start_dt).total_seconds())
        random_offset = self._rng.randint(0, max(0, total_seconds))
        result = start_dt + timedelta(seconds=random_offset)

        local_dt = tz.localize(result)
        utc_dt = local_dt.astimezone(timezone.utc)
        return utc_dt

    def add_linkedin_gap(self, base_time: datetime) -> datetime:
        """Add humanised gap for LinkedIn actions.

        Distribution:
          75% — 90–180 s (normal browsing pace)
          20% — 3–8 min  (distracted user)
           5% — 10–20 min (longer break)
        """
        roll = self._rng.random()
        if roll < 0.75:
            gap = self._rng.randint(90, 180)
        elif roll < 0.95:
            gap = self._rng.randint(180, 480)
        else:
            gap = self._rng.randint(600, 1200)
        return base_time + timedelta(seconds=gap)
