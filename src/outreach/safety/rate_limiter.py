"""
Contract: src/outreach/safety/rate_limiter.py
Purpose: Per-channel rate limiting, email warming ladder, account rotation,
         and same-prospect frequency caps for outreach safety.
Layer: 3 - engines
Imports: stdlib + src.outreach.safety.timing_engine
Consumers: outreach orchestration

KNOWN SIMPLIFICATIONS (to be resolved in 'linkedin-subtype-split' dispatch):
  - LinkedIn subtypes (connect vs message) are collapsed into a single
    Channel.LINKEDIN cap: 50 sends per day per account.
  - The full spec calls for 100 connects/week + 50 msgs/day as separate
    sub-channel limits. This requires channel-subtype awareness not yet
    in the enum. Documented here; revisit when subtypes land.

Violation codes:
    DAILY_CAP_EXCEEDED          — account hit its daily send ceiling
    WEEKLY_CAP_EXCEEDED         — account hit its 7-day send ceiling (LinkedIn connects)
    PROSPECT_COOLDOWN_ACTIVE    — same-prospect cooldown window not elapsed
    PROSPECT_FREQUENCY_EXCEEDED — prospect received too many emails in rolling window
    CYCLE_CAP_EXCEEDED          — SMS cycle cap reached for this prospect
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.outreach.safety.timing_engine import Channel

# ---------------------------------------------------------------------------
# Email warming ladder: warming_day -> daily_cap
# Days 1-3: 10, 4-6: 25, 7-10: 50, 11-14: 75, 15+: 100
# ---------------------------------------------------------------------------
_WARMING_LADDER: dict[int, int] = {
    **dict.fromkeys(range(1, 4), 10),
    **dict.fromkeys(range(4, 7), 25),
    **dict.fromkeys(range(7, 11), 50),
    **dict.fromkeys(range(11, 15), 75),
}
_WARMED_CAP = 100

# Per-channel caps
_DAILY_CAP: dict[Channel, int] = {
    Channel.LINKEDIN: 50,  # simplified: connect+msg collapsed (see module docstring)
}
_EMAIL_WARMED_CAP = _WARMED_CAP

# Prospect frequency / cooldown caps
_EMAIL_PROSPECT_WINDOW_DAYS = 14
_EMAIL_PROSPECT_MAX = 3
_VOICE_DAILY_PROSPECT_MAX = 3
_VOICE_COOLDOWN_HOURS = 24
_SMS_CYCLE_DAYS = 30


@dataclass
class RateDecision:
    allowed: bool
    reason: str
    violations: list[str] = field(default_factory=list)
    retry_after: datetime | None = None  # earliest datetime caller can retry


@dataclass
class AccountPool:
    """Pool of accounts (mailboxes/seats/phones) eligible for rotation per channel."""

    channel: Channel
    accounts: list[str]  # account ids

    def pick_next(self, usage_counts: dict[str, int]) -> str | None:
        """Return the account with the lowest current usage.

        Tie-breaking: lexicographically smallest account_id (deterministic).
        Returns None if pool is empty.
        """
        if not self.accounts:
            return None
        return min(self.accounts, key=lambda a: (usage_counts.get(a, 0), a))


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Per-channel caps + warming ladder + rotation + same-prospect frequency cap.

    Storage is injected via callables so the class is unit-testable without
    a real database:
      get_window_count(channel, account_id, window_start) -> int
      incr_window_count(channel, account_id, window_start) -> None
      get_warming_day(account_id) -> int | None           # None = warmed
      get_prospect_frequency(prospect_id, channel, since) -> int
      record_prospect_send(prospect_id, channel, now) -> None
    """

    def __init__(
        self,
        get_window_count: Callable[[Channel, str, datetime], int],
        incr_window_count: Callable[[Channel, str, datetime], None],
        get_warming_day: Callable[[str], int | None],
        get_prospect_frequency: Callable[[str, Channel, datetime], int],
        record_prospect_send: Callable[[str, Channel, datetime], None],
        now_fn: Callable[[], datetime] = lambda: datetime.utcnow(),
    ) -> None:
        self._get_window_count = get_window_count
        self._incr_window_count = incr_window_count
        self._get_warming_day = get_warming_day
        self._get_prospect_frequency = get_prospect_frequency
        self._record_prospect_send = record_prospect_send
        self._now_fn = now_fn

    def check(
        self,
        channel: Channel,
        account_id: str,
        prospect_id: str,
        now: datetime | None = None,
    ) -> RateDecision:
        """Evaluate all caps for this send. Returns RateDecision.

        Accumulates all violation codes; any violation sets allowed=False.
        """
        now = now or self._now_fn()
        violations: list[str] = []
        retry_after: datetime | None = None

        if channel == Channel.EMAIL:
            ra = _check_email_caps(
                account_id,
                prospect_id,
                now,
                self._get_window_count,
                self._get_warming_day,
                self._get_prospect_frequency,
                violations,
            )
            retry_after = _earliest(retry_after, ra)

        elif channel == Channel.LINKEDIN:
            ra = _check_linkedin_caps(account_id, now, self._get_window_count, violations)
            retry_after = _earliest(retry_after, ra)

        elif channel == Channel.VOICE:
            ra = _check_voice_caps(prospect_id, now, self._get_prospect_frequency, violations)
            retry_after = _earliest(retry_after, ra)

        elif channel == Channel.SMS:
            ra = _check_sms_caps(prospect_id, now, self._get_prospect_frequency, violations)
            retry_after = _earliest(retry_after, ra)

        allowed = len(violations) == 0
        reason = "; ".join(violations) if violations else "allowed"
        return RateDecision(
            allowed=allowed, reason=reason, violations=violations, retry_after=retry_after
        )

    def consume(
        self,
        channel: Channel,
        account_id: str,
        prospect_id: str,
        now: datetime | None = None,
    ) -> None:
        """Record a send against window and prospect-frequency counters.

        Caller should check() first — consume() does not re-check.
        """
        now = now or self._now_fn()
        window_start = _day_window(now)
        self._incr_window_count(channel, account_id, window_start)
        self._record_prospect_send(prospect_id, channel, now)


