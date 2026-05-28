"""Layer 4 — compression (STUB).

Position in the retrieval orchestrator: L1 semantic recall → L2 rerank →
L3 contradiction filter → **L4 compression** → spawn hydration.

Purpose (when complete): compress the assembled hydration block to the highest-
signal content that fits the spawn token budget — extractive/semantic
summarisation that keeps the load-bearing sentences and discards filler.

▸ STATUS: STUB (`IS_STUB = True`). The real semantic compressor is in progress.
Until it lands this applies the **honest minimal compression**: a hard clamp to
the token budget (~4 chars/token, the same KEI-55 ceiling spawn_recall already
enforces). This guarantees the budget invariant without pretending to do
summarisation. **Fail-open:** any error returns the input clamped, or unchanged
if even clamping fails — L4 must never block a spawn.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4  # belt-and-suspenders approximation, matches spawn_recall

# Marks this layer as a not-yet-real stub (semantic compression pending).
IS_STUB = True


def compress(block: str, *, max_tokens: int) -> str:
    """L4 stub: clamp the block to the token budget, fail-open.

    Replace the body with real semantic/extractive compression when L4 lands;
    keep the budget invariant (output never exceeds max_tokens) and the
    fail-open contract (never raise).
    """
    try:
        return block[: max_tokens * CHARS_PER_TOKEN]
    except Exception:  # noqa: BLE001 — L4 must never block hydration
        logger.debug("compression stub failed — returning block unchanged", exc_info=True)
        return block
