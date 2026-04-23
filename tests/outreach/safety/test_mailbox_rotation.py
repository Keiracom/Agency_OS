"""Tests for src/outreach/safety/mailbox_rotation.py — 11 cases."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.outreach.safety.mailbox_rotation import MailboxRotator, MailboxState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 22, 12, 0, 0)


def _cap(warming_day: int | None) -> int:
    """Simplified warming cap for tests: day 1 = 10, None = 100."""
    if warming_day is None:
        return 100
    if warming_day == 1:
        return 10
    if warming_day <= 3:
        return 10
    if warming_day <= 6:
        return 25
    if warming_day <= 10:
        return 50
    return 75


def _make_rotator(pool: list[MailboxState], redis_client=None) -> MailboxRotator:
    sends: dict[str, datetime] = {}

    def list_pool(client_id, channel):
        return [s for s in pool if s.client_id == client_id and s.channel == channel]

    def record_send(mailbox_id, now):
        sends[mailbox_id] = now

    return MailboxRotator(
        list_pool=list_pool,
        record_send=record_send,
        warming_ladder_cap=_cap,
        redis_client=redis_client,
        now_fn=lambda: _NOW,
    )


def _state(
    mailbox_id: str,
    last_send_at: datetime | None = None,
    daily_count: int = 0,
    warming_day: int | None = None,
    healthy: bool = True,
) -> MailboxState:
    return MailboxState(
        mailbox_id=mailbox_id,
        client_id="client-1",
        channel="email",
        last_send_at=last_send_at,
        daily_count=daily_count,
        warming_day=warming_day,
        healthy=healthy,
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_lru_none_sorts_first():
    """Pool A(1h ago), B(30min ago), C(never) → pick C (None last_send sorts first)."""
    pool = [
        _state("A", last_send_at=_NOW - timedelta(hours=1)),
        _state("B", last_send_at=_NOW - timedelta(minutes=30)),
        _state("C", last_send_at=None),
    ]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id == "C"


def test_all_at_cap_returns_no_eligible():
    """All mailboxes at cap → no-eligible."""
    pool = [
        _state("A", daily_count=100, warming_day=None),
        _state("B", daily_count=100, warming_day=None),
    ]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id is None
    assert decision.reason == "no-eligible"


def test_warming_day1_at_cap_skipped():
    """Mailbox on warming_day=1 with daily_count=10 → at cap (10) → skipped."""
    pool = [
        _state("A", daily_count=10, warming_day=1),    # at cap
        _state("B", daily_count=5, warming_day=None),  # eligible
    ]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id == "B"


def test_warmed_cap_respected():
    """warming_day=None with daily_count=100 → at cap (100) → skipped."""
    pool = [
        _state("A", daily_count=100, warming_day=None),  # at cap
        _state("B", daily_count=0, warming_day=None),    # eligible
    ]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id == "B"


def test_unhealthy_skipped():
    """healthy=False mailboxes are excluded from rotation."""
    pool = [
        _state("A", healthy=False),
        _state("B", healthy=True),
    ]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id == "B"


def test_lex_tiebreak_on_identical_last_send():
    """Identical last_send_at → lexicographically smallest mailbox_id wins."""
    ts = _NOW - timedelta(hours=1)
    pool = [
        _state("mailbox-Z", last_send_at=ts),
        _state("mailbox-A", last_send_at=ts),
    ]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id == "mailbox-A"


def test_reason_lru_warming_when_warming_day_set():
    """Returned reason is 'lru-warming' when chosen mailbox has warming_day set."""
    pool = [_state("A", warming_day=3, daily_count=0)]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.reason == "lru-warming"


def test_reason_lru_warmed_when_no_warming_day():
    """Returned reason is 'lru-warmed' when chosen mailbox is fully warmed."""
    pool = [_state("A", warming_day=None, daily_count=0)]
    rotator = _make_rotator(pool)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.reason == "lru-warmed"


def test_no_redis_works_normally():
    """redis_client=None → no locking, still returns correct mailbox."""
    pool = [_state("A")]
    rotator = _make_rotator(pool, redis_client=None)
    decision = rotator.pick_next_mailbox("client-1")
    assert decision.mailbox_id == "A"


def test_redis_lock_acquired_returns_mailbox():
    """Fake Redis set(NX=True) → True: returns that mailbox."""
    fake_redis = MagicMock()
    fake_redis.set.return_value = True

    pool = [_state("A")]
    rotator = _make_rotator(pool, redis_client=fake_redis)
    decision = rotator.pick_next_mailbox("client-1")

    assert decision.mailbox_id == "A"
    fake_redis.set.assert_called_once_with("mailbox-rotate:A", "1", nx=True, ex=30)


def test_redis_lock_held_by_other_falls_through():
    """set(NX) -> False on A → rotator skips A and picks B."""
    fake_redis = MagicMock()
    # A is locked; B is free
    fake_redis.set.side_effect = lambda key, val, nx, ex: (
        False if "A" in key else True
    )

    pool = [
        _state("A", last_send_at=None),          # LRU-first but locked
        _state("B", last_send_at=_NOW - timedelta(hours=1)),
    ]
    rotator = _make_rotator(pool, redis_client=fake_redis)
    decision = rotator.pick_next_mailbox("client-1")

    assert decision.mailbox_id == "B"


def test_record_send_releases_redis_lock():
    """record_send should call redis.delete on the held lock key."""
    fake_redis = MagicMock()
    fake_redis.set.return_value = True

    pool = [_state("A")]
    rotator = _make_rotator(pool, redis_client=fake_redis)
    rotator.pick_next_mailbox("client-1")   # acquires lock on A
    rotator.record_send("A")

    fake_redis.delete.assert_called_once_with("mailbox-rotate:A")
