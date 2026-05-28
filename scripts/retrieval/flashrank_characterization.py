"""FlashRank characterisation harness — NOT a precision@5 evaluator.

Option B of the Wave-3 pre-swap baseline (Aiden decision 2026-05-28). Produces
a ground-truth-FREE characterisation of how the in-process FlashRank reranker
reshapes the raw Hindsight ANN recall order, so Wave 3 (FlashRank -> Nova
cross-encoder sidecar) has an empirical before-picture to diff against.

Measures, over a fixed query set, per query:
  * rank churn   — how many of the raw-ANN top-5 node identities survive into
                   the FlashRank top-5, and how far positions move.
  * scores       — raw-ANN scores (as exposed by Hindsight recall) vs FlashRank
                   relevance scores for the post-rerank top-5.
  * latency      — wall-clock ms inside rerankers.rerank_top_k per query.

This is a characterisation of reordering behaviour + cost. It says nothing
about whether the reranked order is *better* — that needs a labelled golden
set (filed as the Option-A bd issue). Do not read these numbers as quality.

Read-only against the live Hindsight stack; no writes, no production-path edits.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from typing import Any

from src.retrieval import orchestrator, rerankers

# Collections that actually hold content in the live fleet Hindsight banks
# at measurement time (probed 2026-05-28): fleet_global_governance_patterns=19,
# fleet_decisions=2; the other eight fleet banks are empty. Querying only the
# populated banks gives FlashRank a real pool (>k_returned) to reorder — the
# empty banks would contribute nothing but zero-length pools. The empty-bank
# finding is itself recorded in the report.
COLLECTIONS = ("Global_governance_patterns", "Decisions")
TENANT = orchestrator.FLEET_TENANT_SLUG
K_INITIAL = orchestrator.DEFAULT_K_INITIAL
K_RETURNED = orchestrator.DEFAULT_K_RETURNED

QUERIES: tuple[str, ...] = (
    "agent governance rules and laws",
    "Step 0 RESTATE requirement before execution",
    "how are pull requests reviewed and merged",
    "callsign discipline and identity enforcement",
    "FlashRank cross-encoder reranker design",
    "Hindsight memory recall reader cutover",
    "dispatcher spawn budget ceiling gate",
    "bounded spawn one task per spawn enforcement",
    "Linear and Beads issue tracker sync",
    "three-store completion rule LAW XV",
)


def _node_key(node: orchestrator.RetrievedNode) -> str:
    """Stable identity for a node across the raw vs reranked lists."""
    cid = node.metadata.get("chunk_id") or node.metadata.get("external_id")
    return str(cid) if cid else f"{node.collection}:{hash(node.text)}"


def _flashrank_scores(query: str, pool: tuple[Any, ...]) -> list[float]:
    """Call the FlashRank ranker directly to capture relevance scores in order."""
    ranker = rerankers._get_reranker(rerankers.DEFAULT_MODEL)
    if ranker is None:
        return []
    from flashrank import RerankRequest

    req = RerankRequest(query=query, passages=rerankers._to_passage_dicts(pool))
    scored = ranker.rerank(req)
    return [float(item.get("score", 0.0)) for item in scored[:K_RETURNED]]


def _churn(raw_top5: list[str], rerank_top5: list[str]) -> dict[str, Any]:
    # Effective top-k is bounded by how many candidates the pool actually held —
    # empty slots (pool < k_returned) must not be counted as "displaced".
    effective_k = max(len(raw_top5), len(rerank_top5))
    survived = [k for k in raw_top5 if k in rerank_top5]
    position_moves = []
    for new_pos, key in enumerate(rerank_top5):
        if key in raw_top5:
            position_moves.append(abs(raw_top5.index(key) - new_pos))
    return {
        "effective_k": effective_k,
        "survivors_in_topk": len(survived),
        "displaced_from_topk": effective_k - len(survived),
        "mean_abs_position_shift": round(statistics.mean(position_moves), 2)
        if position_moves
        else 0.0,
        "top1_changed": (raw_top5[:1] or [None]) != (rerank_top5[:1] or [None]),
    }


def run() -> dict[str, Any]:
    per_query: list[dict[str, Any]] = []
    for q in QUERIES:
        pool = orchestrator._gather_ann_pool(
            q, COLLECTIONS, K_INITIAL, weaviate_client=None, tenant_id=TENANT
        )
        raw_top5 = [_node_key(n) for n in pool[:K_RETURNED]]
        raw_scores = [round(n.score, 4) for n in pool[:K_RETURNED]]

        started = time.perf_counter()
        outcome = rerankers.rerank_top_k(q, tuple(pool), top_k=K_RETURNED)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)

        rerank_top5 = [_node_key(n) for n in outcome.nodes]
        fr_scores = [round(s, 4) for s in _flashrank_scores(q, tuple(pool))]

        per_query.append(
            {
                "query": q,
                "pool_size": len(pool),
                "bypassed": outcome.bypassed,
                "reason": outcome.reason,
                "latency_ms": latency_ms,
                "raw_ann_scores_top5": raw_scores,
                "flashrank_scores_top5": fr_scores,
                "churn": _churn(raw_top5, rerank_top5),
            }
        )

    latencies = [r["latency_ms"] for r in per_query if not r["bypassed"]]
    churn_vals = [r["churn"]["displaced_from_topk"] for r in per_query if not r["bypassed"]]
    top1_changes = sum(1 for r in per_query if not r["bypassed"] and r["churn"]["top1_changed"])
    reranked = [r for r in per_query if not r["bypassed"]]

    return {
        "per_query": per_query,
        "summary": {
            "queries_total": len(QUERIES),
            "queries_reranked": len(reranked),
            "queries_bypassed": len(QUERIES) - len(reranked),
            "latency_ms_mean": round(statistics.mean(latencies), 1) if latencies else None,
            "latency_ms_median": round(statistics.median(latencies), 1) if latencies else None,
            "latency_ms_max": max(latencies) if latencies else None,
            "mean_displaced_from_topk": round(statistics.mean(churn_vals), 2)
            if churn_vals
            else None,
            "top1_changed_count": top1_changes,
        },
    }


if __name__ == "__main__":
    json.dump(run(), sys.stdout, indent=2)
    sys.stdout.write("\n")
