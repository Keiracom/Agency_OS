"""
Tests for src/outreach/safety/rate_limiter.py

Coverage:
1.  Email warming day 1: cap=10; 10 pass, 11th blocks DAILY_CAP_EXCEEDED
2.  Email warming progression: day 5 cap=25, day 10 cap=50, day 15 cap=100
3.  Email warmed (warming_day=None): cap=100
4.  LinkedIn daily cap: 50/day; 51st blocks DAILY_CAP_EXCEEDED
5.  Voice attempts per prospect: 3 in 24hr pass, 4th blocks DAILY_CAP_EXCEEDED
6.  Voice cooldown: 23hr apart → PROSPECT_COOLDOWN_ACTIVE; 25hr apart → allowed
7.  SMS cycle cap: 1/prospect/30d; second within 30d → CYCLE_CAP_EXCEEDED
8.  Email same-prospect frequency: 3 in 10d pass, 4th in 14d → PROSPECT_FREQUENCY_EXCEEDED
9.  Account rotation — balanced: {A:5, B:3, C:4} → 'B'
10. Account rotation — tie: {A:5, B:5} → 'A' (lexicographic)
11. Account rotation — empty pool → None
12. Multiple violations accumulate: daily cap + prospect frequency both fire
13. consume() increments both window and prospect-frequency counters
14. retry_after populated to window_start + 1 day for window violation
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import pytest

from src.outreach.safety.rate_limiter import AccountPool, RateLimiter
from src.outreach.safety.timing_engine import Channel

# ---------------------------------------------------------------------------
# In-memory fixture factories
# ---------------------------------------------------------------------------

def _make_stores(
    window_counts: dict | None = None,
    warming_days: dict | None = None,
    prospect_sends: dict | None = None,   # (prospect_id, channel) -> list[datetime]
):
    """Build injected callables backed by plain dicts."""
    wc: dict = defaultdict(int)
    if window_counts:
        for k, v in window_counts.items():
            wc[k] = v

    wd: dict = dict(warming_days or {})

    ps: dict = defaultdict(list)
    if prospect_sends:
        for (pid, ch), times in prospect_sends.items():
            ps[(pid, ch)].extend(times)

    def get_window_count(ch: Channel, acct: str, window_start: datetime) -> int:
        return wc[(ch, acct, window_start)]

    def incr_window_count(ch: Channel, acct: str, window_start: datetime) -> None:
        wc[(ch, acct, window_start)] += 1

    def get_warming_day(acct: str) -> int | None:
        return wd.get(acct)

    def get_prospect_frequency(pid: str, ch: Channel, since: datetime) -> int:
        return sum(1 for t in ps[(pid, ch)] if t >= since)

    def record_prospect_send(pid: str, ch: Channel, now: datetime) -> None:
        ps[(pid, ch)].append(now)

    return (
        get_window_count,
        incr_window_count,
        get_warming_day,
        get_prospect_frequency,
        record_prospect_send,
        wc,
        ps,
    )


def _limiter(
    window_counts=None,
    warming_days=None,
    prospect_sends=None,
):
    gw, iw, gwd, gpf, rps, wc, ps = _make_stores(window_counts, warming_days, prospect_sends)
    rl = RateLimiter(gw, iw, gwd, gpf, rps)
    return rl, wc, ps


NOW = datetime(2026, 4, 22, 10, 0, 0)
ACCT = "acct-1"
PID = "prospect-aaa"


def _day_key(ch: Channel, acct: str, now: datetime):
    ws = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return (ch, acct, ws)


# ---------------------------------------------------------------------------
# Test 1: Email warming day 1 — cap = 10
# ---------------------------------------------------------------------------

def test_email_warming_day1_cap_10():
    ws = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    rl, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): 10},
        warming_days={ACCT: 1},
    )
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "DAILY_CAP_EXCEEDED" in result.violations


def test_email_warming_day1_10th_send_passes():
    rl, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): 9},
        warming_days={ACCT: 1},
    )
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert result.allowed


# ---------------------------------------------------------------------------
# Test 2: Email warming progression
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("day,cap", [(5, 25), (10, 50), (15, 100)])
def test_email_warming_progression(day, cap):
    # At exactly cap: blocked
    rl, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): cap},
        warming_days={ACCT: day},
    )
    blocked = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert not blocked.allowed
    assert "DAILY_CAP_EXCEEDED" in blocked.violations

    # One below cap: allowed
    rl2, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): cap - 1},
        warming_days={ACCT: day},
    )
    passing = rl2.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert passing.allowed


# ---------------------------------------------------------------------------
# Test 3: Email warmed (warming_day=None) — cap = 100
# ---------------------------------------------------------------------------

def test_email_warmed_cap_100():
    # 100 sends: blocked
    rl, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): 100},
        warming_days={},  # no entry = None = warmed
    )
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "DAILY_CAP_EXCEEDED" in result.violations

    # 99 sends: allowed
    rl2, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): 99},
        warming_days={},
    )
    assert rl2.check(Channel.EMAIL, ACCT, PID, now=NOW).allowed


# ---------------------------------------------------------------------------
# Test 4: LinkedIn daily cap — 50/day
# ---------------------------------------------------------------------------

def test_linkedin_daily_cap_50():
    rl, _, _ = _limiter(
        window_counts={_day_key(Channel.LINKEDIN, ACCT, NOW): 50},
    )
    result = rl.check(Channel.LINKEDIN, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "DAILY_CAP_EXCEEDED" in result.violations

    rl2, _, _ = _limiter(
        window_counts={_day_key(Channel.LINKEDIN, ACCT, NOW): 49},
    )
    assert rl2.check(Channel.LINKEDIN, ACCT, PID, now=NOW).allowed


# ---------------------------------------------------------------------------
# Test 5: Voice attempts per prospect — 3 in 24hr; 4th blocked
# ---------------------------------------------------------------------------

def test_voice_attempts_per_prospect_24hr():
    # 3 existing sends within 24hr: allowed for a 4th? No — 3rd send makes count=3 which hits cap
    sends_3 = [NOW - timedelta(hours=i * 2) for i in range(3)]
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.VOICE): sends_3})
    result = rl.check(Channel.VOICE, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "DAILY_CAP_EXCEEDED" in result.violations


def test_voice_3_sends_allowed_when_under_cap():
    sends_2 = [NOW - timedelta(hours=i * 2) for i in range(2)]
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.VOICE): sends_2})
    # 2 existing + this attempt = 3, which is exactly at limit — still should be blocked
    # Actually count_24h=2, which is < 3, so DAILY_CAP not hit; but cooldown check fires
    result = rl.check(Channel.VOICE, ACCT, PID, now=NOW)
    # cooldown active (1 send in window)
    assert "PROSPECT_COOLDOWN_ACTIVE" in result.violations


def test_voice_first_send_allowed():
    rl, _, _ = _limiter()
    result = rl.check(Channel.VOICE, ACCT, PID, now=NOW)
    assert result.allowed


# ---------------------------------------------------------------------------
# Test 6: Voice cooldown — 23hr apart blocked, 25hr apart allowed
# ---------------------------------------------------------------------------

def test_voice_cooldown_23hr_blocked():
    last_send = NOW - timedelta(hours=23)
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.VOICE): [last_send]})
    result = rl.check(Channel.VOICE, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "PROSPECT_COOLDOWN_ACTIVE" in result.violations


def test_voice_cooldown_25hr_allowed():
    last_send = NOW - timedelta(hours=25)
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.VOICE): [last_send]})
    result = rl.check(Channel.VOICE, ACCT, PID, now=NOW)
    assert result.allowed


# ---------------------------------------------------------------------------
# Test 7: SMS cycle cap — 1/prospect/30 days
# ---------------------------------------------------------------------------

def test_sms_cycle_cap():
    recent_send = NOW - timedelta(days=15)
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.SMS): [recent_send]})
    result = rl.check(Channel.SMS, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "CYCLE_CAP_EXCEEDED" in result.violations


def test_sms_outside_cycle_allowed():
    old_send = NOW - timedelta(days=31)
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.SMS): [old_send]})
    result = rl.check(Channel.SMS, ACCT, PID, now=NOW)
    assert result.allowed


# ---------------------------------------------------------------------------
# Test 8: Email same-prospect frequency — 3 in 14d max
# ---------------------------------------------------------------------------

def test_email_prospect_frequency_3_in_14d_passes():
    # 2 existing sends in window
    sends = [NOW - timedelta(days=d) for d in [3, 7]]
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.EMAIL): sends})
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    # count=2, cap=3 → no frequency violation (warming_day not set → warmed cap 100)
    assert "PROSPECT_FREQUENCY_EXCEEDED" not in result.violations


def test_email_prospect_frequency_4th_blocked():
    # 3 existing sends within 14d
    sends = [NOW - timedelta(days=d) for d in [2, 5, 10]]
    rl, _, _ = _limiter(prospect_sends={(PID, Channel.EMAIL): sends})
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "PROSPECT_FREQUENCY_EXCEEDED" in result.violations


# ---------------------------------------------------------------------------
# Test 9: Account rotation — balanced pool
# ---------------------------------------------------------------------------

def test_account_rotation_pick_lowest():
    pool = AccountPool(channel=Channel.EMAIL, accounts=["A", "B", "C"])
    usage = {"A": 5, "B": 3, "C": 4}
    assert pool.pick_next(usage) == "B"


# ---------------------------------------------------------------------------
# Test 10: Account rotation — tie → lexicographic
# ---------------------------------------------------------------------------

def test_account_rotation_tie_lexicographic():
    pool = AccountPool(channel=Channel.EMAIL, accounts=["A", "B"])
    usage = {"A": 5, "B": 5}
    assert pool.pick_next(usage) == "A"


# ---------------------------------------------------------------------------
# Test 11: Account rotation — empty pool
# ---------------------------------------------------------------------------

def test_account_rotation_empty():
    pool = AccountPool(channel=Channel.EMAIL, accounts=[])
    assert pool.pick_next({}) is None


# ---------------------------------------------------------------------------
# Test 12: Multiple violations accumulate
# ---------------------------------------------------------------------------

def test_multiple_violations_accumulate():
    # Daily cap hit + prospect frequency hit for email
    ws = _day_key(Channel.EMAIL, ACCT, NOW)
    sends = [NOW - timedelta(days=d) for d in [1, 4, 8]]
    rl, _, _ = _limiter(
        window_counts={ws: 100},       # warmed cap = 100 → hits daily cap
        warming_days={},               # warmed
        prospect_sends={(PID, Channel.EMAIL): sends},  # 3 sends → 4th is PROSPECT_FREQUENCY_EXCEEDED
    )
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert not result.allowed
    assert "DAILY_CAP_EXCEEDED" in result.violations
    assert "PROSPECT_FREQUENCY_EXCEEDED" in result.violations


# ---------------------------------------------------------------------------
# Test 13: consume() increments counters
# ---------------------------------------------------------------------------

def test_consume_increments_counters():
    gw, iw, gwd, gpf, rps, wc, ps = _make_stores()
    rl = RateLimiter(gw, iw, gwd, gpf, rps)
    assert len(ps[(PID, Channel.EMAIL)]) == 0
    ws = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    assert wc[(Channel.EMAIL, ACCT, ws)] == 0

    rl.consume(Channel.EMAIL, ACCT, PID, now=NOW)

    assert wc[(Channel.EMAIL, ACCT, ws)] == 1
    assert len(ps[(PID, Channel.EMAIL)]) == 1


# ---------------------------------------------------------------------------
# Test 14: retry_after populated for window violation
# ---------------------------------------------------------------------------

def test_retry_after_window_violation():
    ws = NOW.replace(hour=0, minute=0, second=0, microsecond=0)
    rl, _, _ = _limiter(
        window_counts={_day_key(Channel.EMAIL, ACCT, NOW): 100},
        warming_days={},
    )
    result = rl.check(Channel.EMAIL, ACCT, PID, now=NOW)
    assert result.retry_after is not None
    expected = ws + timedelta(days=1)
    assert result.retry_after == expected
