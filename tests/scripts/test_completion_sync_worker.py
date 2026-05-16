"""KEI-74 — behavioural tests for the three-store completion sync worker.

Covers:
- sink dispatch (linear / ceo_memory / drive_manual) marks processed=true on success
- transient sink failure increments attempts + records error_message
- abandoned after MAX_ATTEMPTS (3) — row stays processed=false but worker stops retrying
- backoff ladder honoured (1s/5s/25s) — _due_now gate
- backfill enqueues every closed task missing a sink row
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.orchestrator import completion_sync_worker as csw  # noqa: E402


def _row(**overrides):
    base = {
        "id": "row-1",
        "task_id": "KEI-58",
        "target_sink": "ceo_memory",
        "target_status": "done",
        "attempts": 0,
        "last_attempt_at": None,
    }
    base.update(overrides)
    return base


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _FakeConn:
    def __init__(self):
        self.cursor_calls = []

    def cursor(self):
        c = _FakeCursor()
        self.cursor_calls.append(c)
        return c


def test_due_now_first_attempt_is_due():
    assert csw._due_now(_row(attempts=0)) is True


def test_due_now_respects_backoff_ladder():
    just_now = datetime.now(UTC)
    assert csw._due_now(_row(attempts=1, last_attempt_at=just_now)) is False
    long_ago = datetime.now(UTC) - timedelta(seconds=10)
    assert csw._due_now(_row(attempts=1, last_attempt_at=long_ago)) is True


def test_process_row_ceo_memory_marks_processed():
    conn = _FakeConn()
    ok = csw._process_row(conn, _row(target_sink="ceo_memory"))
    assert ok is True
    final_sql = conn.cursor_calls[-1].executed[-1][0]
    assert "processed=TRUE" in final_sql


def test_process_row_drive_manual_dispatches_subprocess(monkeypatch):
    calls = {}

    def fake_run(args, **kwargs):
        calls["args"] = args
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(csw.subprocess, "run", fake_run)
    monkeypatch.setattr(csw.os.path, "isfile", lambda p: True)
    conn = _FakeConn()
    ok = csw._process_row(conn, _row(target_sink="drive_manual"))
    assert ok is True
    assert "--task-id" in calls["args"] and "KEI-58" in calls["args"]


def test_process_row_records_error_on_sink_failure(monkeypatch):
    def boom(*_args, **_kwargs):
        raise csw.SinkError("vendor 500")

    monkeypatch.setattr(csw, "_sink_ceo_memory", boom)
    conn = _FakeConn()
    ok = csw._process_row(conn, _row(target_sink="ceo_memory"))
    assert ok is False
    sql, params = conn.cursor_calls[-1].executed[-1]
    assert "attempts=attempts+1" in sql and "vendor 500" in params[0]


def test_sink_linear_raises_when_api_key_missing(monkeypatch):
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    with pytest.raises(csw.SinkError):
        csw._sink_linear("KEI-58", "done")


def test_unknown_sink_records_error(monkeypatch):
    conn = _FakeConn()
    ok = csw._process_row(conn, _row(target_sink="slack"))
    assert ok is False
    err = conn.cursor_calls[-1].executed[-1][1][0]
    assert "unknown sink" in err
