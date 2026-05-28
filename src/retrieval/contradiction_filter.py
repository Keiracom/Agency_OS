"""Layer 3 — contradiction filtering (STUB).

Position in the retrieval orchestrator: L1 semantic recall → L2 rerank →
**L3 contradiction filter** → L4 compression → spawn hydration.

Purpose (when complete): drop recall results that contradict a higher-ranked or
more-recent result — e.g. a superseded decision surfacing alongside its
successor — so the hydration payload never feeds an ephemeral agent two
conflicting "canonical" answers.

▸ STATUS: STUB (`IS_STUB = True`). The real implementation — pairwise
contradiction detection over recalled atoms, superseded-edge awareness from the
decision graph — is in progress. Until it lands this is an **identity pass**:
results are returned unchanged so the 4-layer pipeline is wired end-to-end
without altering behaviour. **Fail-open:** any error returns the input
untouched — L3 must never drop the whole context or block a spawn.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Marks this layer as a not-yet-real stub. Callers / tests assert on it so the
# stub status is observable, not buried in a docstring.
IS_STUB = True


def filter_contradictions(results: list[str]) -> list[str]:
    """L3 stub: return recall results unchanged (identity), fail-open.

    Replace the body with real contradiction detection when L3 lands; keep the
    fail-open contract (never raise, never return None).
    """
    try:
        # TODO(L3-real): detect contradicted results (superseded edges, pairwise
        # entailment) and drop them. Stub = identity to wire the pipeline.
        return list(results)
    except Exception:  # noqa: BLE001 — L3 must never block hydration
        logger.debug("contradiction_filter stub failed — passing results through", exc_info=True)
        return results
