"""Tests for keiracom_paused_tasks accessor (PausedTaskStore).

Covers tenant-prefix-guard discipline, all five accessor methods (insert,
find by task_ref, find paused by callsign, resolve, abort, expire_old),
input-validation guards, and TTL semantics. Uses a fake DB cursor + spy
list so tests don't need a real Postgres.

bd: Agency_OS-70hb
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.keiracom_system.paused_tasks import (
    PausedTaskRecord,
    PausedTaskStore,
    PausedTaskStoreError,
)
from src.keiracom_system.paused_tasks.store import DEFAULT_TTL_DAYS

TENANT = "00000000-0000-0000-0000-000000000001"
NOW = datetime(2026, 5, 26, 12, 0, 0, tzinfo=UTC)


class _FakeCursor:
    def __init__(self, fetch_one=None, fetch_all=None, rowcount: int = 0) -> None:
        self._fetch_one = fetch_one
        self._fetch_all = fetch_all or []
        self.rowcount = rowcount
        self.executed: list[tuple[str, tuple | dict | None]] = []

    def execute(self, sql: str, params: tuple | dict | None = None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._fetch_one

    def fetchall(self):
        return self._fetch_all


class _FakeDB:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commit_count = 0

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.commit_count += 1


def _store(cur: _FakeCursor, *, tenant_id: str = TENANT) -> PausedTaskStore:
    return PausedTaskStore(db=_FakeDB(cur), tenant_id=tenant_id)


def _row(**overrides) -> tuple:
    base = {
        "paused_task_id": "11111111-1111-1111-1111-111111111111",
        "tenant_id": TENANT,
        "callsign": "atlas",
        "task_ref": "Agency_OS-xxxx",
        "question": "what should I do?",
        "state_snapshot": {"step": 2, "artifact": "/tmp/x"},
        "paused_at": NOW,
        "expires_at": NOW + timedelta(days=7),
        "status": "paused",
        "resolved_at": None,
        "decision_response_ref": None,
    }
    base.update(overrides)
    return tuple(
        base[k]
        for k in (
            "paused_task_id",
            "tenant_id",
            "callsign",
            "task_ref",
            "question",
            "state_snapshot",
            "paused_at",
            "expires_at",
            "status",
            "resolved_at",
            "decision_response_ref",
        )
    )


# ---------- init guard ----------


def test_init_rejects_empty_tenant_id():
    with pytest.raises(PausedTaskStoreError) as exc:
        PausedTaskStore(db=_FakeDB(_FakeCursor()), tenant_id="")
    assert "tenant_id required" in str(exc.value)


def test_init_exposes_tenant_id_property():
    store = _store(_FakeCursor())
    assert store.tenant_id == TENANT


# ---------- insert_paused ----------


def test_insert_paused_returns_id_and_binds_tenant_callsign_task_ref():
    cur = _FakeCursor(fetch_one=("aa-bb-cc",))
    store = _store(cur)
    pid = store.insert_paused(
        callsign="atlas",
        task_ref="Agency_OS-70hb",
        question="proceed?",
        state_snapshot={"step": 1},
        now=NOW,
    )
    assert pid == "aa-bb-cc"
    sql, params = cur.executed[0]
    assert "INSERT INTO public.keiracom_paused_tasks" in sql
    assert params[0] == TENANT
    assert params[1] == "atlas"
    assert params[2] == "Agency_OS-70hb"
    assert params[3] == "proceed?"


def test_insert_paused_applies_default_ttl_seven_days():
    cur = _FakeCursor(fetch_one=("aa",))
    store = _store(cur)
    store.insert_paused(
        callsign="atlas",
        task_ref="t",
        question="q",
        now=NOW,
    )
    _, params = cur.executed[0]
    paused_at = params[5]
    expires_at = params[6]
    assert (expires_at - paused_at).days == DEFAULT_TTL_DAYS


def test_insert_paused_respects_custom_ttl_days():
    cur = _FakeCursor(fetch_one=("aa",))
    store = _store(cur)
    store.insert_paused(
        callsign="atlas",
        task_ref="t",
        question="q",
        ttl_days=3,
        now=NOW,
    )
    _, params = cur.executed[0]
    assert (params[6] - params[5]).days == 3


def test_insert_paused_rejects_zero_or_negative_ttl():
    store = _store(_FakeCursor(fetch_one=("x",)))
    for bad in (0, -1):
        with pytest.raises(PausedTaskStoreError):
            store.insert_paused(
                callsign="atlas",
                task_ref="t",
                question="q",
                ttl_days=bad,
            )


def test_insert_paused_rejects_missing_required_fields():
    store = _store(_FakeCursor(fetch_one=("x",)))
    with pytest.raises(PausedTaskStoreError):
        store.insert_paused(callsign="", task_ref="t", question="q")
    with pytest.raises(PausedTaskStoreError):
        store.insert_paused(callsign="atlas", task_ref="", question="q")
    with pytest.raises(PausedTaskStoreError):
        store.insert_paused(callsign="atlas", task_ref="t", question="")


def test_insert_paused_defaults_snapshot_to_empty_dict():
    cur = _FakeCursor(fetch_one=("aa",))
    store = _store(cur)
    store.insert_paused(callsign="atlas", task_ref="t", question="q")
    _, params = cur.executed[0]
    assert params[4] == {}


# ---------- find_by_task_ref ----------


def test_find_by_task_ref_returns_record_when_present():
    cur = _FakeCursor(fetch_one=_row(task_ref="Agency_OS-yy"))
    store = _store(cur)
    rec = store.find_by_task_ref("Agency_OS-yy")
    assert isinstance(rec, PausedTaskRecord)
    assert rec.task_ref == "Agency_OS-yy"
    assert rec.tenant_id == TENANT
    sql, params = cur.executed[0]
    assert "WHERE tenant_id = %s AND task_ref = %s" in sql
    assert params == (TENANT, "Agency_OS-yy")


def test_find_by_task_ref_returns_none_when_absent():
    cur = _FakeCursor(fetch_one=None)
    store = _store(cur)
    assert store.find_by_task_ref("not-here") is None


# ---------- find_paused_by_callsign ----------


def test_find_paused_by_callsign_filters_by_tenant_and_callsign():
    cur = _FakeCursor(fetch_all=[_row(callsign="atlas"), _row(callsign="atlas", task_ref="t2")])
    store = _store(cur)
    rows = store.find_paused_by_callsign("atlas")
    assert len(rows) == 2
    assert all(r.callsign == "atlas" for r in rows)
    sql, params = cur.executed[0]
    assert "AND status = 'paused'" in sql
    assert params == (TENANT, "atlas")


def test_find_paused_by_callsign_returns_empty_list_when_no_rows():
    cur = _FakeCursor(fetch_all=[])
    assert _store(cur).find_paused_by_callsign("atlas") == []


# ---------- resolve ----------


def test_resolve_returns_true_when_row_updated():
    cur = _FakeCursor(rowcount=1)
    store = _store(cur)
    result = store.resolve(task_ref="t", decision_response_ref="env-123")
    assert result is True
    sql, params = cur.executed[0]
    assert "SET status = 'resolved'" in sql
    assert "AND status = 'paused'" in sql
    assert params == ("env-123", TENANT, "t")


def test_resolve_returns_false_when_no_row():
    cur = _FakeCursor(rowcount=0)
    assert _store(cur).resolve(task_ref="t", decision_response_ref="env") is False


# ---------- abort ----------


def test_abort_returns_true_when_row_updated():
    cur = _FakeCursor(rowcount=1)
    assert _store(cur).abort(task_ref="t") is True


def test_abort_returns_false_when_no_row():
    cur = _FakeCursor(rowcount=0)
    assert _store(cur).abort(task_ref="t") is False


def test_abort_query_binds_tenant_and_task_ref():
    cur = _FakeCursor(rowcount=1)
    _store(cur).abort(task_ref="t")
    sql, params = cur.executed[0]
    assert "SET status = 'aborted'" in sql
    assert params == (TENANT, "t")


# ---------- expire_old ----------


def test_expire_old_returns_row_count():
    cur = _FakeCursor(rowcount=3)
    assert _store(cur).expire_old(now=NOW) == 3


def test_expire_old_binds_tenant_and_now():
    cur = _FakeCursor(rowcount=0)
    _store(cur).expire_old(now=NOW)
    sql, params = cur.executed[0]
    assert "SET status = 'expired'" in sql
    assert "AND expires_at <= %s" in sql
    assert params == (TENANT, NOW)


# ---------- tenant isolation locked across all methods ----------


def test_every_query_binds_self_tenant_id():
    """Iterates the accessor methods + asserts the tenant_id constant appears
    in every emitted query's params. Catches a future regression that forgets
    the WHERE tenant_id = %s clause on any method.

    Each accessor method gets its OWN cursor so fetch shapes don't collide
    (insert returns 1-tuple, find_by_task_ref expects a full 11-tuple row).
    """
    # insert
    cur_insert = _FakeCursor(fetch_one=("xx",))
    PausedTaskStore(db=_FakeDB(cur_insert), tenant_id=TENANT).insert_paused(
        callsign="atlas",
        task_ref="t",
        question="q",
        now=NOW,
    )
    # find_by_task_ref (needs full row tuple)
    cur_find = _FakeCursor(fetch_one=_row())
    PausedTaskStore(db=_FakeDB(cur_find), tenant_id=TENANT).find_by_task_ref("t")
    # find_paused_by_callsign
    cur_callsign = _FakeCursor(fetch_all=[])
    PausedTaskStore(db=_FakeDB(cur_callsign), tenant_id=TENANT).find_paused_by_callsign("atlas")
    # resolve
    cur_resolve = _FakeCursor(rowcount=0)
    PausedTaskStore(db=_FakeDB(cur_resolve), tenant_id=TENANT).resolve(
        task_ref="t",
        decision_response_ref="env",
    )
    # abort
    cur_abort = _FakeCursor(rowcount=0)
    PausedTaskStore(db=_FakeDB(cur_abort), tenant_id=TENANT).abort(task_ref="t")
    # expire_old
    cur_expire = _FakeCursor(rowcount=0)
    PausedTaskStore(db=_FakeDB(cur_expire), tenant_id=TENANT).expire_old(now=NOW)

    for cur in (cur_insert, cur_find, cur_callsign, cur_resolve, cur_abort, cur_expire):
        for _, params in cur.executed:
            assert TENANT in params, f"tenant_id missing from params: {params}"
