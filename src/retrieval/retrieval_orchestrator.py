"""Retrieval Orchestrator — 4-layer spawn-hydration assembly (ratified arch).

    Dispatcher → [ L1 semantic recall → L2 rerank → L3 contradiction filter →
                   L4 compression ] → spawn hydration

L1 + L2 are already built — they are the recall + cross-encoder rerank behind
`spawn_recall.query_for_spawn` / `query_failures_for_spawn` (which call
`agent_query.query` → `orchestrator.retrieve_with_outcome`). L3 and L4 are
fail-open stubs (`contradiction_filter` / `compression`, both `IS_STUB = True`)
until their real implementations land. The Graphiti doctrine graph is Phase 2
and is deliberately NOT wired here.

This module is the single assembly point that runs a query through all four
layers and returns the hydration block an ephemeral spawn receives (placed in
`env[AGENCY_OS_PRIOR_CONTEXT]` by `spawn_recall.inject_block`).

Gated behind `RETRIEVAL_ORCHESTRATOR_4LAYER_ENABLED` (default off). When off the
dispatcher uses the existing `spawn_recall.build_spawn_context_block` path
unchanged — this is purely additive. Fail-open at every layer: a failure in any
layer degrades to the content gathered so far, never an exception to the spawn.
"""

from __future__ import annotations

import logging
import os

from src.retrieval import compression, contradiction_filter, spawn_recall

logger = logging.getLogger(__name__)

_FOUR_LAYER_ENABLED_ENV = "RETRIEVAL_ORCHESTRATOR_4LAYER_ENABLED"
_TRUTHY = {"1", "true", "yes", "on"}


def four_layer_enabled() -> bool:
    """True when RETRIEVAL_ORCHESTRATOR_4LAYER_ENABLED is set truthy (default off)."""
    return os.environ.get(_FOUR_LAYER_ENABLED_ENV, "").lower() in _TRUTHY


def assemble_hydration_block(task_type: str, task_brief: str) -> str:
    """Run a spawn query through all 4 retrieval layers → hydration block.

    L1+L2 (recall+rerank) produce the positive and negative result sets; L3
    filters contradictions from each; the sets are formatted + combined; L4
    compresses the combined block to the token budget. Every layer is fail-open
    (the underlying calls swallow their own errors); the outer guard is
    belt-and-suspenders so a catastrophic raise still yields "" rather than
    blocking the spawn.
    """
    try:
        # L1 + L2 — semantic recall + cross-encoder rerank (already built).
        positive = spawn_recall.query_for_spawn(task_type, task_brief)
        failures = spawn_recall.query_failures_for_spawn(task_type, task_brief)

        # L3 — contradiction filter (stub, identity, fail-open).
        positive = contradiction_filter.filter_contradictions(positive)
        failures = contradiction_filter.filter_contradictions(failures)

        # Format each set with spawn_recall's canonical block builders.
        blocks = [
            spawn_recall.build_prior_context_block(positive),
            spawn_recall.build_failure_context_block(failures),
        ]
        combined = "\n\n".join(block for block in blocks if block)

        # L4 — compression (stub, budget clamp, fail-open).
        return compression.compress(combined, max_tokens=spawn_recall.MAX_TOKENS)
    except Exception:  # noqa: BLE001 — 4-layer assembly must never block a spawn
        logger.debug("4-layer hydration assembly failed — empty block", exc_info=True)
        return ""


def inject_hydration(spawn_kwargs: dict, *, task_type: str, task_brief: str) -> dict:
    """Assemble the 4-layer block and inject it into the spawn env.

    Fail-open: on any error returns `spawn_kwargs` unchanged (matching
    `spawn_recall.inject_prior_context`'s contract). Reuses
    `spawn_recall.inject_block` so the env key + empty-block handling stay
    identical to the single-layer path.
    """
    try:
        block = assemble_hydration_block(task_type, task_brief)
        return spawn_recall.inject_block(spawn_kwargs, block)
    except Exception:  # noqa: BLE001 — injection must never block a spawn
        logger.debug("inject_hydration failed — spawn proceeds unchanged", exc_info=True)
        return spawn_kwargs
