"""Tests for src/skill_gen/extractor.py — turn_log compression."""

from __future__ import annotations

from src.skill_gen.extractor import compress


def _seed_fixture():
    turns = [
        {"id": "t1", "turn_index": 0, "session_id": "s1"},
        {"id": "t2", "turn_index": 1, "session_id": "s1"},
    ]
    logs = [
        {
            "id": "l1",
            "turn_id": "t1",
            "tool_name": "Read",
            "exit_status": "success",
            "tool_result_summary": "read file foo.py",
            "started_at": "2026-05-11T22:00:00Z",
        },
        {
            "id": "l2",
            "turn_id": "t1",
            "tool_name": "Bash",
            "exit_status": "error",
            "error_message": "exit 1: command not found",
            "tool_result_summary": "ls -la",
            "started_at": "2026-05-11T22:00:01Z",
        },
        {
            "id": "l3",
            "turn_id": "t2",
            "tool_name": "Read",
            "exit_status": "success",
            "tool_result_summary": "read file bar.py",
            "started_at": "2026-05-11T22:01:00Z",
        },
    ]
    files = [
        {"id": "f1", "turn_log_id": "l1", "file_path": "foo.py", "operation": "read"},
        {
            "id": "f2",
            "turn_log_id": "l3",
            "file_path": "bar.py",
            "operation": "write",
            "lines_added": 12,
            "lines_removed": 0,
        },
    ]
    messages = [
        {"content_text": "do the thing", "timestamp": "2026-05-11T22:00:00Z"},
        {"content_text": "no, do it differently", "timestamp": "2026-05-11T22:00:30Z"},
    ]

    def fetch_turns(session_id, start_ts, end_ts):
        assert session_id == "s1"
        return turns

    def fetch_turn_logs(turn_ids):
        assert turn_ids == ["t1", "t2"]
        return logs

    def fetch_turn_files(turn_log_ids):
        assert turn_log_ids == ["l1", "l2", "l3"]
        return files

    def fetch_user_messages(session_id, start_ts, end_ts):
        return messages

    return fetch_turns, fetch_turn_logs, fetch_turn_files, fetch_user_messages


def test_compress_shapes_freq_errors_files_chronology():
    ft, fl, ff, fm = _seed_fixture()
    out = compress(
        "s1",
        "2026-05-11T21:00:00Z",
        "2026-05-11T23:00:00Z",
        fetch_turns=ft,
        fetch_turn_logs=fl,
        fetch_turn_files=ff,
        fetch_user_messages=fm,
    )
    assert out["session_id"] == "s1"
    assert out["turn_count"] == 2
    assert out["tool_call_freq"] == {"Read": 2, "Bash": 1}
    assert len(out["errors"]) == 1
    assert out["errors"][0]["tool"] == "Bash"
    assert "command not found" in out["errors"][0]["error_message"]
    assert {f["file_path"] for f in out["files_touched"]} == {"foo.py", "bar.py"}
    assert len(out["chronology"]) == 3
    assert out["chronology"][0]["tool"] == "Read"
    assert out["user_messages"] == ["do the thing", "no, do it differently"]


def test_compress_empty_session_returns_zero_counts():
    out = compress(
        "s-empty",
        "2026-05-11T21:00:00Z",
        "2026-05-11T23:00:00Z",
        fetch_turns=lambda *a: [],
        fetch_turn_logs=lambda *a: [],
        fetch_turn_files=lambda *a: [],
        fetch_user_messages=lambda *a: [],
    )
    assert out["turn_count"] == 0
    assert out["tool_call_freq"] == {}
    assert out["errors"] == []
    assert out["files_touched"] == []
    assert out["chronology"] == []
    assert out["user_messages"] == []


def test_compress_truncates_long_user_messages():
    long_msg = "x" * 2000
    out = compress(
        "s2",
        "2026-05-11T21:00:00Z",
        "2026-05-11T23:00:00Z",
        fetch_turns=lambda *a: [],
        fetch_turn_logs=lambda *a: [],
        fetch_turn_files=lambda *a: [],
        fetch_user_messages=lambda *a: [{"content_text": long_msg, "timestamp": "t"}],
    )
    assert len(out["user_messages"]) == 1
    assert len(out["user_messages"][0]) == 500
