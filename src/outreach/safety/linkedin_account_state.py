"""
Contract: src/outreach/safety/linkedin_account_state.py
Purpose: Track LinkedIn connect-request lifecycle per (account, prospect) pair so
         the dispatcher can (a) route around prospects whose invites have not
         been accepted and (b) auto-skip stale-pending connects past 7 days.
Layer:   3 - engines (pure Python; storage via injected callables)
Imports: stdlib + src.outreach.safety.timing_engine (Channel enum)
Consumers: outreach dispatcher / hourly cadence flow / per-prospect routing

State machine:
    connect_sent ──► accepted  ──► allows DMs
                 ├─► rejected  ──► skip LinkedIn channel for this prospect
                 └─► pending > STALE_DAYS ──► auto-skip to next channel
                                              (state advances to 'stale_skipped')

Valid state transitions:
    (None)           -> connect_sent
    connect_sent     -> accepted | rejected | stale_skipped
    stale_skipped    -> (terminal — routing moves on)
    accepted         -> (terminal — DMs now allowed)
    rejected         -> (terminal — skip LinkedIn)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable

STALE_CONNECT_DAYS = 7


class LinkedInState(str, Enum):
    CONNECT_SENT = "connect_sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    STALE_SKIPPED = "stale_skipped"


_VALID_TRANSITIONS: dict[LinkedInState | None, set[LinkedInState]] = {
    None: {LinkedInState.CONNECT_SENT},
    LinkedInState.CONNECT_SENT: {
        LinkedInState.ACCEPTED,
        LinkedInState.REJECTED,
        LinkedInState.STALE_SKIPPED,
    },
    LinkedInState.ACCEPTED: set(),
    LinkedInState.REJECTED: set(),
    LinkedInState.STALE_SKIPPED: set(),
}


class InvalidTransition(ValueError):
    """Raised when a caller attempts a transition not permitted by the FSM."""


@dataclass
class ConnectionRecord:
    account_id: str
    prospect_id: str
    state: LinkedInState
    sent_at: datetime | None
    accepted_at: datetime | None
    days_pending: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class SkipResult:
    prospect_id: str
    account_id: str
    previous_state: LinkedInState
    new_state: LinkedInState
    days_pending: int


class LinkedInAccountState:
    """Lifecycle manager for LinkedIn connect-request states.

    Injected callables for storage (keeps pure-Python contract):
      get_record(account_id, prospect_id) -> ConnectionRecord | None
      upsert_record(record: ConnectionRecord) -> None
      list_pending(account_id=None) -> list[ConnectionRecord]
    """

    def __init__(
        self,
        get_record: Callable,
        upsert_record: Callable,
        list_pending: Callable,
        now_fn: Callable = lambda: datetime.now(timezone.utc),
    ):
        self._get = get_record
        self._upsert = upsert_record
        self._list_pending = list_pending
        self._now = now_fn

    def record_connect_sent(self, account_id: str, prospect_id: str) -> ConnectionRecord:
        existing = self._get(account_id, prospect_id)
        prev = existing.state if existing else None
        self._assert_transition(prev, LinkedInState.CONNECT_SENT)
        record = ConnectionRecord(
            account_id=account_id,
            prospect_id=prospect_id,
            state=LinkedInState.CONNECT_SENT,
            sent_at=self._now(),
            accepted_at=None,
            days_pending=0,
        )
        self._upsert(record)
        return record

    def record_accepted(self, account_id: str, prospect_id: str) -> ConnectionRecord:
        record = self._require(account_id, prospect_id)
        self._assert_transition(record.state, LinkedInState.ACCEPTED)
        record.state = LinkedInState.ACCEPTED
        record.accepted_at = self._now()
        record.days_pending = self._elapsed_days(record.sent_at)
        self._upsert(record)
        return record

    def record_rejected(self, account_id: str, prospect_id: str) -> ConnectionRecord:
        record = self._require(account_id, prospect_id)
        self._assert_transition(record.state, LinkedInState.REJECTED)
        record.state = LinkedInState.REJECTED
        record.days_pending = self._elapsed_days(record.sent_at)
        self._upsert(record)
        return record

    def allows_dm(self, account_id: str, prospect_id: str) -> bool:
        existing = self._get(account_id, prospect_id)
        return existing is not None and existing.state is LinkedInState.ACCEPTED

    def auto_skip_stale_connects(self, account_id: str | None = None) -> list[SkipResult]:
        """Scan pending connects; for every record older than STALE_CONNECT_DAYS,
        advance to STALE_SKIPPED and return a list of affected prospects so the
        caller can route them past LinkedIn to the next channel."""
        now = self._now()
        threshold = now - timedelta(days=STALE_CONNECT_DAYS)
        results: list[SkipResult] = []
        for record in self._list_pending(account_id):
            if record.state is not LinkedInState.CONNECT_SENT:
                continue
            if record.sent_at is None or record.sent_at > threshold:
                continue
            prev = record.state
            record.state = LinkedInState.STALE_SKIPPED
            record.days_pending = self._elapsed_days(record.sent_at, now=now)
            self._upsert(record)
            results.append(SkipResult(
                prospect_id=record.prospect_id,
                account_id=record.account_id,
                previous_state=prev,
                new_state=record.state,
                days_pending=record.days_pending,
            ))
        return results

    def _require(self, account_id: str, prospect_id: str) -> ConnectionRecord:
        record = self._get(account_id, prospect_id)
        if record is None:
            raise InvalidTransition(
                f"no record for account={account_id} prospect={prospect_id}"
            )
        return record

    @staticmethod
    def _assert_transition(
        from_state: LinkedInState | None, to_state: LinkedInState
    ) -> None:
        allowed = _VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidTransition(f"{from_state} -> {to_state} not permitted")

    def _elapsed_days(self, sent_at: datetime | None, now: datetime | None = None) -> int:
        if sent_at is None:
            return 0
        now = now or self._now()
        return max(0, (now - sent_at).days)
