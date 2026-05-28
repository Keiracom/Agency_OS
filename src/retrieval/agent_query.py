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

from src.retrieval import multi_query, orchestrator

logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS: tuple[str, ...] = ("Discoveries", "Decisions", "Keis")
DEFAULT_MAX_TOKENS = 500  # KEI-55 ceiling
DEFAULT_MIN_SCORE = 0.50  # KEI-198: now a SOFT signal, not a hard filter (kept for backward compat callers passing explicit values)
# KEI-198: when ALL returned scores are exactly 0.0, treat it as a vectorizer-regression sentinel.
# We log a warning + tag the retrieval event but STILL return the top-N citations so the caller
# gets non-empty results. This is the defensive replacement for the prior hard min_score gate
# that filtered everything out when scores collapsed to 0.0 (KEI-192 audit finding).
_ZERO_SCORE_SENTINEL = 0.0
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
    # KEI-103: Supabase pooler DSN often comes as `postgresql+asyncpg://...`
    # but psycopg3 only parses `postgresql://`. Strip the dialect tag here so
    # the INSERT actually fires; without this, _record_event silently no-ops
    # and retrieval_events stays at 0 (memory: reference_psycopg_supabase_pgbouncer).
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
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
    # KEI-75: prefer specific identifiers (chunk_id, source_path, explicit
    # source_id) over the umbrella `kei` tag. The old ordering hoisted
    # md.get('kei') above source_path, which made every citation read
    # 'KEI-73' on the Wave 3 corpus and 'discoveries:unknown' on chunks
    # without a tag — neither points the operator at the doc that actually
    # matched.
    source_id = (
        md.get("source_id")
        or md.get("chunk_id")
        or md.get("source_path")
        or md.get("file_path")
        or md.get("doc_id")
        or md.get("kei")
        or f"{node.collection.lower()}:unknown"
    )
    return Citation(
        source_id=str(source_id),
        collection=node.collection,
        score=node.score,
        excerpt=excerpt,
        parent_path=str(md.get("parent_path") or md.get("section") or ""),
    )


def _synthesise_answer(citations: tuple[Citation, ...], max_tokens: int) -> str:
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
    min_score: float = DEFAULT_MIN_SCORE,  # noqa: ARG001 KEI-198 back-compat  # NOSONAR S1172
    k_initial: int = orchestrator.DEFAULT_K_INITIAL,
    k_returned: int = orchestrator.DEFAULT_K_RETURNED,
    tenant_id: str = orchestrator.FLEET_TENANT_SLUG,
) -> QueryResult:
    """Run one retrieval query.

    Args:
        text: Natural-language query string.
        agent: Callsign of the asking agent — recorded for observability.
        collections: Which Weaviate collections to search (default 3-tuple
            covers the most common precision-retrieval surfaces).
        tenant_id: Hindsight tenant slug for the recall URL. Defaults to
            `orchestrator.FLEET_TENANT_SLUG` because this entry is the
            fleet-internal recall API; customer-facing recall goes through
            the Decision/Artifact/TaskContext/AntiPattern wrappers in
            src/keiracom_system/memory/wrappers/, which derive the slug
            from the tenant_id arg per-call. The orchestrator wire boundary
            (`_hindsight_recall`) still validates and rejects empty/invalid
            values via `MissingTenantContextError` — audit fix YELLOW-4
            (Agency_OS-7sj6, 2026-05-28).
        max_tokens: Response synthesis ceiling (KEI-55, 500-token default).
        citation_required: When True (default) AND all returned scores are
            exactly 0.0 (vectorizer-regression sentinel per KEI-198), return
            `answer=""`. Mixed / non-zero score sets ALWAYS surface top-N
            regardless of absolute value.
        min_score: DEPRECATED in KEI-198 — retained for back-compat but
            no-op'd. The prior hard score-floor (default 0.50) excluded all
            citations when Weaviate vectorizer=none collapsed scores to 0.0
            (KEI-192 audit). Callers passing explicit values get the new
            distribution-aware top-N selection regardless of the value.
        k_initial: ANN top-K per collection.
        k_returned: Citations returned (post-rank — top-N sorted by score).

    Returns:
        `QueryResult` with answer + citations + elapsed_ms + bypass flag.
    """
    started = time.monotonic()
    # Multi-query expansion (Wave 4, RETRIEVAL_MULTI_QUERY_ENABLED, default off).
    # Generates N query variants and merges+deduplicates results by memory_id.
    # Fail-open: falls back to single-query when flag is off or generation fails.
    if multi_query.multi_query_enabled():
        outcome = multi_query.retrieve_multi(
            text=text,
            collections=collections,
            k_initial=k_initial,
            k_returned=k_returned,
            tenant_id=tenant_id,
        )
    else:
        outcome = orchestrator.retrieve_with_outcome(
            text=text,
            collections=collections,
            k_initial=k_initial,
            k_returned=k_returned,
            tenant_id=tenant_id,
        )
    citations = [_node_to_citation(n) for n in outcome.nodes]
    # KEI-198 — distribution-aware citation selection.
    # OLD shape (pre-KEI-192 audit): hard `score >= min_score` filter excluded
    # everything when vectorizer=none collapsed all scores to 0.0 — 12/14 of the
    # session's retrieval_events landed with top_citation_id=NULL despite
    # k_returned=5 nodes.
    # NEW shape: always sort + slice top-N; only drop on the all-zero sentinel
    # when caller explicitly opted in via citation_required=True.
    top_n: tuple[Citation, ...] = tuple(
        sorted(citations, key=lambda c: c.score, reverse=True)[:k_returned]
    )
    all_zero = bool(top_n) and all(c.score == _ZERO_SCORE_SENTINEL for c in top_n)
    if all_zero:
        logger.warning(
            "retrieval scores all 0.0 — vectorizer-regression sentinel (KEI-198) "
            "agent=%s text=%s collections=%s",
            agent,
            text[:QUERY_TEXT_LOG_CAP],
            collections,
        )
    if citation_required and all_zero:
        answer = ""
        emitted_citations: tuple[Citation, ...] = ()
    else:
        emitted_citations = top_n
        answer = _synthesise_answer(emitted_citations, max_tokens) if top_n else ""
    elapsed_ms = int((time.monotonic() - started) * 1000)
    top = emitted_citations[0] if emitted_citations else None
    _record_event(
        agent=agent,
        query_text=text,
        collections=collections,
        k_initial=k_initial,
        k_returned=k_returned,
        elapsed_ms=elapsed_ms,
        bypass_rerank=outcome.bypass_rerank,
        top_citation=top,
    )
    return QueryResult(
        answer=answer,
        citations=emitted_citations,
        elapsed_ms=elapsed_ms,
        bypass_rerank=outcome.bypass_rerank,
    )
