"""
Contract: src/outreach/safety/timing_engine.py
Purpose: Multi-channel timing decision engine for outreach safety
Layer: 3 - engines
Imports: stdlib only
Consumers: outreach orchestration, compliance_guard

Checks whether a given channel/time combination is within
optimal sending windows, work hours, and workday constraints
per AU public holiday schedule. Returns a TimingDecision with
allow/deny, human-readable reason, and next window start.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Australia/Sydney"

# 2026 Australian national public holidays
AU_PUBLIC_HOLIDAYS_2026: frozenset[date] = frozenset(
    {
        date(2026, 1, 1),  # New Year's Day
        date(2026, 1, 26),  # Australia Day
        date(2026, 4, 3),  # Good Friday
        date(2026, 4, 4),  # Easter Saturday
        date(2026, 4, 5),  # Easter Sunday
        date(2026, 4, 6),  # Easter Monday
        date(2026, 4, 25),  # ANZAC Day
        date(2026, 12, 25),  # Christmas Day
        date(2026, 12, 26),  # Boxing Day
    }
)

# Work-hour window (inclusive start, exclusive end) in prospect TZ
WORK_HOUR_START = 9  # 9am
WORK_HOUR_END = 17  # 5pm (excluded)

# Optimal windows: dict of channel -> list of (weekdays, hour_start, hour_end_exclusive)
# weekdays: set of 0=Mon..4=Fri
_TUE_THU = {1, 2, 3}
_MON_FRI = {0, 1, 2, 3, 4}

_OPTIMAL: dict[str, list[tuple[set[int], int, int]]] = {
    "email": [(_TUE_THU, 10, 11), (_TUE_THU, 14, 15)],
    "linkedin": [(_TUE_THU, 8, 10)],
    "voice": [(_TUE_THU, 10, 12), (_TUE_THU, 14, 16)],
    "sms": [(_MON_FRI, 12, 13)],
}


class Channel(StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    VOICE = "voice"
    SMS = "sms"


@dataclass
class TimingDecision:
    allowed: bool
    reason: str
    next_window_start: datetime | None = field(default=None)


class TimingEngine:
    """
    Contract: src/outreach/safety/timing_engine.py — TimingEngine
    Purpose:  Decides whether channel/time is within optimal send window.
    Layer:    engines
    """

    def check(
        self,
        channel: Channel,
        now: datetime,
        prospect_tz: str | None = None,
    ) -> TimingDecision:
        """
        Evaluate channel + datetime against workday, work-hour, and optimal-window rules.

        Args:
            channel:     Outreach channel to check.
            now:         Current datetime (may be tz-aware or naive UTC).
            prospect_tz: IANA timezone string for the prospect.  Defaults to Australia/Sydney.

        Returns:
            TimingDecision with allowed, reason, and next_window_start if blocked.
        """
        tz = ZoneInfo(prospect_tz or DEFAULT_TZ)
        local = (
            now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        )

        # 1. Workday check
        workday_decision = _check_workday(local, tz)
        if workday_decision is not None:
            return workday_decision

        # 2. Work-hour check
        work_hour_decision = _check_work_hour(local, tz)
        if work_hour_decision is not None:
            return work_hour_decision

        # 3. Optimal-window check
        return _check_optimal_window(channel, local, tz)


# ---------------------------------------------------------------------------
# Private helpers — each fits well under 50 lines
# ---------------------------------------------------------------------------


def _check_workday(local: datetime, tz: ZoneInfo) -> TimingDecision | None:
    """Return a blocking TimingDecision if today is not a valid workday, else None."""
    d = local.date()
    weekday = local.weekday()  # 0=Mon .. 6=Sun

    if weekday >= 5:
        next_open = _next_workday(d + timedelta(days=1), tz)
        return TimingDecision(
            allowed=False,
            reason=f"weekend — outreach blocked on {d.strftime('%A')}",
            next_window_start=next_open,
        )

    if d in AU_PUBLIC_HOLIDAYS_2026:
        next_open = _next_workday(d + timedelta(days=1), tz)
        return TimingDecision(
            allowed=False,
            reason=f"AU public holiday ({d.isoformat()})",
            next_window_start=next_open,
        )

    return None


def _check_work_hour(local: datetime, tz: ZoneInfo) -> TimingDecision | None:
    """Return a blocking TimingDecision if current time is outside 9am-5pm, else None."""
    hour = local.hour
    minute = local.minute

    if hour < WORK_HOUR_START:
        next_open = local.replace(hour=WORK_HOUR_START, minute=0, second=0, microsecond=0)
        return TimingDecision(
            allowed=False,
            reason=f"before work hours (9am–5pm) — currently {hour:02d}:{minute:02d}",
            next_window_start=next_open,
        )

    if hour >= WORK_HOUR_END:
        # Next workday 9am
        next_day = _next_workday(local.date() + timedelta(days=1), tz)
        return TimingDecision(
            allowed=False,
            reason=f"after work hours (9am–5pm) — currently {hour:02d}:{minute:02d}",
            next_window_start=next_day,
        )

    return None


def _check_optimal_window(channel: Channel, local: datetime, tz: ZoneInfo) -> TimingDecision:
    """Check optimal window for channel; return TimingDecision (always returns a value)."""
    windows = _OPTIMAL[channel.value]
    weekday = local.weekday()
    hour = local.hour

    for days_set, w_start, w_end in windows:
        if weekday in days_set and w_start <= hour < w_end:
            return TimingDecision(allowed=True, reason="within optimal window")

    next_win = _next_optimal_window(channel, local, tz)
    return TimingDecision(
        allowed=False,
        reason=f"outside optimal window for {channel.value}",
        next_window_start=next_win,
    )


def _next_optimal_window(channel: Channel, local: datetime, tz: ZoneInfo) -> datetime:
    """Find the next datetime that falls in an optimal window for this channel."""
    windows = _OPTIMAL[channel.value]
    candidate = local + timedelta(minutes=1)

    for _ in range(14 * 24 * 60):  # search up to 2 weeks minute-by-minute
        d = candidate.date()
        weekday = candidate.weekday()

        if weekday < 5 and d not in AU_PUBLIC_HOLIDAYS_2026:
            hour = candidate.hour
            for days_set, w_start, w_end in windows:
                if weekday in days_set and w_start <= hour < w_end:
                    return candidate.replace(second=0, microsecond=0)

        candidate += timedelta(hours=1)

    # Fallback: return 9am next workday (should never reach this)
    return _next_workday(local.date() + timedelta(days=1), tz)


def _next_workday(from_date: date, tz: ZoneInfo) -> datetime:
    """Return 9am on the next valid workday (skipping weekends + AU holidays)."""
    d = from_date
    for _ in range(30):
        if d.weekday() < 5 and d not in AU_PUBLIC_HOLIDAYS_2026:
            return datetime(d.year, d.month, d.day, WORK_HOUR_START, 0, 0, tzinfo=tz)
        d += timedelta(days=1)

    # Fallback — should never happen in practice
    return datetime(
        from_date.year, from_date.month, from_date.day, WORK_HOUR_START, 0, 0, tzinfo=tz
    )
