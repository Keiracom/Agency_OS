#!/usr/bin/env python3
"""agent_activity.py — combine DB activity_state with filesystem inbox check.

Companion to public.agent_activity_signal + public.fleet_liveness_status. The
DB views surface activity_state ∈ {active, idle, no_data}; this module adds the
fourth state `idle_with_work_queued` by checking
/tmp/telegram-relay-<callsign>/inbox/ for pending messages.

A SQL view CANNOT read the filesystem; the existing context_watchdog (per
scripts/orchestrator/context_watchdog.py — current trigger: IDLE_TIMEOUT_MIN=40
on pane-unchanged + WAKE_TIMEOUT_SEC=1200 before escalation) can call this
function to refine its decision: an `idle_with_work_queued` agent is a stronger
signal than plain `idle` (work is waiting, the agent is not just quietly
finished) — the watchdog should prioritise wake/respawn for that state.

This file does NOT build a new restart loop (scope hard limit from dispatch).
It exposes a signal the existing watchdog can consume.

Usage:
  from scripts.orchestrator.agent_activity import compute_activity_state
  state = compute_activity_state("nova")          # uses default DB + FS paths
  # state ∈ {"active", "idle", "idle_with_work_queued", "no_data"}

Dispatched by Elliot 2026-06-03 ref: scout-agent-activity-signal.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ActivityState = Literal["active", "idle", "idle_with_work_queued", "no_data"]

INBOX_PATH_TEMPLATE = "/tmp/telegram-relay-{callsign}/inbox"

_QUERY = """
SELECT activity_state FROM public.agent_activity_signal WHERE callsign = %s
"""


def _resolve_dsn() -> str | None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not raw:
        return None
    return raw.replace("postgresql+asyncpg://", "postgresql://", 1)


def _default_db_state(callsign: str) -> ActivityState:
    """Read activity_state for `callsign` from public.agent_activity_signal.

    Returns 'no_data' on any failure (missing DSN, psycopg unavailable, DB
    unreachable, callsign absent from the view).
    """
    dsn = _resolve_dsn()
    if not dsn:
        return "no_data"
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        return "no_data"
    try:
        with (
            psycopg.connect(dsn, prepare_threshold=None) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(_QUERY, (callsign,))
            row = cur.fetchone()
        if row is None:
            return "no_data"
        value = row[0]
        if value in ("active", "idle"):
            return value  # type: ignore[return-value]
        return "no_data"
    except Exception as exc:  # noqa: BLE001 — fail-open per signal-not-control contract
        logger.debug("agent_activity: DB read failed for %s: %s", callsign, exc)
        return "no_data"


def _default_inbox_has_pending(callsign: str) -> bool:
    """True iff /tmp/telegram-relay-<callsign>/inbox/ contains at least one
    regular file. Missing dir / permission errors return False (fail-closed
    on the inbox signal — never invent work that isn't there)."""
    inbox = Path(INBOX_PATH_TEMPLATE.format(callsign=callsign))
    try:
        if not inbox.is_dir():
            return False
        for entry in inbox.iterdir():
            if entry.is_file():
                return True
    except OSError as exc:
        logger.debug("agent_activity: inbox check failed for %s: %s", callsign, exc)
    return False


def compute_activity_state(
    callsign: str,
    *,
    db_state_fn: Callable[[str], ActivityState] | None = None,
    inbox_has_pending_fn: Callable[[str], bool] | None = None,
) -> ActivityState:
    """Combine DB activity_state with the per-callsign inbox check.

    Returns one of:
      - 'active' — DB says agent has tool calls in last 10m. Inbox not checked.
      - 'idle_with_work_queued' — DB says idle AND inbox has pending file(s).
      - 'idle' — DB says idle AND inbox empty.
      - 'no_data' — DB query failed or callsign absent from agent_activity_signal.

    `db_state_fn` and `inbox_has_pending_fn` are injection hooks for tests —
    production callers leave both None.
    """
    get_db_state = db_state_fn or _default_db_state
    has_pending = inbox_has_pending_fn or _default_inbox_has_pending

    db_state = get_db_state(callsign)
    if db_state == "active":
        return "active"
    if db_state == "no_data":
        return "no_data"
    # db_state == "idle" — check inbox for queued work
    return "idle_with_work_queued" if has_pending(callsign) else "idle"


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: agent_activity.py <callsign>", file=sys.stderr)
        raise SystemExit(2)
    print(compute_activity_state(sys.argv[1]))
