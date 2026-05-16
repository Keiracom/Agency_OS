"""Public agent-facing query API for the retrieval layer.

Single entry point: `query(text, agent=..., collections=..., ...)`. The
contract follows Scout's design spec §7 verbatim — `citation_required=True`
default, 500-token ceiling, dataclass-typed result.

Observability: every call records to `public.retrieval_events` via the
audit pipeline. PR1 logs the row inline (synchronous) so the contract is
visible end-to-end; the indexing-queue worker pattern (KEI-61) is the
natural follow-up if write latency starts mattering at scale.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Literal

from src.retrieval import orchestrator

logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS: tuple[str, ...] = ("Discoveries", "Decisions", "Keis")
DEFAULT_MAX_TOKENS = 500  # KEI-55 ceiling
DEFAULT_MIN_SCORE = 0.50  # below this, citation_required=True returns answer=""
EXCERPT_LEN = 80
QUERY_TEXT_LOG_CAP = 200


CollectionName = Literal["Discoveries", "Decisions", "Codebase", "Keis", "Sessions"]


@dataclass(frozen=True)
class Citation:
    source_id: str
    collection: str
    score: float
    excerpt: str
    parent_path: str = ""


@dataclass(frozen=True)
class QueryResult:
    answer: str
    citations: tuple[Citation, ...]
    elapsed_ms: int
    bypass_rerank: bool


def _record_event(
    agent: str,
    query_text: str,
    collections: tuple[str, ...],
    k_initial: int,
    k_returned: int,
    elapsed_ms: int,
    bypass_rerank: bool,
    top_citation: Citation | None,
) -> None:
    """Write one row to public.retrieval_events. Best-effort; logs on failure.

    The write path stays light: in PR1 we log structured JSON to stdout so
    operators can pipe to whatever sink they like (Better Stack, file). The
    DB write happens via the same MCP bridge pattern used elsewhere in the
    repo when the DSN env is set; absent that, the log line is the
    audit trail.
    """
    payload = {
        "agent": agent,
        "query_text": query_text[:QUERY_TEXT_LOG_CAP],
        "collections": list(collections),
        "k_initial": k_initial,
        "k_returned": k_returned,
        "elapsed_ms": elapsed_ms,
        "bypass_rerank": bypass_rerank,
        "top_citation_id": top_citation.source_id if top_citation else None,
        "top_score": round(top_citation.score, 3) if top_citation else None,
    }
    logger.info("retrieval_event %s", payload)
    dsn = os.environ.get("RETRIEVAL_EVENTS_DSN") or os.environ.get("DATABASE_URL")
    if not dsn:
        return
    try:
        import psycopg

        with (
            psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                """
                    INSERT INTO public.retrieval_events
                      (agent, query_text, collections, k_initial, k_returned,
                       elapsed_ms, bypass_rerank, top_citation_id, top_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                (
                    payload["agent"],
                    payload["query_text"],
                    payload["collections"],
                    payload["k_initial"],
                    payload["k_returned"],
                    payload["elapsed_ms"],
                    payload["bypass_rerank"],
                    payload["top_citation_id"],
                    payload["top_score"],
                ),
            )
    except Exception:  # noqa: BLE001
        logger.debug("retrieval_events insert failed (non-fatal)", exc_info=True)


def _node_to_citation(node: orchestrator.RetrievedNode) -> Citation:
    excerpt = node.text.strip().replace("\n", " ")[:EXCERPT_LEN]
    md = node.metadata or {}
    source_id = (
        md.get("source_id")
        or md.get("kei")
        or md.get("doc_id")
        or md.get("file_path")
        or f"{node.collection.lower()}:unknown"
    )
    return Citation(
        source_id=str(source_id),
        collection=node.collection,
        score=node.score,
        excerpt=excerpt,
        parent_path=str(md.get("parent_path") or ""),
    )


def _synthesise_answer(text: str, citations: tuple[Citation, ...], max_tokens: int) -> str:
    """PR1 synth: extractive — return the top citation's excerpt with
    source markers. LLM-driven synth (CitationQueryEngine.synthesise) is a
    follow-up KEI; PR1's job is "indexes test doc + queries + accurate
    result", which extractive answers meet.

    `max_tokens` is honoured via char-count approximation (4 chars ~= 1
    token); cap chars at max_tokens*4. This keeps the contract intact
    without LLM dependency in the hot path.
    """
    if not citations:
        return ""
    head = citations[0]
    char_cap = max_tokens * 4
    body = head.excerpt
    sources = ", ".join(f"[{c.source_id}]" for c in citations)
    answer = f"{body} (sources: {sources})"
    return answer[:char_cap]


def query(
    text: str,
    *,
    agent: str,
    collections: tuple[str, ...] = DEFAULT_COLLECTIONS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    citation_required: bool = True,
    min_score: float = DEFAULT_MIN_SCORE,
    k_initial: int = orchestrator.DEFAULT_K_INITIAL,
    k_returned: int = orchestrator.DEFAULT_K_RETURNED,
) -> QueryResult:
    """Run one retrieval query.

    Args:
        text: Natural-language query string.
        agent: Callsign of the asking agent — recorded for observability.
        collections: Which Weaviate collections to search (default 3-tuple
            covers the most common precision-retrieval surfaces).
        max_tokens: Response synthesis ceiling (KEI-55, 500-token default).
        citation_required: When True (default) and no citation passes
            `min_score`, return `answer=""` instead of synthesising.
        min_score: Floor for citation eligibility under
            `citation_required=True`.
        k_initial: ANN top-K per collection.
        k_returned: Citations returned (post-rank — raw ANN in PR1).

    Returns:
        `QueryResult` with answer + citations + elapsed_ms + bypass flag.
    """
    started = time.monotonic()
    nodes = orchestrator.retrieve_nodes(
        text=text,
        collections=collections,
        k_initial=k_initial,
        k_returned=k_returned,
    )
    citations = tuple(_node_to_citation(n) for n in nodes)
    qualified = tuple(c for c in citations if c.score >= min_score)
    if citation_required and not qualified:
        answer = ""
        emitted_citations: tuple[Citation, ...] = ()
    else:
        emitted_citations = qualified or citations
        answer = _synthesise_answer(text, emitted_citations, max_tokens)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    top = emitted_citations[0] if emitted_citations else None
    _record_event(
        agent=agent,
        query_text=text,
        collections=collections,
        k_initial=k_initial,
        k_returned=k_returned,
        elapsed_ms=elapsed_ms,
        bypass_rerank=orchestrator.RAW_ANN_RERANK_BYPASS,
        top_citation=top,
    )
    return QueryResult(
        answer=answer,
        citations=emitted_citations,
        elapsed_ms=elapsed_ms,
        bypass_rerank=orchestrator.RAW_ANN_RERANK_BYPASS,
    )
