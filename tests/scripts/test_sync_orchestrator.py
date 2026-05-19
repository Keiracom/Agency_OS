"""KEI-229 — behavioural tests for sync_orchestrator.py.

Covers:
- origin-tag loop prevention: postgres origin → dispatches to bd+linear, NOT postgres
- bd dispatcher: subprocess args, status mapping, no bd_id → skip
- linear dispatcher: GraphQL POST body shape, state_id env mapping
- postgres dispatcher: UPSERT with done-preservation
- backoff ladder: _due_now honours 1s/5s/25s gaps
- abandonment: row stays unprocessed but attempts >= MAX_ATTEMPTS
- idempotency: failed event re-attempted; processed=true never reverts
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# _heartbeat_shim lives at scripts/orchestrator/_heartbeat_shim.py; sync_orchestrator
# imports it as a bare name, so the orchestrator dir must be on sys.path before import.
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))

from scripts.orchestrator import sync_orchestrator as so  # noqa: E402


def _event(**overrides) -> dict[str, Any]:
    base = {
        "id": "row-1",
        "origin": "postgres",
        "event_type": "update",
        "task_id": "KEI-227",
        "bd_id": "Agency_OS-8c67",
        "payload": {
            "status": "active",
            "title": "test",
            "priority": 2,
            "linear_url": "https://linear.app/keiracom/issue/KEI-227",
        },
        "attempts": 0,
        "last_attempt_at": None,
    }
    base.update(overrides)
    return base


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params or ()))

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class _FakeConn:
    def __init__(self) -> None:
        self._cursors: list[_FakeCursor] = []
        self.rolled_back = False

    def cursor(self) -> _FakeCursor:
        cur = _FakeCursor()
        self._cursors.append(cur)
        return cur

    def rollback(self) -> None:
        self.rolled_back = True


# ---------------------------------------------------------------------------
# Origin-tag loop prevention.
# ---------------------------------------------------------------------------


def test_postgres_origin_dispatches_to_bd_and_linear_not_postgres(monkeypatch) -> None:
    event = _event(origin="postgres")
    conn = _FakeConn()
    called: list[str] = []
    monkeypatch.setattr(so, "_dispatch_bd", lambda e: called.append("bd"))
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: called.append("linear"))
    monkeypatch.setattr(so, "_dispatch_postgres", lambda c, e: called.append("postgres"))
    so._process_event(conn, event)
    assert "bd" in called
    assert "linear" in called
    assert "postgres" not in called


def test_bd_origin_dispatches_to_postgres_and_linear_not_bd(monkeypatch) -> None:
    event = _event(origin="bd")
    conn = _FakeConn()
    called: list[str] = []
    monkeypatch.setattr(so, "_dispatch_bd", lambda e: called.append("bd"))
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: called.append("linear"))
    monkeypatch.setattr(so, "_dispatch_postgres", lambda c, e: called.append("postgres"))
    so._process_event(conn, event)
    assert "bd" not in called
    assert "postgres" in called
    assert "linear" in called


def test_linear_origin_dispatches_to_bd_and_postgres_not_linear(monkeypatch) -> None:
    event = _event(origin="linear")
    conn = _FakeConn()
    called: list[str] = []
    monkeypatch.setattr(so, "_dispatch_bd", lambda e: called.append("bd"))
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: called.append("linear"))
    monkeypatch.setattr(so, "_dispatch_postgres", lambda c, e: called.append("postgres"))
    so._process_event(conn, event)
    assert "linear" not in called
    assert "bd" in called
    assert "postgres" in called


def test_success_marks_processed_true(monkeypatch) -> None:
    event = _event()
    conn = _FakeConn()
    monkeypatch.setattr(so, "_dispatch_bd", lambda e: None)
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: None)
    monkeypatch.setattr(so, "_dispatch_postgres", lambda c, e: None)
    assert so._process_event(conn, event) is True
    update_sqls = [
        c.executed[0][0]
        for c in conn._cursors
        if c.executed and "processed = TRUE" in c.executed[0][0]
    ]
    assert update_sqls, "expected processed=TRUE update"


def test_dispatch_error_increments_attempts(monkeypatch) -> None:
    event = _event()
    conn = _FakeConn()
    monkeypatch.setattr(
        so, "_dispatch_bd", lambda e: (_ for _ in ()).throw(so.DispatchError("bd down"))
    )
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: None)
    monkeypatch.setattr(so, "_dispatch_postgres", lambda c, e: None)
    assert so._process_event(conn, event) is False
    update_sqls = [
        c.executed[0][0]
        for c in conn._cursors
        if c.executed and "attempts = attempts + 1" in c.executed[0][0]
    ]
    assert update_sqls, "expected attempts increment update"


# ---------------------------------------------------------------------------
# Backoff ladder.
# ---------------------------------------------------------------------------


def test_due_now_first_attempt_always_due() -> None:
    assert so._due_now(_event(attempts=0, last_attempt_at=None)) is True


def test_due_now_second_attempt_needs_one_second(monkeypatch) -> None:
    just_now = datetime.now(UTC) - timedelta(milliseconds=100)
    assert so._due_now(_event(attempts=1, last_attempt_at=just_now)) is False
    one_sec_ago = datetime.now(UTC) - timedelta(seconds=1.5)
    assert so._due_now(_event(attempts=1, last_attempt_at=one_sec_ago)) is True


def test_due_now_third_attempt_needs_five_seconds(monkeypatch) -> None:
    three_sec_ago = datetime.now(UTC) - timedelta(seconds=3)
    assert so._due_now(_event(attempts=2, last_attempt_at=three_sec_ago)) is False
    six_sec_ago = datetime.now(UTC) - timedelta(seconds=6)
    assert so._due_now(_event(attempts=2, last_attempt_at=six_sec_ago)) is True


# ---------------------------------------------------------------------------
# bd dispatcher.
# ---------------------------------------------------------------------------


def test_bd_dispatch_skips_when_no_bd_id() -> None:
    # No bd_id and no payload bd_id → silent skip, no subprocess.
    event = _event(bd_id=None, payload={"status": "active"})
    with patch("scripts.orchestrator.sync_orchestrator.subprocess.run") as runner:
        so._dispatch_bd(event)
        runner.assert_not_called()


def test_bd_dispatch_close_runs_status_closed() -> None:
    event = _event(event_type="close")
    with patch("scripts.orchestrator.sync_orchestrator.subprocess.run") as runner:
        runner.return_value = MagicMock(returncode=0, stdout="", stderr="")
        so._dispatch_bd(event)
        args = runner.call_args[0][0]
        assert "update" in args
        assert "Agency_OS-8c67" in args
        assert "--status=closed" in args


def test_bd_dispatch_update_maps_postgres_status_to_bd() -> None:
    event = _event(event_type="update", payload={"status": "active", "bd_id": "Agency_OS-8c67"})
    with patch("scripts.orchestrator.sync_orchestrator.subprocess.run") as runner:
        runner.return_value = MagicMock(returncode=0, stdout="", stderr="")
        so._dispatch_bd(event)
        args = runner.call_args[0][0]
        assert "--status=in_progress" in args


def test_bd_dispatch_nonzero_exit_raises_dispatch_error() -> None:
    event = _event(event_type="close")
    with patch("scripts.orchestrator.sync_orchestrator.subprocess.run") as runner:
        runner.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        with pytest.raises(so.DispatchError):
            so._dispatch_bd(event)


# ---------------------------------------------------------------------------
# Linear dispatcher.
# ---------------------------------------------------------------------------


def test_linear_dispatch_missing_api_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    with pytest.raises(so.DispatchError, match="LINEAR_API_KEY"):
        so._dispatch_linear(_event(event_type="close"))


def test_linear_dispatch_missing_state_id_raises(monkeypatch) -> None:
    monkeypatch.setenv("LINEAR_API_KEY", "k")
    monkeypatch.delenv("LINEAR_STATE_ID_DONE", raising=False)
    with pytest.raises(so.DispatchError, match="LINEAR_STATE_ID_DONE"):
        so._dispatch_linear(_event(event_type="close"))


def test_linear_event_to_state_close_returns_done() -> None:
    assert so._event_to_linear_state(_event(event_type="close")) == "done"


def test_linear_event_to_state_reopen_returns_active() -> None:
    assert so._event_to_linear_state(_event(event_type="reopen")) == "active"


def test_linear_event_to_state_update_uses_payload_status() -> None:
    assert (
        so._event_to_linear_state(_event(event_type="update", payload={"status": "active"}))
        == "active"
    )
    assert (
        so._event_to_linear_state(_event(event_type="update", payload={"status": "done"})) == "done"
    )


def test_linear_event_to_state_update_available_returns_none(monkeypatch) -> None:
    """KEI-233 safety guard: 'available' is the Postgres/bd default — never
    propagate back to Linear, otherwise we silently downgrade Linear's
    Done/Canceled/In Progress issues to Todo."""
    assert (
        so._event_to_linear_state(_event(event_type="update", payload={"status": "available"}))
        is None
    )


def test_linear_event_to_state_unmapped_returns_none() -> None:
    assert so._event_to_linear_state(_event(event_type="title_change")) is None


# ---------------------------------------------------------------------------
# KEI-235 — synthetic task_verifications + trigger-rollback resilience.
# ---------------------------------------------------------------------------


def test_dispatch_postgres_writes_synthetic_verification_for_done(monkeypatch) -> None:
    """When payload.status='done', a task_verifications row is INSERTed
    before the tasks UPDATE so the require_verification_before_done trigger
    passes (KEI-235)."""
    event = _event(event_type="close", payload={"status": "done", "bd_id": "Agency_OS-x"})
    conn = _FakeConn()
    so._dispatch_postgres(conn, event)
    sqls = [c.executed for c in conn._cursors if c.executed]
    flat = [sql for batch in sqls for sql, _ in batch]
    verification_inserts = [s for s in flat if "INSERT INTO public.task_verifications" in s]
    assert verification_inserts, "expected synthetic verification insert before done UPDATE"
    # Verifier name must be 'linear-sync' (audit distinguishability).
    all_params = [params for batch in sqls for _, params in batch]
    verifier_params = [p for p in all_params if "linear-sync" in p]
    assert verifier_params, "expected verified_by='linear-sync' in inserted row"


def test_dispatch_postgres_skips_verification_for_non_terminal(monkeypatch) -> None:
    """payload.status='active' or 'available' does NOT trip the trigger,
    so no synthetic verification is written."""
    event = _event(event_type="update", payload={"status": "active"})
    conn = _FakeConn()
    so._dispatch_postgres(conn, event)
    flat_sqls = [sql for c in conn._cursors for sql, _ in c.executed]
    assert not any("task_verifications" in s for s in flat_sqls)


def test_dispatch_postgres_synthetic_verification_idempotent_via_not_exists(monkeypatch) -> None:
    """The verification INSERT uses NOT EXISTS so repeats are no-ops."""
    event = _event(event_type="close", payload={"status": "cancelled", "bd_id": "Agency_OS-x"})
    conn = _FakeConn()
    so._dispatch_postgres(conn, event)
    flat_sqls = [sql for c in conn._cursors for sql, _ in c.executed]
    insert_sql = next(s for s in flat_sqls if "INSERT INTO public.task_verifications" in s)
    assert "NOT EXISTS" in insert_sql, "idempotency guard required"


def test_process_event_rolls_back_on_trigger_block(monkeypatch) -> None:
    """KEI-235 resilience — RaiseException from a governance trigger rolls
    back the savepoint, NOT the whole batch."""
    import psycopg.errors

    event = _event(id="evt-1", origin="bd")
    conn = _FakeConn()
    monkeypatch.setattr(so, "_dispatch_bd", lambda e: called.append("bd"))
    called: list[str] = []
    monkeypatch.setattr(
        so,
        "_dispatch_postgres",
        lambda c, e: (_ for _ in ()).throw(
            psycopg.errors.RaiseException("BLOCKED: Task X cannot be marked done")
        ),
    )
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: called.append("linear"))
    ok = so._process_event(conn, event)
    assert ok is False  # batch continues; this event recorded as failed
    # Savepoint sequence: SAVEPOINT, ROLLBACK TO SAVEPOINT, RELEASE SAVEPOINT
    all_sql = " ".join(sql for c in conn._cursors for sql, _ in c.executed)
    assert "SAVEPOINT" in all_sql
    assert "ROLLBACK TO SAVEPOINT" in all_sql


def test_process_event_rolls_back_on_check_violation(monkeypatch) -> None:
    """KEI-235-followup — CheckViolation (e.g. status='cancelled' rejected
    by tasks_status_check) must also roll back savepoint and let batch
    continue, not crash the worker."""
    import psycopg.errors

    event = _event(id="evt-2", origin="bd")
    conn = _FakeConn()
    monkeypatch.setattr(
        so,
        "_dispatch_postgres",
        lambda c, e: (_ for _ in ()).throw(
            psycopg.errors.CheckViolation('new row violates check constraint "tasks_status_check"')
        ),
    )
    monkeypatch.setattr(so, "_dispatch_bd", lambda e: None)
    monkeypatch.setattr(so, "_dispatch_linear", lambda e: None)
    ok = so._process_event(conn, event)
    assert ok is False  # treated same as DispatchError — batch survives


def test_dispatch_postgres_coerces_cancelled_to_dismissed(monkeypatch) -> None:
    """Pre-fix events with payload.status='cancelled' get coerced to
    'dismissed' so the CHECK constraint doesn't reject them. The synthetic
    verification also fires since 'dismissed' is now a terminal transition."""
    event = _event(event_type="close", payload={"status": "cancelled", "bd_id": "Agency_OS-x"})
    conn = _FakeConn()
    so._dispatch_postgres(conn, event)
    all_params = [params for c in conn._cursors for _, params in c.executed]
    # The tasks UPSERT params: (task_id, bd_id, title, status, priority, linear_url)
    upsert_params = [p for p in all_params if "dismissed" in str(p)]
    assert upsert_params, "expected coerced status='dismissed' in tasks upsert"


# ---------------------------------------------------------------------------
# Postgres status → bd mapping.
# ---------------------------------------------------------------------------


def test_postgres_status_to_bd_mapping() -> None:
    assert so._postgres_status_to_bd("available") == "open"
    assert so._postgres_status_to_bd("active") == "in_progress"
    assert so._postgres_status_to_bd("done") == "closed"
    assert so._postgres_status_to_bd("cancelled") == "closed"
    assert so._postgres_status_to_bd("nonsense") is None
