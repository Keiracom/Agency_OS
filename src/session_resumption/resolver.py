"""resolver.py — read + claim Claude Code session_uuid for a callsign.

Read path (resolve_session_uuid): PostgREST GET on sessions, filtered to
watchdog-fresh + status='active' + session_uuid IS NOT NULL, ordered by
started_at desc, limit 1. Returns the session_uuid string or None.

Write path (claim_session_uuid): delegates to src.session_store.recorder
.record_session_start to keep schema knowledge in one place. Returns the
row UUID or None (best-effort — never raises).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from src.evo.supabase_client import sb_get

logger = logging.getLogger("session_resumption.resolver")

DEFAULT_FRESH_MINUTES = 30


def resolve_session_uuid(
    callsign: str,
    fresh_minutes: int = DEFAULT_FRESH_MINUTES,
) -> str | None:
    """Return the most-recent resumable session_uuid for callsign, or None.

    Resumable = ended_at IS NULL AND status='active' AND session_uuid IS NOT
    NULL AND started_at >= NOW() - INTERVAL fresh_minutes. Best-effort: any
    Supabase failure logs + returns None so the launcher falls through to a
    fresh session rather than blocking.
    """
    cutoff_iso = (datetime.now(UTC) - timedelta(minutes=fresh_minutes)).isoformat()
    params = {
        "callsign": f"eq.{callsign}",
        "status": "eq.active",
        "ended_at": "is.null",
        "session_uuid": "not.is.null",
        "started_at": f"gte.{cutoff_iso}",
        "deleted_at": "is.null",
        "select": "session_uuid",
        "order": "started_at.desc",
        "limit": "1",
    }
    try:
        rows = sb_get("sessions", params)
    except Exception as exc:
        logger.warning("resolve_session_uuid sb_get failed for %s: %s", callsign, exc)
        return None
    if not rows:
        return None
    return rows[0].get("session_uuid")


def claim_session_uuid(
    callsign: str,
    session_uuid: str,
    working_directory: str,
    *,
    tmux_session: str | None = None,
    model_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> UUID | None:
    """Open a sessions row marking this session_uuid as active for callsign.

    Thin pass-through to src.session_store.recorder.record_session_start so
    schema details (column names, defaults, soft-delete) stay in one place.
    Returns the new sessions.id UUID, or None on failure (best-effort).
    """
    # Imported lazily so tests can monkey-patch without the recorder's
    # supabase_client import (which loads .env at module import time) being
    # required when only resolver paths are exercised.
    from src.session_store.recorder import record_session_start

    return record_session_start(
        callsign,
        working_directory,
        session_uuid=session_uuid,
        tmux_session=tmux_session,
        model_id=model_id,
        extra=extra,
    )
