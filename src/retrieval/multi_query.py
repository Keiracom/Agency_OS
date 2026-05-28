"""FILE: src/retrieval/multi_query.py
PURPOSE: Wave 4 — multi-query retrieval expansion.

Generates N alternative phrasings of the original query, searches each
against Hindsight, then merges and deduplicates results. Catches synonyms
and paraphrases the original phrasing misses.

Contract:
  * generate_variants(query, n=3) -> list[str]
        N alternative phrasings; fail-open — returns [query] on any error.
  * retrieve_multi(text, *, collections, k_initial, k_returned, tenant_id)
        Run one search per variant, merge + dedup by memory_id, re-rank by
        max score across variants, return a RetrievalOutcome.

Feature-flagged: RETRIEVAL_MULTI_QUERY_ENABLED (default False).
Fail-open: any generation error → [query] (original only), so a variant-
generation outage never degrades retrieval below the single-query baseline.

Cost note: uses the sync Anthropic SDK (one ~128-token Haiku call) routed
through the budget-tracked gateway via ANTHROPIC_BASE_URL. When the gateway
is not configured, _get_client() raises and generate_variants falls back to
[query] — no untracked direct call is ever made.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.retrieval import orchestrator as _orch

logger = logging.getLogger(__name__)

MULTI_QUERY_ENABLED_ENV = "RETRIEVAL_MULTI_QUERY_ENABLED"
ANTHROPIC_BASE_URL_ENV = "ANTHROPIC_BASE_URL"
DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_N_VARIANTS = 3
MAX_TOKENS = 128

_VARIANT_PROMPT = (
    "Generate {n} alternative phrasings of the search query below. "
    "Return ONLY the rephrased queries, one per line, no numbering, bullets, or explanations. "
    "Each phrasing must be semantically equivalent but use different words or structure. "
    "Query: {query}"
)


def multi_query_enabled() -> bool:
    """True when RETRIEVAL_MULTI_QUERY_ENABLED is set truthy (default off)."""
    return os.environ.get(MULTI_QUERY_ENABLED_ENV, "").lower() in {"1", "true", "yes"}


def _get_client() -> Any:
    """Lazily construct a sync Anthropic client routed through the gateway.

    Multi-query LLM calls MUST go through the budget-tracked gateway (set via
    ANTHROPIC_BASE_URL). Raises RuntimeError when the env var is unset so
    generate_variants can fall back without making an untracked direct call.
    (Passing base_url=None would silently default to the direct API — that is
    the exact failure mode this guard prevents.)
    """
    base_url = os.environ.get(ANTHROPIC_BASE_URL_ENV, "").strip()
    if not base_url:
        raise RuntimeError(
            f"{ANTHROPIC_BASE_URL_ENV} unset — refusing a direct/untracked Anthropic "
            "API call; multi-query routes through the budget-tracked gateway only"
        )
    import anthropic  # lazy: keep retrieval import light + SDK optional

    return anthropic.Anthropic(base_url=base_url)


def generate_variants(query: str, n: int = DEFAULT_N_VARIANTS) -> list[str]:
    """Return up to n alternative phrasings of query.

    Always includes the original query as the first element. On any error
    (missing gateway, LLM failure, parse failure) returns [query] so callers
    get at least single-query behaviour.
    """
    q = (query or "").strip()
    if not q:
        return [query] if query else [""]
    try:
        resp = _get_client().messages.create(
            model=DEFAULT_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": _VARIANT_PROMPT.format(n=n, query=q)}],
        )
        raw = ""
        for block in resp.content or []:
            text = getattr(block, "text", "")
            if text:
                raw = text.strip()
                break
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        variants = [v for v in lines if v and v != q][:n]
        return [q] + variants
    except Exception:  # noqa: BLE001 — never break retrieval
        logger.debug("multi_query variant generation failed — using original query", exc_info=True)
        return [q]


def _node_key(node: _orch.RetrievedNode) -> str:  # type: ignore[name-defined]
    """Stable dedup key for a retrieved node.

    Prefers explicit memory/chunk ID fields over text content so the same
    underlying memory is collapsed regardless of which variant query surfaced it.
    """
    md = node.metadata or {}
    explicit = (
        md.get("id")
        or md.get("memory_id")
        or md.get("source_id")
        or md.get("chunk_id")
        or md.get("doc_id")
    )
    if explicit:
        return f"{node.collection}:{explicit}"
    # Fall back to text fingerprint when no stable ID is present.
    return f"{node.collection}:{node.text[:120]}"


def merge_results(
    node_groups: list[tuple[_orch.RetrievedNode, ...]],  # type: ignore[name-defined]
) -> tuple[_orch.RetrievedNode, ...]:  # type: ignore[name-defined]
    """Merge node groups from multiple variant searches, dedup, re-rank by max score."""
    best: dict[str, Any] = {}
    for group in node_groups:
        for node in group:
            key = _node_key(node)
            if key not in best or node.score > best[key].score:
                best[key] = node
    return tuple(sorted(best.values(), key=lambda n: n.score, reverse=True))


def retrieve_multi(
    text: str,
    *,
    collections: tuple[str, ...],
    k_initial: int,
    k_returned: int,
    tenant_id: str,
) -> _orch.RetrievalOutcome:  # type: ignore[name-defined]
    """Run multi-query retrieval: generate variants, search each, merge+dedup.

    One orchestrator.retrieve_with_outcome call per variant. Results are
    merged, deduped by node_key, and re-ranked by max score across variants.
    The returned outcome carries the top k_returned nodes.

    Fail-open: if all variant searches fail, returns an empty RetrievalOutcome.
    """
    from src.retrieval import orchestrator

    variants = generate_variants(text)
    outcomes = []
    for variant in variants:
        try:
            outcome = orchestrator.retrieve_with_outcome(
                text=variant,
                collections=collections,
                k_initial=k_initial,
                k_returned=k_returned,
                tenant_id=tenant_id,
            )
            outcomes.append(outcome)
        except Exception:  # noqa: BLE001
            logger.debug("multi_query search failed for variant %r", variant, exc_info=True)
    if not outcomes:
        return orchestrator.RetrievalOutcome((), False, "multi_query_all_failed", 0)
    merged = merge_results([o.nodes for o in outcomes])
    bypass = any(o.bypass_rerank for o in outcomes)
    elapsed = sum(o.rerank_elapsed_ms for o in outcomes)
    return orchestrator.RetrievalOutcome(
        nodes=merged[:k_returned],
        bypass_rerank=bypass,
        rerank_reason="multi_query_merged",
        rerank_elapsed_ms=elapsed,
    )
