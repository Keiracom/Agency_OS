#!/usr/bin/env python3
"""kei45_realtime_listener.py — KEI-45 Phase A.2 wake-up listener.

Single global Python daemon subscribing to public.tasks Supabase Realtime
postgres_changes channel. On INSERT/UPDATE event where status='available',
injects 'bd ready' into ALL 6 agent tmux panes via tmux send-keys.

This is the LISTENER half of KEI-45 — the wake-up trigger. Server-side
trigger + Realtime publication shipped in PR #860 Phase A (Components 1).
This script consumes those events agent-side.

Per Dave acceptance criterion (KEI-45 reopen ts ~1778742900): 'Orion wakes
up automatically when a task becomes available.' This script delivers
that runtime behavior. Without it, the trigger fires but nothing
consumes the event.

Fallback hierarchy:
  1. This listener (primary) — sub-second wake-up via Realtime websocket.
  2. KEI-45 idle daemon (kei45_idle_daemon.sh, 15-min ceiling, shipped PR #860 Component 6).
  3. KEI-63 bd-complete-hook (shipped) — next-task auto-injection on completion.

Idempotent: tmux send-keys is no-op if pane is busy (key buffer queues).
Crash-safe: systemd Restart=on-failure brings listener back; postgres_changes
re-subscribes from latest event on reconnect.

Usage:
    python3 scripts/orchestrator/kei45_realtime_listener.py
    # OR via systemd: systemctl --user start kei45-realtime-listener
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import time
from typing import Any

logger = logging.getLogger("kei45_realtime_listener")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Canonical callsign → tmux session map. Mirrors elliot_polling_loop.py
# CALLSIGN_TO_TMUX. Update in lockstep if that source changes.
CALLSIGN_TO_TMUX: dict[str, str] = {
    "elliot": "elliottbot",
    "aiden": "aiden",
    "max": "maxbot",
    "atlas": "atlas",
    "orion": "orion",
    "scout": "scout",
}

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY", "")
)

# Re-trigger debounce: don't fire on rapid bursts; one wake-up per agent
# per N seconds (events are deduped by recency).
DEBOUNCE_SECONDS = 5.0

_last_wake_at: dict[str, float] = {}


def inject_bd_ready_into_pane(callsign: str) -> None:
    """Send 'bd ready' into the agent's tmux pane via tmux send-keys.

    Idempotent: tmux queues the keystroke; if the pane is mid-execution the
    keystroke lands at the next prompt. Debounced by DEBOUNCE_SECONDS so
    rapid task-event bursts don't queue 10 'bd ready' lines.
    """
    now = time.time()
    last = _last_wake_at.get(callsign, 0.0)
    if (now - last) < DEBOUNCE_SECONDS:
        logger.debug("debounced wake for %s (last %.1fs ago)", callsign, now - last)
        return

    tmux_session = CALLSIGN_TO_TMUX.get(callsign)
    if not tmux_session:
        logger.warning("no tmux session mapping for %s; skipping", callsign)
        return

    has_session = subprocess.run(  # noqa: S603 — fixed args
        ["tmux", "has-session", "-t", tmux_session],
        capture_output=True,
        timeout=3,
        check=False,
    )
    if has_session.returncode != 0:
        logger.warning("tmux session %s not running; skipping (KEI-43 should restart)", tmux_session)
        return

    result = subprocess.run(  # noqa: S603 — fixed args
        [
            "tmux",
            "send-keys",
            "-t",
            tmux_session,
            f"bd ready  # KEI-45 listener wake-up at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            "Enter",
        ],
        capture_output=True,
        timeout=3,
        check=False,
    )
    if result.returncode == 0:
        _last_wake_at[callsign] = now
        logger.info("WAKE %s (tmux=%s)", callsign, tmux_session)
    else:
        logger.warning("tmux send-keys failed for %s rc=%d", callsign, result.returncode)


def on_task_event(payload: dict[str, Any]) -> None:
    """Realtime callback. supabase-py 2.x delivers payload shape:
        {"data": {"type": INSERT|UPDATE, "record": {...}, ...}, "ids": [...]}

    Fires wake-up on INSERT or UPDATE where status='available'. Empirical
    payload shape confirmed via DEBUG-log smoke test 2026-05-14.
    """
    data = payload.get("data") or {}
    event_type = data.get("type")
    if hasattr(event_type, "value"):
        event_type = event_type.value
    record = data.get("record") or {}
    status = record.get("status")
    kei_id = record.get("id", "?")

    if event_type in ("INSERT", "UPDATE") and status == "available":
        logger.info("EVENT %s available %s — fanning out wake-up", event_type, kei_id)
        for callsign in CALLSIGN_TO_TMUX:
            inject_bd_ready_into_pane(callsign)
    else:
        logger.debug("EVENT ignored type=%s status=%s id=%s", event_type, status, kei_id)


async def async_main() -> int:
    """Block-subscribe to public.tasks Realtime postgres_changes channel.

    supabase-py 2.x supports Realtime ONLY in the async client (sync raises
    NotImplementedError on channel()). Caught by empirical smoke 2026-05-14
    pre-merge — see PR #869 amend log.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY/SUPABASE_ANON_KEY env vars required")
        return 2

    try:
        from supabase import acreate_client  # type: ignore[import-untyped]
    except ImportError:
        logger.error("supabase-py not installed; pip install supabase>=2.3.0")
        return 2

    client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    channel = client.channel("kei45-task-events")
    for ev in ("INSERT", "UPDATE"):
        channel.on_postgres_changes(
            event=ev,
            schema="public",
            table="tasks",
            callback=on_task_event,
        )
    def _subscribe_state(state, err):  # type: ignore[no-untyped-def]
        logger.info("channel state: %s (err=%s)", state, err)

    await channel.subscribe(_subscribe_state)
    logger.info("subscribe() returned — waiting for SUBSCRIBED state...")

    stop_event = asyncio.Event()

    def _shutdown(signum, frame):  # type: ignore[no-untyped-def]
        logger.info("received signal %d; shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    await stop_event.wait()

    try:
        await channel.unsubscribe()
    except Exception:  # noqa: BLE001 — best-effort on shutdown
        pass
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
