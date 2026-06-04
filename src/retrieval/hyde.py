"""FILE: src/retrieval/hyde.py
PURPOSE: Wave 4 — HyDE (Hypothetical Document Embeddings) query expansion.

HyDE improves recall by searching with a hypothetical *answer* rather than
the raw question. We generate a one-paragraph hypothetical document that
would answer the query, then fuse it with the original query text. That
fused text is what flows to the retrieval backend.

Embedding-path note: the live read path (orchestrator._hindsight_recall)
sends QUERY TEXT to Hindsight, which embeds it server-side — the client
does not compute a search vector. So HyDE here operates at the text level:
the hypothetical becomes part of the `query` text and is embedded by the
*same* server-side path as every normal query. This is the faithful HyDE
realisation for a text-in retrieval backend.

Contract:
  * generate_hypothetical(query, model='governance_tier_fast') -> str
        One-paragraph hypothetical answer document; "" on any error.
  * expand_query(query, model=...) -> str
        The search text: raw query fused with the hypothetical when HyDE is
        enabled AND generation succeeds; the raw query otherwise.

Feature-flagged: RETRIEVAL_HYDE_ENABLED (default False).
Fail-open: any generation error → fall back to the original query, so a
HyDE outage never degrades retrieval below the pre-HyDE baseline.

Cost note: uses the sync Anthropic SDK (a single short Haiku call) to match
the synchronous retrieval entry point, but routed through the budget-tracked
gateway via ANTHROPIC_BASE_URL (Aiden HOLD, PR #1243). When the gateway is
not configured, generation fails open to the raw query rather than making an
untracked pay-as-you-go API call the budget-ceiling gate cannot see.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

HYDE_ENABLED_ENV = "RETRIEVAL_HYDE_ENABLED"
# Routes through the LiteLLM governance-tier proxy alias (gate_roadmap
# litellm_routing cb31edd9, C3). The proxy serves only governance_tier_{fast,
# premium}; the prior 'claude-haiku-4-5' literal had no model group there and
# 400'd on every routed call. governance_tier_fast → openai/gpt-4o-mini.
DEFAULT_MODEL = "governance_tier_fast"
MAX_TOKENS = 256

_HYDE_PROMPT = (
    "Write a single concise paragraph that could plausibly answer the question "
    "below, as if excerpted from an internal engineering document. Write it as a "
    "confident factual passage — do not hedge, do not say you are unsure, do not "
    "restate the question. Question: {query}"
)


def hyde_enabled() -> bool:
    """True when the RETRIEVAL_HYDE_ENABLED flag is set truthy (default off)."""
    return os.environ.get(HYDE_ENABLED_ENV, "").lower() in {"1", "true", "yes"}


ANTHROPIC_BASE_URL_ENV = "ANTHROPIC_BASE_URL"


def _get_client() -> Any:
    """Lazily construct a sync Anthropic client routed through the gateway.

    HyDE LLM calls MUST go through the budget-tracked gateway (set via
    ANTHROPIC_BASE_URL), never the pay-as-you-go API directly — an untracked
    direct call is invisible to the budget-ceiling gate (Aiden HOLD, PR #1243).

    Raises RuntimeError when ANTHROPIC_BASE_URL is unset; generate_hypothetical
    catches it and falls back to the raw query, so no untracked call is ever
    made. (Passing base_url=None would silently default to the direct API —
    that is the exact failure mode this guard prevents.)
    """
    base_url = os.environ.get(ANTHROPIC_BASE_URL_ENV, "").strip()
    if not base_url:
        raise RuntimeError(
            f"{ANTHROPIC_BASE_URL_ENV} unset — refusing a direct/untracked Anthropic "
            "API call; HyDE routes through the budget-tracked gateway only"
        )
    import anthropic  # lazy: keep retrieval import light + SDK optional

    return anthropic.Anthropic(base_url=base_url)


def generate_hypothetical(query: str, model: str = DEFAULT_MODEL) -> str:
    """Generate a one-paragraph hypothetical answer document for `query`.

    Returns "" on empty input or any error (fail-open) so callers can fall
    back to the raw query embedding path.
    """
    q = (query or "").strip()
    if not q:
        return ""
    try:
        resp = _get_client().messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": _HYDE_PROMPT.format(query=q)}],
        )
        for block in resp.content or []:
            text = getattr(block, "text", "")
            if text:
                return text.strip()
        return ""
    except Exception:  # noqa: BLE001 — HyDE must never break retrieval
        logger.debug("HyDE generation failed — falling back to raw query", exc_info=True)
        return ""


def expand_query(query: str, model: str = DEFAULT_MODEL) -> str:
    """Return the text to search with.

    When HyDE is enabled and generation succeeds, returns the raw query fused
    with the hypothetical document — the original query signal is retained so
    both ANN recall and downstream rerank stay anchored to what was asked.
    Returns the raw query unchanged when HyDE is disabled or generation fails.
    """
    if not hyde_enabled():
        return query
    hypothetical = generate_hypothetical(query, model=model)
    if not hypothetical:
        return query
    return f"{query}\n\n{hypothetical}"
