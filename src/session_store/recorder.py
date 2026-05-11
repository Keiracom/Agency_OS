"""recorder.py — write paths for the Drevon PR-A session store.

Thin functional layer over src.evo.supabase_client REST helpers. All writes
are idempotent-on-id where possible (sessions: id returned by INSERT;
subsequent rows reference that UUID).

Hooks under .claude/hooks/ invoke these via subprocess (`python3 -c "from
src.session_store import record_tool_call; record_tool_call(...)"`).

Error handling: log + swallow. Recording is best-effort; missing rows must
NEVER block agent execution. Per PR-A spec: NO retroactive backfill, NEW
sessions only.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.evo.supabase_client import sb_patch, sb_post

logger = logging.getLogger("session_store.recorder")


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _safe_post(table: str, payload: dict) -> dict | None:
    """POST + log+swallow on failure (best-effort recording)."""
    try:
        rows = sb_post(table, payload)
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("session_store %s POST failed: %s", table, exc)
        return None


def _safe_patch(table: str, params: dict, payload: dict) -> None:
    try:
        sb_patch(table, params, payload)
    except Exception as exc:
        logger.warning("session_store %s PATCH failed: %s", table, exc)


def record_session_start(
    callsign: str,
    working_directory: str,
    *,
    session_uuid: str | None = None,
    tmux_session: str | None = None,
    model_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> UUID | None:
    """Open a sessions row. Returns the row's UUID, or None on failure."""
    sid = uuid4()
    payload = {
        "id": str(sid),
        "callsign": callsign,
        "session_uuid": session_uuid,
        "working_directory": working_directory,
        "tmux_session": tmux_session,
        "started_at": _utc_iso(),
        "status": "active",
        "model_id": model_id,
        "extra": extra or {},
    }
    row = _safe_post("sessions", payload)
    return sid if row else None


def record_message(
    session_id: UUID,
    role: str,
    message_index: int,
    content_text: str | None = None,
    *,
    content_bytes: int | None = None,
    store_full_content: bool = False,
) -> UUID | None:
    """Append a messages row. If store_full_content=False, content_text is None
    in the row (only hash + bytes preserved). Caller decides the trade-off."""
    mid = uuid4()
    text_for_hash = content_text or ""
    payload = {
        "id": str(mid),
        "session_id": str(session_id),
        "role": role,
        "message_index": message_index,
        "timestamp": _utc_iso(),
        "content_hash": _hash(text_for_hash) if text_for_hash else None,
        "content_text": content_text if store_full_content else None,
        "content_bytes": content_bytes
        if content_bytes is not None
        else len(text_for_hash.encode("utf-8")),
    }
    row = _safe_post("messages", payload)
    return mid if row else None


def record_turn_start(
    session_id: UUID,
    turn_index: int,
    trigger_message_id: UUID | None = None,
) -> UUID | None:
    """Open a turns row."""
    tid = uuid4()
    payload = {
        "id": str(tid),
        "session_id": str(session_id),
        "trigger_message_id": str(trigger_message_id) if trigger_message_id else None,
        "turn_index": turn_index,
        "started_at": _utc_iso(),
        "status": "in_progress",
    }
    row = _safe_post("turns", payload)
    return tid if row else None


def record_turn_complete(
    turn_id: UUID,
    *,
    status: str = "completed",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cost_aud: float | None = None,
) -> None:
    """Close a turns row with cost rollup."""
    payload: dict[str, Any] = {
        "completed_at": _utc_iso(),
        "status": status,
    }
    if input_tokens is not None:
        payload["input_tokens"] = input_tokens
    if output_tokens is not None:
        payload["output_tokens"] = output_tokens
    if cost_aud is not None:
        payload["cost_aud"] = cost_aud
    _safe_patch("turns", {"id": f"eq.{turn_id}"}, payload)


def record_tool_call(
    turn_id: UUID,
    tool_name: str,
    tool_args: dict[str, Any],
    *,
    tool_result_summary: str | None = None,
    tool_result_bytes: int | None = None,
    exit_status: str = "success",
    error_message: str | None = None,
    duration_ms: int | None = None,
    files: list[dict[str, Any]] | None = None,
) -> UUID | None:
    """Append a turn_logs row, plus optional turn_files rows for file ops.

    files is a list of dicts with keys matching turn_files columns
    (file_path, operation, bytes_written, bytes_read, content_hash,
    lines_added, lines_removed).
    """
    lid = uuid4()
    import json as _json

    args_json_str = _json.dumps(tool_args, default=str)
    payload = {
        "id": str(lid),
        "turn_id": str(turn_id),
        "tool_name": tool_name,
        "tool_args_json": tool_args,
        "tool_args_bytes": len(args_json_str.encode("utf-8")),
        "tool_result_summary": tool_result_summary,
        "tool_result_bytes": tool_result_bytes,
        "exit_status": exit_status,
        "error_message": error_message,
        "started_at": _utc_iso(),
        "completed_at": _utc_iso(),
        "duration_ms": duration_ms,
    }
    row = _safe_post("turn_logs", payload)
    if not row:
        return None
    for f in files or []:
        f_payload = {
            "id": str(uuid4()),
            "turn_log_id": str(lid),
            "file_path": f["file_path"],
            "operation": f["operation"],
            "bytes_written": f.get("bytes_written"),
            "bytes_read": f.get("bytes_read"),
            "content_hash": f.get("content_hash"),
            "lines_added": f.get("lines_added"),
            "lines_removed": f.get("lines_removed"),
            "timestamp": _utc_iso(),
        }
        _safe_post("turn_files", f_payload)
    return lid


def record_session_end(session_id: UUID, *, status: str = "closed") -> None:
    """Close a sessions row."""
    _safe_patch(
        "sessions",
        {"id": f"eq.{session_id}"},
        {"ended_at": _utc_iso(), "status": status},
    )


def mark_session_stuck(session_id: UUID) -> None:
    """Watchdog marker — sets status='stuck' and ended_at without graceful close."""
    _safe_patch(
        "sessions",
        {"id": f"eq.{session_id}"},
        {"ended_at": _utc_iso(), "status": "stuck"},
    )
