"""Unit tests for src/relay/paused_tasks.py.

Covers PausedTasksStore: insert_from_envelope (positive + negative paths,
idempotency, ON CONFLICT semantics), get_by_task_ref (hit + miss), delete
(idempotent), mark_state, iter_expired.

bd: Agency_OS-tjni
"""

from __future__ import annotations

from typing import Any

import pytest

from src.relay.paused_tasks import (
    DEFAULT_TTL_SECONDS,
    STATE_DEAD_LETTERED,
    STATE_PENDING,
    STATE_RESUMED,
    PausedTask,
    PausedTasksStore,
    PausedTasksStoreError,
    _row_to_paused_task,
)


class _FakeDB:
    """Minimal _DBProtocol implementation with scripted fetch responses."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, tuple[Any, ...]]] = []
        self._next_one: Any = None
        self._next_all: list[Any] = []
        self._script: list[tuple[Any, list[Any]]] = []

    def script(self, one: Any, all_: list[Any]) -> None:
        self._script.append((one, all_))

    def execute(self, query: str, *params: Any) -> Any:
        self.queries.append((query, params))
        if self._script:
            self._next_one, self._next_all = self._script.pop(0)
        return self

    def fetchone(self) -> Any:
        return self._next_one

    def fetchall(self) -> Any:
        return self._next_all


_GOOD_ENVELOPE = {
    "id": "paused_1",
    "type": "paused_pending_decision",
    "from": "nova",
    "task_ref": "review-pr-N",
    "paused_at": 1748252600,
    "interim_state": {"notes": "waiting on Elliot"},
}


# ─── insert_from_envelope ──────────────────────────────────────────────────────


def test_insert_from_envelope_writes_with_default_ttl():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    store.insert_from_envelope(_GOOD_ENVELOPE, callsign="nova")
    assert len(db.queries) == 1
    query, params = db.queries[0]
    assert "INSERT INTO public.keiracom_paused_tasks" in query
    assert "ON CONFLICT (task_ref) DO UPDATE" in query
    # task_ref, callsign, paused_at, deadline_at = paused_at + 7d
    assert params[0] == "review-pr-N"
    assert params[1] == "nova"
    assert params[2] == 1748252600
    assert params[3] == 1748252600 + DEFAULT_TTL_SECONDS


def test_insert_from_envelope_respects_ttl_override():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    store.insert_from_envelope(_GOOD_ENVELOPE, callsign="nova", ttl_seconds=3600)
    _, params = db.queries[0]
    assert params[3] == 1748252600 + 3600


def test_insert_from_envelope_raises_on_missing_required_fields():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    with pytest.raises(PausedTasksStoreError, match="missing required fields"):
        store.insert_from_envelope(
            {"id": "x", "type": "paused_pending_decision", "from": "nova"},
            callsign="nova",
        )


def test_insert_from_envelope_raises_on_empty_callsign():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    with pytest.raises(PausedTasksStoreError, match="callsign is required"):
        store.insert_from_envelope(_GOOD_ENVELOPE, callsign="")


def test_insert_from_envelope_carries_optional_question_and_options():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    envelope = {
        **_GOOD_ENVELOPE,
        "question": "push or override?",
        "options": ["push", "override"],
    }
    store.insert_from_envelope(envelope, callsign="nova")
    _, params = db.queries[0]
    assert params[5] == "push or override?"  # question
    assert params[6] == ["push", "override"]  # options


def test_insert_from_envelope_handles_missing_optional_fields():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    store.insert_from_envelope(_GOOD_ENVELOPE, callsign="nova")
    _, params = db.queries[0]
    assert params[5] is None  # question absent
    assert params[6] is None  # options absent


# ─── get_by_task_ref ───────────────────────────────────────────────────────────


def test_get_by_task_ref_returns_paused_task_on_hit():
    db = _FakeDB()
    db.script(
        (
            "review-pr-N",  # task_ref
            "nova",  # callsign
            1748252600,  # paused_at
            1748857400,  # deadline_at
            {"notes": "x"},  # interim_state
            None,  # question
            None,  # options
            "pending",  # state
        ),
        [],
    )
    store = PausedTasksStore(db=db)
    row = store.get_by_task_ref("review-pr-N")
    assert isinstance(row, PausedTask)
    assert row.task_ref == "review-pr-N"
    assert row.callsign == "nova"
    assert row.paused_at == 1748252600
    assert row.state == STATE_PENDING


def test_get_by_task_ref_returns_none_on_miss():
    db = _FakeDB()
    db.script(None, [])  # fetchone returns None
    store = PausedTasksStore(db=db)
    assert store.get_by_task_ref("ghost") is None


# ─── delete ────────────────────────────────────────────────────────────────────


def test_delete_executes_idempotent_query():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    store.delete("review-pr-N")
    query, params = db.queries[0]
    assert "DELETE FROM public.keiracom_paused_tasks" in query
    assert params == ("review-pr-N",)


def test_delete_missing_row_does_not_raise():
    """The DELETE WHERE task_ref = X is idempotent at the SQL level — fake DB
    doesn't simulate the missing-row case (no rowcount semantics needed)."""
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    # Should not raise even without scripting a response.
    store.delete("never-existed")


# ─── mark_state ────────────────────────────────────────────────────────────────


def test_mark_state_accepts_known_states():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    for state in (STATE_PENDING, STATE_RESUMED, STATE_DEAD_LETTERED):
        store.mark_state("review-pr-N", state)
    assert len(db.queries) == 3


def test_mark_state_rejects_unknown_state():
    db = _FakeDB()
    store = PausedTasksStore(db=db)
    with pytest.raises(PausedTasksStoreError, match="unknown state"):
        store.mark_state("review-pr-N", "bogus")


# ─── iter_expired ──────────────────────────────────────────────────────────────


def test_iter_expired_yields_paused_task_rows():
    db = _FakeDB()
    db.script(
        None,
        [
            (
                "task_a",
                "nova",
                1748000000,
                1748000300,  # already expired
                {"notes": "a"},
                None,
                None,
                "pending",
            ),
            (
                "task_b",
                "atlas",
                1748000100,
                1748000400,
                {},
                "q?",
                ["yes", "no"],
                "pending",
            ),
        ],
    )
    store = PausedTasksStore(db=db)
    rows = list(store.iter_expired(now=1748252600))
    assert len(rows) == 2
    assert {r.task_ref for r in rows} == {"task_a", "task_b"}
    assert all(r.state == STATE_PENDING for r in rows)
    # The query is parameterised on now; verify it landed correctly.
    query, params = db.queries[0]
    assert "WHERE state = 'pending'" in query
    assert params == (1748252600,)


def test_iter_expired_empty_yields_nothing():
    db = _FakeDB()
    db.script(None, [])
    store = PausedTasksStore(db=db)
    assert list(store.iter_expired(now=1748252600)) == []


# ─── _row_to_paused_task ───────────────────────────────────────────────────────


def test_row_to_paused_task_normalises_null_interim_state_to_empty_dict():
    row = ("t", "c", 1, 2, None, None, None, "pending")
    task = _row_to_paused_task(row)
    assert task.interim_state == {}
