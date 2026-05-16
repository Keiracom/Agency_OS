"""FlashRank cross-encoder reranker (KEI-75 PR2 / Scout design §6).

Sits between Weaviate ANN retrieval and the agent_query response synth.
Reorders the k_initial=20 vector hits to k_returned=5 using a CPU
cross-encoder (ms-marco-MiniLM-L-12-v2 by default, ~30ms per pass on a
modest box). Two failure modes both fall back to raw ANN scores rather
than blocking the query:

    1. flashrank not installed — typical first-boot / lean CI environment.
    2. rerank latency exceeds the budget (default 200ms) — cold-start or
       container OOM. The fallback preserves liveness; bypass is logged
       via the QueryResult.bypass_rerank flag the orchestrator returns.

The model itself is loaded lazily on first call and cached for the
process lifetime so subsequent reranks pay zero startup cost.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get("AGENCY_OS_RERANK_MODEL", "ms-marco-MiniLM-L-12-v2")
DEFAULT_BUDGET_MS = int(os.environ.get("AGENCY_OS_RERANK_BUDGET_MS", "200"))

_RERANKER: Any | None = None
_LOCK = threading.Lock()


@dataclass(frozen=True)
class RerankOutcome:
    """Return shape from `rerank_top_k`. `bypassed=True` means the caller
    should treat scores as raw Weaviate ANN, not FlashRank-reranked."""

    nodes: tuple[Any, ...]
    bypassed: bool
    reason: str
    elapsed_ms: int


def _get_reranker(model: str) -> Any | None:
    """Load FlashRank lazily; return None if the dep isn't installed."""
    global _RERANKER
    if _RERANKER is not None:
        return _RERANKER
    with _LOCK:
        if _RERANKER is not None:
            return _RERANKER
        try:
            from flashrank import Ranker
        except ImportError:
            logger.info("flashrank not installed; rerank pass will bypass")
            return None
        try:
            _RERANKER = Ranker(model_name=model)
        except Exception:  # noqa: BLE001
            logger.warning("flashrank Ranker init failed; rerank pass will bypass", exc_info=True)
            _RERANKER = None
        return _RERANKER


def reset_reranker() -> None:
    """Test-only: drop the cached Ranker so the next call re-resolves env."""
    global _RERANKER
    with _LOCK:
        _RERANKER = None


def _to_passage_dicts(nodes: tuple[Any, ...]) -> list[dict]:
    out: list[dict] = []
    for idx, node in enumerate(nodes):
        out.append({"id": idx, "text": getattr(node, "text", "") or ""})
    return out


def rerank_top_k(
    query_text: str,
    nodes: tuple[Any, ...],
    *,
    top_k: int = 5,
    latency_budget_ms: int = DEFAULT_BUDGET_MS,
    model: str = DEFAULT_MODEL,
) -> RerankOutcome:
    """Rerank `nodes` against `query_text`, keep top_k. Bypass on budget miss
    or missing dep — caller honours `bypassed`/`reason` to set
    QueryResult.bypass_rerank verbatim."""
    if not nodes:
        return RerankOutcome(nodes=(), bypassed=False, reason="empty_input", elapsed_ms=0)
    started = time.monotonic()
    ranker = _get_reranker(model)
    if ranker is None:
        elapsed = int((time.monotonic() - started) * 1000)
        return RerankOutcome(
            nodes=nodes[:top_k],
            bypassed=True,
            reason="flashrank_not_available",
            elapsed_ms=elapsed,
        )
    try:
        from flashrank import RerankRequest

        request = RerankRequest(query=query_text, passages=_to_passage_dicts(nodes))
        scored = ranker.rerank(request)
    except Exception:  # noqa: BLE001
        elapsed = int((time.monotonic() - started) * 1000)
        logger.warning("flashrank rerank call failed; bypassing", exc_info=True)
        return RerankOutcome(
            nodes=nodes[:top_k],
            bypassed=True,
            reason="rerank_call_failed",
            elapsed_ms=elapsed,
        )
    elapsed = int((time.monotonic() - started) * 1000)
    if elapsed > latency_budget_ms:
        return RerankOutcome(
            nodes=nodes[:top_k],
            bypassed=True,
            reason=f"latency_exceeded_{elapsed}ms_over_{latency_budget_ms}ms",
            elapsed_ms=elapsed,
        )
    ordered_ids = [int(item.get("id", -1)) for item in scored if item.get("id", -1) >= 0]
    reordered: list[Any] = []
    seen: set[int] = set()
    for original_id in ordered_ids:
        if 0 <= original_id < len(nodes):
            reordered.append(nodes[original_id])
            seen.add(original_id)
        if len(reordered) >= top_k:
            break
    for idx, node in enumerate(nodes):
        if len(reordered) >= top_k:
            break
        if idx not in seen:
            reordered.append(node)
    return RerankOutcome(
        nodes=tuple(reordered),
        bypassed=False,
        reason="reranked",
        elapsed_ms=elapsed,
    )
