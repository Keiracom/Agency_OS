"""src/session_store — Drevon PR-A write paths for the 5-table session store.

Public interface:
    record_session_start(...) — open a sessions row when Claude Code launches.
    record_message(...) — append a messages row.
    record_turn_start(...) — open a turns row.
    record_tool_call(...) — append a turn_logs row with optional turn_files rows.
    record_turn_complete(...) — close a turns row with cost rollup.
    record_session_end(...) — close a sessions row (status='closed').
    mark_session_stuck(...) — watchdog marks status='stuck'.

Hooks under .claude/hooks/ invoke these via subprocess. Models live in
src/models/session_store.py; migration is supabase/migrations/20260511_drevon_session_store.sql.
"""

from src.session_store.recorder import (
    mark_session_stuck,
    record_message,
    record_session_end,
    record_session_start,
    record_tool_call,
    record_turn_complete,
    record_turn_start,
)

__all__ = [
    "mark_session_stuck",
    "record_message",
    "record_session_end",
    "record_session_start",
    "record_tool_call",
    "record_turn_complete",
    "record_turn_start",
]
