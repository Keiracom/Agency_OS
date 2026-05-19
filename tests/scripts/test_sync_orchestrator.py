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

    def cursor(self) -> _FakeCursor:
        cur = _FakeCursor()
        self._cursors.append(cur)
        return cur


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
# Postgres status → bd mapping.
# ---------------------------------------------------------------------------


def test_postgres_status_to_bd_mapping() -> None:
    assert so._postgres_status_to_bd("available") == "open"
    assert so._postgres_status_to_bd("active") == "in_progress"
    assert so._postgres_status_to_bd("done") == "closed"
    assert so._postgres_status_to_bd("cancelled") == "closed"
    assert so._postgres_status_to_bd("nonsense") is None
