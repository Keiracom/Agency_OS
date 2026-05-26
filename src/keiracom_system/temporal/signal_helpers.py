"""signal_helpers.py — caller-side helpers for sending Temporal signals.

Phase A6 first-workflow per Dave KEI-DAVE-MIGRATION-PATH.

Used by `scripts/fleet_supervisor.py` to dual-publish agent-state updates
during the V1 NATS → Temporal transition (per first-target scope-confirm
2026-05-25: dual-publish for 7 days, then flip Temporal-only).

DESIGN NOTE — best-effort signal:
  Failure to signal does NOT raise. NATS publish remains the operational
  source of truth; Temporal signal is observability-track during dual-publish
  window. A logged warning surfaces missed signals to deliberators without
  breaking the fleet supervisor loop.

DESIGN NOTE — per-call connect:
  fleet_supervisor.py runs every ~60s; ~50-100ms Temporal connect overhead
  per signal is acceptable for V1. Connection-pooling lands as a separate
  refinement bd if signal volume grows.
"""

from __future__ import annotations

import logging
from typing import Any

from .client import TemporalConnectError, from_env
from .fleet_supervisor_workflow import (
    FLEET_SUPERVISOR_WORKFLOW_ID,
    AgentStateUpdate,
)

log = logging.getLogger(__name__)


async def signal_fleet_supervisor(
    callsign: str,
    state: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Best-effort: signal the FleetSupervisorWorkflow with an agent-state update.

    Returns True on signal sent; False on any error (logged). Does NOT raise —
    fleet supervisor cannot afford to crash on a degraded observability sink.

    Pre-conditions:
      - TEMPORAL_ADDR env set (e.g. 45.76.114.137:7233)
      - FleetSupervisorWorkflow already started on the worker (workflow id
        FLEET_SUPERVISOR_WORKFLOW_ID via signal-with-start would work; for
        V1 we assume operator started the workflow once via tctl/UI)
    """
    try:
        client = await from_env()
    except (OSError, TemporalConnectError) as exc:
        log.warning(
            "temporal signal SKIPPED for %s/%s — env or connect: %s",
            callsign,
            state,
            exc,
        )
        return False

    update = AgentStateUpdate(callsign=callsign, state=state, metadata=metadata or {})
    try:
        handle = client.get_workflow_handle(FLEET_SUPERVISOR_WORKFLOW_ID)
        await handle.signal("update_agent_state", update)
        log.info("temporal signal sent: %s state=%s", callsign, state)
        return True
    except Exception as exc:
        log.warning(
            "temporal signal failed for %s/%s — workflow signal error: %s",
            callsign,
            state,
            exc,
        )
        return False


def signal_fleet_supervisor_sync(
    callsign: str,
    state: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Sync wrapper for callers that aren't async (fleet_supervisor.py main path).

    Runs the async coroutine via asyncio.run; safe because fleet_supervisor.py
    invocation is synchronous outside its asyncio internals.
    """
    import asyncio

    try:
        return asyncio.run(signal_fleet_supervisor(callsign, state, metadata))
    except Exception as exc:
        log.warning("temporal signal sync wrapper error for %s/%s: %s", callsign, state, exc)
        return False
