#!/usr/bin/env python3
"""tool_call_logger.py — KEI-54 Stage A: producer SDK for Claude Code tool calls.

Inserts one row per tool execution into public.tool_call_log. Caller passes
metadata + a truncated output excerpt (full output stays in Claude Code logs;
this table is a retrieval-cache excerpt that Stage B will index into Weaviate
once KEI-48 Atlas Weaviate install lands).

Usage (Python):
    from tool_call_logger import log_tool_call
    row_id = log_tool_call(
        callsign="aiden",
        session_uuid="...",
        tool_name="Bash",
        tool_input={"command": "ls -la"},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        exit_code=0,
        output="...",  # truncated caller-side to ~500 chars
    )
    # row_id is a uuid string; the row is now in tool_call_log.

Env:
    DATABASE_URL or SUPABASE_DB_URL — postgres DSN.

Exit codes (when run as a CLI, future surface):
    0 — happy path.
    2 — DSN missing or query failure.

Stage B (gated on KEI-48): a separate worker scans WHERE indexed=false
and copies rows to a Weaviate collection. This module is index-agnostic.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger("tool_call_logger")

# Bound the tool_output_excerpt column to a sensible size — caller can pass
# anything but we'll truncate defensively. Full output stays in Claude Code
# session logs; this is a retrieval-cache excerpt for Stage B Weaviate index.
_OUTPUT_EXCERPT_MAX_CHARS = 500


class ToolCallLoggerError(RuntimeError):
    """Wraps DB / connection failures so callers can ignore-or-handle uniformly."""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise ToolCallLoggerError("DATABASE_URL / SUPABASE_DB_URL not set")
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _truncate(text: str | None, limit: int = _OUTPUT_EXCERPT_MAX_CHARS) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated {len(text) - limit} chars]"


def log_tool_call(
    *,
    callsign: str,
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
    started_at: datetime,
    completed_at: datetime | None = None,
    exit_code: int | None = None,
    output: str | None = None,
    session_uuid: str | None = None,
) -> str:
    """Insert one tool call row; return the inserted row's uuid as a string.

    Raises ToolCallLoggerError on DSN-missing or DB error. Caller decides
    whether to suppress (logging is observability, not a gate).

    duration_ms is computed from started_at + completed_at when both supplied.
    """
    import json as _json

    import psycopg

    duration_ms: int | None = None
    if completed_at is not None:
        delta = completed_at - started_at
        duration_ms = int(delta.total_seconds() * 1000)

    payload = tool_input if tool_input is not None else {}
    excerpt = _truncate(output)

    try:
        with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.tool_call_log
                    (callsign, session_uuid, tool_name, tool_input,
                     tool_output_excerpt, started_at, completed_at,
                     duration_ms, exit_code)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    callsign.lower(),
                    session_uuid,
                    tool_name,
                    _json.dumps(payload),
                    excerpt,
                    started_at,
                    completed_at,
                    duration_ms,
                    exit_code,
                ),
            )
            row = cur.fetchone()
            conn.commit()
    except psycopg.Error as exc:
        raise ToolCallLoggerError(f"insert failed: {exc}") from exc

    if row is None:
        raise ToolCallLoggerError("INSERT returned no row")
    return str(row[0])