# ---------------------------------------------------------------------------
# Private per-channel checkers — each under 50 lines
# ---------------------------------------------------------------------------


def _check_email_caps(
    account_id: str,
    prospect_id: str,
    now: datetime,
    get_window_count: Callable,
    get_warming_day: Callable,
    get_prospect_frequency: Callable,
    violations: list[str],
) -> datetime | None:
    """Check email daily cap (with warming) + prospect frequency. Returns retry_after or None."""
    window_start = _day_window(now)
    count = get_window_count(Channel.EMAIL, account_id, window_start)
    warming_day = get_warming_day(account_id)
    cap = _email_cap(warming_day)

    retry_after: datetime | None = None
    if count >= cap:
        violations.append("DAILY_CAP_EXCEEDED")
        retry_after = window_start + timedelta(days=1)

    since = now - timedelta(days=_EMAIL_PROSPECT_WINDOW_DAYS)
    freq = get_prospect_frequency(prospect_id, Channel.EMAIL, since)
    if freq >= _EMAIL_PROSPECT_MAX:
        violations.append("PROSPECT_FREQUENCY_EXCEEDED")
        # retry_after not set for frequency — no deterministic window end available

    return retry_after


def _check_linkedin_caps(
    account_id: str,
    now: datetime,
    get_window_count: Callable,
    violations: list[str],
) -> datetime | None:
    """Check LinkedIn daily cap (collapsed connect+msg simplification). Returns retry_after or None."""
    window_start = _day_window(now)
    count = get_window_count(Channel.LINKEDIN, account_id, window_start)
    cap = _DAILY_CAP[Channel.LINKEDIN]

    if count >= cap:
        violations.append("DAILY_CAP_EXCEEDED")
        return window_start + timedelta(days=1)
    return None


def _check_voice_caps(
    prospect_id: str,
    now: datetime,
    get_prospect_frequency: Callable,
    violations: list[str],
) -> datetime | None:
    """Check voice: 3 attempts per prospect per 24hr + 24hr cooldown. Returns retry_after or None."""
    since_24h = now - timedelta(hours=_VOICE_COOLDOWN_HOURS)
    count_24h = get_prospect_frequency(prospect_id, Channel.VOICE, since_24h)

    retry_after: datetime | None = None
    if count_24h >= _VOICE_DAILY_PROSPECT_MAX:
        violations.append("DAILY_CAP_EXCEEDED")
        retry_after = since_24h + timedelta(hours=_VOICE_COOLDOWN_HOURS)

    # Cooldown: at least 24hr since last send (same-prospect)
    # Represented as: any send in last 24hr means cooldown active (count_24h >= 1)
    if count_24h >= 1 and count_24h < _VOICE_DAILY_PROSPECT_MAX:
        violations.append("PROSPECT_COOLDOWN_ACTIVE")
        retry_after = _earliest(retry_after, since_24h + timedelta(hours=_VOICE_COOLDOWN_HOURS))

    return retry_after


def _check_sms_caps(
    prospect_id: str,
    now: datetime,
    get_prospect_frequency: Callable,
    violations: list[str],
) -> datetime | None:
    """Check SMS: 1 per prospect per 30-day cycle. Returns retry_after or None."""
    since_cycle = now - timedelta(days=_SMS_CYCLE_DAYS)
    count = get_prospect_frequency(prospect_id, Channel.SMS, since_cycle)

    if count >= 1:
        violations.append("CYCLE_CAP_EXCEEDED")
        return since_cycle + timedelta(days=_SMS_CYCLE_DAYS)
    return None


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _email_cap(warming_day: int | None) -> int:
    """Return daily cap given warming_day. None = warmed."""
    if warming_day is None:
        return _WARMED_CAP
    return _WARMING_LADDER.get(warming_day, _WARMED_CAP)


def _day_window(now: datetime) -> datetime:
    """Truncate datetime to start of UTC day."""
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _earliest(a: datetime | None, b: datetime | None) -> datetime | None:
    """Return the earlier of two optional datetimes."""
    if a is None:
        return b
    if b is None:
        return a
    return a if a <= b else b
