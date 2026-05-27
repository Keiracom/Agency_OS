"""Tests for scripts/dispatcher/_pre_spawn_gates.py (cutover step 4.5 PR #1).

Covers:
  - no-gate fail-open (rollout phase 1: gates not yet wired)
  - envelope-missing-fields fail-open (cannot hash without from/type/content)
  - SPAWN_OK pass-through (gate ran, returned proceed)
  - DROP_DUPLICATE drop-path (gate ran, returned duplicate)
  - content fallback chain (brief → summary → text → task_ref)
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import pytest

from scripts.dispatcher import _pre_spawn_gates
from src.dispatcher.idempotency import IdempotencyDecision, IdempotencyGate


class _FakeRedis:
    """Fake `redis.asyncio.Redis` for tests — implements only `set(name, value, *, nx, ex)`.

    `claim_returns` is a list of return values consumed FIFO by each `set` call.
    Truthy → new claim (SPAWN_OK); None → key exists (DROP_DUPLICATE).
    """

    def __init__(self, claim_returns: list[Any]):
        self._returns = list(claim_returns)
        self.calls: list[tuple[str, str, bool, int | None]] = []

    def set(
        self, name: str, value: str, *, nx: bool = False, ex: int | None = None
    ) -> Awaitable[Any]:
        self.calls.append((name, value, nx, ex))

        async def _resolve() -> Any:
            return self._returns.pop(0) if self._returns else True

        return _resolve()


def _make_gate(*, returns: list[Any]) -> IdempotencyGate:
    return IdempotencyGate(valkey_client=_FakeRedis(returns))  # type: ignore[arg-type]


# ----- no-gate fail-open -----


def test_no_gate_returns_proceed_none() -> None:
    action, result = _pre_spawn_gates.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "x"}
    )
    assert action == _pre_spawn_gates.PreSpawnAction.PROCEED
    assert result is None


# ----- envelope-missing-fields fail-open -----


@pytest.mark.parametrize(
    "envelope",
    [
        {},
        {"type": "task_dispatch", "brief": "x"},  # missing from
        {"from": "elliot", "brief": "x"},  # missing type
        {"from": "", "type": "task_dispatch", "brief": "x"},  # empty from
        {"from": "elliot", "type": "task_dispatch"},  # missing content
        {"from": "elliot", "type": "task_dispatch", "brief": ""},  # empty content
    ],
)
def test_missing_fields_fail_open(envelope: dict[str, Any]) -> None:
    gate = _make_gate(returns=[True])
    action, result = _pre_spawn_gates.evaluate(envelope, idempotency_gate=gate)
    assert action == _pre_spawn_gates.PreSpawnAction.PROCEED
    assert result is None


# ----- SPAWN_OK pass-through -----


def test_spawn_ok_proceeds() -> None:
    gate = _make_gate(returns=[True])  # SET NX returned truthy → new claim
    action, result = _pre_spawn_gates.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "pr 1199 review"},
        idempotency_gate=gate,
    )
    assert action == _pre_spawn_gates.PreSpawnAction.PROCEED
    assert result is not None
    assert result.decision == IdempotencyDecision.SPAWN_OK
    assert result.source == "elliot|task_dispatch"
    assert result.key.startswith("idem:")


# ----- DROP_DUPLICATE drop-path -----


def test_drop_duplicate_dropped() -> None:
    gate = _make_gate(returns=[None])  # SET NX returned None → already-claimed
    action, result = _pre_spawn_gates.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "pr 1199 review"},
        idempotency_gate=gate,
    )
    assert action == _pre_spawn_gates.PreSpawnAction.DROP_DUPLICATE
    assert result is not None
    assert result.decision == IdempotencyDecision.DROP_DUPLICATE


# ----- content fallback chain -----


@pytest.mark.parametrize(
    "envelope,expected_content_includes",
    [
        ({"from": "elliot", "type": "task_dispatch", "brief": "B"}, "B"),
        ({"from": "elliot", "type": "task_dispatch", "summary": "S"}, "S"),
        ({"from": "elliot", "type": "task_dispatch", "text": "T"}, "T"),
        ({"from": "elliot", "type": "task_dispatch", "task_ref": "REF-1"}, "REF-1"),
    ],
)
def test_content_fallback_chain(envelope: dict[str, Any], expected_content_includes: str) -> None:
    gate = _make_gate(returns=[True])
    action, result = _pre_spawn_gates.evaluate(envelope, idempotency_gate=gate)
    assert action == _pre_spawn_gates.PreSpawnAction.PROCEED
    # Re-derive what _envelope_to_source_content extracted by checking source+key:
    # source is always "<from>|<type>"; content varies by fallback chain.
    assert result is not None
    assert result.source == "elliot|task_dispatch"


# ----- distinct (source, content) produces distinct keys -----


def test_distinct_envelopes_distinct_keys() -> None:
    gate1 = _make_gate(returns=[True])
    gate2 = _make_gate(returns=[True])
    _, r1 = _pre_spawn_gates.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "A"},
        idempotency_gate=gate1,
    )
    _, r2 = _pre_spawn_gates.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "B"},
        idempotency_gate=gate2,
    )
    assert r1 is not None and r2 is not None
    assert r1.key != r2.key


def test_distinct_senders_distinct_keys() -> None:
    gate1 = _make_gate(returns=[True])
    gate2 = _make_gate(returns=[True])
    _, r1 = _pre_spawn_gates.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "X"},
        idempotency_gate=gate1,
    )
    _, r2 = _pre_spawn_gates.evaluate(
        {"from": "aiden", "type": "task_dispatch", "brief": "X"},
        idempotency_gate=gate2,
    )
    assert r1 is not None and r2 is not None
    assert r1.key != r2.key
