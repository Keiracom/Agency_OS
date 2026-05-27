"""Budget ceiling gate — dispatcher hook layer (Step 4.5 wiring PR #2).

Wires the BudgetCeilingGate (PR #1203 / Cat 21 lever 28 / cutover-blocker 2)
into dispatcher_main's pre-spawn lifecycle hook. The gate shipped as a module
on main but dispatcher_main.py did not call it — code-on-main but NOT WIRED.

DESIGN:
  - Single sync entry-point `evaluate(envelope, *, budget_gate)`.
  - BudgetCeilingGate.check_budget is sync (DB read only) — no asyncio needed.
  - Decision mapping:
      SPAWN_OK / OVERAGE_LOG_AND_SPAWN / DAVE_BYPASS / FORCE_OVERRIDE → PROCEED
      QUEUE_NEXT_DAY / DROP_WITH_LOG                                  → SKIP_SPAWN
  - DI: caller passes the gate; tests inject a fake gate without DB.
  - Fail-open per PR #1203 contract: DB read failures → SPAWN_OK internally,
    surface as PROCEED here.

PRIORITY DERIVATION from envelope:
  - explicit "priority" field on envelope (HIGH/NORMAL/LOW) wins
  - sender "dave" → high
  - sender "elliot" → high (orchestrator-tier)
  - default → normal

SOURCE DERIVATION:
  - explicit "source" field on envelope wins
  - sender "dave" → SOURCE_DAVE_DM (triggers Haiku-bypass)
  - else → SOURCE_FLEET

bd: cutover-step-4.5-dispatcher-wiring-pr2
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from src.relay.budget_ceiling import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    SOURCE_DAVE_DM,
    SOURCE_FLEET,
    BudgetCeilingGate,
    BudgetCheckResult,
    BudgetDecision,
)

log = logging.getLogger(__name__)


class BudgetAction:
    """Marker constants for the action evaluate() returns."""

    PROCEED = "proceed"
    SKIP_SPAWN = "skip_spawn"


_PROCEED_DECISIONS: frozenset[BudgetDecision] = frozenset(
    {
        BudgetDecision.SPAWN_OK,
        BudgetDecision.OVERAGE_LOG_AND_SPAWN,
        BudgetDecision.DAVE_BYPASS,
        BudgetDecision.FORCE_OVERRIDE,
    }
)


def _envelope_to_priority_source(envelope: Mapping[str, Any]) -> tuple[str, str]:
    """Derive (priority, source) from envelope for the budget check."""
    explicit_priority = str(envelope.get("priority") or "").lower().strip()
    if explicit_priority in {PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW}:
        priority = explicit_priority
    else:
        sender = str(envelope.get("from") or "").lower().strip()
        priority = PRIORITY_HIGH if sender in {"dave", "elliot"} else PRIORITY_NORMAL

    explicit_source = str(envelope.get("source") or "").strip()
    if explicit_source in {SOURCE_DAVE_DM, SOURCE_FLEET}:
        source = explicit_source
    else:
        sender = str(envelope.get("from") or "").lower().strip()
        source = SOURCE_DAVE_DM if sender == "dave" else SOURCE_FLEET

    return priority, source


def evaluate(
    envelope: Mapping[str, Any],
    *,
    budget_gate: BudgetCeilingGate | None = None,
) -> tuple[str, BudgetCheckResult | None]:
    """Run the pre-spawn budget gate against a routed envelope.

    Returns (action, budget_result). action is PROCEED or SKIP_SPAWN.
    budget_result is non-None when a gate was wired AND ran.

    Fail-open by design:
      - no gate wired → PROCEED, None (rollout phase 1 default)
      - any DB / alert exception inside the gate → BudgetCeilingGate fail-opens
        internally (returns SPAWN_OK) per PR #1203 contract; we surface PROCEED
    """
    if budget_gate is None:
        return BudgetAction.PROCEED, None

    priority, source = _envelope_to_priority_source(envelope)
    result = budget_gate.check_budget(task_priority=priority, source=source)

    if result.decision in _PROCEED_DECISIONS:
        return BudgetAction.PROCEED, result
    return BudgetAction.SKIP_SPAWN, result
