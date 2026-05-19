"""KEI-228 — tests for the sync_events emit path in the Linear webhook.

Covers:
  - _emit_sync_event_linear inserts via fn_emit_sync_event with right args
  - op→event_type mapping (create / status / status+done / remove)
  - fail-open: psycopg.connect failure does not raise
  - skipped when DATABASE_URL absent
  - skipped when event lacks op or identifier
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from src.api.webhooks import linear as linear_webhook  # noqa: E402


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[Any, ...]]] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params or ()))


class _FakeConn:
    def __init__(self, raise_on_connect: bool = False) -> None:
        self._cur = _FakeCursor()
        self.committed = False

    def __enter__(self) -> _FakeConn:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cur

    def commit(self) -> None:
        self.committed = True


@pytest.fixture
def fake_psycopg(monkeypatch):
    """Install a fake psycopg module on the linear module's import path."""
    conn = _FakeConn()
    fake = MagicMock()
    fake.connect = MagicMock(return_value=conn)
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    return conn


@pytest.fixture(autouse=True)
def _dsn_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")


def test_emit_calls_fn_emit_sync_event_with_origin_linear(fake_psycopg) -> None:
    event = {"op": "create", "identifier": "KEI-501", "title": "x", "priority": 2, "url": "u"}
    linear_webhook._emit_sync_event_linear(event)
    assert fake_psycopg.committed is True
    calls = fake_psycopg._cur.executed
    assert len(calls) == 1
    sql, params = calls[0]
    assert "fn_emit_sync_event" in sql
    # params = (origin, event_type, task_id, bd_id, payload_json)
    assert params[0] == "linear"
    assert params[1] == "create"
    assert params[2] == "KEI-501"
    assert params[3] is None  # bd_id unknown at webhook time


def test_op_status_with_task_status_done_maps_to_close(fake_psycopg) -> None:
    event = {"op": "status", "identifier": "KEI-502", "task_status": "done"}
    linear_webhook._emit_sync_event_linear(event)
    _, params = fake_psycopg._cur.executed[0]
    assert params[1] == "close"


def test_op_status_without_done_maps_to_update(fake_psycopg) -> None:
    event = {"op": "status", "identifier": "KEI-503", "task_status": "active"}
    linear_webhook._emit_sync_event_linear(event)
    _, params = fake_psycopg._cur.executed[0]
    assert params[1] == "update"


def test_op_remove_maps_to_close(fake_psycopg) -> None:
    event = {"op": "remove", "identifier": "KEI-504"}
    linear_webhook._emit_sync_event_linear(event)
    _, params = fake_psycopg._cur.executed[0]
    assert params[1] == "close"


def test_op_unknown_falls_back_to_update(fake_psycopg) -> None:
    event = {"op": "weird", "identifier": "KEI-505"}
    linear_webhook._emit_sync_event_linear(event)
    _, params = fake_psycopg._cur.executed[0]
    assert params[1] == "update"


def test_missing_op_skips_emit(fake_psycopg) -> None:
    linear_webhook._emit_sync_event_linear({"identifier": "KEI-506"})
    assert fake_psycopg._cur.executed == []


def test_missing_identifier_skips_emit(fake_psycopg) -> None:
    linear_webhook._emit_sync_event_linear({"op": "create"})
    assert fake_psycopg._cur.executed == []


def test_missing_dsn_skips_emit(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    # No fake_psycopg fixture — verify no import attempt either.
    linear_webhook._emit_sync_event_linear({"op": "create", "identifier": "KEI-507"})
    # Function returns silently; we just verify no raise.


def test_psycopg_connect_failure_is_fail_open(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    fake = MagicMock()
    fake.connect.side_effect = OSError("connection refused")
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    # Must not raise.
    linear_webhook._emit_sync_event_linear({"op": "create", "identifier": "KEI-508"})


def test_payload_is_serialised_as_json_string(fake_psycopg) -> None:
    event = {"op": "create", "identifier": "KEI-509", "title": "ž — non-ascii"}
    linear_webhook._emit_sync_event_linear(event)
    _, params = fake_psycopg._cur.executed[0]
    # payload (params[4]) must be a JSON string (so psycopg's %s::jsonb cast works).
    assert isinstance(params[4], str)
    import json as _json

    assert _json.loads(params[4])["identifier"] == "KEI-509"
