"""extractor.py — turn_logs → compressed structured summary.

Reads sessions / turns / turn_logs / turn_files for a directive-bounded window
(`session_id`, `start_ts`, `end_ts`) and folds it into a small dict suitable
for prompting claude. Raw tool output is stripped (kept as bytes counts and
1-line summaries); structure is preserved.

Caller responsibilities:
    - Compute (start_ts, end_ts) from Step 0 RESTATE start → completion-log
      emission. This module does not implement directive boundary detection.

The returned dict is intentionally JSON-serialisable so the prompt builder can
hand it straight to `json.dumps(..., indent=2)`.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, TypedDict

from src.evo.supabase_client import sb_get


class CompressedSession(TypedDict):
    session_id: str
    window_start: str
    window_end: str
    turn_count: int
    tool_call_freq: dict[str, int]
    errors: list[dict[str, str]]
    user_messages: list[str]
    files_touched: list[dict[str, Any]]
    chronology: list[dict[str, Any]]


_MAX_USER_MSG_CHARS = 500
_MAX_ERR_MSG_CHARS = 300
_MAX_USER_MSGS = 30
_MAX_CHRONOLOGY = 200


def _fetch_turns(session_id: str, start_ts: str, end_ts: str) -> list[dict]:
    return sb_get(
        "turns",
        {
            "session_id": f"eq.{session_id}",
            "started_at": f"gte.{start_ts}",
            "completed_at": f"lte.{end_ts}",
            "order": "turn_index.asc",
        },
    )


def _fetch_turn_logs(turn_ids: list[str]) -> list[dict]:
    if not turn_ids:
        return []
    in_clause = "(" + ",".join(turn_ids) + ")"
    return sb_get(
        "turn_logs",
        {"turn_id": f"in.{in_clause}", "order": "started_at.asc"},
    )


def _fetch_turn_files(turn_log_ids: list[str]) -> list[dict]:
    if not turn_log_ids:
        return []
    in_clause = "(" + ",".join(turn_log_ids) + ")"
    return sb_get("turn_files", {"turn_log_id": f"in.{in_clause}"})


def _fetch_user_messages(session_id: str, start_ts: str, end_ts: str) -> list[dict]:
    # PostgREST: multiple constraints on the same column require the `and=()`
    # operator since dict keys can't repeat. start <= timestamp <= end.
    return sb_get(
        "messages",
        {
            "session_id": f"eq.{session_id}",
            "role": "eq.user",
            "and": f"(timestamp.gte.{start_ts},timestamp.lte.{end_ts})",
            "order": "message_index.asc",
            "select": "content_text,timestamp",
        },
    )


def compress(
    session_id: str,
    start_ts: str,
    end_ts: str,
    *,
    fetch_turns=_fetch_turns,
    fetch_turn_logs=_fetch_turn_logs,
    fetch_turn_files=_fetch_turn_files,
    fetch_user_messages=_fetch_user_messages,
) -> CompressedSession:
    """Compress a session slice into a structured summary.

    The four `fetch_*` parameters allow tests to inject deterministic fixtures
    without monkeypatching httpx. Production callers omit them.
    """
    turns = fetch_turns(session_id, start_ts, end_ts)
    turn_ids = [t["id"] for t in turns]
    logs = fetch_turn_logs(turn_ids)
    log_ids = [log["id"] for log in logs]
    files = fetch_turn_files(log_ids)
    user_msgs = fetch_user_messages(session_id, start_ts, end_ts) or []

    freq: Counter[str] = Counter(log["tool_name"] for log in logs)
    errors: list[dict[str, str]] = []
    chronology: list[dict[str, Any]] = []
    for log in logs:
        chronology.append(
            {
                "tool": log["tool_name"],
                "started_at": log.get("started_at"),
                "exit": log.get("exit_status", "success"),
                "summary": (log.get("tool_result_summary") or "")[:160],
            }
        )
        if log.get("exit_status") not in (None, "success"):
            errors.append(
                {
                    "tool": log["tool_name"],
                    "exit_status": log.get("exit_status", ""),
                    "error_message": (log.get("error_message") or "")[:_MAX_ERR_MSG_CHARS],
                }
            )

    files_touched = [
        {
            "file_path": f["file_path"],
            "operation": f.get("operation", ""),
            "lines_added": f.get("lines_added"),
            "lines_removed": f.get("lines_removed"),
        }
        for f in files
    ]

    user_message_texts = [
        (m.get("content_text") or "")[:_MAX_USER_MSG_CHARS]
        for m in user_msgs[:_MAX_USER_MSGS]
        if m.get("content_text")
    ]

    return CompressedSession(
        session_id=session_id,
        window_start=start_ts,
        window_end=end_ts,
        turn_count=len(turns),
        tool_call_freq=dict(freq),
        errors=errors,
        user_messages=user_message_texts,
        files_touched=files_touched,
        chronology=chronology[:_MAX_CHRONOLOGY],
    )
