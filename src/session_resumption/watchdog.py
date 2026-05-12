"""watchdog.py — mark stale active sessions as status='stuck'.

Periodic sweep entry point. Finds sessions where status='active' AND
ended_at IS NULL AND started_at < NOW() - INTERVAL stuck_minutes, then
calls session_store.recorder.mark_session_stuck on each (which sets
ended_at and status='stuck' atomically per row).

PR-C clean-close note: rows with status='closed_clean' are LEFT ALONE.
Those are planned-restart targets owned by the Stop hook + resolver pair.
The resolver's started_at freshness window prevents resumption of stale
closed_clean rows; no need for the watchdog to reap them.

Called from .claude/hooks/session_resumption_watchdog.sh on a cadence
chosen by the operator (cron / systemd timer / agent loop).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.evo.supabase_client import sb_get

logger = logging.getLogger("session_resumption.watchdog")

DEFAULT_STUCK_MINUTES = 60


def clear_stuck_sessions(
    callsign: str | None = None,
    stuck_minutes: int = DEFAULT_STUCK_MINUTES,
) -> int:
    """Mark stale active sessions as status='stuck'. Returns count cleared.

    callsign=None scans all callsigns; pass a single callsign to scope. Best
    -effort: failures log + return 0 rather than raise (watchdog must never
    crash the surrounding scheduler).
    """
    cutoff_iso = (datetime.now(UTC) - timedelta(minutes=stuck_minutes)).isoformat()
    params: dict[str, str] = {
        "status": "eq.active",
        "ended_at": "is.null",
        "started_at": f"lt.{cutoff_iso}",
        "deleted_at": "is.null",
        "select": "id",
    }
    if callsign:
        params["callsign"] = f"eq.{callsign}"
    try:
        rows = sb_get("sessions", params)
    except Exception as exc:
        logger.warning("clear_stuck_sessions sb_get failed: %s", exc)
        return 0
    # Lazy import — keeps recorder/.env loading off the resolver-only test path.
    from src.session_store.recorder import mark_session_stuck

    cleared = 0
    for row in rows:
        sid = row.get("id")
        if not sid:
            continue
        try:
            mark_session_stuck(UUID(sid))
            cleared += 1
        except Exception as exc:
            logger.warning("mark_session_stuck failed for %s: %s", sid, exc)
    if cleared:
        logger.info(
            "watchdog cleared %d stuck session(s) (callsign=%s, stuck_minutes=%d)",
            cleared,
            callsign or "<all>",
            stuck_minutes,
        )
    return cleared
