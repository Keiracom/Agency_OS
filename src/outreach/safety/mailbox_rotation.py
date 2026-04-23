"""
Contract: src/outreach/safety/mailbox_rotation.py
Purpose: LRU mailbox rotation with warming-cap enforcement and optional Redis
         locking for multi-worker coordination.
Layer: 3 - engines
Imports: stdlib + src.outreach.safety.rate_limiter (warming constants only)
Consumers: outreach orchestration, campaign scheduler

Redis is soft-imported — absence degrades gracefully to single-instance mode.
"""

from __future__ import annotations

try:
    import redis as _redis_mod
except ImportError:
    _redis_mod = None  # type: ignore[assignment]

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from src.outreach.safety.rate_limiter import _EMAIL_WARMED_CAP, _WARMING_LADDER


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclass
class MailboxState:
    mailbox_id: str
    client_id: str
    channel: str              # "email" | "linkedin"
    last_send_at: datetime | None
    daily_count: int
    warming_day: int | None   # None = warmed; 1..14 = warming day number
    healthy: bool = True      # toggle to False removes from rotation


@dataclass
class RotationDecision:
    mailbox_id: str | None
    reason: str               # "lru-warming" | "lru-warmed" | "no-eligible" | "locked-by-other"


# ---------------------------------------------------------------------------
# Default warming cap (importable for tests)
# ---------------------------------------------------------------------------

def _default_warming_cap(warming_day: int | None) -> int:
    """Return daily cap given warming_day. None = fully warmed."""
    if warming_day is None:
        return _EMAIL_WARMED_CAP
    return _WARMING_LADDER.get(warming_day, _EMAIL_WARMED_CAP)


# ---------------------------------------------------------------------------
# MailboxRotator
# ---------------------------------------------------------------------------

class MailboxRotator:
    """LRU rotation with warming cap respect. Optional Redis lock for multi-worker coord.

    Callable-based storage (matches rate_limiter pattern so unit tests don't need
    a real DB):
      list_pool(client_id, channel)          -> list[MailboxState]
      record_send(mailbox_id, now)           -> None
      warming_ladder_cap(warming_day|None)   -> int
    """

    def __init__(
        self,
        list_pool: Callable,
        record_send: Callable,
        warming_ladder_cap: Callable,
        redis_client=None,
        lock_ttl_seconds: int = 30,
        now_fn: Callable[[], datetime] = lambda: datetime.utcnow(),
    ) -> None:
        self._list_pool = list_pool
        self._record_send_fn = record_send
        self._warming_ladder_cap = warming_ladder_cap
        self._redis = redis_client
        self._lock_ttl = lock_ttl_seconds
        self._now_fn = now_fn
        self._held_lock_key: str | None = None

    def pick_next_mailbox(self, client_id: str, channel: str = "email") -> RotationDecision:
        """Return the LRU mailbox that has headroom vs its warming cap.

        Redis path: acquires a short per-mailbox lock (SETNX + TTL) to prevent
        two workers picking the same mailbox. Falls through to next candidate
        when lock is held by another worker.
        Single-instance path (no Redis): no locking.
        """
        pool: list[MailboxState] = self._list_pool(client_id, channel)
        eligible = self._filter_eligible(pool)
        if not eligible:
            return RotationDecision(mailbox_id=None, reason="no-eligible")

        for candidate in eligible:
            if not self._acquire_lock(candidate.mailbox_id):
                continue
            reason = "lru-warming" if candidate.warming_day is not None else "lru-warmed"
            return RotationDecision(mailbox_id=candidate.mailbox_id, reason=reason)

        # All eligible candidates were locked by other workers
        return RotationDecision(mailbox_id=None, reason="locked-by-other")

    def record_send(self, mailbox_id: str, at: datetime | None = None) -> None:
        """Release the Redis lock (if held) and call the injected record_send."""
        self._release_lock(mailbox_id)
        self._record_send_fn(mailbox_id, at or self._now_fn())

    # ------------------------------------------------------------------
    # Private helpers (each well under 50 lines)
    # ------------------------------------------------------------------

    def _filter_eligible(self, pool: list[MailboxState]) -> list[MailboxState]:
        """Return healthy mailboxes under their warming cap, sorted LRU-first."""
        eligible = []
        for state in pool:
            if not state.healthy:
                continue
            cap = self._warming_ladder_cap(state.warming_day)
            if state.daily_count < cap:
                eligible.append(state)
        return sorted(eligible, key=lambda s: (
            s.last_send_at is not None,   # None (never-used) sorts first
            s.last_send_at or datetime.min,
            s.mailbox_id,                  # deterministic lex tie-break
        ))

    def _lock_key(self, mailbox_id: str) -> str:
        return f"mailbox-rotate:{mailbox_id}"

    def _acquire_lock(self, mailbox_id: str) -> bool:
        """Attempt to acquire Redis lock. Returns True if acquired (or no Redis)."""
        if self._redis is None:
            self._held_lock_key = None
            return True
        key = self._lock_key(mailbox_id)
        acquired = self._redis.set(key, "1", nx=True, ex=self._lock_ttl)
        if acquired:
            self._held_lock_key = key
        return bool(acquired)

    def _release_lock(self, mailbox_id: str) -> None:
        """Release the held Redis lock if we own it."""
        if self._redis is None:
            return
        key = self._lock_key(mailbox_id)
        if self._held_lock_key == key:
            self._redis.delete(key)
            self._held_lock_key = None
