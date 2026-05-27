"""Pre-spawn gates — dispatcher hook layer (Step 4.5 wiring PR #1).

Sits between `_envelope_route.route_envelope` and `_spawn.handle_envelope`
in dispatcher_main's per-envelope loop. Evaluates each launch-blocker
gate that needs to fire BEFORE a spawn happens.

PR #1 wires the IdempotencyGate (PR #1204 / Agency_OS-6c2k, cutover-blocker 5,
Viktor lever 26). Subsequent wiring PRs add budget + context-window in this
same module so the dispatcher_main call-site stays single-line.

DESIGN:
  - Single sync entry-point `evaluate(envelope, *, idempotency_gate)`.
  - asyncio.run() the async IdempotencyGate.check_and_claim — dispatcher_main
    polls every 2s; one event loop per envelope is fine at fleet scale.
  - Fail-open: if no gate is wired (production rollout phase 1) OR the gate
    can't extract source/content, return PROCEED with no idempotency result.
    Idempotency Gate itself fail-opens on Valkey errors per PR #1204 design.
  - DI: caller passes the gate; tests inject a fake gate without Valkey.

bd: cutover-step-4.5-dispatcher-wiring-pr1
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

from src.dispatcher.idempotency import (
    IdempotencyDecision,
    IdempotencyGate,
    IdempotencyResult,
)

log = logging.getLogger(__name__)


class PreSpawnAction:
    """Marker constants for the action evaluate() returns."""

    PROCEED = "proceed"
    DROP_DUPLICATE = "drop_duplicate"


def _envelope_to_source_content(envelope: Mapping[str, Any]) -> tuple[str, str]:
    """Extract (source, content) for the IdempotencyGate hash.

    source = "<from>|<type>" → distinct dispatchers + envelope kinds get distinct keys
    content = brief / summary / text / task_ref (first non-empty) → the dedup target

    Returns ("", "") when either field can't be derived; caller fail-opens.
    """
    sender = str(envelope.get("from") or "").strip()
    type_value = str(envelope.get("type") or "").strip()
    if not sender or not type_value:
        return "", ""
    source = f"{sender}|{type_value}"
    content = (
        envelope.get("brief")
        or envelope.get("summary")
        or envelope.get("text")
        or envelope.get("task_ref")
        or ""
    )
    content_str = str(content).strip()
    return source, content_str


def evaluate(
    envelope: Mapping[str, Any],
    *,
    idempotency_gate: IdempotencyGate | None = None,
) -> tuple[str, IdempotencyResult | None]:
    """Run pre-spawn gates against a routed envelope.

    Returns (action, idempotency_result). action is PROCEED or DROP_DUPLICATE.
    idempotency_result is non-None only when a gate was wired AND ran; tests
    inspect this for audit-trail verification.

    Fail-open by design:
      - no gate wired → PROCEED, None (rollout phase 1 = gates off by default)
      - envelope missing from/type/content → PROCEED, None (better extra spawn
        than missed dispatch; gate cannot dedup what it cannot hash)
      - IdempotencyGate Valkey error → PROCEED, IdempotencyResult(SPAWN_OK)
        per PR #1204 fail-open contract
    """
    if idempotency_gate is None:
        return PreSpawnAction.PROCEED, None

    source, content = _envelope_to_source_content(envelope)
    if not source or not content:
        log.debug(
            "pre-spawn gate skip: envelope missing fields for hash (from=%r type=%r)",
            envelope.get("from"),
            envelope.get("type"),
        )
        return PreSpawnAction.PROCEED, None

    result = asyncio.run(idempotency_gate.check_and_claim(source=source, content=content))
    if result.decision == IdempotencyDecision.DROP_DUPLICATE:
        return PreSpawnAction.DROP_DUPLICATE, result
    return PreSpawnAction.PROCEED, result
