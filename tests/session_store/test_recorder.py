"""tests for src/session_store/recorder.py — write paths for Drevon PR-A.

Mocks supabase_client.sb_post + sb_patch so tests run without Supabase
network access. Asserts: correct payload shape per table + best-effort
swallow-on-failure semantics.
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest

from src.session_store import recorder


@pytest.fixture
def captured_posts() -> list[tuple[str, dict]]:
    """Capture all sb_post calls. Each entry is (table, payload)."""
    calls: list[tuple[str, dict]] = []

    def fake_post(table: str, payload: dict) -> list:
        calls.append((table, payload))
        return [{"id": payload.get("id", "fake-id")}]

    with patch.object(recorder, "sb_post", side_effect=fake_post):
        yield calls


@pytest.fixture
def captured_patches() -> list[tuple[str, dict, dict]]:
    """Capture all sb_patch calls. Each entry is (table, params, payload)."""
    calls: list[tuple[str, dict, dict]] = []

    def fake_patch(table: str, params: dict, payload: dict) -> list:
        calls.append((table, params, payload))
        return []

    with patch.object(recorder, "sb_patch", side_effect=fake_patch):
        yield calls


def test_record_session_start_writes_sessions_row(captured_posts) -> None:
    sid = recorder.record_session_start(
        callsign="aiden",
        working_directory="/home/elliotbot/clawd/Agency_OS-aiden",
        session_uuid="abc-123",
        tmux_session="aiden",
        model_id="claude-opus-4-7",
        extra={"hello": "world"},
    )
    assert sid is not None
    assert isinstance(sid, UUID)
    assert len(captured_posts) == 1
    table, payload = captured_posts[0]
    assert table == "sessions"
    assert payload["callsign"] == "aiden"
    assert payload["session_uuid"] == "abc-123"
    assert payload["working_directory"] == "/home/elliotbot/clawd/Agency_OS-aiden"
    assert payload["tmux_session"] == "aiden"
    assert payload["model_id"] == "claude-opus-4-7"
    assert payload["extra"] == {"hello": "world"}
    assert payload["status"] == "active"
    assert "started_at" in payload


def test_record_message_with_full_content(captured_posts) -> None:
    sid = UUID("00000000-0000-0000-0000-000000000001")
    mid = recorder.record_message(
        session_id=sid,
        role="user",
        message_index=0,
        content_text="hello world",
        store_full_content=True,
    )
    assert mid is not None
    table, payload = captured_posts[0]
    assert table == "messages"
    assert payload["session_id"] == str(sid)
    assert payload["role"] == "user"
    assert payload["message_index"] == 0
    assert payload["content_text"] == "hello world"
    assert payload["content_hash"] is not None
    assert payload["content_bytes"] == len(b"hello world")


def test_record_message_hash_only(captured_posts) -> None:
    sid = UUID("00000000-0000-0000-0000-000000000001")
    recorder.record_message(
        session_id=sid,
        role="assistant",
        message_index=1,
        content_text="big response",
        store_full_content=False,
    )
    _, payload = captured_posts[0]
    assert payload["content_text"] is None
    assert payload["content_hash"] is not None


def test_record_turn_start_writes_turns_row(captured_posts) -> None:
    sid = UUID("00000000-0000-0000-0000-000000000001")
    tid = recorder.record_turn_start(session_id=sid, turn_index=0)
    assert tid is not None
    table, payload = captured_posts[0]
    assert table == "turns"
    assert payload["session_id"] == str(sid)
    assert payload["turn_index"] == 0
    assert payload["status"] == "in_progress"


def test_record_tool_call_writes_log_and_files(captured_posts, tmp_path) -> None:
    tid = UUID("00000000-0000-0000-0000-000000000002")
    fake_file = str(tmp_path / "x.py")
    lid = recorder.record_tool_call(
        turn_id=tid,
        tool_name="Edit",
        tool_args={"file_path": fake_file, "old_string": "a", "new_string": "b"},
        exit_status="success",
        files=[
            {
                "file_path": fake_file,
                "operation": "edit",
                "lines_added": 1,
                "lines_removed": 1,
            }
        ],
    )
    assert lid is not None
    assert len(captured_posts) == 2  # turn_logs + turn_files
    log_call = captured_posts[0]
    files_call = captured_posts[1]
    assert log_call[0] == "turn_logs"
    assert log_call[1]["tool_name"] == "Edit"
    assert log_call[1]["exit_status"] == "success"
    assert files_call[0] == "turn_files"
    assert files_call[1]["file_path"] == fake_file
    assert files_call[1]["operation"] == "edit"
    assert files_call[1]["lines_added"] == 1


def test_record_turn_complete_patches_turns_row(captured_patches) -> None:
    tid = UUID("00000000-0000-0000-0000-000000000003")
    recorder.record_turn_complete(
        turn_id=tid, status="completed", input_tokens=1000, output_tokens=500, cost_aud=0.05
    )
    table, params, payload = captured_patches[0]
    assert table == "turns"
    assert params == {"id": f"eq.{tid}"}
    assert payload["status"] == "completed"
    assert payload["input_tokens"] == 1000
    assert payload["output_tokens"] == 500
    assert payload["cost_aud"] == pytest.approx(0.05)
    assert "completed_at" in payload


def test_record_session_end_patches_sessions_row(captured_patches) -> None:
    sid = UUID("00000000-0000-0000-0000-000000000004")
    recorder.record_session_end(session_id=sid, status="closed")
    table, params, payload = captured_patches[0]
    assert table == "sessions"
    assert params == {"id": f"eq.{sid}"}
    assert payload["status"] == "closed"
    assert "ended_at" in payload


def test_mark_session_stuck(captured_patches) -> None:
    sid = UUID("00000000-0000-0000-0000-000000000005")
    recorder.mark_session_stuck(session_id=sid)
    table, _params, payload = captured_patches[0]
    assert table == "sessions"
    assert payload["status"] == "stuck"


def test_swallow_on_failure(tmp_path) -> None:
    """sb_post raises → recorder returns None, no exception bubbles up."""

    def raise_fn(*args, **kwargs):
        raise RuntimeError("supabase down")

    with patch.object(recorder, "sb_post", side_effect=raise_fn):
        sid = recorder.record_session_start(callsign="aiden", working_directory=str(tmp_path))
        assert sid is None  # best-effort: no row created, but no exception
