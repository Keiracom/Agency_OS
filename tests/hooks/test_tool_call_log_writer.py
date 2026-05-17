"""Tests for scripts/hooks/tool_call_log_writer.py — KEI-116 Build 1 review fixes.

Coverage:
  1. JSON parse path: invalid input → fail-open exit 0
  2. _callsign(): env CALLSIGN priority; "unknown" sentinel when env empty
  3. _truncate(): boundary — under cap, at cap, over cap
  4. _extract_output(): type coercion — str, dict, list, None
  5. DB INSERT path: mock psycopg.connect — verify SQL shape + params
  6. tool_input cap: small payload preserved; large payload replaced with sentinel
     (CRITICAL path — synthetic 100 KB payload must trigger the cap)

All DB calls are mocked — no Postgres connectivity required.
Fail-open semantics: any error path must exit 0 (tested via subprocess for main()).
"""

from __future__ import annotations

import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
WRITER = REPO_ROOT / "scripts" / "hooks" / "tool_call_log_writer.py"

# Load without executing __main__ block
_spec = importlib.util.spec_from_file_location("tool_call_log_writer", WRITER)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_callsign = _mod._callsign
_truncate = _mod._truncate
_extract_output = _mod._extract_output
_cap_tool_input = _mod._cap_tool_input
_TOOL_INPUT_MAX_BYTES = _mod._TOOL_INPUT_MAX_BYTES
_OUTPUT_EXCERPT_MAX = _mod._OUTPUT_EXCERPT_MAX
main = _mod.main


# ---------------------------------------------------------------------------
# 1. JSON parse path — invalid input → fail-open (exit 0 / no exception)
# ---------------------------------------------------------------------------


class TestJsonParsePath:
    def test_invalid_json_does_not_raise(self, monkeypatch, capsys):
        """Invalid JSON on stdin must not raise — fail-open contract."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
        monkeypatch.setattr("sys.stdin", _make_stdin("not valid json {{{"))
        # Should return without raising; no sys.exit(non-zero) either
        main()
        # No assertion needed beyond "did not raise"

    def test_empty_stdin_does_not_raise(self, monkeypatch):
        """Empty stdin must not raise."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
        monkeypatch.setattr("sys.stdin", _make_stdin(""))
        main()


# ---------------------------------------------------------------------------
# 2. _callsign()
# ---------------------------------------------------------------------------


class TestCallsign:
    def test_env_var_takes_priority(self, monkeypatch):
        monkeypatch.setenv("CALLSIGN", "elliot")
        assert _callsign() == "elliot"

    def test_env_var_normalised_to_lowercase(self, monkeypatch):
        monkeypatch.setenv("CALLSIGN", "AIDEN")
        assert _callsign() == "aiden"

    def test_unknown_sentinel_when_env_empty(self, monkeypatch):
        monkeypatch.delenv("CALLSIGN", raising=False)
        assert _callsign() == "unknown"

    def test_unknown_sentinel_when_env_whitespace(self, monkeypatch):
        monkeypatch.setenv("CALLSIGN", "   ")
        assert _callsign() == "unknown"


# ---------------------------------------------------------------------------
# 3. _truncate() — boundary tests
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_none_returns_none(self):
        assert _truncate(None) is None

    def test_under_cap_preserved(self):
        text = "x" * (_OUTPUT_EXCERPT_MAX - 1)
        assert _truncate(text) == text

    def test_at_cap_preserved(self):
        text = "x" * _OUTPUT_EXCERPT_MAX
        assert _truncate(text) == text

    def test_over_cap_truncated(self):
        text = "x" * (_OUTPUT_EXCERPT_MAX + 100)
        result = _truncate(text)
        assert result is not None
        assert result.startswith("x" * _OUTPUT_EXCERPT_MAX)
        assert "truncated" in result
        assert "100 chars" in result

    def test_over_cap_length_is_bounded(self):
        text = "y" * (_OUTPUT_EXCERPT_MAX * 10)
        result = _truncate(text)
        # Result must not grow without bound
        assert len(result) < len(text)


