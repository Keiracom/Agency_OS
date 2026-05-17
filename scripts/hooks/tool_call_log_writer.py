#!/usr/bin/env python3
"""tool_call_log_writer.py — KEI-116 Build 1: Claude Code PostToolUse → public.tool_call_log.

Reads the PostToolUse hook JSON from stdin and inserts one row into
public.tool_call_log so the tool-call-log-indexer can push it to Weaviate.

Stdin shape (Claude Code PostToolUse hook):
    {
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test"},
        "tool_response": "... output ...",
        "session_id": "abc123",          # optional — Claude Code may omit
        "start_time": 1234567890.123,    # optional float epoch seconds
        "end_time":   1234567890.456     # optional float epoch seconds
    }

Fail-open contract: any exception → log to stderr + exit 0.
Hooks that exit non-zero block the agent turn — this script NEVER does that.

Env (loaded from /home/elliotbot/.config/agency-os/.env if not already set):
    DATABASE_URL or SUPABASE_DB_URL — psycopg-compatible postgres DSN.
    CALLSIGN — agent callsign (elliot / aiden / max / atlas / orion / scout).

psycopg usage: prepare_threshold=None to avoid pgbouncer txn-mode PREPARE errors
(per reference_psycopg_supabase_pgbouncer pin).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] tool_call_log_writer: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("tool_call_log_writer")

_ENV_FILE = Path(
    "/home/elliotbot/.config/agency-os/.env"
)  # single-host design — one machine per deployment
_OUTPUT_EXCERPT_MAX = 500

# Maximum serialised bytes for tool_input before the oversized sentinel replaces it.
# Prevents multi-MB Write/Edit/Bash payloads from bloating tool_call_log JSONB.
# 64 KB chosen to cover virtually all normal structured inputs while capping runaway payloads.
_TOOL_INPUT_MAX_BYTES = 65_536  # 64 KB


def _load_env() -> None:
    """Load .env file if DATABASE_URL not already in environment."""
    if os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"):
        return
    if not _ENV_FILE.exists():
        return
    try:
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError as exc:
        logger.warning("could not load .env: %s", exc)


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL / SUPABASE_DB_URL not set")
    # Strip asyncpg dialect prefix — psycopg uses plain postgresql://
    return dsn.replace("postgresql+asyncpg://", "postgresql://", 1)


def _callsign() -> str:
    # CALLSIGN env var is the canonical source per LAW XVII — agent processes export it.
    # IDENTITY.md file fallback was removed: cwd when hook fires is tool-dependent and
    # unreliable (e.g. Bash tool runs from arbitrary dirs). Env is always available.
    cs = (os.environ.get("CALLSIGN") or "").strip().lower()
    return cs if cs else "unknown"


def _cap_tool_input(tool_input: dict) -> str:
    """Serialise tool_input with a hard byte cap.

    If the JSON representation exceeds _TOOL_INPUT_MAX_BYTES (64 KB), the full
    payload is replaced with a compact sentinel that records size + tool_name so
    the row is still query-able. This prevents multi-MB Write/Edit/Bash bodies
    from bloating the JSONB column.

    Returns the serialised string (always valid JSON) ready for %s::jsonb.
    """
    serialised = json.dumps(tool_input, ensure_ascii=False)
    if len(serialised.encode()) <= _TOOL_INPUT_MAX_BYTES:
        return serialised
    sentinel = {
        "_truncated": True,
        "original_size_bytes": len(serialised.encode()),
        "tool_name": tool_input.get("tool_name") if isinstance(tool_input, dict) else None,
    }
    return json.dumps(sentinel, ensure_ascii=False)


def _truncate(text: str | None) -> str | None:
    if text is None:
        return None
    if len(text) <= _OUTPUT_EXCERPT_MAX:
        return text
    return text[:_OUTPUT_EXCERPT_MAX] + f"\n…[truncated {len(text) - _OUTPUT_EXCERPT_MAX} chars]"


def _extract_output(tool_response: object) -> str | None:
    """Flatten tool_response to a plain string excerpt."""
    if tool_response is None:
        return None
    if isinstance(tool_response, str):
        return tool_response or None
    if isinstance(tool_response, (dict, list)):
        try:
            return json.dumps(tool_response, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(tool_response)
    return str(tool_response)


def _epoch_to_dt(epoch: float | int | None) -> datetime | None:
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(float(epoch), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def main() -> None:
    _load_env()

    raw = sys.stdin.read()
    if not raw.strip():
        logger.warning("empty stdin — nothing to log")
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("invalid JSON on stdin: %s", exc)
        return

    tool_name: str = payload.get("tool_name") or "unknown"
    tool_input: dict = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response")
    session_id: str | None = payload.get("session_id") or None

    now = datetime.now(tz=UTC)
    started_at = _epoch_to_dt(payload.get("start_time")) or now
    completed_at = _epoch_to_dt(payload.get("end_time")) or now

    duration_ms: int | None = None
    if completed_at and started_at:
        delta = completed_at - started_at
        duration_ms = max(0, int(delta.total_seconds() * 1000))

    callsign = _callsign()
    excerpt = _truncate(_extract_output(tool_response))
    tool_input_json = _cap_tool_input(tool_input)

    try:
        import psycopg  # type: ignore[import]
    except ImportError:
        logger.warning("psycopg not installed — cannot write tool_call_log")
        return

    try:
        with (
            psycopg.connect(_dsn(), prepare_threshold=None, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                """
                INSERT INTO public.tool_call_log
                    (callsign, session_uuid, tool_name, tool_input,
                     tool_output_excerpt, started_at, completed_at, duration_ms)
                VALUES (%s, %s::uuid, %s, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    callsign,
                    session_id,
                    tool_name,
                    tool_input_json,
                    excerpt,
                    started_at,
                    completed_at,
                    duration_ms,
                ),
            )
    except Exception as exc:  # noqa: BLE001 — fail-open: never block agent
        logger.warning("DB insert failed: %s", exc)
        return

    logger.debug("logged tool call: callsign=%s tool=%s", callsign, tool_name)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("unexpected error: %s", exc)
    sys.exit(0)
