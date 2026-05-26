"""Retrieval orchestration: read-path sources nodes from Hindsight; write-path
still uses LlamaIndex (transitional).

Sits between `agent_query.query()` and the underlying vector store. Owns:
    * Multi-collection routing (one bank per collection).
    * Two-stage retrieval: Hindsight `/memories/recall` k_initial vector
      hits → FlashRank cross-encoder rerank → k_returned final.
      Bypass-falls-back to raw ANN when FlashRank is unavailable or
      exceeds its latency budget.
    * Citation extraction — every retrieved node carries a source_id,
      collection, score, and 80-char excerpt back to the caller.

The 500-token response budget (KEI-55) is enforced at the response-synth
step via a max-output cap. Empty corpus or low-confidence matches fall
through to the anti-hallucination guard in `agent_query.query()` — this
module returns the raw nodes; the public entry decides whether to
synthesise.

A3-c2 step 5-B (Agency_OS-0zv1, 2026-05-26): the read path (`_gather_ann_pool`)
was cut over from `LlamaIndex.VectorStoreIndex` over Weaviate to direct
Hindsight `POST /v1/default/banks/{bank_id}/memories/recall`. Precondition
was Agency_OS-4bsc (Discoveries hand-migration) so all three default
collections (Discoveries / Decisions / Keis) have Hindsight bank coverage.
The write path (`_build_index` + `index_document`) still uses LlamaIndex
until a follow-up PR — kept here so the orthogonal-scope discipline holds.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib import request as urlrequest

from src.retrieval import rerankers, weaviate_store

logger = logging.getLogger(__name__)

# Hindsight read endpoint — POST /v1/default/banks/{bank_id}/memories/recall
# with body {"query": str, "max_tokens": int, "top_k": int, "tags"?: list,
# "tags_match"?: "all"|"any"}. Returns {"memories": [...]} or {"results": [...]}.
HINDSIGHT_BASE = os.environ.get("HINDSIGHT_BASE", "http://localhost:8889")  # NOSONAR S5332 loopback
HINDSIGHT_RECALL_TIMEOUT_SECONDS = 30.0
HINDSIGHT_RECALL_MAX_TOKENS = 2000

# Local mirror of scripts/orchestrator/indexer_base.CLASS_TO_BANK so src/
# doesn't import from scripts/. Drift between the two is caught by
# `tests/retrieval/test_orchestrator_class_to_bank_parity.py` (locks the
# canonical-source pointer).
HINDSIGHT_BANK_BY_CLASS = {
    "Decisions": "fleet_decisions",
    "Keis": "fleet_keis",
    "Codebase": "fleet_codebase",
    "AgentMemories": "fleet_agent_memories",
    "ToolCalls": "fleet_tool_calls",
    "SessionTranscripts": "fleet_session_transcripts",
    "StrategicDocuments": "fleet_strategic_documents",
    "Discoveries": "fleet_discoveries",
}

DEFAULT_K_INITIAL = 20
DEFAULT_K_RETURNED = 5
# Legacy export retained so existing callers (and tests) that import the
# bypass-default constant don't break — the actual bypass flag now comes
# from `rerankers.rerank_top_k` per query (RerankOutcome.bypassed).
RAW_ANN_RERANK_BYPASS = True


@dataclass(frozen=True)
class RetrievedNode:
    text: str
    score: float
    metadata: dict[str, Any]
    collection: str


def _build_index(client: Any, collection: str) -> Any:
    """Construct a VectorStoreIndex bound to one Weaviate collection."""
    from llama_index.core import VectorStoreIndex
    from llama_index.core.storage.storage_context import StorageContext

    from src.retrieval.embeddings import get_embed_model

    vector_store = weaviate_store.get_vector_store(collection, client=client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=get_embed_model(),
        storage_context=storage_context,
    )


def index_document(
    collection: str,
    text: str,
    metadata: dict[str, Any],
    *,
    client: Any | None = None,
) -> str:
    """Index one document into `collection`. Returns the LlamaIndex node id.

    Required metadata keys (per the canonical schema in infra/weaviate/
    schema.py): environment_hash, created_at, agent, kei. Caller is
    responsible for supplying current values.
    """
    from llama_index.core import Document

    owned = client is None
    weaviate_client = client if client is not None else weaviate_store._connect_client()
    try:
        index = _build_index(weaviate_client, collection)
        doc = Document(text=text, metadata=metadata)
        index.insert(doc)
        return doc.doc_id
    finally:
        if owned:
            weaviate_store.close_client(weaviate_client)


@dataclass(frozen=True)
class RetrievalOutcome:
    nodes: tuple[RetrievedNode, ...]
    bypass_rerank: bool
    rerank_reason: str
    rerank_elapsed_ms: int


def _hindsight_recall(text: str, bank_id: str, *, top_k: int) -> list[dict[str, Any]]:
    """POST /v1/default/banks/{bank_id}/memories/recall — returns memories list.

    Empty list on any HTTP/JSON failure (caller logs at the call site for
    per-collection visibility).
    """
    body = {"query": text, "max_tokens": HINDSIGHT_RECALL_MAX_TOKENS, "top_k": top_k}
    data = json.dumps(body).encode("utf-8")
    req = urlrequest.Request(
        f"{HINDSIGHT_BASE}/v1/default/banks/{bank_id}/memories/recall",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlrequest.urlopen(req, timeout=HINDSIGHT_RECALL_TIMEOUT_SECONDS) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    return parsed.get("memories") or parsed.get("results") or []


def _gather_ann_pool(
    text: str,
    collections: tuple[str, ...],
    k_initial: int,
    weaviate_client: Any,
) -> list[RetrievedNode]:
    """Source the ANN pool from Hindsight `/memories/recall` per collection.

    `weaviate_client` is retained for backwards-compat with the public
    `retrieve_with_outcome(client=...)` signature; ignored on the Hindsight
    path. Removed entirely in the next PR (after the write-path cutover).
    A3-c2 step 5-B, Agency_OS-0zv1.
    """
    del weaviate_client  # noqa: ARG001 — retained for ABI; intentional ignore
    pool: list[RetrievedNode] = []
    for collection in collections:
        bank_id = HINDSIGHT_BANK_BY_CLASS.get(collection)
        if bank_id is None:
            logger.warning(
                "no Hindsight bank mapping for collection=%s — skipping (see "
                "HINDSIGHT_BANK_BY_CLASS canonical at scripts/orchestrator/"
                "indexer_base.CLASS_TO_BANK)",
                collection,
            )
            continue
        try:
            memories = _hindsight_recall(text, bank_id, top_k=k_initial)
        except Exception:  # noqa: BLE001
            logger.warning("hindsight recall failed for %s", collection, exc_info=True)
            continue
        for mem in memories:
            content = mem.get("content") or mem.get("text") or ""
            score = float(mem.get("score") or mem.get("relevance") or 0.0)
            metadata = dict(mem.get("metadata") or {})
            pool.append(
                RetrievedNode(
                    text=content,
                    score=score,
                    metadata=metadata,
                    collection=collection,
                )
            )
    pool.sort(key=lambda n: n.score, reverse=True)
    return pool


def retrieve_with_outcome(
    text: str,
    collections: tuple[str, ...],
    *,
    k_initial: int = DEFAULT_K_INITIAL,
    k_returned: int = DEFAULT_K_RETURNED,
    rerank: bool = True,
    client: Any | None = None,
) -> RetrievalOutcome:
    """Run the two-stage retrieval and surface the bypass flag verbatim.

    A3-c2 step 5-B (2026-05-26): `client` is retained in the signature for
    backwards-compat but ignored — Hindsight is now the recall backend and
    does not need a Weaviate client. Removed from the signature in the next
    PR after callers stop passing it.
    """
    del client  # noqa: ARG001 — retained for ABI; intentional ignore
    pool = _gather_ann_pool(text, collections, k_initial, weaviate_client=None)
    if not pool:
        return RetrievalOutcome((), False, "empty_pool", 0)
    if not rerank:
        return RetrievalOutcome(tuple(pool[:k_returned]), True, "rerank_disabled", 0)
    outcome = rerankers.rerank_top_k(text, tuple(pool), top_k=k_returned)
    return RetrievalOutcome(
        nodes=outcome.nodes,
        bypass_rerank=outcome.bypassed,
        rerank_reason=outcome.reason,
        rerank_elapsed_ms=outcome.elapsed_ms,
    )


def retrieve_nodes(
    text: str,
    collections: tuple[str, ...],
    *,
    k_initial: int = DEFAULT_K_INITIAL,
    k_returned: int = DEFAULT_K_RETURNED,
    client: Any | None = None,
) -> tuple[RetrievedNode, ...]:
    """Backwards-compatible thin wrapper — agents that only need the node
    tuple keep calling this; agents that want the bypass flag call
    `retrieve_with_outcome`."""
    outcome = retrieve_with_outcome(
        text=text,
        collections=collections,
        k_initial=k_initial,
        k_returned=k_returned,
        client=client,
    )
    return outcome.nodes
