"""audit_activity.py — Temporal activity that emits Gate 5 (temp.inline.audit) events.

Phase A6 first-workflow build per Dave KEI-DAVE-MIGRATION-PATH.

CANONICAL KEY ANCHOR — temporal_contract_v1.md §"Common audit event schema":
  {
    "gate": "temp.inline.<name>",
    "workflow_id": "<temporal_workflow_id>",
    "activity_id": "<temporal_activity_id>",
    "tenant_id": "<uuid>",
    "agent_id": "<callsign or ephemeral spawn id>",
    "agent_type": "chat | worker | deliberator | reasoning_listener",
    "tier": "sandbox | solo | pro | team | enterprise",
    "outcome": "pass | block | warn | error",
    "elapsed_ms": <observed>,
    "reason": "<machine-readable>",
    "detail": "<human-readable, sanitised; no raw secrets, no customer payload>",
    "timestamp": "<ISO-8601 UTC>"
  }

Stream destinations per contract V1:
  1. Temporal workflow event history — AUTOMATIC via activity completion event
     (every activity execution becomes an event in the workflow's history)
  2. Layer 12 observability sink — via Atlas's mem.wrap.trace composition
     (PR #1134); V1 best-effort with degrade-gracefully on Hindsight unreach
  3. Customer-visible audit log if tier >= Pro — DEFERRED (no Pro customers yet;
     fleet-internal [READY] signal is operator-facing, not customer-visible)

Per contract V1 cross-cutting principle "Fail-closed default":
  - If audit emission ERRORS, the calling workflow's outcome is BLOCK
    (audit is non-optional for compliance posture)
  - Exception: Hindsight transient unreachable -> WARN + continue
    (don't block fleet signals on observability sink degraded)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Literal

try:
    from temporalio import activity
except ImportError:  # SDK absent — module remains importable for unit tests
    activity = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

AuditOutcome = Literal["pass", "block", "warn", "error"]
AgentType = Literal["chat", "worker", "deliberator", "reasoning_listener"]
Tier = Literal["sandbox", "solo", "pro", "team", "enterprise"]


def build_audit_event(
    *,
    gate: str,
    tenant_id: str,
    agent_id: str,
    agent_type: AgentType,
    tier: Tier,
    outcome: AuditOutcome,
    elapsed_ms: float,
    reason: str,
    detail: str,
    workflow_id: str = "",
    activity_id: str = "",
) -> dict[str, Any]:
    """Construct an audit event dict per contract V1 schema.

    Pure function (no I/O). Workflow + activity IDs default empty when called
    outside a Temporal context (e.g. unit tests); the activity wrapper below
    fills them from `activity.info()` when running inside Temporal.
    """
    return {
        "gate": gate,
        "workflow_id": workflow_id,
        "activity_id": activity_id,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "agent_type": agent_type,
        "tier": tier,
        "outcome": outcome,
        "elapsed_ms": float(elapsed_ms),
        "reason": reason,
        "detail": detail,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def emit_audit_event(event: dict[str, Any]) -> str:
    """Temporal activity: emit a single audit event per contract V1.

    Returns the event timestamp string as a correlation id for the caller.

    Stream 1 (Temporal event history): automatic — the activity execution
    itself is the history event. We additionally log the event payload at
    INFO so the Temporal UI shows it inline.

    Stream 2 (Hindsight observability sink): best-effort. Not wired in this
    first-workflow PR — placeholder TODO calls Atlas's mem.wrap.trace once
    the wrapper-instance is available via env config. Logged at INFO when
    skipped so deliberators see the missing-integration explicitly.
    """
    # Stream 1 — Temporal event history (automatic via this activity call).
    # Log at INFO so the audit event payload is visible in Temporal UI.
    log.info(
        "audit_event gate=%s outcome=%s detail=%s",
        event["gate"],
        event["outcome"],
        event["detail"][:120],
    )

    # Stream 2 — Hindsight observability sink (TODO: wire when Atlas wrappers
    # ship a client-from-env factory; tracked as separate follow-up).
    # For V1 first-workflow we LOG the skip explicitly so we have visibility
    # into the gap rather than silently dropping events on the floor.
    log.info(
        "audit_event hindsight_emit=skipped reason=stream2_wrapper_pending agent_id=%s",
        event["agent_id"],
    )

    # Stream 3 — customer-visible audit log if tier >= pro. Skipped per contract
    # V1 §"Customer-visible audit log if tier >= Pro" — no Pro customers yet;
    # [READY] signal is fleet-internal.

    # Enrich event with workflow + activity ids if running inside Temporal context
    if activity is not None:
        try:
            info = activity.info()
            event["workflow_id"] = info.workflow_id
            event["activity_id"] = info.activity_id
        except Exception:  # outside activity context (e.g. test path)
            pass

    return event["timestamp"]


# Register decoration applied at module load when temporalio SDK is present.
# Keeps the function importable + unit-testable without SDK (decorator becomes
# a no-op via the None fallback above).
if activity is not None:
    emit_audit_event = activity.defn(name="emit_audit_event")(emit_audit_event)  # type: ignore[assignment]
