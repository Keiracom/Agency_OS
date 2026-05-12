"""tests for src/session_store/userpromptsubmit_handler.py — messages-ORPHAN fix.

Mocks recorder.record_message + recorder.record_session_start; covers:
  - _extract_prompt: empty / invalid JSON / valid / missing key / non-string
  - _resolve_session_id: existing state file / missing / start_fn returns None
  - _read_message_index / _write_message_index round-trip + error paths
  - handle_user_prompt_submit: happy path, empty prompt, session failure,
    record_message returns None, monotone index increment
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from src.session_store import userpromptsubmit_handler as h


# _extract_prompt ────────────────────────────────────────────────────────────


def test_extract_prompt_empty_text() -> None:
    assert h._extract_prompt("") == ""
    assert h._extract_prompt("   ") == ""


def test_extract_prompt_invalid_json() -> None:
    assert h._extract_prompt("{not json") == ""


def test_extract_prompt_missing_field() -> None:
    assert h._extract_prompt('{"foo": "bar"}') == ""


def test_extract_prompt_non_string_field() -> None:
    assert h._extract_prompt('{"prompt": 42}') == ""


def test_extract_prompt_valid() -> None:
    assert h._extract_prompt('{"prompt": "hello world"}') == "hello world"


# _resolve_session_id ────────────────────────────────────────────────────────


def test_resolve_session_id_from_existing_state(tmp_path: Path) -> None:
    state = tmp_path / "session"
    state.write_text("abc12345-0000-0000-0000-000000000000:0:0")
    start_fn = MagicMock()
    sid = h._resolve_session_id("max", "/cwd", state, start_fn=start_fn)
    assert sid == "abc12345-0000-0000-0000-000000000000"
    start_fn.assert_not_called()


def test_resolve_session_id_creates_when_missing(tmp_path: Path) -> None:
    state = tmp_path / "session"
    new_sid = uuid4()
    start_fn = MagicMock(return_value=new_sid)
    sid = h._resolve_session_id("max", "/cwd", state, start_fn=start_fn)
    assert sid == str(new_sid)
    start_fn.assert_called_once_with(callsign="max", working_directory="/cwd")
    assert state.exists()
    assert state.read_text().startswith(str(new_sid))


def test_resolve_session_id_start_fn_returns_none(tmp_path: Path) -> None:
    state = tmp_path / "session"
    start_fn = MagicMock(return_value=None)
    assert h._resolve_session_id("max", "/cwd", state, start_fn=start_fn) is None


# _read_message_index / _write_message_index ─────────────────────────────────


def test_read_message_index_missing(tmp_path: Path) -> None:
    assert h._read_message_index(tmp_path / "absent") == 0


def test_read_message_index_valid(tmp_path: Path) -> None:
    p = tmp_path / "msgidx"
    p.write_text("42")
    assert h._read_message_index(p) == 42


def test_read_message_index_invalid_text_returns_zero(tmp_path: Path) -> None:
    p = tmp_path / "msgidx"
    p.write_text("not a number")
    assert h._read_message_index(p) == 0


def test_write_message_index_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "msgidx"
    h._write_message_index(p, 7)
    assert p.read_text() == "7"


# handle_user_prompt_submit ──────────────────────────────────────────────────


def test_handle_empty_prompt_returns_none(tmp_path: Path) -> None:
    record_msg = MagicMock()
    record_start = MagicMock()
    result = h.handle_user_prompt_submit(
        callsign="max",
        payload_text="",
        working_directory="/cwd",
        session_state_dir=str(tmp_path),
        record_message_fn=record_msg,
        record_session_start_fn=record_start,
    )
    assert result is None
    record_msg.assert_not_called()
    record_start.assert_not_called()


def test_handle_session_resolve_failure_returns_none(tmp_path: Path) -> None:
    record_msg = MagicMock()
    record_start = MagicMock(return_value=None)
    result = h.handle_user_prompt_submit(
        callsign="max",
        payload_text='{"prompt": "hi"}',
        working_directory="/cwd",
        session_state_dir=str(tmp_path),
        record_message_fn=record_msg,
        record_session_start_fn=record_start,
    )
    assert result is None
    record_msg.assert_not_called()


def test_handle_happy_path_records_and_increments(tmp_path: Path) -> None:
    session_uuid = uuid4()
    msg_uuid = uuid4()
    (tmp_path / "session").write_text(f"{session_uuid}:0:0")
    record_msg = MagicMock(return_value=msg_uuid)
    record_start = MagicMock()

    result = h.handle_user_prompt_submit(
        callsign="max",
        payload_text='{"prompt": "hello there"}',
        working_directory="/cwd",
        session_state_dir=str(tmp_path),
        record_message_fn=record_msg,
        record_session_start_fn=record_start,
    )

    assert result == msg_uuid
    record_start.assert_not_called()
    record_msg.assert_called_once()
    call = record_msg.call_args
    assert call.kwargs["session_id"] == UUID(str(session_uuid))
    assert call.kwargs["role"] == "user"
    assert call.kwargs["message_index"] == 0
    assert call.kwargs["content_text"] == "hello there"
    assert call.kwargs["content_bytes"] == len("hello there".encode("utf-8"))
    assert call.kwargs["store_full_content"] is True
    assert (tmp_path / "msgidx").read_text() == "1"


def test_handle_increments_existing_message_index(tmp_path: Path) -> None:
    session_uuid = uuid4()
    (tmp_path / "session").write_text(f"{session_uuid}:0:0")
    (tmp_path / "msgidx").write_text("3")
    record_msg = MagicMock(return_value=uuid4())

    h.handle_user_prompt_submit(
        callsign="max",
        payload_text='{"prompt": "second"}',
        working_directory="/cwd",
        session_state_dir=str(tmp_path),
        record_message_fn=record_msg,
        record_session_start_fn=MagicMock(),
    )

    assert record_msg.call_args.kwargs["message_index"] == 3
    assert (tmp_path / "msgidx").read_text() == "4"


def test_handle_record_message_returns_none(tmp_path: Path) -> None:
    (tmp_path / "session").write_text(f"{uuid4()}:0:0")
    record_msg = MagicMock(return_value=None)
    result = h.handle_user_prompt_submit(
        callsign="max",
        payload_text='{"prompt": "x"}',
        working_directory="/cwd",
        session_state_dir=str(tmp_path),
        record_message_fn=record_msg,
        record_session_start_fn=MagicMock(),
    )
    assert result is None
    # Index still advances — best-effort, monotone preserves uniqueness
    assert (tmp_path / "msgidx").read_text() == "1"


def test_handle_record_message_raises_value_error(tmp_path: Path) -> None:
    (tmp_path / "session").write_text(f"{uuid4()}:0:0")
    record_msg = MagicMock(side_effect=ValueError("bad payload"))
    result = h.handle_user_prompt_submit(
        callsign="max",
        payload_text='{"prompt": "x"}',
        working_directory="/cwd",
        session_state_dir=str(tmp_path),
        record_message_fn=record_msg,
        record_session_start_fn=MagicMock(),
    )
    assert result is None
    # Index NOT advanced on raise — we never reached the write
    assert not (tmp_path / "msgidx").exists()
