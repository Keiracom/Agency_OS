"""src/session_resumption — Drevon PR-C Claude Code session UUID resumption.

Public interface:
    resolve_session_uuid(callsign, fresh_minutes=30) -> str | None
        Look up the most-recent watchdog-fresh session_uuid for callsign.
        None if no resumable session.

    claim_session_uuid(callsign, session_uuid, working_directory, **opts) -> UUID | None
        Open a sessions row marking session_uuid as active. Delegates to
        src.session_store.recorder.record_session_start. Best-effort; returns
        the row UUID or None on failure.

    clear_stuck_sessions(callsign=None, stuck_minutes=60) -> int
        Mark sessions with ended_at IS NULL AND started_at < cutoff as
        status='stuck'. Returns count cleared. Watchdog entry point.

Schema source of truth: supabase/migrations/20260511_drevon_session_store.sql
(PR #715). Hooks recording side: src/session_store/recorder.py.

Design notes:
  - Freshness measured from sessions.started_at (no last_activity column on
    sessions per current schema). Watchdog complements this by reaping rows
    that exceed stuck_minutes regardless of activity.
  - Resolver excludes status='stuck' and status='closed' explicitly so
    clear_stuck_sessions takes effect immediately.
  - All DB writes are best-effort: if Supabase is unreachable the launcher
    must still spawn `claude` with a fresh UUID rather than block startup.
"""

from src.session_resumption.resolver import claim_session_uuid, resolve_session_uuid
from src.session_resumption.watchdog import clear_stuck_sessions

__all__ = [
    "claim_session_uuid",
    "clear_stuck_sessions",
    "resolve_session_uuid",
]
