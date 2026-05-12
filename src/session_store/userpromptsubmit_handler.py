"""userpromptsubmit_handler.py — UserPromptSubmit hook Python logic.

Closes the silent data-loss in src/skill_gen/extractor._fetch_user_messages
(audit Surprise #1, 2026-05-12): skill_gen queries public.messages for
role=user but no production hook ever wrote there → every compression
returned [] silently.

Invoked by .claude/hooks/session_store_userpromptsubmit.sh on every user
prompt. Lazy-creates a session row if missing (mirrors the same pattern
used by session_store_posttooluse.sh), reads the per-callsign monotone
message_index from a state file, calls recorder.record_message with
role='user' and store_full_content=True.

Best-effort: any failure logs + returns None. The hook itself always exits
0 so user prompts never get blocked on a recording failure.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Callable
from uuid import UUID

from src.session_store.recorder import record_message, record_session_start

logger = logging.getLogger("session_store.userpromptsubmit_handler")


def _resolve_session_id(
    callsign: str,
    working_directory: str,
    session_state_path: Path,
    start_fn: Callable[..., UUID | None] = record_session_start,
) -> str | None:
    """Read session_id from state file, or lazy-create via record_session_start."""
    sid: str | None = None
    if session_state_path.exists():
        try:
            sid = session_state_path.read_text().strip().split(":")[0] or None
        except OSError as exc:
            logger.warning("session state read failed: %s", exc)
    if not sid:
        new_sid = start_fn(callsign=callsign, working_directory=working_directory)
        if new_sid is not None:
            sid = str(new_sid)
            try:
                session_state_path.write_text(f"{sid}:0:0")
            except OSError as exc:
                logger.warning("session state write failed: %s", exc)
    return sid


def _read_message_index(msgidx_state_path: Path) -> int:
    """Read monotone per-callsign message index. Defaults to 0 on missing/invalid."""
    if not msgidx_state_path.exists():
        return 0
    try:
        return int(msgidx_state_path.read_text().strip() or "0")
    except (OSError, ValueError) as exc:
        logger.warning("msgidx state read failed: %s", exc)
        return 0


def _write_message_index(msgidx_state_path: Path, next_index: int) -> None:
    try:
        msgidx_state_path.write_text(str(next_index))
    except OSError as exc:
        logger.warning("msgidx state write failed: %s", exc)


def _extract_prompt(payload_text: str) -> str:
    """Parse the JSON hook payload and return its 'prompt' field, or ''."""
    if not payload_text.strip():
        return ""
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        logger.warning("UserPromptSubmit payload not JSON: %s", exc)
        return ""
    prompt = payload.get("prompt") or ""
    return prompt if isinstance(prompt, str) else ""


def handle_user_prompt_submit(
    callsign: str,
    payload_text: str,
    working_directory: str | None = None,
    *,
    session_state_dir: str = "/tmp",
    record_message_fn: Callable[..., UUID | None] = record_message,
    record_session_start_fn: Callable[..., UUID | None] = record_session_start,
) -> UUID | None:
    """Record a single UserPromptSubmit event to public.messages.

    Returns the new messages row UUID on success, None on best-effort failure.
    Never raises — the hook always exits 0.
    """
    prompt = _extract_prompt(payload_text)
    if not prompt:
        return None
    session_state = Path(session_state_dir) / f".session_{callsign}"
    msgidx_state = Path(session_state_dir) / f".msgidx_{callsign}"
    sid = _resolve_session_id(
        callsign=callsign,
        working_directory=working_directory or os.getcwd(),
        session_state_path=session_state,
        start_fn=record_session_start_fn,
    )
    if not sid:
        return None
    msg_index = _read_message_index(msgidx_state)
    try:
        mid = record_message_fn(
            session_id=UUID(sid),
            role="user",
            message_index=msg_index,
            content_text=prompt,
            content_bytes=len(prompt.encode("utf-8")),
            store_full_content=True,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("record_message failed: %s", exc)
        return None
    _write_message_index(msgidx_state, msg_index + 1)
    return mid
