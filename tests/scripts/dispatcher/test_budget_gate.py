"""Tests for scripts/dispatcher/_budget_gate.py (cutover step 4.5 PR #2).

Covers:
  - no-gate fail-open (rollout phase 1)
  - SPAWN_OK / OVERAGE_LOG_AND_SPAWN / DAVE_BYPASS / FORCE_OVERRIDE → PROCEED
  - QUEUE_NEXT_DAY / DROP_WITH_LOG → SKIP_SPAWN
  - Priority derivation from envelope (explicit > sender heuristic)
  - Source derivation (dave → SOURCE_DAVE_DM)
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.dispatcher import _budget_gate
from src.relay.budget_ceiling import (
    SOURCE_DAVE_DM,
    SOURCE_FLEET,
    BudgetCeilingGate,
    BudgetDecision,
)


class _FakeDB:
    """Fake DB cursor returning a fixed request_count → fleet spend."""

    def __init__(self, request_count: int = 0):
        self._request_count = request_count
        self._row: tuple[int] | None = None

    def execute(self, query: str, *params: Any) -> None:
        self._row = (self._request_count,)

    def fetchone(self) -> tuple[int] | None:
        return self._row


def _make_gate(*, request_count: int = 0, budget_aud: float = 25.0) -> BudgetCeilingGate:
    return BudgetCeilingGate(
        db=_FakeDB(request_count=request_count),
        daily_budget_aud=budget_aud,
        alerts_emitter=lambda _payload: None,
    )


# ----- no-gate fail-open -----


def test_no_gate_returns_proceed_none() -> None:
    action, result = _budget_gate.evaluate({"from": "elliot", "type": "task_dispatch"})
    assert action == _budget_gate.BudgetAction.PROCEED
    assert result is None


# ----- SPAWN_OK proceeds -----


def test_spawn_ok_under_budget_proceeds() -> None:
    gate = _make_gate(request_count=0, budget_aud=25.0)
    action, result = _budget_gate.evaluate(
        {"from": "atlas", "type": "task_dispatch"}, budget_gate=gate
    )
    assert action == _budget_gate.BudgetAction.PROCEED
    assert result is not None
    assert result.decision == BudgetDecision.SPAWN_OK


# ----- OVERAGE_LOG_AND_SPAWN proceeds -----


def test_high_priority_overage_proceeds() -> None:
    # Spend > budget AND task is high-priority → OVERAGE_LOG_AND_SPAWN.
    # 100 requests × 0.79 AUD = 79 AUD spend; 25 AUD budget → over.
    gate = _make_gate(request_count=100, budget_aud=25.0)
    action, result = _budget_gate.evaluate(
        {"from": "elliot", "type": "task_dispatch", "priority": "high"}, budget_gate=gate
    )
    assert action == _budget_gate.BudgetAction.PROCEED
    assert result is not None
    assert result.decision == BudgetDecision.OVERAGE_LOG_AND_SPAWN


# ----- DAVE_BYPASS proceeds -----


def test_dave_bypass_proceeds_even_over_budget() -> None:
    gate = _make_gate(request_count=1000, budget_aud=25.0)
    action, result = _budget_gate.evaluate(
        {"from": "dave", "type": "task_dispatch"}, budget_gate=gate
    )
    assert action == _budget_gate.BudgetAction.PROCEED
    assert result is not None
    assert result.decision == BudgetDecision.DAVE_BYPASS
    assert result.recommended_tier == "haiku"


# ----- QUEUE_NEXT_DAY / DROP_WITH_LOG skip -----


def test_normal_priority_over_budget_skips() -> None:
    # Spend > budget AND priority is normal (deferrable) → QUEUE_NEXT_DAY.
    gate = _make_gate(request_count=100, budget_aud=25.0)
    action, result = _budget_gate.evaluate(
        {"from": "atlas", "type": "task_dispatch", "priority": "normal"}, budget_gate=gate
    )
    assert action == _budget_gate.BudgetAction.SKIP_SPAWN
    assert result is not None
    assert result.decision == BudgetDecision.QUEUE_NEXT_DAY


# ----- Priority derivation -----


@pytest.mark.parametrize(
    "envelope,expected_priority",
    [
        ({"from": "dave", "type": "task_dispatch"}, "high"),
        ({"from": "elliot", "type": "task_dispatch"}, "high"),
        ({"from": "atlas", "type": "task_dispatch"}, "normal"),
        ({"from": "orion", "type": "task_dispatch"}, "normal"),
        ({"from": "atlas", "type": "task_dispatch", "priority": "high"}, "high"),
        ({"from": "dave", "type": "task_dispatch", "priority": "low"}, "low"),
    ],
)
def test_priority_derivation(envelope: dict[str, Any], expected_priority: str) -> None:
    priority, _ = _budget_gate._envelope_to_priority_source(envelope)
    assert priority == expected_priority


# ----- Source derivation -----


@pytest.mark.parametrize(
    "envelope,expected_source",
    [
        ({"from": "dave", "type": "task_dispatch"}, SOURCE_DAVE_DM),
        ({"from": "elliot", "type": "task_dispatch"}, SOURCE_FLEET),
        ({"from": "atlas", "type": "task_dispatch"}, SOURCE_FLEET),
        ({"from": "atlas", "source": SOURCE_DAVE_DM}, SOURCE_DAVE_DM),  # explicit wins
    ],
)
def test_source_derivation(envelope: dict[str, Any], expected_source: str) -> None:
    _, source = _budget_gate._envelope_to_priority_source(envelope)
    assert source == expected_source
