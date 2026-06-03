"""checkpoint_reader.py — replay the open checkpoint into REVIVED text.

Part of context_checkpoint_resume (gate_roadmap 952c8d0d). Reader is fail-open:
any failure logs + returns None → caller falls through to static REVIVED text.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _connect():
    """Mirrors checkpoint_writer._connect."""
    import psycopg  # noqa: PLC0415

    dsn = os.environ.get("DATABASE_URL_MIGRATIONS") or os.environ.get("DATABASE_URL", "")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not dsn:
        raise RuntimeError("DATABASE_URL_MIGRATIONS / DATABASE_URL unset")
    return psycopg.connect(dsn, prepare_threshold=None, connect_timeout=5)


def fetch_open_checkpoint(callsign: str) -> dict[str, Any] | None:
    """Most recent UN-consumed checkpoint for `callsign`, else None."""
    if not callsign:
        return None
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, callsign, task_id, position_text, pane_tail, "
                "captured_at, captured_by "
                "FROM public.agent_checkpoints "
                "WHERE callsign = %s AND consumed_at IS NULL "
                "ORDER BY captured_at DESC LIMIT 1",
                (callsign,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "callsign": row[1],
            "task_id": row[2],
            "position_text": row[3],
            "pane_tail": row[4] or "",
            "captured_at": row[5].isoformat() if row[5] else "",
            "captured_by": row[6],
        }
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("checkpoint_reader: SELECT failed (fail-open): %s", exc)
        return None


def format_resume_block(checkpoint: dict[str, Any]) -> str:
    """Render the checkpoint as a self-contained markdown block for tmux injection."""
    task_line = (
        f"Task: {checkpoint['task_id']}" if checkpoint.get("task_id") else "Task: (untracked)"
    )
    pane_excerpt = (checkpoint.get("pane_tail") or "")[-1000:]
    return (
        "--- CHECKPOINT (captured "
        f"{checkpoint.get('captured_at', '?')} by {checkpoint.get('captured_by', '?')}) ---\n"
        f"You were here: {checkpoint.get('position_text', '(unknown)')}\n"
        f"{task_line}\n"
        "Recent pane (last ~1000 chars):\n"
        f"{pane_excerpt}\n"
        "--- END CHECKPOINT ---\n\n"
        "Resume that task — do NOT redo what is above. Read IDENTITY.md if needed, "
        "continue from where you were. No paid chain runs without approval."
    )


def mark_consumed(checkpoint_id: str, reason: str) -> bool:
    """Set consumed_at = NOW(), consumed_reason = reason. Returns True on success."""
    if not checkpoint_id:
        return False
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE public.agent_checkpoints "
                "SET consumed_at = NOW(), consumed_reason = %s "
                "WHERE id = %s::uuid AND consumed_at IS NULL",
                (reason[:200], checkpoint_id),
            )
            return cur.rowcount == 1
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("checkpoint_reader: mark_consumed failed (fail-open): %s", exc)
        return False
