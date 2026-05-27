"""Context-window budget gate — dispatcher hook layer (Step 4.5 wiring PR #3).

Wires `src.relay.context_budget.check_context_budget` (PR #1210 / Cat 21
lever 25 / cutover-blocker 3) into dispatcher_main's pre-spawn lifecycle.
The check shipped as a module on main but dispatcher_main.py did not call it.

ROLE DERIVATION:
  Per Cat 21 lever 25 ceilings (PR #1210):
    Reviewer 8K / Deliberator 20K / Builder 12K / Chat 4K

  Heuristic from envelope:
    - explicit "role" field on envelope wins (reviewer/deliberator/builder/chat)
    - envelope.task_type from attribution taxonomy (PR #1207/#1209):
        pr_review     → reviewer
        deliberation  → deliberator
        build         → builder
        chat          → chat
    - else → builder (default; conservative — builder ceiling is mid-range)

CONTEXT DERIVATION:
  The dispatcher hasn't composed the full prompt yet at the gate point
  (composition happens inside _spawn.handle_envelope). For the pre-spawn
  pre-check, we use envelope.brief / summary / text / task_ref as a
  conservative proxy. Phase 2 follow-up wires the gate POST-composition
  (inside _spawn.handle_envelope) once the composer-result protocol is
  stabilised — for Phase 1 the envelope-only check catches gross over-
  budget envelopes before any composition cost.

DECISION → ACTION mapping:
  SPAWN_OK    → PROCEED (under ceiling)
  SUMMARISED  → PROCEED (summariser compressed to fit)
  REJECTED    → SKIP_SPAWN (over ceiling + no summariser or summary still over)

bd: cutover-step-4.5-dispatcher-wiring-pr3
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from src.relay.context_budget import (
    DECISION_REJECTED,
    DECISION_SPAWN_OK,
    DECISION_SUMMARISED,
    ROLE_BUILDER,
    ROLE_CEILINGS,
    ROLE_CHAT,
    ROLE_DELIBERATOR,
    ROLE_REVIEWER,
    BudgetResult,
    check_context_budget,
)

log = logging.getLogger(__name__)


class ContextWindowAction:
    """Marker constants for the action evaluate() returns."""

    PROCEED = "proceed"
    SKIP_SPAWN = "skip_spawn"


_TASK_TYPE_TO_ROLE: Mapping[str, str] = {
    "pr_review": ROLE_REVIEWER,
    "deliberation": ROLE_DELIBERATOR,
    "build": ROLE_BUILDER,
    "chat": ROLE_CHAT,
}


def _envelope_to_role(envelope: Mapping[str, Any]) -> str:
    """Derive role from envelope; default ROLE_BUILDER for unknowns."""
    explicit = str(envelope.get("role") or "").lower().strip()
    if explicit in ROLE_CEILINGS:
        return explicit

    task_type = str(envelope.get("task_type") or "").lower().strip()
    if task_type in _TASK_TYPE_TO_ROLE:
        return _TASK_TYPE_TO_ROLE[task_type]

    return ROLE_BUILDER


def _envelope_to_context(envelope: Mapping[str, Any]) -> str:
    """Extract a context-shaped string from envelope for the pre-check.

    Returns "" when no content field is present; caller fail-opens to PROCEED
    (cannot check what cannot be assembled).
    """
    parts: list[str] = []
    for field in ("brief", "summary", "text", "task_ref"):
        value = envelope.get(field)
        if value:
            parts.append(str(value))
    return " ".join(parts)


def evaluate(
    envelope: Mapping[str, Any],
    *,
    enabled: bool = False,
    summariser: Any = None,
    alerts_emitter: Any = None,
) -> tuple[str, BudgetResult | None]:
    """Run pre-spawn context-window budget check against an envelope.

    Returns (action, budget_result). action is PROCEED or SKIP_SPAWN.

    Fail-open by design:
      - enabled=False (rollout phase 1) → PROCEED, None
      - envelope-derived context empty → PROCEED, None (cannot assess; caller
        proceeds — the gate is a safety-net, not a strict requirement)
      - check_context_budget exception → PROCEED, None (DB/network class issues
        should not block legitimate dispatches at the gate layer)
    """
    if not enabled:
        return ContextWindowAction.PROCEED, None

    context = _envelope_to_context(envelope)
    if not context:
        log.debug("context-window gate skip: envelope has no content fields")
        return ContextWindowAction.PROCEED, None

    role = _envelope_to_role(envelope)
    try:
        kwargs: dict[str, Any] = {}
        if summariser is not None:
            kwargs["summariser"] = summariser
        if alerts_emitter is not None:
            kwargs["alerts_emitter"] = alerts_emitter
        result = check_context_budget(role, context, **kwargs)
    except Exception:  # noqa: BLE001 — fail-open per gate-layer design
        log.exception("context-window gate raised — failing open")
        return ContextWindowAction.PROCEED, None

    if result.decision in (DECISION_SPAWN_OK, DECISION_SUMMARISED):
        return ContextWindowAction.PROCEED, result
    if result.decision == DECISION_REJECTED:
        return ContextWindowAction.SKIP_SPAWN, result
    return ContextWindowAction.PROCEED, result
