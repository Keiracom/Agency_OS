"""
Tests for src/outreach/safety/linkedin_account_state.py.

Covers state transitions (valid + invalid), DM gate, stale-connect auto-skip,
and elapsed-day accounting. Storage is faked via an in-memory dict.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.outreach.safety.linkedin_account_state import (
    STALE_CONNECT_DAYS,
    ConnectionRecord,
    InvalidTransition,
    LinkedInAccountState,
    LinkedInState,
    SkipResult,
)


class _FakeStore:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], ConnectionRecord] = {}

    def get(self, account_id: str, prospect_id: str) -> ConnectionRecord | None:
        return self.rows.get((account_id, prospect_id))

    def upsert(self, record: ConnectionRecord) -> None:
        self.rows[(record.account_id, record.prospect_id)] = record

    def list_pending(self, account_id: str | None = None) -> list[ConnectionRecord]:
        return [r for (a, _), r in self.rows.items() if account_id is None or a == account_id]


def _manager(now: datetime | None = None) -> tuple[LinkedInAccountState, _FakeStore]:
    store = _FakeStore()
    clock = now or datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc)
    return (
        LinkedInAccountState(
            get_record=store.get,
            upsert_record=store.upsert,
            list_pending=store.list_pending,
            now_fn=lambda: clock,
        ),
        store,
    )


# -- happy-path transitions --------------------------------------------------

def test_record_connect_sent_creates_row():
    mgr, store = _manager()
    rec = mgr.record_connect_sent("acct-1", "p-1")
    assert rec.state is LinkedInState.CONNECT_SENT
    assert rec.sent_at is not None
    assert store.get("acct-1", "p-1") is rec


def test_connect_sent_to_accepted_allows_dm():
    mgr, _ = _manager()
    mgr.record_connect_sent("acct-1", "p-1")
    rec = mgr.record_accepted("acct-1", "p-1")
    assert rec.state is LinkedInState.ACCEPTED
    assert rec.accepted_at is not None
    assert mgr.allows_dm("acct-1", "p-1") is True


def test_connect_sent_to_rejected_blocks_dm():
    mgr, _ = _manager()
    mgr.record_connect_sent("acct-1", "p-1")
    rec = mgr.record_rejected("acct-1", "p-1")
    assert rec.state is LinkedInState.REJECTED
    assert mgr.allows_dm("acct-1", "p-1") is False


def test_allows_dm_false_when_no_record():
    mgr, _ = _manager()
    assert mgr.allows_dm("acct-1", "p-1") is False


# -- invalid transitions -----------------------------------------------------

def test_cannot_accept_without_connect_sent():
    mgr, _ = _manager()
    with pytest.raises(InvalidTransition):
        mgr.record_accepted("acct-1", "p-1")


def test_cannot_double_connect_send():
    mgr, _ = _manager()
    mgr.record_connect_sent("acct-1", "p-1")
    with pytest.raises(InvalidTransition):
        mgr.record_connect_sent("acct-1", "p-1")


def test_cannot_transition_from_accepted():
    mgr, _ = _manager()
    mgr.record_connect_sent("acct-1", "p-1")
    mgr.record_accepted("acct-1", "p-1")
    with pytest.raises(InvalidTransition):
        mgr.record_rejected("acct-1", "p-1")


# -- stale connect auto-skip -------------------------------------------------

def test_auto_skip_advances_connects_older_than_threshold():
    now = datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc)
    mgr, store = _manager(now)
    # 10-day-old pending connect → should advance to stale_skipped
    store.upsert(ConnectionRecord(
        account_id="acct-1", prospect_id="p-old",
        state=LinkedInState.CONNECT_SENT,
        sent_at=now - timedelta(days=10),
        accepted_at=None, days_pending=10,
    ))
    # 3-day-old pending → untouched (< 7 days)
    store.upsert(ConnectionRecord(
        account_id="acct-1", prospect_id="p-fresh",
        state=LinkedInState.CONNECT_SENT,
        sent_at=now - timedelta(days=3),
        accepted_at=None, days_pending=3,
    ))
    results = mgr.auto_skip_stale_connects()
    assert len(results) == 1
    assert results[0] == SkipResult(
        prospect_id="p-old", account_id="acct-1",
        previous_state=LinkedInState.CONNECT_SENT,
        new_state=LinkedInState.STALE_SKIPPED,
        days_pending=10,
    )
    assert store.get("acct-1", "p-fresh").state is LinkedInState.CONNECT_SENT
    assert store.get("acct-1", "p-old").state is LinkedInState.STALE_SKIPPED


def test_auto_skip_ignores_accepted_rejected_and_already_skipped():
    now = datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc)
    mgr, store = _manager(now)
    for pid, state in [
        ("p-acc", LinkedInState.ACCEPTED),
        ("p-rej", LinkedInState.REJECTED),
        ("p-skipped", LinkedInState.STALE_SKIPPED),
    ]:
        store.upsert(ConnectionRecord(
            account_id="acct-1", prospect_id=pid, state=state,
            sent_at=now - timedelta(days=30), accepted_at=None, days_pending=30,
        ))
    results = mgr.auto_skip_stale_connects()
    assert results == []


def test_auto_skip_filters_by_account_id():
    now = datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc)
    mgr, store = _manager(now)
    for acct in ["acct-A", "acct-B"]:
        store.upsert(ConnectionRecord(
            account_id=acct, prospect_id="p-1",
            state=LinkedInState.CONNECT_SENT,
            sent_at=now - timedelta(days=10),
            accepted_at=None, days_pending=10,
        ))
    results = mgr.auto_skip_stale_connects(account_id="acct-A")
    assert [r.account_id for r in results] == ["acct-A"]
    assert store.get("acct-B", "p-1").state is LinkedInState.CONNECT_SENT


def test_stale_threshold_constant_is_seven_days():
    assert STALE_CONNECT_DAYS == 7


# -- elapsed-day accounting --------------------------------------------------

def test_accepted_records_actual_days_pending():
    sent = datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc)
    accept = sent + timedelta(days=2, hours=4)
    mgr, store = _manager(sent)
    mgr.record_connect_sent("acct-1", "p-1")
    # advance clock
    mgr._now = lambda: accept
    rec = mgr.record_accepted("acct-1", "p-1")
    assert rec.days_pending == 2
    assert rec.accepted_at == accept
