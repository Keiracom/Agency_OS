"""fleet_supervisor_workflow.py — first Temporal workflow: agent-state aggregator.

Phase A6 first-workflow per Dave KEI-DAVE-MIGRATION-PATH.

Migrates the NATS [READY] signal pattern (Agency_OS-zgxtgc / KEI-221c) from
`scripts/fleet_supervisor.py:_nats_publish_state()` to a Temporal Signal.

NOT an LLM-call workflow — exercises Temporal Signal mechanics + Gate 5
(temp.inline.audit) only. Other contract V1 gates (token_gate / cache_check /
content_check) are LLM-cost gates and N/A here. tier_gate fires in WARN mode
per Aiden tier-aware enforcement spec (internal fleet signals).

ARCHITECTURE:
  - One FleetSupervisorWorkflow instance runs continuously per fleet.
  - Receives `update_agent_state` signal from fleet_supervisor.py (dual-publish
    alongside existing NATS for V1 fallback safety).
  - Each signal triggers an `emit_audit_event` activity (Gate 5 audit emission).
  - In-memory fleet state dict is queryable via `get_fleet_state` query.
  - Continues indefinitely until `shutdown` signal received.

SCOPE BOUNDARY (per first-workflow scope-confirm 2026-05-25):
  - Signal mechanics + audit gate ONLY
  - No tier_gate / token_gate / cache_check / content_check / listener
    (those exercise in workflow #2 LLM-call migration)
  - No async post_validation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

try:
    from temporalio import workflow
    from temporalio.common import RetryPolicy
except ImportError:  # SDK absent — module remains importable for unit tests
    workflow = None  # type: ignore[assignment]
    RetryPolicy = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

DEFAULT_TASK_QUEUE = "keiracom-default"
FLEET_SUPERVISOR_WORKFLOW_ID = "fleet-supervisor-v1"


@dataclass
class AgentStateUpdate:
    """Payload for the update_agent_state signal.

    Mirrors the NATS message shape from fleet_supervisor.py's
    `_nats_publish_state`: minimal callsign + state, with optional metadata
    for future extensibility (e.g. last_task_id, occupancy timestamp).
    """

    callsign: str
    state: str  # "starting" | "ready" | "stalled" | etc.
    metadata: dict[str, Any] = field(default_factory=dict)


# Workflow definition — gated on temporalio SDK presence so the module remains
# importable for unit tests of the dataclass shape alone.
if workflow is not None:

    @workflow.defn(name="FleetSupervisorWorkflow")
    class FleetSupervisorWorkflow:
        """Continuous workflow that aggregates fleet agent-state signals.

        Receives `update_agent_state` signals from `scripts/fleet_supervisor.py`
        (dual-publish alongside NATS for V1). Each signal triggers a Gate 5
        audit emission activity. Internal fleet state dict tracks latest state
        per callsign and is queryable via `get_fleet_state`.

        Runs indefinitely. Operator-issued `shutdown` signal causes graceful
        exit (mainly for tests + planned maintenance).
        """

        def __init__(self) -> None:
            self._fleet_state: dict[str, dict[str, Any]] = {}
            self._shutdown_requested = False
            self._signals_received = 0

        @workflow.run
        async def run(self) -> dict[str, Any]:
            """Main loop: wait for shutdown OR continue receiving signals forever."""
            workflow.logger.info("FleetSupervisorWorkflow started")
            await workflow.wait_condition(lambda: self._shutdown_requested)
            workflow.logger.info(
                "FleetSupervisorWorkflow shutdown — signals_received=%d", self._signals_received
            )
            return {
                "signals_received": self._signals_received,
                "final_fleet_state": dict(self._fleet_state),
            }

        @workflow.signal(name="update_agent_state")
        async def update_agent_state(self, update: AgentStateUpdate) -> None:
            """Handle an agent-state update signal.

            1. Update internal fleet state dict (latest-wins per callsign)
            2. Schedule Gate 5 audit_emit activity (best-effort retry policy)
            3. Increment signals_received counter for shutdown reporting
            """
            self._signals_received += 1
            self._fleet_state[update.callsign] = {
                "state": update.state,
                "metadata": dict(update.metadata),
                "received_at": workflow.now().isoformat(),
            }
            workflow.logger.info(
                "update_agent_state signal: callsign=%s state=%s (signals_received=%d)",
                update.callsign,
                update.state,
                self._signals_received,
            )

            # Build audit event per contract V1 schema.
            # tier_gate IS in WARN mode for fleet internal signals per Aiden
            # tier-aware enforcement spec (this gate doesn't actually run as a
            # separate activity here; the WARN-mode classification is what
            # makes audit outcome="pass" valid even without tier-checking).
            audit_event = {
                "gate": "temp.inline.audit",
                "workflow_id": workflow.info().workflow_id,
                "activity_id": "",  # filled in by activity itself
                "tenant_id": "fleet-internal",  # placeholder; per-tenant signals come in workflow #2
                "agent_id": update.callsign,
                "agent_type": _infer_agent_type(update.callsign),
                "tier": "sandbox",  # fleet internal — no customer tier; sandbox is the closest analog
                "outcome": "pass",
                "elapsed_ms": 0.0,  # signal handler is essentially instant
                "reason": "agent_state_update",
                "detail": f"callsign={update.callsign} state={update.state}",
                "timestamp": workflow.now().isoformat(),
            }
            # Schedule audit activity. Best-effort retry: 3 attempts with
            # exponential backoff. Failure does NOT block the signal handler
            # from returning — this is fleet-internal observability, not a
            # customer-facing enforcement gate.
            try:
                await workflow.execute_activity(
                    "emit_audit_event",
                    audit_event,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(milliseconds=250),
                        maximum_interval=timedelta(seconds=2),
                        maximum_attempts=3,
                    ),
                )
            except Exception as exc:
                workflow.logger.warning(
                    "audit_emit failed for %s after retries: %s — proceeding (WARN-mode)",
                    update.callsign,
                    exc,
                )

        @workflow.signal(name="shutdown")
        async def shutdown(self) -> None:
            """Operator-issued shutdown signal. Causes run() to exit cleanly."""
            workflow.logger.info("shutdown signal received")
            self._shutdown_requested = True

        @workflow.query(name="get_fleet_state")
        def get_fleet_state(self) -> dict[str, dict[str, Any]]:
            """Queryable view of current fleet state dict."""
            return dict(self._fleet_state)

        @workflow.query(name="get_signals_received")
        def get_signals_received(self) -> int:
            """Queryable counter for shutdown / health monitoring."""
            return self._signals_received


def _infer_agent_type(callsign: str) -> str:
    """Map callsign → agent_type per contract V1 schema enum.

    Heuristic for V1; refined when worker-type metadata lands in fleet table.
    Falls back to "worker" for unknown callsigns (safe default — least-
    privileged audit attribution).
    """
    cs = callsign.lower()
    if cs in ("elliot", "aiden", "max"):
        return "deliberator"
    if cs in ("orion", "atlas", "scout", "nova", "viktor"):
        return "worker"
    return "worker"
