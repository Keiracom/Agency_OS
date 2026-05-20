"""Tests for KEI-54B tool_call_log_indexer."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "tool_call_log_indexer.py"
# tool_call_log_indexer imports `_heartbeat_shim` (a sibling in
# scripts/orchestrator/) — that dir must be on sys.path or collection fails.
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))

_spec = importlib.util.spec_from_file_location("tool_call_log_indexer", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["tool_call_log_indexer"] = _mod
_spec.loader.exec_module(_mod)


def test_connect_kwargs_pooler_safe() -> None:
    """Regression lock (Agency_OS-telw): the indexer's psycopg connection MUST
    set connect_timeout + TCP keepalives so a stalled / black-holed Supabase
    connection fails fast instead of hanging forever in poll() — the failure
    mode that froze this indexer for 3 days with no error. prepare_threshold
    stays None for the txn-mode pooler."""
    kw = _mod._CONNECT_KWARGS
    assert kw["prepare_threshold"] is None
    assert kw["connect_timeout"] > 0
    assert kw["keepalives"] == 1
    assert kw["keepalives_idle"] > 0 and kw["keepalives_count"] > 0


def _row(**overrides):
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "callsign": "max",
        "session_uuid": "22222222-2222-2222-2222-222222222222",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_output_excerpt": "file1.txt",
        "started_at": "2026-05-14T08:00:00+00:00",
        "duration_ms": 42,
        "exit_code": 0,
    }
    base.update(overrides)
    return _mod.ToolCallRow(**base)


def test_build_weaviate_doc_uses_row_id_as_object_id():
    row = _row()
    doc = _mod.build_weaviate_doc(row)
    assert doc["id"] == row.id
    assert doc["class"] == _mod.TOOL_CALLS_CLASS


def test_build_weaviate_doc_serializes_tool_input_jsonb_to_text():
    row = _row(tool_input={"k": "v", "nested": [1, 2]})
    doc = _mod.build_weaviate_doc(row)
    assert json.loads(doc["properties"]["tool_input"]) == {"k": "v", "nested": [1, 2]}


def test_build_weaviate_doc_handles_null_optional_fields():
    row = _row(session_uuid=None, tool_output_excerpt=None, duration_ms=None, exit_code=None)
    doc = _mod.build_weaviate_doc(row)
    assert doc["properties"]["session_uuid"] == ""
    assert doc["properties"]["tool_output_excerpt"] == ""
    assert doc["properties"]["duration_ms"] == 0
    assert doc["properties"]["exit_code"] == -1


def test_index_row_returns_true_on_201():
    row = _row()
    fake_resp = mock.MagicMock(status=201)
    fake_resp.__enter__.return_value = fake_resp
    with mock.patch.object(_mod, "_http_request", return_value=fake_resp):
        assert _mod.index_row(row) is True


def test_index_row_treats_422_as_idempotent_success():
    from urllib import error as urlerror

    row = _row()
    err = urlerror.HTTPError(url="x", code=422, msg="exists", hdrs=None, fp=None)
    with mock.patch.object(_mod, "_http_request", side_effect=err):
        assert _mod.index_row(row) is True


def test_index_row_retries_then_fails_on_persistent_transient_error():
    from urllib import error as urlerror

    row = _row()
    err = urlerror.URLError("connection refused")
    with (
        mock.patch.object(_mod, "_http_request", side_effect=err),
        mock.patch.object(_mod.time, "sleep") as sleep,
    ):
        result = _mod.index_row(row)
    assert result is False
    assert sleep.call_count == _mod.MAX_RETRIES - 1


def test_index_row_succeeds_after_one_transient_failure():
    from urllib import error as urlerror

    row = _row()
    err = urlerror.URLError("transient")
    fake_resp = mock.MagicMock(status=200)
    fake_resp.__enter__.return_value = fake_resp
    with (
        mock.patch.object(_mod, "_http_request", side_effect=[err, fake_resp]),
        mock.patch.object(_mod.time, "sleep"),
    ):
        assert _mod.index_row(row) is True


def test_index_row_retries_use_exponential_backoff():
    from urllib import error as urlerror

    row = _row()
    err = urlerror.URLError("oops")
    with (
        mock.patch.object(_mod, "_http_request", side_effect=err),
        mock.patch.object(_mod.time, "sleep") as sleep,
    ):
        _mod.index_row(row)
    sleeps = [c.args[0] for c in sleep.call_args_list]
    assert sleeps[1] > sleeps[0], f"expected exp backoff growth: {sleeps}"


def test_ensure_class_exists_no_op_when_present():
    fake_resp = mock.MagicMock(status=200)
    fake_resp.__enter__.return_value = fake_resp
    with mock.patch.object(_mod, "_http_request", return_value=fake_resp) as http:
        _mod.ensure_tool_calls_class_exists()
    # Only GET, no POST.
    assert http.call_count == 1
    assert http.call_args.args[0] == "GET"


def test_ensure_class_exists_creates_when_404():
    from urllib import error as urlerror

    err = urlerror.HTTPError(url="x", code=404, msg="not found", hdrs=None, fp=None)
    fake_resp = mock.MagicMock(status=200)
    fake_resp.__enter__.return_value = fake_resp
    with mock.patch.object(_mod, "_http_request", side_effect=[err, fake_resp]) as http:
        _mod.ensure_tool_calls_class_exists()
    # GET then POST.
    assert http.call_count == 2
    assert http.call_args_list[0].args[0] == "GET"
    assert http.call_args_list[1].args[0] == "POST"


def test_process_batch_marks_indexed_on_success():
    row = _row()
    fake_cur = mock.MagicMock()
    fake_cur.fetchall.return_value = [
        (
            row.id,
            row.callsign,
            row.session_uuid,
            row.tool_name,
            row.tool_input,
            row.tool_output_excerpt,
            mock.MagicMock(isoformat=lambda: row.started_at),
            row.duration_ms,
            row.exit_code,
        )
    ]
    fake_conn = mock.MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cur
    fake_resp = mock.MagicMock(status=200)
    fake_resp.__enter__.return_value = fake_resp
    with mock.patch.object(_mod, "_http_request", return_value=fake_resp):
        outcome = _mod.process_batch(fake_conn, batch_size=10)
    assert outcome == {"claimed": 1, "done": 1, "failed": 0}
    # UPDATE indexed=true was called.
    update_calls = [
        c
        for c in fake_cur.execute.call_args_list
        if "UPDATE public.tool_call_log SET indexed" in c.args[0]
    ]
    assert len(update_calls) == 1


def test_process_batch_empty_skips_audit_write():
    fake_cur = mock.MagicMock()
    fake_cur.fetchall.return_value = []
    fake_conn = mock.MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = fake_cur
    outcome = _mod.process_batch(fake_conn, batch_size=10)
    assert outcome == {"claimed": 0, "done": 0, "failed": 0}
    # No audit_logs INSERT when batch is empty.
    audit_calls = [
        c for c in fake_cur.execute.call_args_list if "INSERT INTO public.audit_logs" in c.args[0]
    ]
    assert audit_calls == []


def test_dsn_missing_raises():
    with (
        mock.patch.dict(_mod.os.environ, {}, clear=True),
        pytest.raises(_mod.IndexerError, match="DATABASE_URL"),
    ):
        _mod._dsn()


def test_dsn_prefers_database_url_over_supabase_db_url():
    with mock.patch.dict(
        _mod.os.environ,
        {"DATABASE_URL": "first", "SUPABASE_DB_URL": "second"},
        clear=True,
    ):
        assert _mod._dsn() == "first"


def test_dsn_strips_sqlalchemy_driver_tag():
    """psycopg can't parse postgresql+asyncpg:// — strip the driver tag."""
    with mock.patch.dict(
        _mod.os.environ,
        {"DATABASE_URL": "postgresql+asyncpg://u:p@h:5432/db"},
        clear=True,
    ):
        assert _mod._dsn() == "postgresql://u:p@h:5432/db"


def test_main_once_flag_passes_max_iterations_1():
    with mock.patch.object(_mod, "run", return_value=0) as run:
        _mod.main(["--once"])
    assert run.call_args.kwargs["max_iterations"] == 1
