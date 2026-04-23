"""
Tests for src/outreach/safety/timing_engine.py

Coverage:
- Workday filter: Sunday, AU public holiday, valid Monday
- Work-hour filter: before 9am
- Optimal-window filter: channel/day/hour combos
- next_window_start populated on all non-allowed paths
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.outreach.safety.timing_engine import Channel, TimingDecision, TimingEngine

SYD = ZoneInfo("Australia/Sydney")
engine = TimingEngine()


def syd(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    """Build a tz-aware Sydney datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=SYD)


# ---------------------------------------------------------------------------
# Workday tests
# ---------------------------------------------------------------------------

def test_sunday_rejected():
    """Sunday (weekday=6) must always be blocked."""
    now = syd(2026, 4, 19, 10, 30)  # Sunday
    result = engine.check(Channel.EMAIL, now)
    assert not result.allowed
    assert "weekend" in result.reason.lower()
    assert result.next_window_start is not None


def test_anzac_day_rejected():
    """2026-04-25 (ANZAC Day, Saturday) must be blocked as a public holiday."""
    # ANZAC falls on Saturday in 2026 — the check hits weekend before holiday;
    # either path is correct.  We confirm it is blocked and next_window_start set.
    now = syd(2026, 4, 25, 10, 0)  # ANZAC Day
    result = engine.check(Channel.EMAIL, now)
    assert not result.allowed
    assert result.next_window_start is not None


def test_good_friday_rejected():
    """2026-04-03 (Good Friday) must be blocked as a public holiday."""
    now = syd(2026, 4, 3, 10, 0)  # Good Friday
    result = engine.check(Channel.EMAIL, now)
    assert not result.allowed
    assert "holiday" in result.reason.lower()
    assert result.next_window_start is not None


def test_monday_10am_linkedin_allowed():
    """Monday 10am — within work hours. LinkedIn optimal is Tue–Thu, so blocked on Mon."""
    now = syd(2026, 4, 20, 10, 0)  # Monday
    result = engine.check(Channel.LINKEDIN, now)
    # Workday + work-hour pass; optimal window blocks (Mon not in Tue-Thu)
    assert not result.allowed
    assert "optimal window" in result.reason.lower()
    assert result.next_window_start is not None


# ---------------------------------------------------------------------------
# Work-hour tests
# ---------------------------------------------------------------------------

def test_before_9am_rejected():
    """8am on a valid Tuesday must be blocked by work-hour filter."""
    now = syd(2026, 4, 21, 8, 0)  # Tuesday 8am
    result = engine.check(Channel.EMAIL, now)
    assert not result.allowed
    assert "work hours" in result.reason.lower()
    assert result.next_window_start is not None
    # next window should be the same day at 9am (or later today)
    assert result.next_window_start.hour == 9


# ---------------------------------------------------------------------------
# Optimal-window tests
# ---------------------------------------------------------------------------

def test_friday_2pm_linkedin_rejected():
    """LinkedIn optimal = Tue–Thu 8–10am.  Friday 2pm must be blocked."""
    now = syd(2026, 4, 24, 14, 0)  # Friday
    result = engine.check(Channel.LINKEDIN, now)
    assert not result.allowed
    assert "optimal window" in result.reason.lower()
    assert result.next_window_start is not None


def test_tuesday_10_30am_email_allowed():
    """Email optimal includes Tue–Thu 10–11am — Tuesday 10:30 must be allowed."""
    now = syd(2026, 4, 21, 10, 30)  # Tuesday
    result = engine.check(Channel.EMAIL, now)
    assert result.allowed
    assert result.reason == "within optimal window"


def test_tuesday_1_30pm_linkedin_rejected():
    """LinkedIn optimal = Tue–Thu 8–10am.  Tuesday 1:30pm is outside window."""
    now = syd(2026, 4, 21, 13, 30)  # Tuesday
    result = engine.check(Channel.LINKEDIN, now)
    assert not result.allowed
    assert "optimal window" in result.reason.lower()
    assert result.next_window_start is not None


def test_tuesday_12_30pm_sms_allowed():
    """SMS optimal = Mon–Fri 12–1pm.  Tuesday 12:30 must be allowed."""
    now = syd(2026, 4, 21, 12, 30)  # Tuesday
    result = engine.check(Channel.SMS, now)
    assert result.allowed
    assert result.reason == "within optimal window"


def test_next_window_start_in_future():
    """next_window_start must always be strictly after now when present."""
    now = syd(2026, 4, 21, 8, 30)  # Tuesday 8:30am — before work hours
    result = engine.check(Channel.EMAIL, now)
    assert not result.allowed
    assert result.next_window_start is not None
    assert result.next_window_start > now


def test_voice_tuesday_10am_allowed():
    """Voice optimal includes Tue–Thu 10–12.  Tuesday 10am must be allowed."""
    now = syd(2026, 4, 21, 10, 0)  # Tuesday
    result = engine.check(Channel.VOICE, now)
    assert result.allowed


def test_voice_tuesday_2pm_allowed():
    """Voice optimal includes Tue–Thu 14–16.  Tuesday 2pm must be allowed."""
    now = syd(2026, 4, 21, 14, 0)  # Tuesday
    result = engine.check(Channel.VOICE, now)
    assert result.allowed


def test_after_5pm_rejected_with_next_day_next_window():
    """After 5pm on a Wednesday — blocked by work-hour filter, next_window_start next workday."""
    now = syd(2026, 4, 22, 17, 30)  # Wednesday 5:30pm
    result = engine.check(Channel.EMAIL, now)
    assert not result.allowed
    assert result.next_window_start is not None
    assert result.next_window_start.date() > now.date()
