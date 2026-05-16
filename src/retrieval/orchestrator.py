"""LlamaIndex orchestration: build CitationQueryEngine on top of Weaviate.

Sits between `agent_query.query()` and the Weaviate vector store. Owns:
    * Multi-collection routing (one VectorStoreIndex per collection).
    * Two-stage retrieval: Weaviate k_initial vector hits → FlashRank
      cross-encoder rerank → k_returned final. Bypass-falls-back to raw
      ANN when FlashRank is unavailable or exceeds its latency budget.
    * Citation extraction — every retrieved node carries a source_id,
      collection, score, and 80-char excerpt back to the caller.

The 500-token response budget (KEI-55) is enforced at the response-synth
step via `response_mode="compact"` + a max-output cap. Empty corpus or
low-confidence matches fall through to the anti-hallucination guard in
`agent_query.query()` — this module returns the raw nodes; the public
entry decides whether to synthesise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.retrieval import rerankers, weaviate_store

logger = logging.getLogger(__name__)

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


def _gather_ann_pool(
    text: str,
    collections: tuple[str, ...],
    k_initial: int,
    weaviate_client: Any,
) -> list[RetrievedNode]:
    pool: list[RetrievedNode] = []
    for collection in collections:
        try:
            index = _build_index(weaviate_client, collection)
            retriever = index.as_retriever(similarity_top_k=k_initial)
            nodes = retriever.retrieve(text)
        except Exception:  # noqa: BLE001
            logger.warning("retrieve failed for %s", collection, exc_info=True)
            continue
        for node in nodes:
            pool.append(
                RetrievedNode(
                    text=node.get_content(),
                    score=float(node.score or 0.0),
                    metadata=dict(node.metadata or {}),
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
    """Run the two-stage retrieval and surface the bypass flag verbatim."""
    owned = client is None
    weaviate_client = client if client is not None else weaviate_store._connect_client()
    try:
        pool = _gather_ann_pool(text, collections, k_initial, weaviate_client)
    finally:
        if owned:
            weaviate_store.close_client(weaviate_client)
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
