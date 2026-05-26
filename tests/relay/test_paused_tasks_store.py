"""paused_tasks_store unit tests — A8 §7 piece 2 (Agency_OS-70hb)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from src.relay.paused_tasks_store import (
    DEFAULT_TTL_DAYS,
    STATUS_ABORTED,
    STATUS_ACTIVE,
    STATUS_EXPIRED,
    STATUS_RESUMED,
    VALID_STATUSES,
    PausedTaskRow,
    PausedTasksStore,
    PausedTasksStoreError,
    dead_letter_payload,
)


class _FakeDB:
    """Minimal DB fake — record executes + serve canned fetchone/fetchall."""

    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self._next_one: Any = None
        self._next_all: list[Any] = []

    def execute(self, query: str, *params):
        self.calls.append((query, params))

    def fetchone(self):
        return self._next_one

    def fetchall(self):
        return self._next_all

    def queue_fetchone(self, row: Any) -> None:
        self._next_one = row

    def queue_fetchall(self, rows: list[Any]) -> None:
        self._next_all = rows


def _fixed_now() -> datetime:
    return datetime(2026, 5, 26, 13, 30, 0, tzinfo=UTC)


def _row_tuple(
    *,
    task_ref: str = "Agency_OS-test",
    callsign: str = "orion",
    decision_target: str = "elliot",
    question: str = "should we X?",
    state_snapshot: Any = None,
    status: str = "active",
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    resumed_at: datetime | None = None,
    expired_at: datetime | None = None,
) -> tuple:
    """Build a DB row tuple in the order returned by SELECT columns."""
    return (
        task_ref,
        callsign,
        decision_target,
        question,
        state_snapshot if state_snapshot is not None else "{}",
        status,
        created_at or _fixed_now(),
        expires_at or (_fixed_now() + timedelta(days=DEFAULT_TTL_DAYS)),
        resumed_at,
        expired_at,
    )


# ---- Constants + enum locks ------------------------------------------------


def test_default_ttl_is_seven_days():
    assert DEFAULT_TTL_DAYS == 7


def test_valid_statuses_set():
    assert (
        frozenset({STATUS_ACTIVE, STATUS_RESUMED, STATUS_EXPIRED, STATUS_ABORTED}) == VALID_STATUSES
    )


def test_status_constants():
    assert STATUS_ACTIVE == "active"
    assert STATUS_RESUMED == "resumed"
    assert STATUS_EXPIRED == "expired"
    assert STATUS_ABORTED == "aborted"


# ---- PausedTaskRow invariants ----------------------------------------------


def test_paused_task_row_valid():
    row = PausedTaskRow(
        task_ref="Agency_OS-x",
        callsign="orion",
        decision_target="elliot",
        question="should we?",
        state_snapshot={},
        status="active",
        created_at=_fixed_now(),
        expires_at=_fixed_now() + timedelta(days=7),
    )
    assert row.task_ref == "Agency_OS-x"
    assert row.resumed_at is None


def test_paused_task_row_rejects_empty_task_ref():
    with pytest.raises(PausedTasksStoreError, match="task_ref"):
        PausedTaskRow(
            task_ref="",
            callsign="orion",
            decision_target="elliot",
            question="q",
            state_snapshot={},
            status="active",
            created_at=_fixed_now(),
            expires_at=_fixed_now() + timedelta(days=7),
        )


def test_paused_task_row_rejects_unknown_status():
    with pytest.raises(PausedTasksStoreError, match="status"):
        PausedTaskRow(
            task_ref="x",
            callsign="orion",
            decision_target="elliot",
            question="q",
            state_snapshot={},
            status="_bogus",
            created_at=_fixed_now(),
            expires_at=_fixed_now() + timedelta(days=7),
        )


# ---- insert() --------------------------------------------------------------


def test_insert_validates_required_fields():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    with pytest.raises(PausedTasksStoreError, match="task_ref"):
        store.insert(
            task_ref="",
            callsign="orion",
            decision_target="elliot",
            question="q",
        )
    with pytest.raises(PausedTasksStoreError, match="callsign"):
        store.insert(
            task_ref="x",
            callsign="",
            decision_target="elliot",
            question="q",
        )
    with pytest.raises(PausedTasksStoreError, match="decision_target"):
        store.insert(
            task_ref="x",
            callsign="orion",
            decision_target="",
            question="q",
        )
    with pytest.raises(PausedTasksStoreError, match="question"):
        store.insert(
            task_ref="x",
            callsign="orion",
            decision_target="elliot",
            question="",
        )
    with pytest.raises(PausedTasksStoreError, match="ttl_days"):
        store.insert(
            task_ref="x",
            callsign="orion",
            decision_target="elliot",
            question="q",
            ttl_days=0,
        )


def test_insert_uses_default_7_day_ttl():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.insert(
        task_ref="Agency_OS-x",
        callsign="orion",
        decision_target="elliot",
        question="should we?",
    )
    query, params = db.calls[0]
    assert "INSERT INTO paused_tasks" in query
    assert "ON CONFLICT (task_ref) DO NOTHING" in query
    # Params: task_ref, callsign, decision_target, question, snapshot_json,
    # created_at (now), expires_at (now + 7d)
    assert params[0] == "Agency_OS-x"
    assert params[5] == _fixed_now()
    assert params[6] == _fixed_now() + timedelta(days=DEFAULT_TTL_DAYS)


def test_insert_custom_ttl_days():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.insert(
        task_ref="x",
        callsign="orion",
        decision_target="elliot",
        question="q",
        ttl_days=14,
    )
    _, params = db.calls[0]
    assert params[6] == _fixed_now() + timedelta(days=14)


def test_insert_serializes_state_snapshot_to_jsonb():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    snapshot = {"intermediate_file": "/tmp/work.json", "step": 3}
    store.insert(
        task_ref="x",
        callsign="orion",
        decision_target="elliot",
        question="q",
        state_snapshot=snapshot,
    )
    _, params = db.calls[0]
    import json as _json

    parsed = _json.loads(params[4])
    assert parsed == snapshot


def test_insert_empty_snapshot_serializes_to_empty_object():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.insert(
        task_ref="x",
        callsign="orion",
        decision_target="elliot",
        question="q",
        state_snapshot=None,
    )
    _, params = db.calls[0]
    assert params[4] == "{}"


# ---- fetch() ---------------------------------------------------------------


def test_fetch_returns_none_when_absent():
    db = _FakeDB()
    db.queue_fetchone(None)
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    assert store.fetch("nonexistent") is None


def test_fetch_validates_empty_task_ref():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    with pytest.raises(PausedTasksStoreError, match="task_ref"):
        store.fetch("")


def test_fetch_returns_paused_task_row():
    db = _FakeDB()
    db.queue_fetchone(_row_tuple(task_ref="Agency_OS-x", question="should we?"))
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    row = store.fetch("Agency_OS-x")
    assert row is not None
    assert row.task_ref == "Agency_OS-x"
    assert row.question == "should we?"
    assert row.status == "active"
    assert row.callsign == "orion"


def test_fetch_parses_state_snapshot_jsonb_string():
    db = _FakeDB()
    db.queue_fetchone(_row_tuple(state_snapshot='{"step": 3, "path": "/tmp/x"}'))
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    row = store.fetch("Agency_OS-test")
    assert row.state_snapshot == {"step": 3, "path": "/tmp/x"}


def test_fetch_parses_state_snapshot_already_dict():
    """psycopg may adapt JSONB to dict directly — tolerate either shape."""
    db = _FakeDB()
    db.queue_fetchone(_row_tuple(state_snapshot={"adapted": True}))
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    row = store.fetch("Agency_OS-test")
    assert row.state_snapshot == {"adapted": True}


# ---- mark_resumed() --------------------------------------------------------


def test_mark_resumed_updates_status():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.mark_resumed("Agency_OS-x")
    query, params = db.calls[0]
    assert "UPDATE paused_tasks" in query
    assert "status = 'resumed'" in query
    assert "resumed_at" in query
    # Only flips if currently active (idempotency invariant)
    assert "status = 'active'" in query
    assert params[1] == "Agency_OS-x"


def test_mark_resumed_validates_task_ref():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    with pytest.raises(PausedTasksStoreError, match="task_ref"):
        store.mark_resumed("")


# ---- mark_aborted() --------------------------------------------------------


def test_mark_aborted_updates_status():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.mark_aborted("Agency_OS-x")
    query, params = db.calls[0]
    assert "status = 'aborted'" in query
    assert "status = 'active'" in query  # idempotency invariant
    assert params[0] == "Agency_OS-x"


# ---- sweep_expired() -------------------------------------------------------


def test_sweep_expired_returns_empty_when_no_stale_rows():
    db = _FakeDB()
    db.queue_fetchall([])
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    assert store.sweep_expired() == []


def test_sweep_expired_uses_atomic_update_returning():
    db = _FakeDB()
    db.queue_fetchall([])
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.sweep_expired()
    query, params = db.calls[0]
    assert "UPDATE paused_tasks SET status = 'expired'" in query
    assert "RETURNING" in query
    assert "expires_at <= %s" in query
    assert "status = 'active'" in query


def test_sweep_expired_returns_paused_task_rows():
    db = _FakeDB()
    db.queue_fetchall(
        [
            _row_tuple(task_ref="A1", status="expired", expired_at=_fixed_now()),
            _row_tuple(task_ref="A2", status="expired", expired_at=_fixed_now()),
        ]
    )
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    rows = store.sweep_expired()
    assert len(rows) == 2
    assert {r.task_ref for r in rows} == {"A1", "A2"}
    assert all(r.status == "expired" for r in rows)


# ---- list_by_callsign() ----------------------------------------------------


def test_list_by_callsign_default_active():
    db = _FakeDB()
    db.queue_fetchall([_row_tuple(callsign="orion", task_ref="x")])
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    rows = store.list_by_callsign("orion")
    assert len(rows) == 1
    query, params = db.calls[0]
    assert "WHERE callsign = %s AND status = %s" in query
    assert params == ("orion", "active")


def test_list_by_callsign_custom_status():
    db = _FakeDB()
    db.queue_fetchall([])
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    store.list_by_callsign("orion", status="resumed")
    _, params = db.calls[0]
    assert params == ("orion", "resumed")


def test_list_by_callsign_rejects_invalid_status():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    with pytest.raises(PausedTasksStoreError, match="status"):
        store.list_by_callsign("orion", status="_bogus")


# ---- list_pending_for_target() --------------------------------------------


def test_list_pending_for_target_filters_active_only():
    db = _FakeDB()
    db.queue_fetchall(
        [
            _row_tuple(decision_target="elliot", task_ref="x1"),
            _row_tuple(decision_target="elliot", task_ref="x2"),
        ]
    )
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    rows = store.list_pending_for_target("elliot")
    assert len(rows) == 2
    query, params = db.calls[0]
    assert "decision_target = %s AND status = 'active'" in query
    assert params == ("elliot",)


def test_list_pending_for_target_validates_empty():
    db = _FakeDB()
    store = PausedTasksStore(db=db, now_provider=_fixed_now)
    with pytest.raises(PausedTasksStoreError, match="decision_target"):
        store.list_pending_for_target("")


# ---- dead_letter_payload() helper -----------------------------------------


def test_dead_letter_payload_serializes_for_inbox_dump():
    rows = [
        PausedTaskRow(
            task_ref="Agency_OS-stale-1",
            callsign="orion",
            decision_target="elliot",
            question="should we ship?",
            state_snapshot={"step": 3},
            status="expired",
            created_at=_fixed_now() - timedelta(days=8),
            expires_at=_fixed_now() - timedelta(days=1),
            expired_at=_fixed_now(),
        )
    ]
    payload = dead_letter_payload(rows)
    assert len(payload) == 1
    assert payload[0]["task_ref"] == "Agency_OS-stale-1"
    assert payload[0]["state_snapshot"] == {"step": 3}
    # All timestamps serialized as ISO format strings
    assert isinstance(payload[0]["created_at"], str)
    assert isinstance(payload[0]["expired_at"], str)
    assert "T" in payload[0]["created_at"]  # ISO format check


def test_dead_letter_payload_handles_empty():
    assert dead_letter_payload([]) == []


def test_dead_letter_payload_handles_resumed_at_none():
    """Expired rows never had resumed_at — should serialize cleanly."""
    rows = [
        PausedTaskRow(
            task_ref="x",
            callsign="orion",
            decision_target="elliot",
            question="q",
            state_snapshot={},
            status="expired",
            created_at=_fixed_now(),
            expires_at=_fixed_now() + timedelta(days=7),
            expired_at=_fixed_now(),
            resumed_at=None,
        )
    ]
    payload = dead_letter_payload(rows)
    # No KeyError on resumed_at; just absent from payload (not required)
    assert "task_ref" in payload[0]
