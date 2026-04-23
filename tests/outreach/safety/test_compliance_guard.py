"""
Tests for src/outreach/safety/compliance_guard.py

Coverage:
- Suppression blocks all 4 channels
- DNCR blocks only voice/SMS
- TCP hours: edge cases (8pm allowed, 9pm blocked, Sunday blocked)
- SPAM Act: unsubscribed email blocked, LinkedIn unaffected
- Multiple violations accumulate
- Clean prospect on email Tue 11am → allowed
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.outreach.safety.compliance_guard import ComplianceGuard
from src.outreach.safety.timing_engine import Channel

SYD = ZoneInfo("Australia/Sydney")


def syd(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=SYD)


# Helpers
def _suppressed(contact: str) -> bool:
    return contact in {"bad@example.com", "+61400000000"}


def _dncr(phone: str) -> bool:
    return phone == "+61400000000"


BASE_PROSPECT = {
    "email": "prospect@example.com",
    "phone": "+61411111111",
    "tz": "Australia/Sydney",
    "has_unsubscribed": False,
}

TUESDAY_11AM = syd(2026, 4, 21, 11, 0)   # Tue within work + optimal email
TUESDAY_8PM = syd(2026, 4, 21, 20, 0)    # Tue 8pm — boundary (TCP: hour < 20 allowed, 20 blocked)
TUESDAY_9PM = syd(2026, 4, 21, 21, 0)    # Tue 9pm — TCP blocked
SUNDAY_2PM = syd(2026, 4, 19, 14, 0)     # Sunday — TCP always blocked for voice/SMS


# ---------------------------------------------------------------------------
# Suppression — all 4 channels
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("channel", [Channel.EMAIL, Channel.LINKEDIN, Channel.VOICE, Channel.SMS])
def test_suppression_blocks_all_channels(channel: Channel):
    """Suppressed email must block every channel."""
    guard = ComplianceGuard(suppression_lookup=_suppressed)
    prospect = {**BASE_PROSPECT, "email": "bad@example.com"}
    result = guard.check(channel, prospect, TUESDAY_11AM)
    assert not result.allowed
    assert "SUPPRESSION_HIT" in result.violations


@pytest.mark.parametrize("channel", [Channel.EMAIL, Channel.LINKEDIN, Channel.VOICE, Channel.SMS])
def test_suppressed_phone_blocks_all_channels(channel: Channel):
    """Suppressed phone must block every channel."""
    guard = ComplianceGuard(suppression_lookup=_suppressed)
    prospect = {**BASE_PROSPECT, "phone": "+61400000000"}
    result = guard.check(channel, prospect, TUESDAY_11AM)
    assert not result.allowed
    assert "SUPPRESSION_HIT" in result.violations


# ---------------------------------------------------------------------------
# DNCR — voice/SMS only
# ---------------------------------------------------------------------------

def test_dncr_blocks_voice():
    guard = ComplianceGuard(dncr_lookup=_dncr)
    prospect = {**BASE_PROSPECT, "phone": "+61400000000"}
    result = guard.check(Channel.VOICE, prospect, TUESDAY_11AM)
    assert not result.allowed
    assert "DNCR_HIT" in result.violations


def test_dncr_blocks_sms():
    guard = ComplianceGuard(dncr_lookup=_dncr)
    prospect = {**BASE_PROSPECT, "phone": "+61400000000"}
    result = guard.check(Channel.SMS, prospect, TUESDAY_11AM)
    assert not result.allowed
    assert "DNCR_HIT" in result.violations


def test_dncr_does_not_block_email():
    guard = ComplianceGuard(dncr_lookup=_dncr)
    prospect = {**BASE_PROSPECT, "phone": "+61400000000"}
    result = guard.check(Channel.EMAIL, prospect, TUESDAY_11AM)
    assert "DNCR_HIT" not in result.violations


def test_dncr_does_not_block_linkedin():
    guard = ComplianceGuard(dncr_lookup=_dncr)
    prospect = {**BASE_PROSPECT, "phone": "+61400000000"}
    result = guard.check(Channel.LINKEDIN, prospect, TUESDAY_11AM)
    assert "DNCR_HIT" not in result.violations


# ---------------------------------------------------------------------------
# TCP hours
# ---------------------------------------------------------------------------

def test_tcp_8pm_boundary_blocked():
    """8pm (hour=20) is >= TCP_END (20) so must be blocked."""
    guard = ComplianceGuard()
    result = guard.check(Channel.VOICE, BASE_PROSPECT, TUESDAY_8PM)
    assert not result.allowed
    assert "TCP_HOURS_VIOLATION" in result.violations


def test_tcp_7_59pm_allowed():
    """7:59pm (hour=19) is within TCP window (< 20) — must be allowed."""
    guard = ComplianceGuard()
    now = syd(2026, 4, 21, 19, 59)
    result = guard.check(Channel.VOICE, BASE_PROSPECT, now)
    assert "TCP_HOURS_VIOLATION" not in result.violations


def test_tcp_9pm_blocked():
    """9pm (hour=21) is outside TCP window — must be blocked."""
    guard = ComplianceGuard()
    result = guard.check(Channel.VOICE, BASE_PROSPECT, TUESDAY_9PM)
    assert not result.allowed
    assert "TCP_HOURS_VIOLATION" in result.violations


def test_tcp_sunday_blocked_for_voice():
    """Sunday is always blocked for voice under TCP rules."""
    guard = ComplianceGuard()
    result = guard.check(Channel.VOICE, BASE_PROSPECT, SUNDAY_2PM)
    assert not result.allowed
    assert "TCP_HOURS_VIOLATION" in result.violations


def test_tcp_sunday_blocked_for_sms():
    """Sunday is always blocked for SMS under TCP rules."""
    guard = ComplianceGuard()
    result = guard.check(Channel.SMS, BASE_PROSPECT, SUNDAY_2PM)
    assert not result.allowed
    assert "TCP_HOURS_VIOLATION" in result.violations


def test_tcp_does_not_apply_to_email():
    """TCP hours rule must not apply to email channel."""
    guard = ComplianceGuard()
    # Send at 9pm — TCP would block voice, but email should not get TCP_HOURS_VIOLATION
    result = guard.check(Channel.EMAIL, BASE_PROSPECT, TUESDAY_9PM)
    assert "TCP_HOURS_VIOLATION" not in result.violations


# ---------------------------------------------------------------------------
# SPAM Act
# ---------------------------------------------------------------------------

def test_spam_act_unsubscribed_email_blocked():
    guard = ComplianceGuard()
    prospect = {**BASE_PROSPECT, "has_unsubscribed": True}
    result = guard.check(Channel.EMAIL, prospect, TUESDAY_11AM)
    assert not result.allowed
    assert "SPAM_ACT_UNSUBSCRIBED" in result.violations


def test_spam_act_does_not_affect_linkedin():
    guard = ComplianceGuard()
    prospect = {**BASE_PROSPECT, "has_unsubscribed": True}
    result = guard.check(Channel.LINKEDIN, prospect, TUESDAY_11AM)
    assert "SPAM_ACT_UNSUBSCRIBED" not in result.violations


# ---------------------------------------------------------------------------
# Multiple violations accumulate
# ---------------------------------------------------------------------------

def test_multiple_violations_accumulate():
    """
    Suppressed phone + DNCR-listed phone + TCP late hour = 3 violation codes.
    Use Voice channel so DNCR and TCP both apply.
    """
    def _always_suppress(contact: str) -> bool:
        return True

    def _always_dncr(phone: str) -> bool:
        return True

    guard = ComplianceGuard(suppression_lookup=_always_suppress, dncr_lookup=_always_dncr)
    result = guard.check(Channel.VOICE, BASE_PROSPECT, TUESDAY_9PM)
    assert "SUPPRESSION_HIT" in result.violations
    assert "DNCR_HIT" in result.violations
    assert "TCP_HOURS_VIOLATION" in result.violations
    assert len(result.violations) == 3
    assert not result.allowed


# ---------------------------------------------------------------------------
# Clean prospect — green path
# ---------------------------------------------------------------------------

def test_clean_prospect_email_tuesday_11am_allowed():
    """No violations: clean prospect, email, Tuesday 11am."""
    guard = ComplianceGuard()
    result = guard.check(Channel.EMAIL, BASE_PROSPECT, TUESDAY_11AM)
    assert result.allowed
    assert result.violations == []
    assert result.reason == "compliant"
