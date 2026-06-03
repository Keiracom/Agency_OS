"""checkpoint_writer.py — capture mid-task state BEFORE watchdog /clear.

Part of context_checkpoint_resume (gate_roadmap 952c8d0d). Writer is fail-open:
any failure logs + returns None; MUST NOT block /clear.
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Most-recent tool-call line above the ❯ marker = best position hint.
_TOOL_CALL_LINE = re.compile(r"^\s*●\s+(Bash|Read|Write|Edit|Task|mcp__)\(.*$")
_PROMPT_MARKER = "❯"


def extract_position_hint(pane: str) -> str:
    """Return a one-line 'where you were' summary from pane content.

    Strategy:
      1. Last '● Bash(...)' / '● Read(...)' / '● Edit(...)' / '● Task(...)' /
         '● mcp__...(...)' line ABOVE the most recent ❯ marker.
      2. Fall back to the last non-blank line before the ❯ marker.
      3. Fall back to the literal last non-blank line.
    """
    if not pane:
        return "(no pane content)"
    lines = pane.splitlines()
    # Find the most recent ❯ marker (from bottom).
    prompt_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if _PROMPT_MARKER in lines[i]:
            prompt_idx = i
            break
    search_until = prompt_idx if prompt_idx is not None else len(lines)
    # Walk backwards from the prompt for a tool-call line.
    for i in range(search_until - 1, -1, -1):
        if _TOOL_CALL_LINE.match(lines[i]):
            return lines[i].strip()[:240]
    # Fall back: last non-blank line before the prompt.
    for i in range(search_until - 1, -1, -1):
        if lines[i].strip():
            return lines[i].strip()[:240]
    # Final fall-back: literal last non-blank line.
    for ln in reversed(lines):
        if ln.strip():
            return ln.strip()[:240]
    return "(no position recoverable)"


def _connect():
    """Connect to Postgres via the watchdog's standard DSN (fail-open caller).

    Mirrors the pattern in context_watchdog._gate_roadmap_recent_change.
    """
    import psycopg  # noqa: PLC0415

    dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not dsn:
        raise RuntimeError("DATABASE_URL_MIGRATIONS / DATABASE_URL unset")
    return psycopg.connect(dsn, prepare_threshold=None, connect_timeout=5)


def write_checkpoint(
    *,
    callsign: str,
    source: str = "watchdog",
    task_id: str | None = None,
    pane_tail: str = "",
    position_text: str = "",
    artifact_pointer: dict | None = None,
) -> str | None:
    """INSERT a row into public.agent_checkpoints; return UUID or None on failure.

    Fail-open: any failure (DB unreachable, schema missing, etc.) logs +
    returns None so the caller's /clear path continues unaffected.
    """
    if not callsign:
        return None
    if not position_text or not position_text.strip():
        position_text = "(position not extractable)"
    pane_excerpt = pane_tail[-3000:] if pane_tail else ""
    try:
        with _connect() as conn, conn.cursor() as cur:
            import json  # noqa: PLC0415

            cur.execute(
                "INSERT INTO public.agent_checkpoints "
                "(callsign, task_id, artifact_pointer, position_text, pane_tail, captured_by) "
                "VALUES (%s, %s, %s::jsonb, %s, %s, %s) "
                "RETURNING id",
                (
                    callsign,
                    task_id or None,
                    json.dumps(artifact_pointer or {}),
                    position_text[:1000],
                    pane_excerpt,
                    source,
                ),
            )
            row = cur.fetchone()
        return str(row[0]) if row else None
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("checkpoint_writer: INSERT failed (fail-open): %s", exc)
        return None
