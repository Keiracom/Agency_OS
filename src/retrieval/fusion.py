"""Wave 5 — cross-topology fusion recall.

`fused_recall` fires a recall against EVERY mapped fleet Hindsight bank in
parallel (`asyncio.gather` over `asyncio.to_thread`), instead of the default
three-collection slice `agent_query.query()` uses. Results are merged,
deduplicated by content hash (the higher-scored copy wins when the same text
surfaces in more than one bank), and ranked by score. This prevents siloed
context: a query that semantically spans governance + decisions +
agent_memories + keis no longer has to pick one bank up front.

Gated behind `RETRIEVAL_FUSION_ENABLED` (default False) — matches the
`DISPATCHER_RERANKER_ENABLED` / spawn-recall flag pattern. Fail-open: a bank
whose recall fails is dropped from the union; the surviving banks still
return. Tenant context is validated once, fail-fast, before any HTTP — a
wire-contract violation is never per-bank-swallowed (mirrors
`orchestrator._gather_ann_pool`).

Each bank is recalled by reusing `orchestrator._gather_ann_pool` with a
single-collection tuple, so the Hindsight wire contract, response-shape
parsing, and per-collection fail-open all stay defined in exactly one place.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from collections.abc import Iterable

from src.retrieval import orchestrator
from src.retrieval.orchestrator import RetrievedNode

logger = logging.getLogger(__name__)

_FUSION_ENABLED_ENV = "RETRIEVAL_FUSION_ENABLED"
_TRUTHY = {"1", "true", "yes"}


def fusion_enabled() -> bool:
    """True when RETRIEVAL_FUSION_ENABLED is set truthy (default False)."""
    return os.environ.get(_FUSION_ENABLED_ENV, "").lower() in _TRUTHY


def _content_key(text: str) -> str:
    """Stable dedup key: sha256 of whitespace-stripped content."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _merge_dedup(node_lists: Iterable[list[RetrievedNode]], top_k: int) -> list[RetrievedNode]:
    """Union node lists, keep the higher-scored copy per content hash, rank desc."""
    merged: dict[str, RetrievedNode] = {}
    for nodes in node_lists:
        for node in nodes:
            key = _content_key(node.text)
            existing = merged.get(key)
            if existing is None or node.score > existing.score:
                merged[key] = node
    ranked = sorted(merged.values(), key=lambda n: n.score, reverse=True)
    return ranked[:top_k]


async def fused_recall(
    query: str,
    tenant: str,
    top_k: int = orchestrator.DEFAULT_K_INITIAL,
) -> list[RetrievedNode]:
    """Union recall across all mapped fleet banks; dedup by content; rank by score.

    Args:
        query: Natural-language recall query.
        tenant: Hindsight tenant slug. Validated fail-fast at the wire boundary;
            fleet-internal callers pass `orchestrator.FLEET_TENANT_SLUG`.
        top_k: Max nodes returned after dedup + ranking.

    Returns:
        Up to `top_k` `RetrievedNode`s, ranked by score descending. A bank that
        fails contributes nothing; the surviving banks' nodes still return.
    """
    orchestrator._require_tenant_id(tenant)  # fail-fast; never per-bank-swallowed
    collections = tuple(orchestrator.HINDSIGHT_BANK_BY_CLASS)
    tasks = [
        asyncio.to_thread(
            orchestrator._gather_ann_pool,
            query,
            (collection,),
            top_k,
            None,
            tenant_id=tenant,
        )
        for collection in collections
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    node_lists: list[list[RetrievedNode]] = []
    for collection, result in zip(collections, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning(
                "fusion bank recall failed collection=%s — dropping from union",
                collection,
                exc_info=result,
            )
            continue
        node_lists.append(result)
    return _merge_dedup(node_lists, top_k)