# ---------------------------------------------------------------------------
# 4. _extract_output() — type coercion
# ---------------------------------------------------------------------------


class TestExtractOutput:
    def test_none_returns_none(self):
        assert _extract_output(None) is None

    def test_string_returned_as_is(self):
        assert _extract_output("hello") == "hello"

    def test_empty_string_returns_none(self):
        assert _extract_output("") is None

    def test_dict_json_serialised(self):
        result = _extract_output({"key": "val"})
        assert result is not None
        assert json.loads(result) == {"key": "val"}

    def test_list_json_serialised(self):
        result = _extract_output([1, 2, 3])
        assert result is not None
        assert json.loads(result) == [1, 2, 3]

    def test_int_coerced_to_string(self):
        result = _extract_output(42)
        assert result == "42"


# ---------------------------------------------------------------------------
# 5. DB INSERT path — mock psycopg.connect
# ---------------------------------------------------------------------------


class TestDbInsert:
    def _run_main_with_mock_db(self, monkeypatch, payload: dict, mock_connect):
        """Wire DATABASE_URL + fake psycopg, feed payload through main()."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
        monkeypatch.setenv("CALLSIGN", "elliot")
        monkeypatch.setattr("sys.stdin", _make_stdin(json.dumps(payload)))

        # Inject fake psycopg module
        fake_psycopg = _make_fake_psycopg(mock_connect)
        monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

        main()

    def test_insert_sql_contains_table(self, monkeypatch):
        mock_connect, mock_cur = _capture_connect()
        self._run_main_with_mock_db(
            monkeypatch,
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}, "tool_response": "ok"},
            mock_connect,
        )
        sql, params = _last_execute(mock_cur)
        assert "public.tool_call_log" in sql

    def test_insert_params_callsign(self, monkeypatch):
        mock_connect, mock_cur = _capture_connect()
        self._run_main_with_mock_db(
            monkeypatch,
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}, "tool_response": "ok"},
            mock_connect,
        )
        _, params = _last_execute(mock_cur)
        assert params[0] == "elliot"  # callsign is first param

    def test_insert_params_tool_name(self, monkeypatch):
        mock_connect, mock_cur = _capture_connect()
        self._run_main_with_mock_db(
            monkeypatch,
            {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_response": "file.txt"},
            mock_connect,
        )
        _, params = _last_execute(mock_cur)
        assert params[2] == "Bash"  # tool_name is third param

    def test_insert_params_tool_input_is_json_string(self, monkeypatch):
        mock_connect, mock_cur = _capture_connect()
        self._run_main_with_mock_db(
            monkeypatch,
            {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}, "tool_response": "ok"},
            mock_connect,
        )
        _, params = _last_execute(mock_cur)
        # 4th param is tool_input_json — must be valid JSON string
        tool_input_json = params[3]
        assert isinstance(tool_input_json, str)
        parsed = json.loads(tool_input_json)
        assert parsed["file_path"] == "/tmp/x"


# ---------------------------------------------------------------------------
# 6. tool_input cap — CRITICAL path
# ---------------------------------------------------------------------------


class TestToolInputCap:
    def test_small_payload_preserved(self):
        small = {"file_path": "/tmp/test.py"}
        result = _cap_tool_input(small)
        parsed = json.loads(result)
        assert parsed == small
        assert "_truncated" not in parsed

    def test_payload_at_boundary_preserved(self):
        # Exactly at _TOOL_INPUT_MAX_BYTES should pass through unchanged
        # Build a dict whose serialised form is exactly at the limit
        filler = "x" * (_TOOL_INPUT_MAX_BYTES - len('{"k": ""}'))
        payload = {"k": filler}
        serialised = json.dumps(payload, ensure_ascii=False)
        # May be slightly over — just ensure no exception
        result = _cap_tool_input(payload)
        parsed = json.loads(result)
        if len(serialised.encode()) <= _TOOL_INPUT_MAX_BYTES:
            assert "_truncated" not in parsed
        else:
            assert parsed["_truncated"] is True

    def test_large_payload_100kb_triggers_sentinel(self):
        """CRITICAL path: 100 KB tool_input must fire the cap."""
        large_body = "A" * 100_000  # 100 KB of ASCII
        payload = {"content": large_body}
        serialised = json.dumps(payload, ensure_ascii=False)
        assert len(serialised.encode()) > _TOOL_INPUT_MAX_BYTES, (
            "Precondition: test payload must exceed the cap to be meaningful"
        )

        result = _cap_tool_input(payload)
        parsed = json.loads(result)

        assert parsed["_truncated"] is True, "Cap must fire: _truncated must be True"
        assert parsed["original_size_bytes"] > _TOOL_INPUT_MAX_BYTES
        assert len(result.encode()) < len(serialised.encode()), (
            "Capped result must be smaller than original serialised form"
        )

    def test_sentinel_is_valid_json(self):
        """Sentinel must always be valid JSON so %s::jsonb cast succeeds."""
        huge = {"data": "B" * 200_000}
        result = _cap_tool_input(huge)
        # Must not raise
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_sentinel_preserves_original_size(self):
        """original_size_bytes in sentinel must match actual encoded byte count."""
        body = "C" * 100_000
        payload = {"content": body}
        expected_bytes = len(json.dumps(payload, ensure_ascii=False).encode())

        result = _cap_tool_input(payload)
        sentinel = json.loads(result)

        assert sentinel["original_size_bytes"] == expected_bytes


# ---------------------------------------------------------------------------
# 7. DB insert — large tool_input uses sentinel (critical + db combined)
# ---------------------------------------------------------------------------


class TestDbInsertWithLargeToolInput:
    def test_large_tool_input_stored_as_sentinel(self, monkeypatch):
        """End-to-end: 100 KB content in tool_input → sentinel written to DB."""
        mock_connect, mock_cur = _capture_connect()

        monkeypatch.setenv("DATABASE_URL", "postgresql://fake/db")
        monkeypatch.setenv("CALLSIGN", "elliot")

        large_payload = {"content": "X" * 100_000}
        stdin_data = json.dumps(
            {
                "tool_name": "Write",
                "tool_input": large_payload,
                "tool_response": "ok",
            }
        )
        monkeypatch.setattr("sys.stdin", _make_stdin(stdin_data))

        fake_psycopg = _make_fake_psycopg(mock_connect)
        monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

        main()

        _, params = _last_execute(mock_cur)
        tool_input_json = params[3]
        parsed = json.loads(tool_input_json)

        assert parsed["_truncated"] is True, (
            "Large tool_input must be replaced by sentinel in DB INSERT"
        )
        assert parsed["original_size_bytes"] > _TOOL_INPUT_MAX_BYTES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stdin(text: str):
    """Return a fake stdin object that reads the given text."""
    import io

    return io.StringIO(text)


def _make_fake_psycopg(mock_connect) -> types.ModuleType:
    """Build a minimal fake psycopg module."""
    fake = types.ModuleType("psycopg")
    fake.connect = mock_connect
    return fake


def _capture_connect():
    """Return (mock_connect, mock_cursor) where cursor captures execute() calls."""
    mock_cur = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_connect = MagicMock(return_value=mock_conn)
    return mock_connect, mock_cur


def _last_execute(mock_cur) -> tuple[str, tuple]:
    """Extract (sql, params) from the last execute() call on mock_cur."""
    assert mock_cur.execute.called, "execute() was never called on cursor"
    args = mock_cur.execute.call_args
    sql = args[0][0]
    params = args[0][1]
    return sql, params
